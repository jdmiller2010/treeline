"""SQLite storage for Treeline. Standard library only.

Two kinds of file (docs/DATA_LAYER.md):

  * the central database (this module): what the app needs to route calls and to find a
    household from an outside key (a number, an email, a SIP user, a code), plus the call ledger;
  * one file per treehouse (households.py): that family's call history, notes, audit log and consent.

Both kinds are made by `prepare()`: a marker (`PRAGMA application_id`) says which kind a file is, and
`user_version` says which schema it has. WAL mode lets the API and the controller use a file at once.
"""

import datetime as dt
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import threading

DB_PATH = os.environ.get("TREELINE_DB", "/data/treeline.db")
SIP_REALM = "treeline"

# What kind of file this is. "TRLC" and "TRLH" as 32-bit numbers.
CENTRAL_APP_ID = 0x54524C43
HOUSEHOLD_APP_ID = 0x54524C48

LEDGER_DAYS = 3          # the call ledger keeps this long (long enough for any time zone's "today")
PRE_MIGRATE_DAYS = 7

# The baseline, schema version 1. NEVER EDIT THIS AFTER A RELEASE: a change to the schema is a new
# numbered step in MIGRATIONS below (a fresh file is made at version 1 and then every step is applied,
# the same path an existing file takes).
SCHEMA = """
CREATE TABLE treehouse (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  number TEXT UNIQUE,
  timezone TEXT NOT NULL DEFAULT 'America/Los_Angeles',
  quiet_enabled INTEGER NOT NULL DEFAULT 1,
  quiet_start TEXT NOT NULL DEFAULT '20:00',
  quiet_end TEXT NOT NULL DEFAULT '07:00',
  quiet_days TEXT NOT NULL DEFAULT '1111111',
  paused INTEGER NOT NULL DEFAULT 0,
  max_call_minutes REAL NOT NULL DEFAULT 30,
  daily_minutes REAL,
  parent_pin_hash TEXT,
  pin_fails INTEGER NOT NULL DEFAULT 0,
  pin_locked_until TEXT,
  retention_days INTEGER NOT NULL DEFAULT 90,
  ack_911 INTEGER NOT NULL DEFAULT 0,
  consent_at TEXT,
  consent_version TEXT,
  system INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  left_at TEXT
);

CREATE TABLE handset (
  id INTEGER PRIMARY KEY,
  treehouse_id INTEGER NOT NULL REFERENCES treehouse(id),
  kind TEXT NOT NULL CHECK (kind IN ('rotary','ata','softphone')),
  name TEXT NOT NULL,
  sip_user TEXT NOT NULL UNIQUE,
  sip_md5 TEXT NOT NULL,
  provision_token TEXT,
  provision_secret TEXT,
  disabled INTEGER NOT NULL DEFAULT 0,
  last_seen TEXT,
  online INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  removed_at TEXT
);

CREATE TABLE string (
  id INTEGER PRIMARY KEY,
  a_id INTEGER NOT NULL REFERENCES treehouse(id),
  b_id INTEGER NOT NULL REFERENCES treehouse(id),
  state TEXT NOT NULL CHECK (state IN ('waiting','live','paused','cut')),
  asked_by INTEGER,
  a_approved_by INTEGER,
  b_approved_by INTEGER,
  paused_by INTEGER,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  CHECK (a_id < b_id)
);

CREATE TABLE ladder_code (
  code TEXT PRIMARY KEY,
  treehouse_id INTEGER NOT NULL REFERENCES treehouse(id),
  expires_at TEXT NOT NULL,
  used_by INTEGER,
  used_at TEXT
);

CREATE TABLE grown_up (
  id INTEGER PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  name TEXT,
  treehouse_id INTEGER NOT NULL REFERENCES treehouse(id),
  role TEXT NOT NULL CHECK (role IN ('parent','sitter')),
  created_at TEXT NOT NULL
);

CREATE TABLE login_code (
  email TEXT PRIMARY KEY,
  code_hash TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  attempts INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE session (
  token_hash TEXT PRIMARY KEY,
  email TEXT NOT NULL,
  expires_at TEXT NOT NULL
);

-- The ledger: calls in progress, and the recent record the rules are computed from. The family-facing
-- history is a copy per household (households.py), written when a call ends; `logged` says it was.
CREATE TABLE call (
  id INTEGER PRIMARY KEY,
  started_at TEXT NOT NULL,
  caller_treehouse INTEGER,
  caller_handset INTEGER,
  dialed TEXT,
  callee_treehouse INTEGER,
  state TEXT NOT NULL DEFAULT 'ringing',
  ring_at TEXT,
  answered_at TEXT,
  ended_at TEXT,
  talk_sec INTEGER NOT NULL DEFAULT 0,
  result TEXT,
  reason TEXT,
  answered_handset INTEGER,
  hung_up_first TEXT
);
CREATE INDEX call_caller ON call(caller_treehouse, started_at);
CREATE INDEX call_callee ON call(callee_treehouse, started_at);

CREATE TABLE call_event (
  id INTEGER PRIMARY KEY,
  call_id INTEGER NOT NULL REFERENCES call(id) ON DELETE CASCADE,
  at TEXT NOT NULL,
  handset_id INTEGER,
  event TEXT NOT NULL
);

CREATE TABLE parent_action (
  id INTEGER PRIMARY KEY,
  at TEXT NOT NULL,
  treehouse_id INTEGER,
  email TEXT,
  action TEXT NOT NULL,
  target TEXT,
  before TEXT,
  after TEXT
);

CREATE TABLE notice (
  id INTEGER PRIMARY KEY,
  treehouse_id INTEGER NOT NULL REFERENCES treehouse(id),
  kind TEXT NOT NULL,
  title TEXT NOT NULL,
  body TEXT,
  created_at TEXT NOT NULL,
  dismissed_at TEXT,
  emailed_at TEXT,
  key TEXT
);
CREATE INDEX notice_house ON notice(treehouse_id, created_at);

CREATE TABLE pairing (
  code TEXT PRIMARY KEY,
  token_hash TEXT NOT NULL,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  handset_id INTEGER,
  sip_user TEXT,
  sip_secret TEXT,
  claimed_at TEXT
);

CREATE TABLE push_subscription (
  id INTEGER PRIMARY KEY,
  email TEXT NOT NULL,
  endpoint TEXT NOT NULL UNIQUE,
  p256dh TEXT NOT NULL,
  auth TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE setting (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
"""

# Defaults for the knobs in the `setting` table. Tests change these.
SETTING_DEFAULTS = {
    "ring_timeout_sec": "60",
    "repeat_limit_count": "5",
    "repeat_limit_minutes": "10",
    "unstrung_limit_count": "5",
    "unstrung_limit_minutes": "10",
    "offline_alert_minutes": "10",
}


def utcnow():
    return dt.datetime.now(dt.timezone.utc)


def iso(t=None):
    return (t or utcnow()).isoformat(timespec="seconds")


def parse(s):
    return dt.datetime.fromisoformat(s) if s else None


# ------------------------------------------------------------- schema versions and migrations

# Changes to the central schema after the baseline. Step n (1-based) takes the file from version n to
# n + 1 and runs in one transaction with the version bump, so a step that fails changes nothing. A step
# uses `conn.execute` (never `executescript`, which commits). Never edit, reorder or delete a shipped
# step; a column is added in one release, the code stops using the old one in the next, and the old one
# is dropped in the one after (docs/DATA_LAYER.md, "Schema changes after go-live").
MIGRATIONS = []


class DatabaseRefused(RuntimeError):
    """A file this code must not open. Nothing is written to it."""


class OldLayoutDatabase(DatabaseRefused):
    pass


class WrongKindOfDatabase(DatabaseRefused):
    pass


class DatabaseNewerThanCode(DatabaseRefused):
    pass


OLD_LAYOUT_MESSAGE = ("this is an old-layout dev database; run `./dev clean` to start fresh "
                      "(Treeline's data layout changed and there is no upgrade path)")


def target_version(migrations):
    return 1 + len(migrations)


def _statements(script):
    """Split a script into single statements (so they can run inside our own transaction)."""
    out, buf = [], ""
    for line in script.splitlines(keepends=True):
        buf += line
        if sqlite3.complete_statement(buf):
            if buf.strip():
                out.append(buf.strip())
            buf = ""
    if buf.strip() and not buf.strip().startswith("--"):
        out.append(buf.strip())
    return out


def _inspect(conn, app_id, target, label, old_message):
    """What state is this file in? 'fresh', 'behind' or 'current'; or refuse it."""
    # One snapshot: another process may be creating this file right now, and three separate reads could
    # see its marker before the commit and its tables after it (and call a new file an old one).
    own = not conn.in_transaction
    if own:
        conn.execute("BEGIN")
    try:
        found = conn.execute("PRAGMA application_id").fetchone()[0]
        version = conn.execute("PRAGMA user_version").fetchone()[0]
        tables = conn.execute("SELECT count(*) FROM sqlite_master").fetchone()[0]
    finally:
        if own:
            conn.execute("COMMIT")
    if found == app_id:
        if version > target:
            raise DatabaseNewerThanCode(
                f"this {label} is at schema version {version}, but this code only knows up to {target}: "
                "refusing to open it (an older release must not write into a newer layout)")
        return ("current" if version == target else "behind"), version
    if found == 0 and version == 0 and tables == 0:
        return "fresh", 0
    if found == 0:
        raise OldLayoutDatabase(old_message)
    raise WrongKindOfDatabase(f"this file is not a Treeline {label} (application id {found:#x})")


def _timestamp(now=None):
    return (now or utcnow()).strftime("%Y%m%dT%H%M%S")


def backup_before_migration(conn, directory, stem, version, now=None):
    """An online copy of the file as it is now, kept for PRE_MIGRATE_DAYS (it holds the same personal
    data as the file). Recovery from a bad migration: stop, restore this file, deploy the previous release."""
    os.makedirs(directory, mode=0o700, exist_ok=True)
    out = os.path.join(directory, f"{stem}-v{version}-{_timestamp(now)}-{secrets.token_hex(3)}.db")
    fd = os.open(out, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)      # private from the first byte
    os.close(fd)
    dst = sqlite3.connect(out)
    try:
        conn.backup(dst)
    finally:
        dst.close()
    return out


_PRE_MIGRATE_NAME = re.compile(r"^.+-v\d+-(\d{8}T\d{6})-[0-9a-f]+\.db$")


def prune_pre_migrate(directory, now=None):
    """Delete pre-migration backups older than PRE_MIGRATE_DAYS (by the timestamp in the name)."""
    now = now or utcnow()
    cutoff = _timestamp(now - dt.timedelta(days=PRE_MIGRATE_DAYS))
    try:
        names = os.listdir(directory)
    except FileNotFoundError:
        return
    for name in names:
        m = _PRE_MIGRATE_NAME.match(name)
        if m and m.group(1) < cutoff:
            try:
                os.remove(os.path.join(directory, name))
            except FileNotFoundError:
                pass


def prepare(conn, *, app_id, schema, migrations, label, old_message=OLD_LAYOUT_MESSAGE,
            init=None, backup=None):
    """Make this file ready: create it if it is brand new, refuse it if it is not ours or is newer than
    this code, and apply any pending migration steps, each in its own transaction with the version
    re-read inside it (so two processes starting together apply a step once).

    `init(conn)` runs inside the transaction that creates a fresh file. `backup(version)` is called
    once, before the first pending step on an existing file.
    """
    target = target_version(migrations)
    state, version = _inspect(conn, app_id, target, label, old_message)
    if state == "current":
        return
    if state == "behind" and backup:
        backup(version)
    if state == "fresh":
        conn.execute("BEGIN IMMEDIATE")
        try:
            state, _ = _inspect(conn, app_id, target, label, old_message)      # someone may have beaten us to it
            if state == "fresh":
                for statement in _statements(schema):
                    conn.execute(statement)
                conn.execute(f"PRAGMA application_id={int(app_id)}")
                conn.execute("PRAGMA user_version=1")
                if init:
                    init(conn)
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
    while True:
        conn.execute("BEGIN IMMEDIATE")
        try:
            _, version = _inspect(conn, app_id, target, label, old_message)
            if version >= target:
                conn.execute("COMMIT")
                return
            migrations[version - 1](conn)
            conn.execute(f"PRAGMA user_version={version + 1}")
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise


def migrate(conn, migrations=None):
    """Apply pending central steps to an open central database."""
    prepare(conn, app_id=CENTRAL_APP_ID, schema=SCHEMA,
            migrations=MIGRATIONS if migrations is None else migrations, label="central database")


def connect(path=None, migrations=None):
    path = path or DB_PATH
    migrations = MIGRATIONS if migrations is None else migrations
    if path != ":memory:":
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    conn = sqlite3.connect(path, timeout=15, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=15000")
    try:
        # The marker is read before anything is changed: a file we refuse is left exactly as it was.
        directory = os.path.join(os.path.dirname(path) or ".", "pre-migrate")
        prepare(conn, app_id=CENTRAL_APP_ID, schema=SCHEMA, migrations=migrations, label="central database",
                backup=None if path == ":memory:" else
                lambda v: backup_before_migration(conn, directory, "treeline", v))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
    except BaseException:
        conn.close()
        raise
    return conn


_local = threading.local()


def local_conn():
    """This thread's own connection. SQLite connections can't cross threads,
    and the call engine runs on timer threads as well as the event thread."""
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = _local.conn = connect()
    return conn


def get_setting(conn, key):
    row = conn.execute("SELECT value FROM setting WHERE key=?", (key,)).fetchone()
    return row["value"] if row else SETTING_DEFAULTS[key]


def set_setting(conn, key, value):
    conn.execute("INSERT INTO setting(key,value) VALUES(?,?) "
                 "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                 (key, str(value)))


def sip_digest(user, secret):
    """The value Asterisk stores instead of the password (md5_cred)."""
    return hashlib.md5(f"{user}:{SIP_REALM}:{secret}".encode()).hexdigest()


def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def hash_pin(pin):
    """A parent code, salted and slow (scrypt). It is short, so the real protection is the lockout in the API."""
    salt = os.urandom(16)
    return "scrypt$" + salt.hex() + "$" + hashlib.scrypt(pin.encode(), salt=salt, n=2 ** 14, r=8, p=1).hex()


def check_pin(stored, pin):
    try:
        _, salt, digest = stored.split("$")
        got = hashlib.scrypt(str(pin).encode(), salt=bytes.fromhex(salt), n=2 ** 14, r=8, p=1)
    except (ValueError, AttributeError):
        return False
    return hmac.compare_digest(got, bytes.fromhex(digest))


# ------------------------------------------------------------- numbers

def assign_number(conn, rng=None):
    """A random free 4-digit number from 1000-9999 (0xxx is reserved)."""
    rng = rng or secrets.SystemRandom()
    taken = {r[0] for r in conn.execute("SELECT number FROM treehouse WHERE number IS NOT NULL")}
    free = [n for n in (f"{i:04d}" for i in range(1000, 10000)) if n not in taken]
    if not free:
        raise RuntimeError("no free numbers")
    return rng.choice(free)


def number_is_free(conn, number):
    if not (len(number) == 4 and number.isdigit() and number[0] != "0"):
        return False
    return not conn.execute("SELECT 1 FROM treehouse WHERE number=?", (number,)).fetchone()


# ------------------------------------------------------------- treehouses

def create_treehouse(conn, name, number=None, timezone="America/Los_Angeles",
                     system=False, ack_911=False, **fields):
    number = number or assign_number(conn)
    cols = {"name": name, "number": number, "timezone": timezone,
            "system": int(system), "ack_911": int(ack_911), "created_at": iso()}
    cols.update(fields)
    keys = ",".join(cols)
    cur = conn.execute(f"INSERT INTO treehouse({keys}) VALUES({','.join('?' * len(cols))})",
                       list(cols.values()))
    return cur.lastrowid


def get_treehouse(conn, tid):
    return conn.execute("SELECT * FROM treehouse WHERE id=? AND left_at IS NULL", (tid,)).fetchone()


def treehouse_by_number(conn, number):
    return conn.execute("SELECT * FROM treehouse WHERE number=? AND left_at IS NULL",
                        (number,)).fetchone()


def leave_treehouse(conn, tid):
    """The treehouse leaves the Treeline: strings end, and its number goes back to be claimed again right away
    (a call only connects over a string both families approved, so a stale number can't reach anyone)."""
    now = utcnow()
    conn.execute("UPDATE treehouse SET left_at=?, number=NULL WHERE id=?", (iso(now), tid))
    conn.execute("UPDATE string SET state='cut', updated_at=? WHERE (a_id=? OR b_id=?) AND state!='cut'",
                 (iso(now), tid, tid))
    conn.execute("UPDATE handset SET removed_at=? WHERE treehouse_id=? AND removed_at IS NULL",
                 (iso(now), tid))


# ------------------------------------------------------------- handsets

def create_handset(conn, treehouse_id, kind, name, secret=None, sip_user=None):
    """Returns (handset id, sip_user, secret). The secret is shown once."""
    sip_user = sip_user or "h" + secrets.token_hex(5)
    secret = secret or secrets.token_urlsafe(18)
    cur = conn.execute(
        "INSERT INTO handset(treehouse_id,kind,name,sip_user,sip_md5,created_at) VALUES(?,?,?,?,?,?)",
        (treehouse_id, kind, name, sip_user, sip_digest(sip_user, secret), iso()))
    return cur.lastrowid, sip_user, secret


def handsets_of(conn, treehouse_id):
    return conn.execute("SELECT * FROM handset WHERE treehouse_id=? AND removed_at IS NULL "
                        "ORDER BY id", (treehouse_id,)).fetchall()


def handset_by_user(conn, sip_user):
    return conn.execute("SELECT * FROM handset WHERE sip_user=? AND removed_at IS NULL",
                        (sip_user,)).fetchone()


# ------------------------------------------------------------- strings

def ordered(a, b):
    return (a, b) if a < b else (b, a)


def get_string(conn, x, y):
    a, b = ordered(x, y)
    return conn.execute("SELECT * FROM string WHERE a_id=? AND b_id=? AND state!='cut' "
                        "ORDER BY id DESC", (a, b)).fetchone()


def live_string(conn, x, y):
    s = get_string(conn, x, y)
    return s if s and s["state"] == "live" else None


# ------------------------------------------------------------- audit

def log_action(conn, treehouse_id, email, action, target=None, before=None, after=None):
    conn.execute("INSERT INTO parent_action(at,treehouse_id,email,action,target,before,after) "
                 "VALUES(?,?,?,?,?,?,?)",
                 (iso(), treehouse_id, email, action, target,
                  None if before is None else str(before), None if after is None else str(after)))


def add_notice(conn, treehouse_id, kind, title, body=None, key=None):
    """Add a note for a treehouse's parents. A repeated `key` is ignored while
    an undismissed note with that key exists."""
    if key and conn.execute("SELECT 1 FROM notice WHERE treehouse_id=? AND key=? AND dismissed_at IS NULL",
                            (treehouse_id, key)).fetchone():
        return None
    cur = conn.execute("INSERT INTO notice(treehouse_id,kind,title,body,created_at,key) VALUES(?,?,?,?,?,?)",
                       (treehouse_id, kind, title, body, iso(), key))
    return cur.lastrowid
