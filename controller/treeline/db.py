"""SQLite storage for Treeline. Standard library only.

One file, shared by the control app (calls) and the API (parent app).
WAL mode lets both processes use it at once.
"""

import datetime as dt
import hashlib
import os
import secrets
import sqlite3
import threading

DB_PATH = os.environ.get("TREELINE_DB", "/data/treeline.db")
SIP_REALM = "treeline"

SCHEMA = """
CREATE TABLE IF NOT EXISTS treehouse (
  id INTEGER PRIMARY KEY,
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
  retention_days INTEGER NOT NULL DEFAULT 90,
  ack_911 INTEGER NOT NULL DEFAULT 0,
  consent_at TEXT,
  consent_version TEXT,
  system INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  left_at TEXT
);

CREATE TABLE IF NOT EXISTS handset (
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

CREATE TABLE IF NOT EXISTS string (
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

CREATE TABLE IF NOT EXISTS ladder_code (
  code TEXT PRIMARY KEY,
  treehouse_id INTEGER NOT NULL REFERENCES treehouse(id),
  expires_at TEXT NOT NULL,
  used_by INTEGER,
  used_at TEXT
);

CREATE TABLE IF NOT EXISTS grown_up (
  id INTEGER PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  name TEXT,
  treehouse_id INTEGER NOT NULL REFERENCES treehouse(id),
  role TEXT NOT NULL CHECK (role IN ('parent','sitter')),
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS login_code (
  email TEXT PRIMARY KEY,
  code_hash TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  attempts INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS session (
  token_hash TEXT PRIMARY KEY,
  email TEXT NOT NULL,
  expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS call (
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
CREATE INDEX IF NOT EXISTS call_caller ON call(caller_treehouse, started_at);
CREATE INDEX IF NOT EXISTS call_callee ON call(callee_treehouse, started_at);

CREATE TABLE IF NOT EXISTS call_event (
  id INTEGER PRIMARY KEY,
  call_id INTEGER NOT NULL REFERENCES call(id) ON DELETE CASCADE,
  at TEXT NOT NULL,
  handset_id INTEGER,
  event TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS parent_action (
  id INTEGER PRIMARY KEY,
  at TEXT NOT NULL,
  treehouse_id INTEGER,
  email TEXT,
  action TEXT NOT NULL,
  target TEXT,
  before TEXT,
  after TEXT
);

CREATE TABLE IF NOT EXISTS notice (
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
CREATE INDEX IF NOT EXISTS notice_house ON notice(treehouse_id, created_at);

CREATE TABLE IF NOT EXISTS pairing (
  code TEXT PRIMARY KEY,
  token_hash TEXT NOT NULL,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  handset_id INTEGER,
  sip_user TEXT,
  sip_secret TEXT,
  claimed_at TEXT
);

CREATE TABLE IF NOT EXISTS push_subscription (
  id INTEGER PRIMARY KEY,
  email TEXT NOT NULL,
  endpoint TEXT NOT NULL UNIQUE,
  p256dh TEXT NOT NULL,
  auth TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS setting (
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


# Changes to tables that already exist. CREATE TABLE IF NOT EXISTS never alters a
# table, so every later change to the schema goes here as a numbered step. Never
# edit or reorder an old step; add a new one.
def _has_column(conn, table, column):
    return any(r["name"] == column for r in conn.execute(f"PRAGMA table_info({table})"))


def _add_column(conn, table, column, decl):
    if not _has_column(conn, table, column):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")


MIGRATIONS = [
    # 1: adapters fetch their settings by a private link, which needs the secret kept.
    lambda c: _add_column(c, "handset", "provision_secret", "TEXT"),
    # 2: a parent agrees to the privacy notes when setting up; we keep when, and which version.
    lambda c: _add_column(c, "treehouse", "consent_at", "TEXT"),
    lambda c: _add_column(c, "treehouse", "consent_version", "TEXT"),
    # 4: a parent can disconnect one phone: it stops ringing and calling, nothing else changes.
    lambda c: _add_column(c, "handset", "disabled", "INTEGER NOT NULL DEFAULT 0"),
    # 5: a released number used to rest for a year before anyone could claim it. It no longer does.
    lambda c: c.execute("DROP TABLE IF EXISTS number_rest"),
]


def migrate(conn):
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    for number, step in enumerate(MIGRATIONS, 1):
        if number > version:
            step(conn)
            conn.execute(f"PRAGMA user_version={number}")


_initialized = set()


def connect(path=None):
    path = path or DB_PATH
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    conn = sqlite3.connect(path, timeout=15, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=15000")
    if path == ":memory:" or path not in _initialized:
        conn.executescript(SCHEMA)
        migrate(conn)
        _initialized.add(path)
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
