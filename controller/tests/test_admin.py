"""Admin foundation (docs/ADMIN.md): the first real central migration, the admins table, the audit table and the gate on /api/admin.

The point of most of these: an admin is not a way into a family. The gate, the key sets and the source lint are how that is kept true.
"""
import datetime as dt
import os
import re
import sqlite3
import tempfile
import threading
import unittest

from tests import helpers  # noqa: F401
from tests.test_api import Person, client, make_house, new_email
from treeline import api, db

CONTROLLER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def central():
    return db.local_conn()


def make_admin(email=None, by="test"):
    p = Person(email)
    db.add_admin(central(), p.email, by)
    return p


def age_session(person, hours):
    """Make this person's session look like it began `hours` ago."""
    central().execute("UPDATE session SET created_at=? WHERE token_hash=?",
                      (db.iso(db.utcnow() - dt.timedelta(hours=hours)), db.hash_token(person.token)))


class Migration(unittest.TestCase):
    def path(self):
        return os.path.join(tempfile.mkdtemp(prefix="treeline-adm-"), "t.db")

    def test_a_file_at_version_one_is_moved_to_two_and_keeps_its_data(self):
        """Rule 6 of DATA_LAYER.md: build the file at the PREVIOUS schema, put data in it, then migrate it."""
        path = self.path()
        c = db.connect(path, migrations=[])                         # the baseline, version 1
        self.assertEqual(c.execute("PRAGMA user_version").fetchone()[0], 1)
        c.execute("INSERT INTO session(token_hash,email,expires_at) VALUES('h','keep@example.com','2999-01-01T00:00:00+00:00')")
        c.execute("INSERT INTO setting(key,value) VALUES('keep','me')")
        c.close()
        c = db.connect(path)                                        # the real list
        self.assertEqual(c.execute("PRAGMA user_version").fetchone()[0], 2)
        self.assertEqual(c.execute("SELECT email, created_at FROM session").fetchone()[:], ("keep@example.com", None))
        self.assertEqual(c.execute("SELECT value FROM setting WHERE key='keep'").fetchone()[0], "me")
        tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({"app_admin", "admin_audit"} <= tables)
        c.close()
        c = db.connect(path)                                        # running it again changes nothing
        self.assertEqual(c.execute("PRAGMA user_version").fetchone()[0], 2)
        c.close()

    def test_a_pre_migration_copy_is_taken_and_is_the_old_version(self):
        path = self.path()
        db.connect(path, migrations=[]).close()
        db.connect(path).close()
        folder = os.path.join(os.path.dirname(path), "pre-migrate")
        copies = os.listdir(folder)
        self.assertEqual(len(copies), 1)
        old = sqlite3.connect(os.path.join(folder, copies[0]))
        self.assertEqual(old.execute("PRAGMA user_version").fetchone()[0], 1)
        self.assertEqual(old.execute("SELECT count(*) FROM sqlite_master WHERE name='app_admin'").fetchone()[0], 0)
        old.close()

    def test_a_later_failing_step_leaves_this_one_in_place(self):
        path = self.path()
        db.connect(path, migrations=[]).close()
        def boom(conn):
            conn.execute("CREATE TABLE half(x)")
            raise RuntimeError("nope")
        with self.assertRaises(RuntimeError):
            db.connect(path, migrations=[db.add_admin_tables, boom])
        c = sqlite3.connect(path)
        self.assertEqual(c.execute("PRAGMA user_version").fetchone()[0], 2)
        self.assertEqual(c.execute("SELECT count(*) FROM sqlite_master WHERE name='half'").fetchone()[0], 0)
        c.close()


class Admins(unittest.TestCase):
    def setUp(self):
        self.c = db.connect(":memory:")

    def test_add_list_remove_and_re_add(self):
        self.assertEqual(db.add_admin(self.c, " Boss@Example.COM ", "ssh:me"), "boss@example.com")
        db.add_admin(self.c, "second@example.com", "boss@example.com")
        self.assertEqual([a["email"] for a in db.list_admins(self.c)], ["boss@example.com", "second@example.com"])
        db.remove_admin(self.c, "second@example.com", "boss@example.com")
        self.assertFalse(db.is_admin(self.c, "second@example.com"))
        db.add_admin(self.c, "second@example.com", "ssh:me")          # a removed admin can be brought back (the ssh recovery path)
        self.assertTrue(db.is_admin(self.c, "second@example.com"))
        self.assertEqual([a["added_by"] for a in db.list_admins(self.c) if a["email"] == "second@example.com"], ["ssh:me"])

    def test_the_last_admin_cannot_be_removed(self):
        db.add_admin(self.c, "only@example.com", "ssh:me")
        with self.assertRaises(db.AdminError):
            db.remove_admin(self.c, "only@example.com", "only@example.com")
        self.assertTrue(db.is_admin(self.c, "only@example.com"))

    def test_removing_someone_who_is_not_an_admin_says_so(self):
        db.add_admin(self.c, "a@example.com", "x")
        with self.assertRaises(db.AdminError) as cm:
            db.remove_admin(self.c, "nobody@example.com", "a@example.com")
        self.assertIn("not an admin", str(cm.exception))

    def test_bad_addresses_are_refused(self):
        for bad in ("", "no-at", "a@b", "a b@example.com", "@x.com", "x@", "a@@b.com", "x" * 250 + "@b.com", None):
            with self.assertRaises(db.AdminError, msg=repr(bad)):
                db.add_admin(self.c, bad, "x")

    def test_two_admins_removing_each_other_at_once_leave_one(self):
        folder = tempfile.mkdtemp(prefix="treeline-adm-")
        path = os.path.join(folder, "t.db")
        c = db.connect(path)
        db.add_admin(c, "a@example.com", "x")
        db.add_admin(c, "b@example.com", "x")
        c.close()
        results, barrier = [], threading.Barrier(2)
        def go(me, other):
            conn = db.connect(path)
            barrier.wait()
            try:
                db.remove_admin(conn, other, me)
                results.append("removed")
            except db.AdminError:
                results.append("refused")
            conn.close()
        ts = [threading.Thread(target=go, args=("a@example.com", "b@example.com")),
              threading.Thread(target=go, args=("b@example.com", "a@example.com"))]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        c = db.connect(path)
        self.assertEqual(len(db.list_admins(c)), 1, results)
        c.close()

    def test_the_audit_log_pages_and_trims(self):
        for i in range(5):
            db.log_admin(self.c, "a@example.com", "view", "treehouse", i)
        rows = db.list_audit(self.c, 2)
        self.assertEqual([r["target_id"] for r in rows], ["4", "3"])
        self.assertEqual([r["target_id"] for r in db.list_audit(self.c, 2, before=rows[-1]["id"])], ["2", "1"])
        self.c.execute("UPDATE admin_audit SET at='2000-01-01T00:00:00+00:00' WHERE id<=2")
        db.trim_admin_audit(self.c)
        self.assertEqual(len(db.list_audit(self.c, 50)), 3)


class Gate(unittest.TestCase):
    ROUTES = ("/api/admin/admins", "/api/admin/audit")

    def test_nobody_signed_in_is_told_to_sign_in(self):
        for path in self.ROUTES:
            self.assertEqual(client.get(path).status_code, 401, path)

    def test_a_signed_in_person_who_is_not_an_admin_gets_what_an_unknown_address_gets(self):
        p = Person()
        unknown = client.get("/api/admin/no-such-thing", headers=p.h())
        for path in self.ROUTES:
            r = p.get(path)
            self.assertEqual(r.status_code, 404, path)
            self.assertEqual(r.get_json(), unknown.get_json(), "no hint that the page exists")

    def test_an_admin_with_a_young_session_gets_in(self):
        a = make_admin()
        r = a.get("/api/admin/admins")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(list(r.get_json()), ["admins"])
        self.assertEqual({tuple(sorted(x)) for x in r.get_json()["admins"]}, {("added_by", "created_at", "email")})
        r = a.get("/api/admin/audit")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(set(r.get_json()), {"audit", "next"})

    def test_a_sign_in_records_when_the_session_began(self):
        p = Person()
        row = central().execute("SELECT created_at FROM session WHERE token_hash=?", (db.hash_token(p.token),)).fetchone()
        self.assertIsNotNone(row["created_at"])

    def test_an_old_session_or_one_with_no_start_time_must_sign_in_again(self):
        a = make_admin()
        age_session(a, 13)
        r = a.get("/api/admin/admins")
        self.assertEqual((r.status_code, r.get_json()["code"]), (401, "needs_fresh_signin"))
        age_session(a, 11)
        self.assertEqual(a.get("/api/admin/admins").status_code, 200)
        central().execute("UPDATE session SET created_at=NULL WHERE token_hash=?", (db.hash_token(a.token),))
        self.assertEqual(a.get("/api/admin/admins").get_json()["code"], "needs_fresh_signin", "sessions from before the column")

    def test_a_removed_admin_loses_the_page_at_once_even_with_a_young_session(self):
        a, b = make_admin(), make_admin()
        db.remove_admin(central(), b.email, a.email)
        self.assertEqual(b.get("/api/admin/admins").status_code, 404)
        self.assertEqual(a.get("/api/admin/admins").status_code, 200)

    def test_me_says_whether_to_draw_the_menu_link_and_nothing_else_changes(self):
        p, a = Person(), make_admin()
        self.assertIs(p.get("/api/me").get_json()["admin"], False)
        self.assertIs(a.get("/api/me").get_json()["admin"], True)

    def test_the_admin_routes_are_exactly_these(self):
        """A new /api/admin route has to be a deliberate edit of this list (and of docs/ADMIN.md)."""
        rules = sorted((r.rule, tuple(sorted(r.methods - {"HEAD", "OPTIONS"}))) for r in api.app.url_map.iter_rules() if r.rule.startswith("/api/admin"))
        self.assertEqual(rules, [("/api/admin/admins", ("GET",)), ("/api/admin/audit", ("GET",))])


class AnAdminIsNotAWayIntoAFamily(unittest.TestCase):
    def test_an_admin_who_is_also_a_parent_sees_only_their_own_family_on_family_routes(self):
        mine = make_house("Mine", email=new_email())
        other = make_house("Other", email=new_email())
        db.add_admin(central(), mine.email, "test")
        r = mine.get("/api/me").get_json()
        self.assertEqual(r["treehouse"]["name"], "Mine")
        self.assertTrue(r["admin"])
        # the family routes work exactly as for any parent: nothing of the other family comes back
        self.assertNotIn("Other", mine.get("/api/treehouse").get_data(as_text=True))
        self.assertNotIn(other.email, mine.get("/api/admin/admins").get_data(as_text=True))

    def test_admin_routes_never_return_a_family_or_a_handset(self):
        a = make_admin()
        make_house("Secret family", email=new_email())
        for path in ("/api/admin/admins", "/api/admin/audit"):
            body = a.get(path).get_data(as_text=True)
            self.assertNotIn("Secret family", body, path)

    def test_the_module_cannot_touch_a_family_by_construction(self):
        with open(os.path.join(CONTROLLER, "treeline", "admin.py"), encoding="utf-8") as f:
            code = "\n".join(l for l in f.read().splitlines() if not l.lstrip().startswith("#"))
        code = re.sub(r'"""(.|\n)*?"""', "", code)            # the docstring names what is forbidden
        for forbidden in (r"\bhouseholds\b", r"INSERT\s+INTO\s+(grown_up|handset|session|pairing|ladder_code)", r"\bth_json\b",
                          r"\bhandset_json\b", r"\bg\.th\b", r"\bg\.gu\b", r"\bcreate_handset\b", r"\bcreate_treehouse\b"):
            self.assertIsNone(re.search(forbidden, code, re.I), forbidden)


if __name__ == "__main__":
    unittest.main()
