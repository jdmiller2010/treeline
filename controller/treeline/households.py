"""One SQLite file per treehouse (docs/DATA_LAYER.md).

A household's own records live in `households/<id>.db` next to the central database: its call history,
notes for the parents, the log of what its grown-ups changed, and its consent and retention. Backing up,
trimming and deleting one family never touches another's file.

Rules this module keeps:

* Nothing here spans two files. There is no ATTACH, and no transaction covers a household and the central
  database; the order of the steps is what keeps a crash harmless (see "Writes that touch two files").
* A household file is created only by `create()`. Every other open is `mode=rw`, so a stale handle (the
  file was deleted by another thread or by the other process, the API and the controller both write these)
  can never bring a deleted household back as an empty file.
* The connection cache is per thread and checked against the file's identity (device and inode) on every
  use, so a handle to a deleted file is closed and never written through.
"""

import contextlib
import logging
import os
import re
import sqlite3
import threading
from collections import OrderedDict

from . import db

log = logging.getLogger("treeline")

CACHE_LIMIT = 32          # open household files per thread (the jobs thread visits every household)
DEFAULT_RETENTION_DAYS = 90

# The baseline, schema version 1 of a household file. NEVER EDIT after a release: add a step to
# HOUSEHOLD_MIGRATIONS (same rules as db.MIGRATIONS).
HOUSEHOLD_SCHEMA = """
CREATE TABLE meta (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  treehouse_id INTEGER NOT NULL,
  retention_days INTEGER NOT NULL DEFAULT 90,
  ack_911 INTEGER NOT NULL DEFAULT 0,
  consent_at TEXT,
  consent_version TEXT,
  created_at TEXT NOT NULL
);

-- This family's copy of each finished call: the columns of the central `call` ledger, written redacted.
CREATE TABLE call_log (
  id INTEGER PRIMARY KEY,
  started_at TEXT NOT NULL,
  caller_treehouse INTEGER,
  caller_handset INTEGER,
  dialed TEXT,
  callee_treehouse INTEGER,
  state TEXT NOT NULL DEFAULT 'ended',
  ring_at TEXT,
  answered_at TEXT,
  ended_at TEXT,
  talk_sec INTEGER NOT NULL DEFAULT 0,
  result TEXT,
  reason TEXT,
  answered_handset INTEGER,
  hung_up_first TEXT
);
CREATE INDEX call_log_started ON call_log(started_at);

CREATE TABLE call_event (
  id INTEGER PRIMARY KEY,
  call_id INTEGER NOT NULL REFERENCES call_log(id) ON DELETE CASCADE,
  at TEXT NOT NULL,
  handset_id INTEGER,
  theirs INTEGER NOT NULL DEFAULT 0,
  event TEXT NOT NULL
);
CREATE INDEX call_event_call ON call_event(call_id);

CREATE TABLE notice (
  id INTEGER PRIMARY KEY,
  kind TEXT NOT NULL,
  title TEXT NOT NULL,
  body TEXT,
  created_at TEXT NOT NULL,
  dismissed_at TEXT,
  emailed_at TEXT,
  key TEXT
);

CREATE TABLE parent_action (
  id INTEGER PRIMARY KEY,
  at TEXT NOT NULL,
  email TEXT,
  action TEXT NOT NULL,
  target TEXT,
  before TEXT,
  after TEXT
);
"""

HOUSEHOLD_MIGRATIONS = []


class HouseholdGone(LookupError):
    """There is no file for this household (never made, deleted, or deleted under us)."""


_NAME = re.compile(r"^(\d+)\.db$")


def root():
    return os.environ.get("TREELINE_HOUSEHOLDS_DIR") or os.path.join(os.path.dirname(db.DB_PATH) or ".", "households")


def path(tid):
    return os.path.join(root(), f"{int(tid)}.db")            # int(): an id can never be a path


def pre_migrate_dir():
    return os.path.join(root(), "pre-migrate")


def ids():
    """The households that have a file, by id."""
    try:
        names = os.listdir(root())
    except FileNotFoundError:
        return []
    return sorted(int(m.group(1)) for m in map(_NAME.match, names) if m)


def exists(tid):
    return os.path.exists(path(tid))


# ------------------------------------------------------------- opening

_local = threading.local()


def _cache():
    cache = getattr(_local, "cache", None)
    if cache is None:
        cache = _local.cache = OrderedDict()
    return cache


def _identity(p):
    st = os.stat(p)
    return (st.st_dev, st.st_ino)


def _forget(p):
    """Close this thread's handle to a file, if it has one."""
    hit = _cache().pop(p, None)
    if hit:
        with contextlib.suppress(sqlite3.Error):
            hit[0].close()


def forget_all():
    """Close this thread's cached handles (tests; and a thread that is about to stop)."""
    for p in list(_cache()):
        _forget(p)


def _no_new_file(_conn):
    raise db.DatabaseRefused("this household file is empty (a create that never finished)")


def _open(tid, create=False, init=None):
    p = path(tid)
    uri = "file:" + p.replace("%", "%25").replace("?", "%3f").replace("#", "%23") + ("?mode=rwc" if create else "?mode=rw")
    try:
        conn = sqlite3.connect(uri, uri=True, timeout=15, isolation_level=None)
    except sqlite3.OperationalError as err:
        raise HouseholdGone(tid) from err          # mode=rw: a missing file is an error, never a new empty file
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA busy_timeout=15000")
        migrations = HOUSEHOLD_MIGRATIONS
        prepare_args = dict(
            app_id=db.HOUSEHOLD_APP_ID, schema=HOUSEHOLD_SCHEMA, migrations=migrations,
            label="household file", old_message="this file is not a Treeline household file",
            init=init or _no_new_file,
            backup=lambda v: db.backup_before_migration(conn, pre_migrate_dir(), str(int(tid)), v))
        db.prepare(conn, **prepare_args)
        row = conn.execute("SELECT treehouse_id FROM meta WHERE id=1").fetchone()
        if row is None or row["treehouse_id"] != int(tid):
            raise db.DatabaseRefused(
                f"household file {int(tid)}.db belongs to treehouse {row['treehouse_id'] if row else '(none)'}, "
                "not this one: refusing to read it")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
    except BaseException:
        conn.close()
        raise
    return conn


def conn(tid):
    """This thread's connection to a household's file. Raises HouseholdGone if there is no file."""
    p = path(tid)
    cache = _cache()
    try:
        ident = _identity(p)
    except FileNotFoundError:
        _forget(p)
        raise HouseholdGone(tid) from None
    hit = cache.get(p)
    if hit and hit[1] == ident:
        cache.move_to_end(p)
        return hit[0]
    _forget(p)                                       # a different file now (deleted, and made again): not ours
    c = _open(tid)
    _remember(p, c, ident)
    return c


def _remember(p, c, ident):
    cache = _cache()
    cache[p] = (c, ident)
    while len(cache) > CACHE_LIMIT:
        _, (oldest, _) = cache.popitem(last=False)
        with contextlib.suppress(sqlite3.Error):
            oldest.close()


@contextlib.contextmanager
def transaction(tid):
    """BEGIN IMMEDIATE .. COMMIT on one household's file."""
    c = conn(tid)
    c.execute("BEGIN IMMEDIATE")
    try:
        yield c
        c.execute("COMMIT")
    except BaseException:
        if c.in_transaction:
            c.execute("ROLLBACK")
        raise


# ------------------------------------------------------------- create and remove

def create(tid, retention_days=DEFAULT_RETENTION_DAYS, ack_911=False, consent_at=None, consent_version=None):
    """Make a household's file, with its consent and 911 acknowledgement. Replaces any file already at
    this id (a rolled-back create gives the id out again, and so does a central database restored from
    a backup; the leftover is not this household's)."""
    remove(tid)
    os.makedirs(root(), mode=0o700, exist_ok=True)
    p = path(tid)
    os.close(os.open(p, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))      # private from the first byte

    def write_meta(c):
        c.execute("INSERT INTO meta(id,treehouse_id,retention_days,ack_911,consent_at,consent_version,created_at) "
                  "VALUES(1,?,?,?,?,?,?)",
                  (int(tid), int(retention_days), int(bool(ack_911)), consent_at, consent_version, db.iso()))

    try:
        c = _open(tid, create=True, init=write_meta)
    except BaseException:
        remove(tid)
        raise
    _remember(p, c, _identity(p))
    return c


def remove(tid):
    """Delete a household's file, its WAL files and its pre-migration backups. Safe while other threads
    or the other process have it open: they find the file gone on their next use. Missing is fine."""
    p = path(tid)
    _forget(p)
    for suffix in ("", "-wal", "-shm", "-journal"):          # the file first, so nobody can open it any more
        with contextlib.suppress(FileNotFoundError):
            os.remove(p + suffix)
    prefix = f"{int(tid)}-v"
    with contextlib.suppress(FileNotFoundError):
        for name in os.listdir(pre_migrate_dir()):
            if name.startswith(prefix):
                with contextlib.suppress(FileNotFoundError):
                    os.remove(os.path.join(pre_migrate_dir(), name))


# ------------------------------------------------------------- startup sweep and health

def sweep():
    """Open every household file once, so a migration that fails shows up at startup (and in the health
    check), not when a family first opens the app. Returns {id: error} for the ones that could not be opened."""
    failed = {}
    for tid in ids():
        try:
            conn(tid)
        except HouseholdGone:
            continue
        except Exception as err:                              # a refused or failing file must not stop the rest
            log.error("household %s could not be opened: %s", tid, err)
            failed[tid] = str(err)
    forget_all()
    return failed


def behind():
    """Ids of household files that are not at this code's schema version (or cannot be read at all),
    without migrating anything."""
    target = db.target_version(HOUSEHOLD_MIGRATIONS)
    out = []
    for tid in ids():
        try:
            c = sqlite3.connect("file:" + path(tid) + "?mode=ro", uri=True, timeout=5)
        except sqlite3.Error:
            out.append(tid)
            continue
        try:
            found = c.execute("PRAGMA application_id").fetchone()[0]
            version = c.execute("PRAGMA user_version").fetchone()[0]
            if found != db.HOUSEHOLD_APP_ID or version != target:
                out.append(tid)
        except sqlite3.Error:
            out.append(tid)
        finally:
            c.close()
    return out


# ------------------------------------------------------------- meta

def meta(tid):
    """The household's own settings (retention, consent, 911 acknowledgement), or None if it has no file."""
    try:
        return conn(tid).execute("SELECT * FROM meta WHERE id=1").fetchone()
    except HouseholdGone:
        return None


def retention_days(tid):
    m = meta(tid)
    return m["retention_days"] if m else DEFAULT_RETENTION_DAYS


def set_retention(tid, days):
    conn(tid).execute("UPDATE meta SET retention_days=? WHERE id=1", (int(days),))


# ------------------------------------------------------------- notes for the parents and the audit log

def add_notice(tid, kind, title, body=None, key=None):
    """Add a note for a treehouse's parents. A repeated `key` is ignored while an undismissed note with
    that key exists. A household with no file (deleted) has no one to tell: nothing is written."""
    try:
        c = conn(tid)
    except HouseholdGone:
        return None
    if key and c.execute("SELECT 1 FROM notice WHERE key=? AND dismissed_at IS NULL", (key,)).fetchone():
        return None
    return c.execute("INSERT INTO notice(kind,title,body,created_at,key) VALUES(?,?,?,?,?)",
                     (kind, title, body, db.iso(), key)).lastrowid


def notices(tid, limit=20):
    try:
        return conn(tid).execute("SELECT * FROM notice WHERE dismissed_at IS NULL ORDER BY id DESC LIMIT ?",
                                 (limit,)).fetchall()
    except HouseholdGone:
        return []


def dismiss_notice(tid, nid, at=None):
    with contextlib.suppress(HouseholdGone):
        conn(tid).execute("UPDATE notice SET dismissed_at=? WHERE id=? AND dismissed_at IS NULL", (at or db.iso(), nid))


def dismiss_key(tid, key, at=None):
    with contextlib.suppress(HouseholdGone):
        conn(tid).execute("UPDATE notice SET dismissed_at=? WHERE key=? AND dismissed_at IS NULL", (at or db.iso(), key))


def log_action(tid, email, action, target=None, before=None, after=None):
    """Record what a grown-up (or a phone) changed, in the household's own file."""
    if tid is None:
        return
    with contextlib.suppress(HouseholdGone):
        conn(tid).execute(
            "INSERT INTO parent_action(at,email,action,target,before,after) VALUES(?,?,?,?,?,?)",
            (db.iso(), email, action, target, None if before is None else str(before),
             None if after is None else str(after)))


def actions(tid, limit=200):
    try:
        return conn(tid).execute("SELECT * FROM parent_action ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    except HouseholdGone:
        return []
