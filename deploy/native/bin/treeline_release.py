"""Release handling for the Treeline deploy agent (runs as root; standard library only).

A release is a signed tarball. The signature is checked with `ssh-keygen -Y verify` against
/etc/treeline/release_signers, a file the installer wrote and no release can replace. Nothing from a tarball is
unpacked, executed or even listed before its signature has verified.
"""

import hashlib
import io
import json
import os
import re
import shutil
import stat
import struct
import subprocess
import tarfile

import treeline_common as common

NAMESPACE = "treeline-release"
IDENTITY = "treeline-release"
VERSION_RE = re.compile(r"^v\d+\.\d+\.\d+(-[a-z0-9.]+)?$")
MAX_MEMBERS = 20000
MAX_BYTES = 400 * 1024 * 1024
FORMAT = 2                                   # release.json "format": 2 carries an Asterisk build (1 did not, and is refused)
ASTERISK_ID_RE = re.compile(r"\d+\.\d+\.\d+-[tx]\d+")   # -t<n> is a real build (asterisk/build), -x<n> a test repack
SHA256_RE = re.compile(r"[0-9a-f]{64}")
TEST_ID_RE = re.compile(r".*-x\d+")           # ids a test makes by repacking the real build: never accepted on a real install. The real build's ids (-t<n>, any n: t9, t90...) cannot be mistaken for these, and scripts/asterisk_build.py refuses -x for BUILD_ID
ASTERISK_MAX_BYTES = 64 * 1024 * 1024        # the real artifact is about 10 MB unpacked
ASTERISK_MAX_MEMBERS = 500                   # and about 60 members
ASTERISK_SOUNDS_LINK = "/usr/share/asterisk/sounds"   # where the operator messages are built; linked into each build's data dir


class ReleaseError(Exception):
    pass


def signers_file(etc=None):
    return os.path.join(etc or common.ETC, "release_signers")


def has_signer(path):
    """True if the file holds at least one real key line (not just comments)."""
    try:
        with open(path, encoding="utf-8") as f:
            return any(l.strip() and not l.lstrip().startswith("#") and (" ssh-" in l or " sk-ssh-" in l) for l in f)
    except FileNotFoundError:
        return False


def private_copy(path, directory):
    """Copy `path` once into `directory` (a folder only root can write) and return the copy's path. The signature is checked on the
    copy and the copy is what is unpacked, so a file that changes between the check and the unpack (a --tarball in a folder somebody
    else can write, R10-7) cannot become unsigned content. A link is refused, not followed; only a plain file is copied."""
    os.makedirs(directory, mode=0o700, exist_ok=True)
    dest = os.path.join(directory, os.path.basename(path) or "file")
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError as err:
        raise ReleaseError(f"cannot open {path}: {err}") from err
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        raise ReleaseError(f"{path} is not a plain file")
    with os.fdopen(fd, "rb") as src:
        out = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        with os.fdopen(out, "wb") as dst:
            shutil.copyfileobj(src, dst, 1 << 20)
    return dest


def verify(tarball, sig, signers):
    """Raise ReleaseError unless `sig` is a valid signature of `tarball` by a key in `signers`."""
    if not has_signer(signers):
        raise ReleaseError(f"{signers} holds no signing key; refusing to trust any release")
    if not os.path.isfile(sig):
        raise ReleaseError(f"no signature file {sig}")
    with open(tarball, "rb") as f:
        done = subprocess.run(["ssh-keygen", "-Y", "verify", "-f", signers, "-I", IDENTITY, "-n", NAMESPACE, "-s", sig],
                              stdin=f, capture_output=True, text=True)
    if done.returncode != 0:
        raise ReleaseError("signature check FAILED: " + (done.stderr.strip() or done.stdout.strip() or "unknown reason"))


def extract(tarball, dest):
    """Unpack into `dest` (which must not exist), refusing absolute paths, links out of the tree, devices, and bombs."""
    if os.path.exists(dest):
        raise ReleaseError(f"{dest} already exists")
    os.makedirs(dest, mode=0o755)
    try:
        with tarfile.open(tarball, "r:gz") as tf:
            members = tf.getmembers()
            if len(members) > MAX_MEMBERS or sum(m.size for m in members) > MAX_BYTES:
                raise ReleaseError("the release is implausibly large")
            for m in members:       # a real release never has these; the "data" filter would quietly rewrite them
                if m.name.startswith("/") or ".." in m.name.split("/"):
                    raise ReleaseError(f"unsafe path in the release: {m.name!r}")
            tf.extractall(dest, members=members, filter="data")
    except (tarfile.TarError, OSError) as err:
        shutil.rmtree(dest, ignore_errors=True)
        raise ReleaseError(f"could not unpack the release: {err}") from err
    except BaseException:
        shutil.rmtree(dest, ignore_errors=True)
        raise
    return dest


def read_info(release_dir, ci=False):
    """The release's own description. Format 2 is required: it names the Asterisk build the release carries."""
    try:
        with open(os.path.join(release_dir, "release.json"), encoding="utf-8") as f:
            info = json.load(f)
    except (OSError, ValueError) as err:
        raise ReleaseError(f"release.json is missing or unreadable: {err}") from err
    if not isinstance(info, dict):
        raise ReleaseError("release.json is not an object")
    if not VERSION_RE.match(str(info.get("version", ""))):
        raise ReleaseError("release.json has no valid version")
    schema = info.get("schema") or {}
    if not all(isinstance(schema.get(k), int) and schema[k] >= 1 for k in ("central", "household")):
        raise ReleaseError("release.json has no schema versions")
    fmt = info.get("format")
    if type(fmt) is not int or fmt != FORMAT:
        raise ReleaseError(f"this release is format {fmt!r}; this agent only installs format {FORMAT} (a release that carries "
                           "its own Asterisk). Nothing on this machine was changed. Install a newer release, or re-run install.sh "
                           "from one to update the tools.")
    ast = info.get("asterisk")
    if not isinstance(ast, dict) or set(ast) != {"id", "sha256"}:
        raise ReleaseError("release.json names no Asterisk build (it needs asterisk: {id, sha256})")
    if not isinstance(ast["id"], str) or not ASTERISK_ID_RE.fullmatch(ast["id"]):
        raise ReleaseError("release.json has an invalid Asterisk build id")
    if not isinstance(ast["sha256"], str) or not SHA256_RE.fullmatch(ast["sha256"]):
        raise ReleaseError("release.json has an invalid Asterisk sha256")
    if TEST_ID_RE.fullmatch(ast["id"]) and not ci:
        raise ReleaseError(f"Asterisk build id {ast['id']} is a test id and is refused outside the CI job")
    return info


# ---------------------------------------------------------------- the Asterisk build inside a release
def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def read_asterisk_artifact(release_dir, info):
    """The nested artifact's bytes, read ONCE from a sealed release directory and hashed as read: what is checked is exactly
    what is then unpacked. Any other file under asterisk/runtime/ is refused."""
    ast = info["asterisk"]
    runtime = os.path.join(release_dir, "asterisk", "runtime")
    want = f"asterisk-{ast['id']}.tar.gz"
    try:
        found = sorted(os.listdir(runtime))
    except OSError as err:
        raise ReleaseError(f"the release has no asterisk/runtime/: {err}") from err
    if found != [want]:
        raise ReleaseError(f"asterisk/runtime/ must hold exactly {want}, not {found}")
    try:
        fd = os.open(os.path.join(runtime, want), os.O_RDONLY | os.O_NOFOLLOW)
    except OSError as err:
        raise ReleaseError(f"cannot open the Asterisk artifact (a link, or missing): {err}") from err
    with os.fdopen(fd, "rb") as f:
        st = os.fstat(f.fileno())
        if not stat.S_ISREG(st.st_mode) or st.st_size > ASTERISK_MAX_BYTES:
            raise ReleaseError("the Asterisk artifact is not a regular file of a plausible size")
        data = f.read(ASTERISK_MAX_BYTES + 1)
    if len(data) > ASTERISK_MAX_BYTES:
        raise ReleaseError("the Asterisk artifact is larger than allowed")
    if _sha256(data) != ast["sha256"]:
        raise ReleaseError("the Asterisk artifact does not match the sha256 in release.json")
    return data


def _safe_symlink(name, linkname, names):
    """A link is allowed only to a sibling in the same directory (as libasteriskpj.so -> libasteriskpj.so.2 is)."""
    if not linkname or "/" in linkname or linkname in (".", "..") or "\0" in linkname:
        return False
    return (os.path.dirname(name) + "/" + linkname).lstrip("/") in names


def asterisk_archive(data, ast_id):
    """Validate the artifact's tar and return {relative path: entry}: entry is ("d", mode), ("f", mode, sha256, bytes) or
    ("l", target). Paths are relative to /opt/asterisk/<id>. Raises ReleaseError for anything that is not exactly the plain
    tree a build produces: absolute or `..` names, hard links, devices, set-id or group/other-writable entries, duplicates,
    links to anything but a sibling, names that go through a link, or too many or too large members."""
    prefix = f"opt/asterisk/{ast_id}"
    try:
        tf = tarfile.open(fileobj=io.BytesIO(data), mode="r:gz")
        members = tf.getmembers()
    except (tarfile.TarError, OSError, EOFError) as err:
        raise ReleaseError(f"the Asterisk artifact cannot be read: {err}") from err
    if len(members) > ASTERISK_MAX_MEMBERS or sum(m.size for m in members) > ASTERISK_MAX_BYTES:
        raise ReleaseError("the Asterisk artifact is implausibly large")
    names = {m.name.rstrip("/") for m in members}
    seen, entries, links = set(), {}, set()
    for m in members:
        name = m.name.rstrip("/")
        if name in seen:
            raise ReleaseError(f"the Asterisk artifact lists {name!r} twice")
        seen.add(name)
        parts = name.split("/")
        if name.startswith("/") or ".." in parts or "." in parts or "" in parts or any(ord(c) < 32 or c == "\\" for c in name):
            raise ReleaseError(f"unsafe path in the Asterisk artifact: {name!r}")
        if name != prefix and not name.startswith(prefix + "/"):
            raise ReleaseError(f"{name!r} is outside {prefix}/")
        if not m.issym() and (m.mode & 0o7000 or m.mode & 0o022):      # a link's own mode is meaningless (tar records 0777)
            raise ReleaseError(f"{name!r} has set-id, sticky or group/other-write permissions")
        rel = name[len(prefix):].lstrip("/")
        if any(rel.startswith(l + "/") for l in links):
            raise ReleaseError(f"{name!r} is inside a link")
        if m.isdir():
            entries[rel] = ("d", 0o755)
        elif m.isreg():
            blob = tf.extractfile(m).read()
            entries[rel] = ("f", 0o755 if m.mode & 0o111 else 0o644, _sha256(blob), blob)
        elif m.issym():
            if not _safe_symlink(name, m.linkname, names):
                raise ReleaseError(f"{name!r} is a link to {m.linkname!r}, which is not a sibling in the artifact")
            entries[rel] = ("l", m.linkname)
            links.add(rel)
        else:
            raise ReleaseError(f"{name!r} is a hard link, device or other special file")
    for rel in ("sbin/asterisk", "sbin/rasterisk", "lib/asterisk/modules", "share/asterisk/rest-api", "share/asterisk/documentation"):
        if rel not in entries:
            raise ReleaseError(f"the Asterisk artifact has no {rel}")
    return entries


def asterisk_expected(entries):
    """What a correct tree looks like, as {path: signature}: the archive plus the one link root adds (the operator messages)."""
    want = {"": ("d", 0o755)}
    for rel, e in entries.items():
        want[rel] = e[:2] if e[0] == "d" else (("f", e[1], e[2]) if e[0] == "f" else ("l", e[1]))
    want["share/asterisk/sounds"] = ("l", ASTERISK_SOUNDS_LINK)
    return want


def tree_actual(root):
    """The same shape of dict for what is on disk, by lstat: nothing is followed, every file is hashed."""
    got = {}
    me = os.geteuid()
    for base, dirs, files in os.walk(root, followlinks=False):
        for name in sorted(dirs) + sorted(files):
            full = os.path.join(base, name)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            st = os.lstat(full)
            if st.st_uid != me:
                got[rel] = ("owner", st.st_uid)
            elif stat.S_ISLNK(st.st_mode):
                got[rel] = ("l", os.readlink(full))
            elif stat.S_ISDIR(st.st_mode):
                got[rel] = ("d", stat.S_IMODE(st.st_mode))
            elif stat.S_ISREG(st.st_mode):
                with open(full, "rb") as f:
                    got[rel] = ("f", stat.S_IMODE(st.st_mode), _sha256(f.read()))
            else:
                got[rel] = ("special", stat.S_IFMT(st.st_mode))
    st = os.lstat(root)
    got[""] = ("d", stat.S_IMODE(st.st_mode)) if stat.S_ISDIR(st.st_mode) and st.st_uid == me else ("owner", st.st_uid)
    return got


def verify_asterisk_tree(tree, release_dir, info, ci=False):
    """Raise ReleaseError unless `tree` (a directory under /opt/asterisk) is exactly what this release's artifact makes:
    every path, mode, link and file hash. Used before anything is stopped, switched or trusted."""
    ast = info["asterisk"]
    entries = asterisk_archive(read_asterisk_artifact(release_dir, info), ast["id"])
    want, got = asterisk_expected(entries), tree_actual(tree)
    if want != got:
        extra = sorted(set(got) - set(want))[:3]
        missing = sorted(set(want) - set(got))[:3]
        changed = sorted(k for k in set(want) & set(got) if want[k] != got[k])[:3]
        raise ReleaseError(f"{tree} is not what the release's Asterisk build makes (extra {extra}, missing {missing}, changed {changed})")
    return True


def install_asterisk(release_dir, opt=None, ci=False):
    """Install the release's Asterisk build under /opt/asterisk/<id>, from the sealed release directory only.

    The artifact's bytes are read once and hashed as read (read_asterisk_artifact), validated (asterisk_archive), unpacked into a
    fresh staging directory by our own code (no tarfile extraction), given the one link root adds, sealed, and renamed into
    place. An existing /opt/asterisk/<id> is trusted only after every path and hash in it matches. Returns True if this call
    made the directory."""
    opt = opt or common.ASTERISK_OPT
    info = read_info(release_dir, ci=ci)
    ast_id = info["asterisk"]["id"]
    entries = asterisk_archive(read_asterisk_artifact(release_dir, info), ast_id)
    final = os.path.join(opt, ast_id)
    if os.path.lexists(final):
        verify_asterisk_tree(final, release_dir, info, ci=ci)         # same id, different bytes: refused here
        return False
    os.makedirs(opt, mode=0o755, exist_ok=True)
    staging = os.path.join(opt, f".staging-{os.getpid()}")
    if os.path.lexists(staging):
        raise ReleaseError(f"{staging} exists (a leftover; it is swept under the deploy lock)")
    os.mkdir(staging, 0o755)
    try:
        for rel in sorted(entries):                                   # directories first, so every file has its parent
            if rel and entries[rel][0] == "d":
                os.makedirs(os.path.join(staging, rel), mode=0o755, exist_ok=True)
        for rel in sorted(entries):
            e = entries[rel]
            if not rel or e[0] == "d":
                continue
            dest = os.path.join(staging, rel)
            os.makedirs(os.path.dirname(dest), mode=0o755, exist_ok=True)
            if e[0] == "f":
                fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                with os.fdopen(fd, "wb") as f:
                    f.write(e[3])
                    f.flush()
                    os.fsync(f.fileno())
                os.chmod(dest, e[1])
        for rel in sorted(entries):                                   # links last, once every sibling exists
            e = entries[rel]
            if e[0] == "l":
                os.symlink(e[1], os.path.join(staging, rel))
        os.symlink(ASTERISK_SOUNDS_LINK, os.path.join(staging, "share", "asterisk", "sounds"))
        os.chmod(staging, 0o755)
        if os.geteuid() == 0:
            seal(staging)
        os.rename(staging, final)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return True


def sweep_asterisk(opt=None, keep=()):
    """Under the deploy lock only: remove leftovers of an interrupted install and every build not named in `keep`
    (renamed to a trash name first, so a crash leaves a name that cannot be mistaken for a build)."""
    opt = opt or common.ASTERISK_OPT
    removed = []
    try:
        names = sorted(os.listdir(opt))
    except FileNotFoundError:
        return removed
    for name in names:
        full = os.path.join(opt, name)
        if name.startswith((".staging-", ".trash-")) or (ASTERISK_ID_RE.fullmatch(name) and name not in keep):
            trash = os.path.join(opt, f".trash-{os.getpid()}-{name.lstrip('.')}")
            if name.startswith(".trash-"):
                trash = full
            else:
                os.rename(full, trash)
            shutil.rmtree(trash, ignore_errors=True)
            removed.append(name)
    return removed


def sweep_leftovers(opt=None):
    """Under the deploy lock only: remove what an interrupted install or prune left (.staging-* and .trash-*), and nothing else."""
    opt = opt or common.ASTERISK_OPT
    removed = []
    try:
        names = sorted(os.listdir(opt))
    except FileNotFoundError:
        return removed
    for name in names:
        if name.startswith((".staging-", ".trash-")):
            shutil.rmtree(os.path.join(opt, name), ignore_errors=True)
            removed.append(name)
    return removed


def release_asterisk_id(release_dir):
    """The Asterisk build id a release directory carries, or None if it cannot be read (an old format, a damaged file)."""
    try:
        return read_info(release_dir, ci=True)["asterisk"]["id"]
    except ReleaseError:
        return None


# ---------------------------------------------------------------- reading ELF files without running anything
def elf_dynamic(path):
    """{needed, runpath, rpath, interp} of a 64-bit little-endian ELF, read from its headers. Nothing is executed (ldd can
    run the file it inspects)."""
    with open(path, "rb") as f:
        data = f.read()
    if data[:4] != b"\x7fELF" or data[4] != 2 or data[5] != 1:
        raise ReleaseError(f"{path} is not a 64-bit little-endian ELF file")
    phoff, = struct.unpack_from("<Q", data, 0x20)
    phentsize, phnum = struct.unpack_from("<HH", data, 0x36)
    loads, dyn, interp = [], None, None
    for i in range(phnum):
        ptype, _flags, off, vaddr, _paddr, filesz, _memsz, _align = struct.unpack_from("<IIQQQQQQ", data, phoff + i * phentsize)
        if ptype == 1:
            loads.append((vaddr, off, filesz))
        elif ptype == 2:
            dyn = (off, filesz)
        elif ptype == 3:
            interp = data[off:off + filesz].split(b"\0")[0].decode()
    out = {"needed": [], "runpath": [], "rpath": [], "interp": interp}
    if dyn is None:
        return out

    def file_offset(vaddr):
        for va, off, size in loads:
            if va <= vaddr < va + size:
                return off + vaddr - va
        raise ReleaseError(f"{path} has a dynamic table pointing outside the file")

    tags, strtab = [], None
    for off in range(dyn[0], dyn[0] + dyn[1], 16):
        tag, val = struct.unpack_from("<qQ", data, off)
        if tag == 0:
            break
        tags.append((tag, val))
        if tag == 5:
            strtab = file_offset(val)
    if strtab is None and tags:
        raise ReleaseError(f"{path} has no string table")

    def text(val):
        end = data.index(b"\0", strtab + val)
        return data[strtab + val:end].decode()
    for tag, val in tags:
        if tag == 1:
            out["needed"].append(text(val))
        elif tag == 29:
            out["runpath"] += text(val).split(":")
        elif tag == 15:
            out["rpath"] += text(val).split(":")
    return out


def check_elf_needs(tree, ast_id, system_dirs=("/lib/x86_64-linux-gnu", "/usr/lib/x86_64-linux-gnu")):
    """Every ELF in the build: no RPATH; RUNPATH either absent or exactly /opt/asterisk/<id>/lib (no $ORIGIN, nothing
    relative); no library named by a path; every library it needs either in the build's lib/ or installed on the system."""
    lib = os.path.join(tree, "lib")
    local = {n for n in os.listdir(lib)} if os.path.isdir(lib) else set()
    want_run = [f"/opt/asterisk/{ast_id}/lib"]
    problems = []
    for base, _dirs, files in os.walk(tree, followlinks=False):
        for name in sorted(files):
            full = os.path.join(base, name)
            if os.path.islink(full) or not os.path.isfile(full):
                continue
            with open(full, "rb") as f:
                if f.read(4) != b"\x7fELF":
                    continue
            rel = os.path.relpath(full, tree)
            try:
                d = elf_dynamic(full)
            except (struct.error, ValueError, IndexError, UnicodeDecodeError) as err:   # R10-8: a short or damaged ELF is a refusal, not a traceback
                raise ReleaseError(f"{rel} is not a readable ELF file: {err}") from err
            if d["rpath"]:
                problems.append(f"{rel} has an RPATH")
            if d["runpath"] and d["runpath"] != want_run:
                problems.append(f"{rel} has RUNPATH {d['runpath']}, not {want_run}")
            if d["interp"] and d["interp"] not in ("/lib64/ld-linux-x86-64.so.2",):
                problems.append(f"{rel} names an unexpected interpreter {d['interp']}")
            for need in d["needed"]:
                if "/" in need:
                    problems.append(f"{rel} needs a library named by a path: {need}")
                elif need not in local and not any(os.path.exists(os.path.join(sd, need)) for sd in system_dirs):
                    problems.append(f"{rel} needs {need}, which is neither in the build nor installed")
    if problems:
        raise ReleaseError("; ".join(problems[:5]))


def build_venv(release_dir, python="/usr/bin/python3"):
    """A virtual environment for this release, from the hash-pinned lock (never an unpinned install)."""
    lock = os.path.join(release_dir, "controller", "requirements-prod.lock")
    if not os.path.isfile(lock):
        raise ReleaseError("the release has no requirements-prod.lock")
    venv = os.path.join(release_dir, "venv")
    for cmd in ([python, "-m", "venv", venv],
                [os.path.join(venv, "bin", "pip"), "install", "--quiet", "--disable-pip-version-check", "--no-cache-dir",
                 "--require-hashes", "--no-deps", "-r", lock],
                [os.path.join(venv, "bin", "python"), "-m", "compileall", "-q", os.path.join(release_dir, "controller")]):
        done = subprocess.run(cmd, capture_output=True, text=True)
        if done.returncode != 0:
            raise ReleaseError(f"{' '.join(cmd[:3])} failed: {done.stderr.strip()[-400:]}")
    return venv


def seal(release_dir):
    """Root-owned, not writable by anyone else: the services run as `treeline` and must not be able to change the code."""
    subprocess.run(["chown", "-R", "root:root", release_dir], check=True)
    subprocess.run(["chmod", "-R", "u=rwX,go=rX", release_dir], check=True)


def switch(link, release_dir):
    """Point `link` at `release_dir` atomically (a symlink created beside it, then renamed over it)."""
    tmp = link + ".new"
    if os.path.lexists(tmp):
        os.remove(tmp)
    os.symlink(release_dir, tmp)
    os.replace(tmp, link)


def current(link):
    try:
        return os.path.realpath(link) if os.path.islink(link) else None
    except OSError:
        return None
