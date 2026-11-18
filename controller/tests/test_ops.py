"""Backups and notification keys."""
import datetime as dt
import os
import sqlite3
import tempfile
import time
import unittest

import backup
from tests import helpers  # noqa: F401
from treeline import db


class Backups(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.src = os.path.join(self.dir, "live.db")
        conn = db.connect(self.src)
        db.create_treehouse(conn, "Sam's", number="4321")
        conn.close()
        self.dest = os.path.join(self.dir, "backups")

    def test_a_backup_is_a_working_copy_and_private(self):
        out = backup.backup(self.src, self.dest, 14)
        copy = sqlite3.connect(out)
        self.assertEqual(copy.execute("SELECT name FROM treehouse").fetchone()[0], "Sam's")
        self.assertEqual(oct(os.stat(out).st_mode & 0o777), "0o600")

    def test_backing_up_while_the_database_is_in_use(self):
        live = db.connect(self.src)
        live.execute("BEGIN")
        live.execute("INSERT INTO setting(key,value) VALUES('x','1')")       # a write in progress
        out = backup.backup(self.src, self.dest, 14)
        live.execute("COMMIT")
        self.assertTrue(os.path.exists(out))

    def test_old_backups_are_pruned_new_ones_kept(self):
        old = backup.backup(self.src, self.dest, 14, now=dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc))
        long_ago = time.time() - 30 * 86400
        os.utime(old, (long_ago, long_ago))
        recent = backup.backup(self.src, self.dest, 14)
        self.assertFalse(os.path.exists(old))
        self.assertTrue(os.path.exists(recent))

    def test_the_daemon_waits_for_the_next_run_hour(self):
        now = dt.datetime(2026, 11, 18, 2, 0, tzinfo=dt.timezone.utc)
        self.assertEqual(backup.seconds_until(3, now), 3600)
        now = dt.datetime(2026, 11, 18, 4, 0, tzinfo=dt.timezone.utc)
        self.assertEqual(backup.seconds_until(3, now), 23 * 3600)


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
