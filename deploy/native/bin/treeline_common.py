"""Shared by the root-run Treeline tools (installed beside them, outside any release). Standard library only."""

import ipaddress
import os
import re
import tempfile

ETC = os.environ.get("TREELINE_ETC", "/etc/treeline")            # overridable so tests can run without root
STATE = os.environ.get("TREELINE_STATE", "/var/lib/treeline")
# Inside STATE (root-owned): data/ is the app's (the databases), spool/ the encrypted backups waiting, backup/ and deploy/ root's own.
def data_dir():
    return os.path.join(STATE, "data")
RUN = os.environ.get("TREELINE_RUN", "/run/treeline")
OPT = os.environ.get("TREELINE_OPT", "/opt/treeline")
# The Asterisk builds, one directory per build id (asterisk/build/README.md), and the stable link the CLI uses.
ASTERISK_OPT = os.environ.get("TREELINE_ASTERISK_OPT", "/opt/asterisk")
ASTERISK_BIN = os.environ.get("TREELINE_ASTERISK_BIN", "/usr/local/sbin/asterisk")
ASTERISK_USER = "asterisk"

HOST_RE = re.compile(r"^(?=.{4,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
PLACEHOLDER = re.compile(r"@([A-Z][A-Z0-9_]*)@")


def read_env_file(path):
    """KEY=VALUE lines (no quoting, no export); comments and blank lines ignored."""
    out = {}
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if "=" not in line:
                raise ValueError(f"{path}:{n}: not KEY=VALUE")
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"')
    return out


def host_settings(etc=None):
    return read_env_file(os.path.join(etc or ETC, "host.env"))


def check_host(name):
    name = (name or "").strip().lower()
    if not HOST_RE.match(name) or name.endswith((".invalid.invalid",)):
        raise ValueError(f"{name!r} is not a host name")
    return name


def check_ip(addr):
    return str(ipaddress.ip_address(addr))


def atomic_write(path, data, mode=0o600, uid=None, gid=None):
    """Write `data` (bytes or str) to `path` by rename, private from the first byte; returns True if the contents changed.
    A symlink at `path` is refused: these tools run as root, and must never be steered into changing another file."""
    if isinstance(data, str):
        data = data.encode()
    if os.path.islink(path):
        raise ValueError(f"{path} is a symlink; refusing to write through it")
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as f:
            if f.read() == data:
                os.fchmod(f.fileno(), mode)
                if uid is not None or gid is not None:
                    os.fchown(f.fileno(), -1 if uid is None else uid, -1 if gid is None else gid)
                return False
    except FileNotFoundError:
        pass
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".tmp-")
    try:
        os.fchmod(fd, mode)
        if uid is not None or gid is not None:
            os.fchown(fd, -1 if uid is None else uid, -1 if gid is None else gid)
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    return True


def render(text, values, optional=()):
    """Fill @NAME@ placeholders. An unknown placeholder or a missing value is an error, never a blank."""
    def sub(m):
        name = m.group(1)
        if name not in values:
            raise KeyError(f"no value for @{name}@")
        return values[name]
    return PLACEHOLDER.sub(sub, text)
