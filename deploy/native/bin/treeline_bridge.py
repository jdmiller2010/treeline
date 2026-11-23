"""The root side of the admin page's bridge (docs/ADMIN.md): the web app asks, root decides. Standard library only.

The web app runs as `treeline` and must never get root. To show the machine's logs it writes one small JSON request file into
/var/lib/treeline/bridge/req (the only folder it may write here); a systemd path unit wakes `treeline-bridge run`, which reads at most
MAX_PER_RUN requests, removes EVERYTHING in that folder (whatever its type or name), answers each valid request with a file in
/run/treeline/bridge (tmpfs, group treeline, gone after RESULT_TTL), and records what it did in its own audit log.

The app is treated as hostile here (it may be the compromised part):
- every file and folder is opened through descriptors without following links; a request must be a plain file the app owns, with one
  link, at most MAX_REQUEST_BYTES; a FIFO cannot block us (O_NONBLOCK), a directory or a nest of them is removed, not read;
- a request names an operation and a few values from fixed lists; nothing in it is a path, a command, a flag or free text that reaches
  a program: `journalctl` gets only arguments chosen from SOURCES and SINCE, with an empty environment and no shell;
- what comes back is capped, stripped of control characters, and redacted (emails, IP addresses, AWS account numbers) on top of the
  sources being chosen because they log no family data.
"""

import json
import os
import re
import shutil
import stat
import subprocess
import time

REQ_DIR = os.environ.get("TREELINE_BRIDGE_REQ", "/var/lib/treeline/bridge/req")
OUT_DIR = os.environ.get("TREELINE_BRIDGE_OUT", "/run/treeline/bridge")
AUDIT = os.environ.get("TREELINE_BRIDGE_AUDIT", "/var/lib/treeline/bridge/audit.log")
JOURNALCTL = "/usr/bin/journalctl"

MAX_PER_RUN = 20             # requests answered in one run; the rest are removed (and audited) unread
MAX_SCAN = 2000              # names looked at per pass of the folder: a million planted files cannot make us read a million
MAX_PASSES = 50
MAX_REQUEST_BYTES = 512
MAX_OUTPUT = 256 * 1024
RESULT_TTL = 300             # seconds a result stays readable
AUDIT_MAX = 5 * 1024 * 1024
CLOCK_PAST, CLOCK_FUTURE = 600, 60

# The logs an admin may read. Each was chosen because it logs no family data (calls, numbers, emails); the VM job greps their real
# output for addresses anyway (vm_test.py). The API and controller are NOT here: they log calls and emails (docs/ADMIN.md).
SOURCES = {
    "deploy": ["-u", "treeline-deploy.service"],
    "backup": ["-u", "treeline-backup.service"],
    "health": ["-u", "treeline-health.service"],
    "certsync": ["-u", "treeline-certsync.service"],
    "caddy": ["-u", "caddy.service"],
    "bridge": ["-u", "treeline-bridge.service"],
}
SINCE = {"15m": ["--since", "15 min ago"], "1h": ["--since", "1 hour ago"], "6h": ["--since", "6 hours ago"],
         "24h": ["--since", "24 hours ago"], "boot": ["-b"]}
REQUEST_KEYS = {"v", "id", "op", "source", "lines", "since", "by", "t"}
NAME_RE = re.compile(r"[0-9a-f]{32}\.json")
ID_RE = re.compile(r"[0-9a-f]{32}")
BY_RE = re.compile(r"[A-Za-z0-9@._+-]{1,200}")

_DIR = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


class Refused(ValueError):
    pass


# ---------------------------------------------------------------- reading the folder the app writes
def open_dir(path):
    return os.open(path, _DIR)


def remove_entry(dfd, name):
    """Remove `name` from the folder, whatever it is, without following anything: a file or link is unlinked, a folder (or a nest of
    them) is removed through descriptors (shutil.rmtree with dir_fd checks each step and never follows a link). If the app swaps a
    folder for a link in between, rmtree refuses and the next pass unlinks the link."""
    try:
        os.unlink(name, dir_fd=dfd)
    except FileNotFoundError:
        pass
    except IsADirectoryError:
        shutil.rmtree(name, dir_fd=dfd, ignore_errors=True)


def read_request(dfd, name, owner_uid):
    """The bytes of one request, or Refused. The file is removed before we act on it, so a request that makes us fail is not retried."""
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=dfd)
    except OSError as err:
        raise Refused(f"cannot open: {err.strerror}") from None
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise Refused("not a plain file")
        if st.st_uid != owner_uid:
            raise Refused("not written by the app")
        if st.st_nlink != 1:
            raise Refused("has other links")
        if st.st_size > MAX_REQUEST_BYTES:
            raise Refused("too large")
        data = os.read(fd, MAX_REQUEST_BYTES + 1)
        if len(data) > MAX_REQUEST_BYTES:
            raise Refused("too large")
        return data
    finally:
        os.close(fd)


def _no_duplicates(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise Refused(f"duplicate key {k!r}")
        out[k] = v
    return out


def _no_constants(name):
    raise Refused(f"not a number: {name}")


def parse_request(data, name, now=None):
    """The validated request (a dict of exactly REQUEST_KEYS), or Refused. `name` is the file's name, which must carry the same id."""
    now = int(time.time()) if now is None else now
    try:
        req = json.loads(data.decode("utf-8"), object_pairs_hook=_no_duplicates, parse_constant=_no_constants)
    except (UnicodeDecodeError, ValueError) as err:
        if isinstance(err, Refused):
            raise
        raise Refused("not JSON") from None
    if not isinstance(req, dict) or set(req) != REQUEST_KEYS:
        raise Refused("wrong keys")
    if type(req["v"]) is not int or req["v"] != 1:
        raise Refused("unknown version (the tools on the machine may be older than the app: re-run install.sh)")
    if type(req["id"]) is not str or not ID_RE.fullmatch(req["id"]) or name != req["id"] + ".json":
        raise Refused("id does not match the file")
    if req["op"] != "logs":
        raise Refused("unknown operation")
    if type(req["source"]) is not str or req["source"] not in SOURCES:
        raise Refused("unknown log source")
    if type(req["lines"]) is not int or not 1 <= req["lines"] <= 1000:
        raise Refused("lines must be 1 to 1000")
    if type(req["since"]) is not str or req["since"] not in SINCE:
        raise Refused("unknown time range")
    if type(req["by"]) is not str or not BY_RE.fullmatch(req["by"]):
        raise Refused("bad requester")
    if type(req["t"]) is not int or not now - CLOCK_PAST <= req["t"] <= now + CLOCK_FUTURE:
        raise Refused("too old or from the future")
    return req


# ---------------------------------------------------------------- the answer
_CONTROL = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]|[\x00-\x08\x0b-\x1f\x7f-\x9f]")
_EMAIL = re.compile(r"[^\s@<>()\[\]\"',;]+@[^\s@<>()\[\]\"',;]+\.[A-Za-z]{2,}")
_IPV4 = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
# IPv6: eight-ish groups, or anything with "::". A time such as 18:58:35 (three groups, no "::") is left alone.
_IPV6 = re.compile(r"(?<![\w:])(?:(?:[0-9A-Fa-f]{1,4}:){4,7}[0-9A-Fa-f]{1,4}|[0-9A-Fa-f]{0,4}(?::[0-9A-Fa-f]{0,4}){0,6}::(?:[0-9A-Fa-f]{1,4}(?::[0-9A-Fa-f]{1,4}){0,6})?)(?![\w:])")
_ACCOUNT = re.compile(r"(?<!\d)\d{12}(?!\d)")
# A URL's query string can carry a live token (the phone's pairing poll, /api/pair/status?token=...): Caddy may log the full URI of a
# request that failed while the API restarted. Everything after "?" in a URL-shaped run of characters goes.
_QUERY = re.compile(r"(?<=[\w/.-])\?[^\s\"'<>]+")
_TOKEN_PARAM = re.compile(r"(?i)\b(token|code|secret|password|key|sig|signature)=[^\s&\"'<>]+")


def clean(text):
    """Control characters out; then query strings, token-like parameters, emails, IP addresses and AWS account numbers replaced."""
    text = _CONTROL.sub("", text)
    text = _QUERY.sub("?[query]", text)
    text = _TOKEN_PARAM.sub(lambda m: m.group(1) + "=[hidden]", text)
    text = _EMAIL.sub("[email]", text)
    text = _IPV6.sub(lambda m: "[ip]" if len(m.group(0)) > 2 else m.group(0), text)
    text = _IPV4.sub("[ip]", text)
    return _ACCOUNT.sub("[account]", text)


def journal_command(req):
    return [JOURNALCTL, "--no-pager", "-q", "--no-hostname", "-o", "short-iso", "-n", str(req["lines"]), *SINCE[req["since"]],
            *SOURCES[req["source"]]]


def read_logs(req, run=subprocess.run):
    """(raw text, truncated). Never raises for the journal's own trouble: that becomes the text. run_once cleans it."""
    try:
        done = run(journal_command(req), stdin=subprocess.DEVNULL, capture_output=True, env={}, timeout=10, cwd="/")
        raw = done.stdout or b""
        if done.returncode != 0 and not raw:
            raw = b"(journalctl failed: " + (done.stderr or b"")[-300:] + b")"
    except subprocess.TimeoutExpired:
        raw = b"(journalctl took too long)"
    truncated = len(raw) > MAX_OUTPUT
    if truncated:
        raw = raw[-MAX_OUTPUT:]
        raw = raw[raw.find(b"\n") + 1:] if b"\n" in raw else raw
    return raw.decode("utf-8", "replace"), truncated


def write_result(out_dfd, rid, payload):
    """<id>.json in the results folder, written beside and renamed: the app never reads half a file. 0640: the folder is setgid
    treeline, so the app (and nobody else) can read it."""
    tmp = f".{rid}.tmp"
    data = json.dumps(payload).encode()
    try:
        os.unlink(tmp, dir_fd=out_dfd)
    except FileNotFoundError:
        pass
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o640, dir_fd=out_dfd)
    try:
        os.write(fd, data)
        os.fchmod(fd, 0o640)
    finally:
        os.close(fd)
    os.rename(tmp, f"{rid}.json", src_dir_fd=out_dfd, dst_dir_fd=out_dfd)


def audit(entry, path=None):
    """One JSON line, appended to root's own log (never the app's database, which the app could edit). No log text in it."""
    path = path or AUDIT
    entry = dict(entry, at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    try:
        if os.lstat(path).st_size > AUDIT_MAX:
            os.replace(path, path + ".1")
    except FileNotFoundError:
        pass
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        os.write(fd, (json.dumps(entry) + "\n").encode())
    finally:
        os.close(fd)


# ---------------------------------------------------------------- the two commands
def run_once(owner_uid, req_dir=None, out_dir=None, journal=read_logs, now=None, audit_path=None):
    """Answer what is in the request folder and leave it empty. Returns a list of (id or name, outcome)."""
    done = []
    dfd = open_dir(req_dir or REQ_DIR)
    out_dfd = open_dir(out_dir or OUT_DIR)
    try:
        answered = 0
        for _ in range(MAX_PASSES):
            with os.scandir(dfd) as it:
                names = [e.name for _, e in zip(range(MAX_SCAN), it)]
            if not names:
                break
            for name in sorted(names):
                if not NAME_RE.fullmatch(name) or answered >= MAX_PER_RUN:
                    remove_entry(dfd, name)
                    if NAME_RE.fullmatch(name):
                        done.append((name, "dropped: too many at once"))
                        audit({"name": name, "outcome": "dropped"}, audit_path)
                    continue
                try:
                    data = read_request(dfd, name, owner_uid)
                except Refused as err:
                    remove_entry(dfd, name)
                    done.append((name, f"refused: {err}"))
                    audit({"name": name, "outcome": f"refused: {err}"}, audit_path)
                    continue
                remove_entry(dfd, name)                       # before acting: a request that breaks us is not tried again
                answered += 1
                rid = name[:-5]
                try:
                    req = parse_request(data, name, now)
                except Refused as err:
                    write_result(out_dfd, rid, {"v": 1, "id": rid, "status": "refused", "reason": str(err)})
                    done.append((rid, f"refused: {err}"))
                    audit({"id": rid, "outcome": f"refused: {err}"}, audit_path)
                    continue
                text, truncated = journal(req)
                text = clean(text)                             # here, on every answer, whatever produced the text
                write_result(out_dfd, rid, {"v": 1, "id": rid, "status": "ok", "source": req["source"], "lines": req["lines"],
                                            "since": req["since"], "truncated": truncated, "text": text})
                done.append((rid, "ok"))
                audit({"id": rid, "by": req["by"], "op": "logs", "source": req["source"], "lines": req["lines"], "since": req["since"],
                       "outcome": "ok", "bytes": len(text)}, audit_path)
    finally:
        os.close(dfd)
        os.close(out_dfd)
    return done


def sweep(out_dir=None, now=None, ttl=RESULT_TTL):
    """Results older than the TTL go, and anything in the results folder that is not one of our plain files."""
    now = time.time() if now is None else now
    removed = []
    dfd = open_dir(out_dir or OUT_DIR)
    try:
        with os.scandir(dfd) as it:
            names = [e.name for _, e in zip(range(MAX_SCAN * 5), it)]
        for name in names:
            try:
                st = os.stat(name, dir_fd=dfd, follow_symlinks=False)
            except FileNotFoundError:
                continue
            if not stat.S_ISREG(st.st_mode) or now - st.st_mtime > ttl:
                remove_entry(dfd, name)
                removed.append(name)
    finally:
        os.close(dfd)
    return removed


def main(argv):
    import pwd
    if argv == ["run"]:
        for rid, outcome in run_once(pwd.getpwnam("treeline").pw_uid):
            print(f"{rid}: {outcome}")
        sweep()
        return 0
    if argv == ["sweep"]:
        sweep()
        return 0
    print("usage: treeline-bridge run | sweep")
    return 2
