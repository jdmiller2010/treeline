"""Backups of the Treeline data: the central database and one file per treehouse.

  python backup.py            # one backup of every file now, then prune old ones
  python backup.py --daemon   # one every night at BACKUP_HOUR (default 03:00 UTC)

Layout, the same on disk and (at deploy time) in the bucket:

  central/<timestamp>.db
  households/<id>/<timestamp>.db

Each file is copied with SQLite's own online backup, so this is safe while Treeline is running, and
is checked after copying. One rule for all of them: a backup older than BACKUP_KEEP_DAYS (7) is deleted,
by the timestamp in its name. That includes the folders of households that no longer exist (otherwise a
family that deleted its data would keep its last backups forever). Backups hold call records and emails:
keep them as private as the database. (Encrypting them with `age` and sending them to S3 is deploy work.)
"""

import datetime as dt
import logging
import os
import re
import sqlite3
import sys
import time

DB = os.environ.get("TREELINE_DB", "/data/treeline.db")
HOUSEHOLDS = os.environ.get("TREELINE_HOUSEHOLDS_DIR") or os.path.join(os.path.dirname(DB) or ".", "households")
DEST = os.environ.get("BACKUP_DIR", "/backups")
KEEP_DAYS = int(os.environ.get("BACKUP_KEEP_DAYS", "7"))
HOUR = int(os.environ.get("BACKUP_HOUR", "3"))
log = logging.getLogger("treeline.backup")

STAMP = "%Y%m%dT%H%M%SZ"
_BACKUP = re.compile(r"^(\d{8}T\d{6}Z)\.db(\.age)?$")
_HOUSEHOLD = re.compile(r"^(\d+)\.db$")


class Vanished(Exception):
    """The file was deleted while we were copying it (a family deleted its data): not a failure."""


def _online_copy(src_path, out):
    """Copy one SQLite file with the online backup API into `out` (private from the first byte), and check it."""
    os.makedirs(os.path.dirname(out), mode=0o700, exist_ok=True)
    os.close(os.open(out, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
    try:
        try:
            src = sqlite3.connect(f"file:{src_path}?mode=ro", uri=True)
        except sqlite3.OperationalError as err:
            if not os.path.exists(src_path):                 # only "gone" is a skip; unreadable is a failure
                raise Vanished(src_path) from err
            raise
        try:
            dst = sqlite3.connect(out)
            try:
                src.backup(dst)
            except sqlite3.OperationalError as err:
                if not os.path.exists(src_path):
                    raise Vanished(src_path) from err
                raise
            finally:
                dst.close()
        finally:
            src.close()
        check = sqlite3.connect(out)
        try:
            ok = check.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            check.close()
        if ok != "ok":
            raise RuntimeError(f"backup of {os.path.basename(src_path)} failed its integrity check: {ok}")
    except BaseException:
        if os.path.exists(out):
            os.remove(out)
        raise
    return out


def household_files(folder):
    """(id, path) of every household file. Only `<id>.db` counts: not WAL files, not pre-migrate/."""
    try:
        names = os.listdir(folder)
    except FileNotFoundError:
        return []
    return sorted((int(m.group(1)), os.path.join(folder, m.group(0))) for m in map(_HOUSEHOLD.match, names) if m)


def backup(db=DB, dest=DEST, keep_days=KEEP_DAYS, now=None, households=None):
    """Back up the central database and every household file, then prune. Returns the files made, the
    central one first. A household deleted while this runs is skipped; any other failure is raised at the
    end, after every other file has been tried."""
    now = now or dt.datetime.now(dt.timezone.utc)
    households = HOUSEHOLDS if households is None else households
    stamp = f"{now:{STAMP}}"
    made, failures = [], []
    jobs = [("central", os.path.join(dest, "central", stamp + ".db"), db)]
    jobs += [(f"household {tid}", os.path.join(dest, "households", str(tid), stamp + ".db"), p)
             for tid, p in household_files(households)]
    for label, out, src in jobs:
        try:
            made.append(_online_copy(src, out))
        except Vanished:
            if label == "central":                           # the central database is never "deleted by a family"
                log.error("central database %s is missing", db)
                failures.append(f"central: {db} is missing")
            else:
                log.info("%s was deleted while backing up; skipped", label)
        except Exception as err:
            log.error("backup of %s failed: %s", label, err)
            failures.append(f"{label}: {err}")
    prune(dest, keep_days, now)
    if failures:
        raise RuntimeError("; ".join(failures))
    return made


def prune(dest=DEST, keep_days=KEEP_DAYS, now=None):
    """Delete backups older than keep_days by the timestamp in their name, in central/ and in every household
    folder (also those of households that are gone), and delete household folders left empty."""
    now = now or dt.datetime.now(dt.timezone.utc)
    cutoff = (now - dt.timedelta(days=keep_days)).strftime(STAMP)
    folders = [os.path.join(dest, "central")]
    base = os.path.join(dest, "households")
    if os.path.isdir(base):
        folders += [os.path.join(base, d) for d in sorted(os.listdir(base)) if os.path.isdir(os.path.join(base, d))]
    for folder in folders:
        if not os.path.isdir(folder):
            continue
        for name in os.listdir(folder):
            m = _BACKUP.match(name)
            if m and m.group(1) < cutoff:
                os.remove(os.path.join(folder, name))
        if folder != folders[0] and not os.listdir(folder):
            os.rmdir(folder)


def seconds_until(hour, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    nxt = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    if nxt <= now:
        nxt += dt.timedelta(days=1)
    return (nxt - now).total_seconds()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if "--daemon" not in sys.argv:
        print("\n".join(backup()))
        sys.exit(0)
    while True:
        time.sleep(seconds_until(HOUR))
        try:
            log.info("backed up %d file(s)", len(backup()))
        except Exception:
            log.exception("backup failed")
