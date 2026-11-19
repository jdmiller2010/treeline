"""Household files: where they live, how they are opened and shared by threads and processes, and
how they are made, migrated and removed. Real files and real threads, no mocks of SQLite."""
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock

from tests import helpers  # noqa: F401
from treeline import db, households

CONTROLLER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class HouseholdTest(unittest.TestCase):
    """Each test gets its own empty households directory."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="treeline-households-")
        patcher = mock.patch.dict(os.environ, {"TREELINE_HOUSEHOLDS_DIR": self.dir})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(households.forget_all)

    def in_thread(self, fn):
        """Run fn in another thread (with its own handles) and return its result or raise its error."""
        box = {}

        def run():
            try:
                box["value"] = fn()
            except BaseException as err:
                box["error"] = err
            finally:
                households.forget_all()
        t = threading.Thread(target=run)
        t.start()
        t.join()
        if "error" in box:
            raise box["error"]
        return box.get("value")


class Creating(HouseholdTest):
    def test_a_household_file_has_its_marker_meta_and_is_private(self):
        households.create(7, retention_days=30, ack_911=True, consent_at="2026-11-19T10:00:00+00:00", consent_version="v1")
        p = households.path(7)
        self.assertEqual(os.path.dirname(p), self.dir)
        self.assertEqual(oct(os.stat(p).st_mode & 0o777), "0o600")
        self.assertEqual(oct(os.stat(self.dir).st_mode & 0o777), "0o700")
        raw = sqlite3.connect(p)
        self.assertEqual(raw.execute("PRAGMA application_id").fetchone()[0], db.HOUSEHOLD_APP_ID)
        self.assertEqual(raw.execute("PRAGMA user_version").fetchone()[0], 1)
        meta = raw.execute("SELECT treehouse_id, retention_days, ack_911, consent_version FROM meta").fetchall()
        self.assertEqual(meta, [(7, 30, 1, "v1")])
        tables = {r[0] for r in raw.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({"meta", "call_log", "call_event", "notice", "parent_action"} <= tables)
        self.assertNotIn("grown_up", tables)                # the household never holds an email or a lookup key
        self.assertEqual(households.ids(), [7])

    def test_an_id_can_never_be_a_path(self):
        for bad in ("../x", "1/../../x", "a"):
            with self.assertRaises(ValueError):
                households.path(bad)
        self.assertEqual(households.path("12"), os.path.join(self.dir, "12.db"))

    def test_a_leftover_file_at_a_reused_id_is_replaced_not_inherited(self):
        households.create(3)
        households.conn(3).execute("INSERT INTO notice(kind,title,created_at) VALUES('x','the old family',?)", (db.iso(),))
        households.forget_all()
        households.create(3)                                 # the id was given out again (a rolled-back create)
        self.assertEqual(households.conn(3).execute("SELECT count(*) FROM notice").fetchone()[0], 0)

    def test_a_failure_while_making_the_file_leaves_no_file(self):
        with mock.patch.object(households.db, "prepare", side_effect=RuntimeError("disk full")):
            with self.assertRaises(RuntimeError):
                households.create(4)
        self.assertFalse(households.exists(4))
        self.assertEqual(os.listdir(self.dir), [])

    def test_a_create_that_died_before_its_meta_is_refused_not_turned_into_a_household(self):
        os.makedirs(self.dir, exist_ok=True)
        open(households.path(5), "w").close()               # the empty file a crash leaves
        with self.assertRaises(db.DatabaseRefused):
            households.conn(5)
        self.assertEqual(os.path.getsize(households.path(5)), 0)      # and it was not written to


class Opening(HouseholdTest):
    def test_one_connection_per_thread_reused_while_the_file_is_the_same(self):
        households.create(1)
        a = households.conn(1)
        self.assertIs(households.conn(1), a)
        other = self.in_thread(lambda: id(households.conn(1)))
        self.assertNotEqual(other, id(a))

    def test_a_file_deleted_by_another_thread_is_noticed_and_never_written_through(self):
        households.create(1)
        stale = households.conn(1)
        stale.execute("INSERT INTO notice(kind,title,created_at) VALUES('x','before',?)", (db.iso(),))
        self.in_thread(lambda: households.remove(1))         # another thread (a delete-all-data request)
        self.assertFalse(households.exists(1))
        with self.assertRaises(households.HouseholdGone):
            households.conn(1)
        self.assertNotIn(households.path(1), households._cache())          # the stale handle was dropped
        with self.assertRaises(sqlite3.Error):
            stale.execute("SELECT 1")                                        # and closed
        self.assertEqual(os.listdir(self.dir), [])                           # nothing came back at the path

    def test_a_handle_that_still_has_the_old_file_cannot_recreate_it(self):
        households.create(1)
        keep = sqlite3.connect(households.path(1), isolation_level=None)     # something else holds the old inode open
        households.remove(1)
        with self.assertRaises(households.HouseholdGone):
            households.conn(1)                                               # mode=rw: no implicit create
        keep.close()
        self.assertEqual(os.listdir(self.dir), [])

    def test_a_household_made_again_at_the_same_id_is_a_different_file_to_other_threads(self):
        households.create(1)
        households.conn(1).execute("INSERT INTO notice(kind,title,created_at) VALUES('x','old',?)", (db.iso(),))
        count = lambda: households.conn(1).execute("SELECT count(*) FROM notice").fetchone()[0]    # noqa: E731
        ready, go, done = threading.Event(), threading.Event(), threading.Event()
        seen = {}

        def reader():
            seen["before"] = count()
            ready.set()
            go.wait()
            seen["after"] = count()
            households.forget_all()
            done.set()
        t = threading.Thread(target=reader)
        t.start()
        ready.wait()
        households.create(1)                                  # deleted and made again while the reader holds the old one
        go.set()
        done.wait()
        t.join()
        self.assertEqual((seen["before"], seen["after"]), (1, 0))

    def test_a_file_deleted_by_another_process_is_noticed_too(self):
        households.create(1)
        households.conn(1)
        code = (f"import sys\nsys.path.insert(0, {CONTROLLER!r})\nfrom treeline import households\n"
                "households.remove(1)\n")
        env = dict(os.environ, TREELINE_DB=os.path.join(self.dir, "unused.db"))
        subprocess.run([sys.executable, "-I", "-c", code], env=env, check=True, timeout=60)
        with self.assertRaises(households.HouseholdGone):
            households.conn(1)

    def test_only_a_few_files_are_kept_open_per_thread(self):
        with mock.patch.object(households, "CACHE_LIMIT", 3):
            for i in range(1, 7):
                households.create(i)                                         # making them counts as opening them
            self.assertEqual(len(households._cache()), 3)
            households.forget_all()
            first = households.conn(1)
            for i in range(2, 7):
                households.conn(i)
            self.assertEqual(len(households._cache()), 3)
            with self.assertRaises(sqlite3.Error):
                first.execute("SELECT 1")                                    # the least recently used was closed
            households.conn(1).execute("SELECT 1")                           # and is simply opened again

    def test_a_file_that_belongs_to_another_household_is_refused(self):
        households.create(1)
        households.forget_all()
        with open(households.path(1), "rb") as src, open(households.path(2), "wb") as dst:
            dst.write(src.read())                              # a copy dropped in under the wrong name
        with self.assertRaises(db.DatabaseRefused) as cm:
            households.conn(2)
        self.assertIn("belongs to treehouse 1", str(cm.exception))

    def test_a_file_that_is_not_ours_is_refused_and_left_alone(self):
        os.makedirs(self.dir, exist_ok=True)
        raw = sqlite3.connect(households.path(9))
        raw.executescript("CREATE TABLE treehouse (id INTEGER); PRAGMA user_version=3;")
        raw.close()
        with self.assertRaises(db.DatabaseRefused):
            households.conn(9)
        self.assertEqual(sqlite3.connect(households.path(9)).execute("PRAGMA application_id").fetchone()[0], 0)

    def test_a_household_file_is_not_a_central_database_and_the_other_way_round(self):
        households.create(1)
        with self.assertRaises(db.WrongKindOfDatabase):
            db.connect(households.path(1))
        central = os.path.join(self.dir, "central.db")
        db.connect(central).close()
        os.replace(central, households.path(2))
        with self.assertRaises(db.WrongKindOfDatabase):
            households.conn(2)


class Removing(HouseholdTest):
    def test_removing_takes_the_wal_files_and_the_pre_migration_copies_and_only_this_households(self):
        households.create(1)
        households.create(2)
        c = households.conn(1)
        c.execute("INSERT INTO notice(kind,title,created_at) VALUES('x','y',?)", (db.iso(),))   # makes -wal and -shm
        self.assertTrue(os.path.exists(households.path(1) + "-wal"))
        os.makedirs(households.pre_migrate_dir())
        for name in ("1-v1-20261119T000000-abc123.db", "2-v1-20261119T000000-abc123.db", "11-v1-20261119T000000-abc123.db"):
            open(os.path.join(households.pre_migrate_dir(), name), "w").close()
        households.remove(1)
        self.assertEqual([n for n in os.listdir(self.dir) if n.startswith("1.")], [])
        self.assertTrue(os.path.exists(households.path(2)))
        self.assertEqual(sorted(os.listdir(households.pre_migrate_dir())),
                         ["11-v1-20261119T000000-abc123.db", "2-v1-20261119T000000-abc123.db"])
        households.remove(1)                                  # again, and for one that never existed: fine
        households.remove(99)
        self.assertEqual(households.ids(), [2])


def add_column(c):
    c.execute("ALTER TABLE notice ADD COLUMN seen TEXT")


class Migrating(HouseholdTest):
    def test_a_household_below_the_current_version_is_migrated_on_first_open_after_a_backup(self):
        households.create(1)
        households.conn(1).execute("INSERT INTO notice(kind,title,created_at) VALUES('x','keep',?)", (db.iso(),))
        households.forget_all()
        with mock.patch.object(households, "HOUSEHOLD_MIGRATIONS", [add_column]):
            self.assertEqual(households.behind(), [1])
            c = households.conn(1)                                          # the first open migrates
            self.assertEqual(c.execute("PRAGMA user_version").fetchone()[0], 2)
            self.assertEqual(c.execute("SELECT title FROM notice").fetchone()[0], "keep")
            c.execute("UPDATE notice SET seen='yes'")
            self.assertEqual(households.behind(), [])
        copies = os.listdir(households.pre_migrate_dir())
        self.assertEqual(len(copies), 1)
        self.assertTrue(copies[0].startswith("1-v1-"))
        old = sqlite3.connect(os.path.join(households.pre_migrate_dir(), copies[0]))
        self.assertEqual(old.execute("PRAGMA user_version").fetchone()[0], 1)    # restorable as it was
        self.assertEqual(old.execute("SELECT title FROM notice").fetchone()[0], "keep")

    def test_the_startup_sweep_migrates_them_all_and_one_failing_household_does_not_stop_the_rest(self):
        for i in (1, 2, 3):
            households.create(i)
        households.forget_all()
        sqlite3.connect(households.path(2)).execute("DROP TABLE notice").connection.commit()   # 2 is damaged: its step fails

        with mock.patch.object(households, "HOUSEHOLD_MIGRATIONS", [add_column]):
            self.assertEqual(households.behind(), [1, 2, 3])
            failed = households.sweep()
            self.assertEqual(list(failed), [2])
            self.assertEqual(households.behind(), [2])                       # the count a health check reports
            self.assertEqual(households.conn(1).execute("PRAGMA user_version").fetchone()[0], 2)
            self.assertEqual(households.conn(3).execute("PRAGMA user_version").fetchone()[0], 2)
            self.assertEqual(sqlite3.connect(households.path(2)).execute("PRAGMA user_version").fetchone()[0], 1)

    def test_a_household_being_made_right_now_is_not_counted_as_behind(self):
        os.makedirs(self.dir, exist_ok=True)
        open(households.path(8), "w").close()                                # created, schema not committed yet
        self.assertEqual(households.behind(), [])

    def test_a_household_newer_than_the_code_is_refused(self):
        with mock.patch.object(households, "HOUSEHOLD_MIGRATIONS", [add_column]):
            households.create(1)                                              # a newer release made it: version 2
        households.forget_all()
        with self.assertRaises(db.DatabaseNewerThanCode):
            households.conn(1)
        self.assertEqual(households.behind(), [1])

    def test_two_threads_opening_a_household_that_needs_a_step_apply_it_once(self):
        households.create(1)
        households.forget_all()
        ran = []
        gate = threading.Barrier(4)

        def step(c):
            ran.append(1)
            c.execute("ALTER TABLE notice ADD COLUMN seen TEXT")             # a second run would fail on this

        errors = []

        def open_it():
            try:
                gate.wait()
                households.conn(1)
            except Exception as err:                                          # pragma: no cover
                errors.append(err)
            finally:
                households.forget_all()
        with mock.patch.object(households, "HOUSEHOLD_MIGRATIONS", [step]):
            threads = [threading.Thread(target=open_it) for _ in range(4)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
        self.assertEqual((errors, len(ran)), ([], 1))


if __name__ == "__main__":
    unittest.main()
