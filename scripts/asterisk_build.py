#!/usr/bin/env python3
"""Checks for asterisk/build/ (the pinned Asterisk build, asterisk/build/README.md). Standard library only.

  python3 scripts/asterisk_build.py check                      sources.lock is well formed; artifact.lock (if any) agrees
  python3 scripts/asterisk_build.py write-lock ARTIFACT.tar.gz  write artifact.lock for a built artifact

artifact.lock names the artifact that production runs (its sha256 and size) and holds a digest of every other file in
asterisk/build/. A change to build.sh, modules.txt, sources.lock, the Dockerfile or anything else there therefore fails
`check` until a new artifact has been built from the new tree and its hash recorded: the lock can never describe bytes
that were built by different instructions than the ones in the repository.
"""
import hashlib
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "asterisk", "build")
KEY = re.compile(r"^[A-Z][A-Z0-9_]*$")
HEX = lambda n: re.compile(r"^[0-9a-f]{%d}$" % n)
FPR = re.compile(r"^[0-9A-F]{40}$")
SOURCES_FIELDS = {
    "ASTERISK_VERSION": re.compile(r"^\d+\.\d+\.\d+$"),
    "ASTERISK_URL": re.compile(r"^https://[A-Za-z0-9./_-]+$"),
    "ASTERISK_SIG_URL": re.compile(r"^https://[A-Za-z0-9./_-]+$"),
    "ASTERISK_SHA256": HEX(64), "ASTERISK_SIZE": re.compile(r"^\d+$"), "ASTERISK_KEY_FPR": FPR,
    "PJPROJECT_VERSION": re.compile(r"^\d+\.\d+(\.\d+)?$"),
    "PJPROJECT_URL": re.compile(r"^https://[A-Za-z0-9./_-]+$"),
    "PJPROJECT_SHA256": HEX(64), "PJPROJECT_MD5": HEX(32), "PJPROJECT_SIZE": re.compile(r"^\d+$"),
    "BASE_IMAGE": re.compile(r"^[a-z0-9./_-]+:[A-Za-z0-9._-]+@sha256:[0-9a-f]{64}$"),
    "APT_SNAPSHOT": re.compile(r"^\d{8}T\d{6}Z$"),
    "SOURCE_DATE_EPOCH": re.compile(r"^\d+$"),
    "BUILD_ID": re.compile(r"^\d+\.\d+\.\d+-t\d+$"),
}
ARTIFACT_FIELDS = {"ARTIFACT_ID": SOURCES_FIELDS["BUILD_ID"], "ARTIFACT_SHA256": HEX(64),
                   "ARTIFACT_SIZE": re.compile(r"^\d+$"), "BUILD_TREE_SHA256": HEX(64)}


class Problem(Exception):
    pass


def read_text(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def parse_lock(text, fields, name="lock"):
    """KEY=VALUE lines, # comments, nothing else. Every field must be present, valid and unique."""
    out = {}
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, eq, value = line.partition("=")
        if not eq or not KEY.match(key) or value != value.strip() or not value:
            raise Problem(f"{name}:{n}: not a KEY=VALUE line")
        if key in out:
            raise Problem(f"{name}:{n}: {key} appears twice")
        if key not in fields:
            raise Problem(f"{name}:{n}: unknown field {key}")
        if not fields[key].match(value):
            raise Problem(f"{name}:{n}: {key} has a value that is not allowed")
        out[key] = value
    missing = sorted(set(fields) - set(out))
    if missing:
        raise Problem(f"{name}: missing {', '.join(missing)}")
    return out


def tree_digest(build_dir=BUILD):
    """sha256 over (path, file sha256) of every file under asterisk/build/ except artifact.lock and README.md."""
    lines = []
    for base, dirs, files in os.walk(build_dir):
        dirs[:] = sorted(d for d in dirs if d != "__pycache__")
        for f in sorted(files):
            full = os.path.join(base, f)
            rel = os.path.relpath(full, build_dir).replace(os.sep, "/")
            if rel in ("artifact.lock", "README.md"):
                continue
            if os.path.islink(full):
                raise Problem(f"{rel} is a symbolic link")
            with open(full, "rb") as fh:
                lines.append(f"{rel}\0{hashlib.sha256(fh.read()).hexdigest()}\n")
    return hashlib.sha256("".join(sorted(lines)).encode()).hexdigest()


def modules(text):
    names = [l.strip() for l in text.splitlines() if l.strip() and not l.lstrip().startswith("#")]
    for m in names:
        if not re.match(r"^[a-z][a-z0-9_]*$", m):
            raise Problem(f"modules.txt: {m!r} is not a module name")
    if len(set(names)) != len(names):
        raise Problem("modules.txt lists a module twice")
    return names


def check(build_dir=BUILD):
    """Raise Problem when the inputs are malformed, or artifact.lock does not describe this tree."""
    read = lambda n: read_text(os.path.join(build_dir, n))
    src = parse_lock(read("sources.lock"), SOURCES_FIELDS, "sources.lock")
    modules(read("modules.txt"))
    if src["ASTERISK_URL"].rsplit("/", 1)[-1] != f"asterisk-{src['ASTERISK_VERSION']}.tar.gz":
        raise Problem("ASTERISK_URL is not the tarball of ASTERISK_VERSION")
    if src["ASTERISK_SIG_URL"] != src["ASTERISK_URL"] + ".asc":
        raise Problem("ASTERISK_SIG_URL is not ASTERISK_URL plus .asc")
    if src["PJPROJECT_URL"].rsplit("/", 1)[-1] != f"pjproject-{src['PJPROJECT_VERSION']}.tar.bz2":
        raise Problem("PJPROJECT_URL is not the tarball of PJPROJECT_VERSION")
    if not src["BUILD_ID"].startswith(src["ASTERISK_VERSION"] + "-t"):
        raise Problem("BUILD_ID does not start with ASTERISK_VERSION")
    art_path = os.path.join(build_dir, "artifact.lock")
    if not os.path.exists(art_path):
        return src, None
    art = parse_lock(read("artifact.lock"), ARTIFACT_FIELDS, "artifact.lock")
    if art["ARTIFACT_ID"] != src["BUILD_ID"]:
        raise Problem("artifact.lock is for another build than sources.lock's BUILD_ID: build and record a new artifact")
    if art["BUILD_TREE_SHA256"] != tree_digest(build_dir):
        raise Problem("asterisk/build/ changed since artifact.lock was written: build a new artifact "
                      "(bump BUILD_ID) and run `scripts/asterisk_build.py write-lock`")
    return src, art


def write_lock(artifact, build_dir=BUILD):
    src, _ = check_sources_only(build_dir)
    with open(artifact, "rb") as fh:
        data = fh.read()
    lines = ["# The Asterisk artifact production runs. Written by scripts/asterisk_build.py write-lock, never by hand:",
             "# BUILD_TREE_SHA256 covers every other file in asterisk/build/, so this cannot describe other instructions.",
             f"ARTIFACT_ID={src['BUILD_ID']}", f"ARTIFACT_SHA256={hashlib.sha256(data).hexdigest()}",
             f"ARTIFACT_SIZE={len(data)}", f"BUILD_TREE_SHA256={tree_digest(build_dir)}", ""]
    with open(os.path.join(build_dir, "artifact.lock"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def check_sources_only(build_dir):
    saved = os.path.join(build_dir, "artifact.lock")
    return parse_lock(read_text(os.path.join(build_dir, "sources.lock")), SOURCES_FIELDS, "sources.lock"), saved


def main(argv):
    try:
        if argv[:1] == ["check"] and len(argv) == 1:
            _, art = check()
            print("asterisk/build: inputs are well formed" + ("; artifact.lock matches the tree" if art else "; no artifact.lock yet"))
        elif argv[:1] == ["write-lock"] and len(argv) == 2:
            write_lock(argv[1])
            print("wrote asterisk/build/artifact.lock")
        else:
            print(__doc__.strip().split("\n\n")[0], file=sys.stderr)
            return 2
    except (Problem, OSError) as e:
        print(f"asterisk_build: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
