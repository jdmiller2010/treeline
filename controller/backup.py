"""Nightly backups of the Treeline database.

  python backup.py            # one backup now, then prune old ones
  python backup.py --daemon   # one every night at BACKUP_HOUR (default 03:00 UTC)

Uses SQLite's own online backup, so it's safe while Treeline is running.
Backups hold call records and emails: keep them as private as the database.
"""

import datetime as dt
import glob
import logging
import os
import sqlite3
import sys
import time

DB = os.environ.get("TREELINE_DB", "/data/treeline.db")
DEST = os.environ.get("BACKUP_DIR", "/backups")
KEEP_DAYS = int(os.environ.get("BACKUP_KEEP_DAYS", "14"))
HOUR = int(os.environ.get("BACKUP_HOUR", "3"))
log = logging.getLogger("treeline.backup")


def backup(db=DB, dest=DEST, keep_days=KEEP_DAYS, now=None):
    """Copy the database, check the copy, and delete backups older than keep_days. Returns the new file."""
    now = now or dt.datetime.now(dt.timezone.utc)
    os.makedirs(dest, exist_ok=True)
    out = os.path.join(dest, f"treeline-{now:%Y%m%d-%H%M%S}.db")
    src = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        dst = sqlite3.connect(out)
        try:
            src.backup(dst)
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
        os.remove(out)
        raise RuntimeError(f"backup failed its integrity check: {ok}")
    os.chmod(out, 0o600)
    cutoff = now - dt.timedelta(days=keep_days)
    for old in glob.glob(os.path.join(dest, "treeline-*.db")):
        if old != out and dt.datetime.fromtimestamp(os.path.getmtime(old), dt.timezone.utc) < cutoff:
            os.remove(old)
    return out


def seconds_until(hour, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    nxt = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    if nxt <= now:
        nxt += dt.timedelta(days=1)
    return (nxt - now).total_seconds()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if "--daemon" not in sys.argv:
        print(backup())
        sys.exit(0)
    while True:
        time.sleep(seconds_until(HOUR))
        try:
            log.info("backed up to %s", backup())
        except Exception:
            log.exception("backup failed")
