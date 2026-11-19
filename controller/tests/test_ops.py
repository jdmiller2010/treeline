"""Backups and notification keys."""
import datetime as dt
import os
import sqlite3
import tempfile
import time
import unittest

from unittest import mock

import backup
from tests import helpers  # noqa: F401
from treeline import db, households


class Backups(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.src = os.path.join(self.dir, "live.db")
        self.houses = os.path.join(self.dir, "households")
        conn = db.connect(self.src)
        self.sam = db.create_treehouse(conn, "Sam's", number="4321")
        self.alex = db.create_treehouse(conn, "Alex's", number="4322")
        conn.close()
        for tid, note in ((self.sam, "Sam's note"), (self.alex, "Alex's note")):
            with mock.patch.dict(os.environ, {"TREELINE_HOUSEHOLDS_DIR": self.houses}):
                households.create(tid)
                households.add_notice(tid, "x", note)
                households.forget_all()
        self.dest = os.path.join(self.dir, "backups")

    def run_backup(self, **kw):
        return backup.backup(self.src, self.dest, kw.pop("keep_days", 7), households=self.houses, **kw)

    def test_one_file_per_database_in_the_key_layout_and_each_restores(self):
        now = dt.datetime(2026, 11, 19, 3, 0, 0, tzinfo=dt.timezone.utc)
        made = self.run_backup(now=now)
        rel = [os.path.relpath(p, self.dest) for p in made]
        self.assertEqual(rel, ["central/20261119T030000Z.db", f"households/{self.sam}/20261119T030000Z.db",
                               f"households/{self.alex}/20261119T030000Z.db"])
        central = db.connect(made[0])                                         # a working central database
        self.assertEqual(central.execute("SELECT count(*) FROM treehouse").fetchone()[0], 2)
        for path, tid, note in ((made[1], self.sam, "Sam's note"), (made[2], self.alex, "Alex's note")):
            copy = sqlite3.connect(path)                                      # a working household file: only its own data
            self.assertEqual(copy.execute("SELECT treehouse_id FROM meta").fetchone()[0], tid)
            self.assertEqual([r[0] for r in copy.execute("SELECT title FROM notice")], [note])
            self.assertEqual(oct(os.stat(path).st_mode & 0o777), "0o600")
        self.assertEqual(oct(os.stat(os.path.join(self.dest, "central")).st_mode & 0o777), "0o700")

    def test_only_household_files_are_backed_up_not_wal_files_or_pre_migration_copies(self):
        os.makedirs(os.path.join(self.houses, "pre-migrate"))
        for name in ("9.db-wal", "9.db-shm", "notes.txt", "pre-migrate/9-v1-20261101T000000-abc123.db"):
            open(os.path.join(self.houses, name), "w").close()
        made = self.run_backup()
        self.assertEqual(len(made), 3)

    def test_backing_up_while_the_database_is_in_use(self):
        live = db.connect(self.src)
        live.execute("BEGIN")
        live.execute("INSERT INTO setting(key,value) VALUES('x','1')")       # a write in progress
        mine = households.conn
        with mock.patch.dict(os.environ, {"TREELINE_HOUSEHOLDS_DIR": self.houses}):
            h = mine(self.sam)
            h.execute("BEGIN")
            h.execute("INSERT INTO notice(kind,title,created_at) VALUES('x','mid-write',?)", (db.iso(),))
            made = self.run_backup()
            h.execute("COMMIT")
            households.forget_all()
        live.execute("COMMIT")
        self.assertEqual(len(made), 3)
        self.assertNotIn("mid-write", [r[0] for r in sqlite3.connect(made[1]).execute("SELECT title FROM notice")])  # the committed state

    def test_backups_older_than_seven_days_go_newer_stay_by_the_name_not_the_file_time(self):
        day = dt.timedelta(days=1)
        t0 = dt.datetime(2026, 11, 1, 3, 0, 0, tzinfo=dt.timezone.utc)
        old = self.run_backup(now=t0)
        fresh = self.run_backup(now=t0 + 7 * day)                             # t0 is exactly 7 days old: kept
        self.assertTrue(all(os.path.exists(p) for p in old + fresh))
        for p in old:                                                          # touching a file does not make it young
            os.utime(p, None)
        later = self.run_backup(now=t0 + 8 * day + dt.timedelta(minutes=1))
        self.assertTrue(all(not os.path.exists(p) for p in old))
        self.assertTrue(all(os.path.exists(p) for p in fresh + later))

    def test_a_deleted_households_old_backups_still_roll_off_and_its_folder_goes(self):
        t0 = dt.datetime(2026, 11, 1, 3, 0, 0, tzinfo=dt.timezone.utc)
        made = self.run_backup(now=t0)
        with mock.patch.dict(os.environ, {"TREELINE_HOUSEHOLDS_DIR": self.houses}):
            households.remove(self.alex)                                       # "delete all my data": no new backups of it
        gone_folder = os.path.dirname(made[2])
        self.run_backup(now=t0 + dt.timedelta(days=3))
        self.assertTrue(os.path.exists(made[2]))                               # still inside the week: it is a backup
        self.run_backup(now=t0 + dt.timedelta(days=9))
        self.assertFalse(os.path.exists(gone_folder))                          # rolled off, and the empty folder with it
        self.assertTrue(os.path.isdir(os.path.dirname(made[1])))                # Sam's, still backed up, is untouched

    def test_a_household_deleted_while_the_backup_runs_is_skipped_not_a_failure(self):
        real = backup._online_copy

        def delete_then_copy(src, out):
            if src.endswith(f"{self.sam}.db"):
                with mock.patch.dict(os.environ, {"TREELINE_HOUSEHOLDS_DIR": self.houses}):
                    households.remove(self.sam)                                # the API deletes it just before we copy
            return real(src, out)
        with mock.patch.object(backup, "_online_copy", delete_then_copy):
            made = self.run_backup()
        self.assertEqual(len(made), 2)                                         # central and Alex's
        self.assertFalse(os.path.exists(os.path.join(self.dest, "households", str(self.sam))))      # nothing of it was kept

    def test_one_broken_household_does_not_stop_the_others_but_is_reported(self):
        with open(os.path.join(self.houses, f"{self.sam}.db"), "wb") as f:
            f.write(b"this is not a database " * 200)
        with self.assertLogs("treeline.backup", "ERROR"), self.assertRaises(RuntimeError) as cm:
            self.run_backup()
        self.assertIn(f"household {self.sam}", str(cm.exception))
        self.assertTrue(os.path.exists(os.path.join(self.dest, "households", str(self.alex))))    # Alex's still got its backup
        self.assertFalse(os.path.exists(os.path.join(self.dest, "households", str(self.sam))))    # and no bad copy was kept

    def test_the_daemon_waits_for_the_next_run_hour(self):
        now = dt.datetime(2026, 11, 18, 2, 0, tzinfo=dt.timezone.utc)
        self.assertEqual(backup.seconds_until(3, now), 3600)
        now = dt.datetime(2026, 11, 18, 4, 0, tzinfo=dt.timezone.utc)
        self.assertEqual(backup.seconds_until(3, now), 23 * 3600)

    def test_the_default_is_seven_days(self):
        self.assertEqual(backup.KEEP_DAYS, 7)


class PushKeys(unittest.TestCase):
    def test_generated_keys_work_with_pywebpush(self):
        try:
            from py_vapid import Vapid
        except ImportError:
            self.skipTest("pywebpush isn't installed here")
        import make_vapid
        public, private = make_vapid.make()
        self.assertEqual(len(public), 87)                           # a 65-byte point, base64url, no padding
        claims = Vapid.from_string(private).sign({"sub": "mailto:a@example.com", "aud": "https://push.example.net",
                                                   "exp": int(time.time()) + 3600})
        self.assertIn("Authorization", claims)


if __name__ == "__main__":
    unittest.main()
