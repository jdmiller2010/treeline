#!/usr/bin/env python3
"""Make folders exist with an owner and a mode, without ever following a link. Standard library only. Run by install.sh (as root).

    python3 -I own-dir.py MODE USER GROUP PATH [PATH ...]

install.sh runs as root and re-runs on a machine where Asterisk, a network-facing program, has been running as the `asterisk` user
and owns folders on the state disk. `install -d -o ... -m ...` and `chown`/`chmod` by path would follow a link that user had put in
place of one of its folders (to /etc/treeline, to the databases) and hand that target to it (R10-5). Here each PATH's parent is
opened first, the PATH itself with O_NOFOLLOW|O_DIRECTORY; whatever is there that is not a plain folder (a link, a file) is removed
and replaced by a real folder, and the owner and mode are set on the open descriptor, so nothing can be swapped in between.
Parents must already exist and are the caller's responsibility (they are root's).
"""
import grp
import os
import pwd
import sys

FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


def own_dir(path, mode, uid, gid):
    parent, name = os.path.split(os.path.normpath(path))
    if not name:
        raise ValueError(f"not a folder name: {path!r}")
    pfd = os.open(parent, FLAGS)                      # the parent itself is not followed either
    try:
        try:
            fd = os.open(name, FLAGS, dir_fd=pfd)
        except FileNotFoundError:
            os.mkdir(name, 0o700, dir_fd=pfd)
            fd = os.open(name, FLAGS, dir_fd=pfd)
        except OSError:                                # ELOOP (a link) or ENOTDIR (a file): not ours to follow; replace it
            os.unlink(name, dir_fd=pfd)
            os.mkdir(name, 0o700, dir_fd=pfd)
            fd = os.open(name, FLAGS, dir_fd=pfd)
        try:
            os.fchown(fd, uid, gid)
            os.fchmod(fd, mode)
        finally:
            os.close(fd)
    finally:
        os.close(pfd)


def main(argv):
    if len(argv) < 4:
        print(__doc__.strip().split("\n\n")[0], file=sys.stderr)
        return 2
    mode, user, group, paths = int(argv[0], 8), argv[1], argv[2], argv[3:]
    uid, gid = pwd.getpwnam(user).pw_uid, grp.getgrnam(group).gr_gid
    for path in paths:
        own_dir(path, mode, uid, gid)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
