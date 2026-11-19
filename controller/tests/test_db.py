"""The database layer: markers, refusals and the migration runner.

There are no real migration steps yet (the layout in docs/DATA_LAYER.md is the baseline), so these
use test-only step lists. The first real step must add its own test that builds a file at the
previous schema (rule 6 of "Schema changes after go-live").
"""
import hashlib
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest

from tests import helpers  # noqa: F401  (points the app at a throwaway database)
from treeline import db

CONTROLLER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def new_path(name="t.db"):
    return os.path.join(tempfile.mkdtemp(prefix="treeline-db-"), name)


def digest(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def pragma(path, name):
    c = sqlite3.connect(path)
    try:
        return c.execute(f"PRAGMA {name}").fetchone()[0]
    finally:
        c.close()


def add_note_column(c):
    c.execute("ALTER TABLE setting ADD COLUMN note TEXT")


def add_flag_table(c):
    c.execute("CREATE TABLE flag (id INTEGER PRIMARY KEY, name TEXT)")
    c.execute("INSERT INTO flag(name) VALUES('first')")


class Markers(unittest.TestCase):
    def test_a_new_file_gets_the_schema_the_marker_and_version_one(self):
        path = new_path()
        db.connect(path).close()
        self.assertEqual(pragma(path, "application_id"), db.CENTRAL_APP_ID)
        self.assertEqual(pragma(path, "user_version"), 1)
        c = db.connect(path)
        tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({"treehouse", "handset", "string", "call", "call_event", "grown_up"} <= tables)
        self.assertEqual(c.execute("PRAGMA journal_mode").fetchone()[0], "wal")
        self.assertEqual(c.execute("PRAGMA foreign_keys").fetchone()[0], 1)

    def test_an_old_layout_database_is_refused_with_the_clean_message_and_not_modified(self):
        path = new_path("old.db")
        old = sqlite3.connect(path)
        old.executescript("""CREATE TABLE treehouse (id INTEGER PRIMARY KEY, name TEXT NOT NULL, number TEXT,
          created_at TEXT NOT NULL); INSERT INTO treehouse(name,number,created_at) VALUES('Keeps','1234','t');""")
        old.close()
        before = digest(path)
        with self.assertRaises(db.OldLayoutDatabase) as cm:
            db.connect(path)
        self.assertIn("./dev clean", str(cm.exception))
        self.assertEqual(digest(path), before)
        self.assertEqual(pragma(path, "application_id"), 0)
        self.assertEqual(pragma(path, "user_version"), 0)

    def test_an_old_layout_database_that_already_had_a_version_is_refused_too(self):
        path = new_path("old2.db")
        old = sqlite3.connect(path)
        old.executescript("CREATE TABLE handset (id INTEGER PRIMARY KEY); PRAGMA user_version=8;")
        old.close()
        before = digest(path)
        with self.assertRaises(db.OldLayoutDatabase):
            db.connect(path)
        self.assertEqual(digest(path), before)

    def test_a_household_file_is_not_a_central_database(self):
        path = new_path()
        c = sqlite3.connect(path)
        c.executescript(f"CREATE TABLE meta (id INTEGER); PRAGMA application_id={db.HOUSEHOLD_APP_ID}; PRAGMA user_version=1;")
        c.close()
        with self.assertRaises(db.WrongKindOfDatabase):
            db.connect(path)

    def test_a_database_newer_than_the_code_is_refused_and_not_modified(self):
        path = new_path()
        db.connect(path, migrations=[add_note_column]).close()          # a newer release made this: version 2
        before = digest(path)
        with self.assertRaises(db.DatabaseNewerThanCode) as cm:
            db.connect(path)                                              # this code knows version 1
        self.assertIn("version 2", str(cm.exception))
        self.assertEqual(digest(path), before)
        self.assertEqual(pragma(path, "user_version"), 2)

    def test_a_refused_connection_is_closed_not_leaked(self):
        path = new_path()
        db.connect(path, migrations=[add_note_column]).close()
        for _ in range(3):
            with self.assertRaises(db.DatabaseRefused):
                db.connect(path)
        os.remove(path)                              # nothing holds it open: it can go (Windows would refuse otherwise)
        db.connect(path).close()


class Migrations(unittest.TestCase):
    def test_steps_apply_in_order_the_version_moves_and_a_second_run_does_nothing(self):
        path = new_path()
        db.connect(path).close()                                                # version 1, with a row to keep
        c = db.connect(path)
        c.execute("INSERT INTO setting(key,value) VALUES('keep','me')")
        c.close()
        c = db.connect(path, migrations=[add_note_column, add_flag_table])
        self.assertEqual(c.execute("PRAGMA user_version").fetchone()[0], 3)
        self.assertEqual(c.execute("SELECT value FROM setting WHERE key='keep'").fetchone()[0], "me")
        self.assertEqual(c.execute("SELECT name FROM flag").fetchall()[0][0], "first")
        c.execute("UPDATE setting SET note='ok'")                               # the new column works
        c.close()
        db.connect(path, migrations=[add_note_column, add_flag_table]).close()  # again: nothing runs
        self.assertEqual(pragma(path, "user_version"), 3)
        self.assertEqual(sqlite3.connect(path).execute("SELECT count(*) FROM flag").fetchone()[0], 1)   # not run twice

    def test_a_fresh_file_takes_the_baseline_and_then_every_step(self):
        path = new_path()
        c = db.connect(path, migrations=[add_note_column, add_flag_table])
        self.assertEqual(c.execute("PRAGMA user_version").fetchone()[0], 3)
        self.assertIn("note", [r[1] for r in c.execute("PRAGMA table_info(setting)")])
        self.assertEqual(c.execute("SELECT count(*) FROM flag").fetchone()[0], 1)
        self.assertFalse(os.path.exists(os.path.join(os.path.dirname(path), "pre-migrate")))   # nothing to back up

    def test_a_step_that_raises_changes_nothing_and_the_next_start_can_retry(self):
        path = new_path()
        db.connect(path).close()

        def broken(c):
            c.execute("ALTER TABLE setting ADD COLUMN half_done TEXT")
            c.execute("INSERT INTO setting(key,value) VALUES('half','done')")
            raise RuntimeError("boom")

        with self.assertRaises(RuntimeError):
            db.connect(path, migrations=[broken])
        self.assertEqual(pragma(path, "user_version"), 1)
        c = sqlite3.connect(path)
        self.assertNotIn("half_done", [r[1] for r in c.execute("PRAGMA table_info(setting)")])   # the DDL was undone too
        self.assertEqual(c.execute("SELECT count(*) FROM setting WHERE key='half'").fetchone()[0], 0)
        c.close()
        db.connect(path, migrations=[add_note_column]).close()                  # a fixed step goes through
        self.assertEqual(pragma(path, "user_version"), 2)

    def test_a_second_step_failing_keeps_the_first(self):
        path = new_path()
        db.connect(path).close()

        def broken(c):
            raise RuntimeError("boom")

        with self.assertRaises(RuntimeError):
            db.connect(path, migrations=[add_note_column, broken])
        self.assertEqual(pragma(path, "user_version"), 2)                       # step 1 stands (its own transaction)
        db.connect(path, migrations=[add_note_column, add_flag_table]).close()
        self.assertEqual(pragma(path, "user_version"), 3)

    def test_a_process_killed_half_way_through_a_step_leaves_the_file_as_it_was(self):
        path = new_path()
        db.connect(path).close()
        code = f"""
import os, sys
sys.path.insert(0, {CONTROLLER!r})
from treeline import db
def step(c):
    c.execute("ALTER TABLE setting ADD COLUMN note TEXT")
    c.execute("INSERT INTO setting(key,value) VALUES('half','done')")
    os._exit(9)                                  # the machine goes away mid-step
db.connect({path!r}, migrations=[step])
"""
        env = dict(os.environ, TREELINE_DB=new_path())
        r = subprocess.run([sys.executable, "-I", "-c", code], env=env, timeout=60)
        self.assertEqual(r.returncode, 9)
        self.assertEqual(pragma(path, "user_version"), 1)
        c = db.connect(path, migrations=[add_note_column])                      # and it can be run again
        self.assertEqual(c.execute("PRAGMA user_version").fetchone()[0], 2)
        self.assertEqual(c.execute("SELECT count(*) FROM setting WHERE key='half'").fetchone()[0], 0)

    def test_two_threads_starting_at_once_apply_a_step_once(self):
        path = new_path()
        db.connect(path).close()
        ran, errors = [], []
        gate = threading.Barrier(6)

        def step(c):
            ran.append(1)
            time.sleep(0.2)                                                      # long enough for the others to queue up
            c.execute("CREATE TABLE once (id INTEGER)")                          # a second run would fail here

        def start():
            try:
                gate.wait()
                db.connect(path, migrations=[step]).close()
            except Exception as e:                                               # pragma: no cover
                errors.append(e)

        threads = [threading.Thread(target=start) for _ in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        self.assertEqual(len(ran), 1)
        self.assertEqual(pragma(path, "user_version"), 2)

    def test_several_processes_creating_the_same_new_file_at_once_make_it_once(self):
        # Several rounds: the race this guards against (a half-made file looking like an old-layout one) was
        # seen about one round in forty.
        folder = tempfile.mkdtemp()
        env = dict(os.environ, TREELINE_DB=new_path())
        for n in range(12):
            path = os.path.join(folder, f"new{n}.db")
            code = (f"import sys\nsys.path.insert(0, {CONTROLLER!r})\nfrom treeline import db\n"
                    f"db.connect({path!r}).close()\n")
            procs = [subprocess.Popen([sys.executable, "-I", "-c", code], env=env, stderr=subprocess.PIPE)
                     for _ in range(5)]
            results = []
            for p in procs:
                _, err = p.communicate(timeout=60)
                results.append((p.returncode, err.decode()))
            self.assertEqual([r for r in results if r[0]], [], f"round {n}")
            self.assertEqual(pragma(path, "application_id"), db.CENTRAL_APP_ID)
            self.assertEqual(pragma(path, "user_version"), 1)


class PreMigrationBackup(unittest.TestCase):
    def test_a_backup_is_taken_before_a_step_and_restores_to_the_old_version(self):
        path = new_path()
        c = db.connect(path)
        c.execute("INSERT INTO setting(key,value) VALUES('keep','me')")
        c.close()
        db.connect(path, migrations=[add_note_column]).close()
        folder = os.path.join(os.path.dirname(path), "pre-migrate")
        files = os.listdir(folder)
        self.assertEqual(len(files), 1)
        copy = os.path.join(folder, files[0])
        self.assertEqual(oct(os.stat(copy).st_mode & 0o777), "0o600")
        self.assertEqual(oct(os.stat(folder).st_mode & 0o777), "0o700")
        self.assertEqual(pragma(copy, "user_version"), 1)                       # the file as it was before the step
        restored = db.connect(copy)                                              # and it is a working database
        self.assertEqual(restored.execute("SELECT value FROM setting WHERE key='keep'").fetchone()[0], "me")

    def test_no_backup_when_nothing_is_pending(self):
        path = new_path()
        db.connect(path).close()
        db.connect(path).close()
        self.assertFalse(os.path.exists(os.path.join(os.path.dirname(path), "pre-migrate")))

    def test_old_backups_are_deleted_after_seven_days_new_ones_kept(self):
        import datetime as dt
        folder = tempfile.mkdtemp()
        now = db.utcnow()
        old = os.path.join(folder, f"treeline-v1-{(now - dt.timedelta(days=8)):%Y%m%dT%H%M%S}-a1b2c3.db")
        new = os.path.join(folder, f"treeline-v1-{(now - dt.timedelta(days=6)):%Y%m%dT%H%M%S}-a1b2c3.db")
        other = os.path.join(folder, "notes.txt")
        for p in (old, new, other):
            open(p, "w").close()
        db.prune_pre_migrate(folder, now)
        self.assertEqual(sorted(os.listdir(folder)), sorted([os.path.basename(new), "notes.txt"]))
        db.prune_pre_migrate(os.path.join(folder, "missing"), now)               # no folder is fine


if __name__ == "__main__":
    unittest.main()
