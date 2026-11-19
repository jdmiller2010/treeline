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
import datetime as dt
import logging
import os
import re
import sqlite3
import threading
from collections import OrderedDict

from . import db, rules

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
    forget_all()                                              # really open each file, not a handle cached earlier
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


# ------------------------------------------------------------- call history: the ledger and the two copies

def visible_to_callee(c):
    """What the called treehouse's parents may see of a call. Attempts that never had a live string, and
    the caller's own rules, stay on the caller's side."""
    if c["result"] in (rules.NOT_IN_SERVICE, rules.NOT_STRUNG, rules.NO_911, rules.INCOMPLETE):
        return False
    why = c["reason"] or ""
    return not (why.startswith("caller_") or why in ("unstrung_limit", "repeat_limit"))


# What a caller must not learn about the callee's own rules (it hears the same message for each).
CALLEE_RULE_REASONS = ("callee_paused", "callee_quiet", "callee_daily_limit")


def _copy_of(c, tid):
    """The ledger row as the household `tid` may keep it: nothing of the other family's rules or handsets."""
    row = {k: c[k] for k in ("id", "started_at", "caller_treehouse", "caller_handset", "dialed",
                             "callee_treehouse", "ring_at", "answered_at", "ended_at", "talk_sec", "result",
                             "reason", "answered_handset", "hung_up_first")}
    if c["caller_treehouse"] == tid:
        if row["reason"] in CALLEE_RULE_REASONS:
            row["reason"] = "callee_unavailable"           # not "quiet hours" or "paused": that is their business
        if row["result"] == rules.NOT_STRUNG:
            row["callee_treehouse"] = None                 # only the number they dialed, not whose it is
        row["answered_handset"] = None                      # the callee's handset
    else:
        row["caller_handset"] = None                        # the caller's handset
    return row


def record_call(conn, call_id):
    """Write each family's copy of a finished call (or blocked attempt), then mark the ledger row `logged`.
    Safe to repeat (INSERT OR IGNORE by id), so a crash half way is repaired by reconcile. A household with
    no file is skipped. Any other error leaves `logged` at 0 for reconcile to retry."""
    c = conn.execute("SELECT * FROM call WHERE id=? AND state='ended'", (call_id,)).fetchone()
    if c is None:
        return False
    events = conn.execute("SELECT * FROM call_event WHERE call_id=? ORDER BY id", (call_id,)).fetchall()
    wanted = sorted({int(e["handset_id"]) for e in events if e["handset_id"]})
    owner = {r["id"]: r["treehouse_id"] for r in conn.execute(
        f"SELECT id, treehouse_id FROM handset WHERE id IN ({','.join('?' * len(wanted))})", wanted)} if wanted else {}
    for side, tid in (("caller", c["caller_treehouse"]), ("callee", c["callee_treehouse"])):
        if tid is None or (side == "callee" and not visible_to_callee(c)):
            continue
        try:
            _write_copy(tid, _copy_of(c, tid), events, owner)
        except HouseholdGone:
            log.info("call %s: household %s has no file, so it has no copy", call_id, tid)
    conn.execute("UPDATE call SET logged=1 WHERE id=?", (call_id,))
    return True


def _write_copy(tid, row, events, owner):
    with transaction(tid) as h:
        keep = h.execute("SELECT retention_days FROM meta WHERE id=1").fetchone()["retention_days"]
        if row["started_at"] < db.iso(db.utcnow() - dt.timedelta(days=keep)):
            return                                          # already past this family's retention: not brought back
        cols = list(row)
        h.execute(f"INSERT OR IGNORE INTO call_log({','.join(cols)}) VALUES({','.join('?' * len(cols))})",
                  [row[k] for k in cols])
        for e in events:
            theirs = bool(e["handset_id"]) and owner.get(e["handset_id"]) != tid
            h.execute("INSERT OR IGNORE INTO call_event(id,call_id,at,handset_id,theirs,event) VALUES(?,?,?,?,?,?)",
                      (e["id"], e["call_id"], e["at"], None if theirs else e["handset_id"], int(theirs), e["event"]))


def trim(tid, now=None):
    """Remove what this family's own retention has expired from its file, now. Returns calls removed."""
    now = now or db.utcnow()
    try:
        c = conn(tid)
    except HouseholdGone:
        return 0
    days = c.execute("SELECT retention_days FROM meta WHERE id=1").fetchone()["retention_days"]
    n = c.execute("DELETE FROM call_log WHERE started_at < ?", (db.iso(now - dt.timedelta(days=days)),)).rowcount
    c.execute("DELETE FROM parent_action WHERE at < ?", (db.iso(now - dt.timedelta(days=365)),))
    c.execute("DELETE FROM notice WHERE created_at < ?", (db.iso(now - dt.timedelta(days=90)),))
    return n


def newest_record(tid):
    """The time of the household's newest record of any kind, or None."""
    c = conn(tid)
    newest = [c.execute(sql).fetchone()[0] for sql in (
        "SELECT max(started_at) FROM call_log", "SELECT max(created_at) FROM notice", "SELECT max(at) FROM parent_action")]
    return max((n for n in newest if n), default=None)


def purge_left(conn_, now=None):
    """A treehouse that left keeps its file until its newest record (or its leaving) is past its own retention,
    then the file goes with its pre-migration copies. Returns the ids removed."""
    now = now or db.utcnow()
    gone = []
    for th in conn_.execute("SELECT id, left_at FROM treehouse WHERE left_at IS NOT NULL AND deleted_at IS NULL"):
        if not exists(th["id"]):
            continue
        try:
            newest = max(n for n in (th["left_at"], newest_record(th["id"])) if n)
            if db.parse(newest) < now - dt.timedelta(days=retention_days(th["id"])):
                remove(th["id"])
                gone.append(th["id"])
        except HouseholdGone:
            continue
        except Exception:                                       # one damaged file must not stop the rest
            log.exception("household %s: could not check whether it is past retention", th["id"])
    return gone


def reconcile(conn_, now=None):
    """Repair what a crash or a restore from backup can leave between the two kinds of file
    (docs/DATA_LAYER.md, "Reconcile"). Safe to run at any time, as often as you like."""
    now = now or db.utcnow()
    done = {"orphans": [], "recreated": [], "logged": 0, "left": []}
    rows = {r["id"]: r for r in conn_.execute("SELECT id, left_at, deleted_at, system FROM treehouse")}
    # 1. files with no treehouse, or one that was deleted. A new treehouse's file is made inside the API's
    # still-open central transaction, so for a moment it has no row we can see: only files that have sat
    # for ORPHAN_GRACE are touched.
    for tid in ids():
        r = rows.get(tid)
        if (r is not None and r["deleted_at"]) or (r is None and _older_than_grace(path(tid), now)):
            remove(tid)
            done["orphans"].append(tid)
    for name in _stray_names():                               # WAL leftovers and old copies with no file to belong to
        full = os.path.join(root(), name) if not name.startswith("pre-migrate/") \
            else os.path.join(pre_migrate_dir(), name[len("pre-migrate/"):])
        if _older_than_grace(full, now):
            with contextlib.suppress(FileNotFoundError):
                os.remove(full)
    # 2. active treehouses with no file (central restored from a backup): an empty household, consent unset
    for tid, r in rows.items():
        if not r["left_at"] and not r["deleted_at"] and not r["system"] and not exists(tid):
            log.warning("treehouse %s had no household file; made an empty one (consent not recorded)", tid)
            create(tid)
            done["recreated"].append(tid)
    # 3. finished calls whose copies were not all written
    for call in conn_.execute("SELECT id FROM call WHERE state='ended' AND logged=0 ORDER BY id").fetchall():
        try:
            record_call(conn_, call["id"])
            done["logged"] += 1
        except Exception:
            log.exception("could not copy call %s into its households; will try again", call["id"])
    # 4. households that left and are now past retention
    done["left"] = purge_left(conn_, now)
    return done


ORPHAN_GRACE = dt.timedelta(hours=1)


def _older_than_grace(p, now):
    try:
        return dt.datetime.fromtimestamp(os.path.getmtime(p), dt.timezone.utc) < now - ORPHAN_GRACE
    except FileNotFoundError:
        return False


def _stray_names():
    live = set(ids())
    out = []
    try:
        names = os.listdir(root())
    except FileNotFoundError:
        return out
    for name in names:
        m = re.match(r"^(\d+)\.db(-wal|-shm|-journal)$", name)
        if m and int(m.group(1)) not in live:
            out.append(name)
    try:
        for name in os.listdir(pre_migrate_dir()):
            m = re.match(r"^(\d+)-v\d+-", name)
            if m and int(m.group(1)) not in live:
                out.append("pre-migrate/" + name)
    except FileNotFoundError:
        pass
    return out


def call_page(tid, th, since=None, before=None, limit=300):
    """One page of this family's call copies, newest first, and whether there are older ones. Applies
    `visible_to_callee` again as a second check (the write path already did)."""
    try:
        c = conn(tid)
    except HouseholdGone:
        return [], False
    sql, args = "SELECT * FROM call_log WHERE 1=1", []
    if since:
        sql += " AND started_at>=?"
        args.append(db.iso(since))
    if before:
        sql += " AND id<?"
        args.append(int(before))
    raw = c.execute(sql + " ORDER BY id DESC LIMIT ?", (*args, limit + 1)).fetchall()
    return [r for r in raw[:limit] if r["caller_treehouse"] == tid or visible_to_callee(r)], len(raw) > limit
