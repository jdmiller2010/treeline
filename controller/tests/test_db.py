import sqlite3
import tempfile
import os
import unittest

from tests import helpers  # noqa: F401  (points the app at a throwaway database)
from treeline import db


class Migrations(unittest.TestCase):
    def test_an_old_database_gains_the_new_columns(self):
        path = os.path.join(tempfile.mkdtemp(), "old.db")
        old = sqlite3.connect(path)
        # The handset table as it was before provision_secret existed.
        old.executescript("""CREATE TABLE handset (id INTEGER PRIMARY KEY, treehouse_id INTEGER NOT NULL,
          kind TEXT NOT NULL, name TEXT NOT NULL, sip_user TEXT NOT NULL UNIQUE, sip_md5 TEXT NOT NULL,
          provision_token TEXT, last_seen TEXT, online INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL,
          removed_at TEXT);
          INSERT INTO handset(treehouse_id,kind,name,sip_user,sip_md5,created_at) VALUES(1,'ata','Hall','hx','m','t');""")
        old.close()
        conn = db.connect(path)
        self.assertTrue(db._has_column(conn, "handset", "provision_secret"))
        self.assertEqual(conn.execute("SELECT name FROM handset").fetchone()["name"], "Hall")   # data kept
        conn.execute("UPDATE handset SET provision_secret='s'")                                 # and usable
        self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], len(db.MIGRATIONS))

    def test_the_old_number_rest_table_is_dropped_and_nothing_else_is_lost(self):
        path = os.path.join(tempfile.mkdtemp(), "rest.db")
        old = sqlite3.connect(path)
        old.executescript("""CREATE TABLE number_rest (number TEXT PRIMARY KEY, available_after TEXT NOT NULL);
          INSERT INTO number_rest VALUES('4321','2999-01-01T00:00:00+00:00');
          CREATE TABLE treehouse (id INTEGER PRIMARY KEY, name TEXT NOT NULL, number TEXT, created_at TEXT NOT NULL);
          INSERT INTO treehouse(name,number,created_at) VALUES('Keeps','1234','t');""")
        old.close()
        conn = db.connect(path)
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertNotIn("number_rest", tables)
        self.assertEqual(conn.execute("SELECT number FROM treehouse WHERE name='Keeps'").fetchone()[0], "1234")
        self.assertTrue(db.number_is_free(conn, "4321"))                  # a number that was resting is simply free

    def test_running_migrations_twice_changes_nothing(self):
        conn = helpers.fresh_conn()
        db.migrate(conn)
        db.migrate(conn)
        self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], len(db.MIGRATIONS))


if __name__ == "__main__":
    unittest.main()
