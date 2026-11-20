"""Release handling for the Treeline deploy agent (runs as root; standard library only).

A release is a signed tarball. The signature is checked with `ssh-keygen -Y verify` against
/etc/treeline/release_signers, a file the installer wrote and no release can replace. Nothing from a tarball is
unpacked, executed or even listed before its signature has verified.
"""

import json
import os
import re
import shutil
import subprocess
import tarfile

import treeline_common as common

NAMESPACE = "treeline-release"
IDENTITY = "treeline-release"
VERSION_RE = re.compile(r"^v\d+\.\d+\.\d+(-[a-z0-9.]+)?$")
MAX_MEMBERS = 20000
MAX_BYTES = 400 * 1024 * 1024


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


def read_info(release_dir):
    try:
        with open(os.path.join(release_dir, "release.json"), encoding="utf-8") as f:
            info = json.load(f)
    except (OSError, ValueError) as err:
        raise ReleaseError(f"release.json is missing or unreadable: {err}") from err
    if not VERSION_RE.match(str(info.get("version", ""))):
        raise ReleaseError("release.json has no valid version")
    schema = info.get("schema") or {}
    if not all(isinstance(schema.get(k), int) and schema[k] >= 1 for k in ("central", "household")):
        raise ReleaseError("release.json has no schema versions")
    return info


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
