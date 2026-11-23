"""Admin foundation (docs/ADMIN.md): the first real central migration, the admins table, the audit table and the gate on /api/admin.

The point of most of these: an admin is not a way into a family. The gate, the key sets and the source lint are how that is kept true.
"""
import datetime as dt
import os
import re
import json
import sqlite3
import subprocess
import stat
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
        self.assertEqual(c.execute("PRAGMA user_version").fetchone()[0], len(db.MIGRATIONS) + 1)
        self.assertEqual(c.execute("SELECT email, created_at FROM session").fetchone()[:], ("keep@example.com", None))
        self.assertEqual(c.execute("SELECT value FROM setting WHERE key='keep'").fetchone()[0], "me")
        tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({"app_admin", "admin_audit"} <= tables)
        c.close()
        c = db.connect(path)                                        # running it again changes nothing
        self.assertEqual(c.execute("PRAGMA user_version").fetchone()[0], len(db.MIGRATIONS) + 1)
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
        for bad in ("a\x1b[2J@example.com", "a\tb@example.com", "a\u202eb@example.com", "", "no-at", "a@b", "a b@example.com", "@x.com", "x@", "a@@b.com", "x" * 250 + "@b.com", None):
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
        rules = sorted((r.rule, m) for r in api.app.url_map.iter_rules() if r.rule.startswith("/api/admin")
                       for m in [tuple(sorted(r.methods - {"HEAD", "OPTIONS"}))])
        self.assertEqual(rules, [("/api/admin/admins", ("GET",)), ("/api/admin/admins", ("POST",)), ("/api/admin/admins/remove", ("POST",)),
                                 ("/api/admin/audit", ("GET",)), ("/api/admin/logs", ("POST",)),
                                 ("/api/admin/logs/<rid>", ("GET",)), ("/api/admin/logs/sources", ("GET",)),
                                 ("/api/admin/releases", ("GET",)), ("/api/admin/stepup", ("GET",)), ("/api/admin/stepup", ("POST",)),
                                 ("/api/admin/stepup/code", ("POST",))])


BRIDGE_CODE = os.path.join(os.path.dirname(CONTROLLER), "deploy", "native", "bin")


@unittest.skipUnless(os.path.isfile(os.path.join(BRIDGE_CODE, "treeline_bridge.py")),
                     "needs deploy/native/bin beside controller/ (CI's checkout has it; the dev container mounts only controller/)")
class Logs(unittest.TestCase):
    """The app's half of the log bridge, run against the REAL root half (treeline_bridge.run_once, stdlib only) in temp folders:
    only journalctl is replaced."""

    def setUp(self):
        import sys
        from unittest import mock
        from treeline import admin
        sys.path.insert(0, BRIDGE_CODE)
        import treeline_bridge
        self.bridge = treeline_bridge
        d = tempfile.mkdtemp(prefix="treeline-bridge-")
        self.req, self.out = os.path.join(d, "req"), os.path.join(d, "out")
        os.mkdir(self.req)
        os.mkdir(self.out)
        self.audit_path = os.path.join(d, "audit.log")
        for name, value in (("BRIDGE_REQ", self.req), ("BRIDGE_OUT", self.out)):
            patcher = mock.patch.object(admin, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.a = make_admin()

    def answer(self):
        return self.bridge.run_once(os.getuid(), req_dir=self.req, out_dir=self.out, audit_path=self.audit_path,
                                    journal=lambda req: (f"journal for {req['source']} by mail parent@example.com", False))

    def test_a_request_goes_through_the_root_helper_and_back(self):
        r = self.a.get("/api/admin/logs/sources").get_json()
        self.assertTrue(r["installed"])
        r = self.a.post("/api/admin/logs", {"source": "deploy", "lines": 20, "since": "1h"})
        self.assertEqual(r.status_code, 202, r.get_json())
        rid = r.get_json()["id"]
        self.assertEqual(self.a.get(f"/api/admin/logs/{rid}").get_json(), {"status": "pending"})
        self.assertEqual(self.answer(), [(rid, "ok")])
        got = self.a.get(f"/api/admin/logs/{rid}").get_json()
        self.assertEqual(got["status"], "ok")
        self.assertEqual(got["text"], "journal for deploy by mail [email]", "the helper's redaction reaches the page")
        self.assertEqual(os.listdir(self.req), [])

    def test_a_large_answer_full_of_non_ascii_text_is_still_read(self):
        """256 KiB of text becomes far more once JSON-escaped; the app read only 512 KiB and failed (a review note)."""
        rid = self.a.post("/api/admin/logs", {"source": "deploy", "lines": 1000, "since": "boot"}).get_json()["id"]
        self.bridge.run_once(os.getuid(), req_dir=self.req, out_dir=self.out, audit_path=self.audit_path,
                             journal=lambda req: ("é\u2603" * 90000, True))
        got = self.a.get(f"/api/admin/logs/{rid}").get_json()
        self.assertEqual((got["status"], got["truncated"], len(got["text"])), ("ok", True, 180000))

    def test_the_request_the_app_writes_is_exactly_what_the_helper_accepts(self):
        rid = self.a.post("/api/admin/logs", {"source": "caddy", "lines": 5, "since": "boot"}).get_json()["id"]
        with open(os.path.join(self.req, f"{rid}.json"), "rb") as f:
            data = f.read()
        req = self.bridge.parse_request(data, f"{rid}.json")
        self.assertEqual((req["source"], req["lines"], req["since"], req["by"]), ("caddy", 5, "boot", self.a.email))
        self.assertEqual(stat.S_IMODE(os.stat(os.path.join(self.req, f"{rid}.json")).st_mode), 0o600)

    def test_only_listed_values_are_accepted(self):
        for body in ({"source": "api"}, {"source": "treeline-controller"}, {"source": "deploy", "since": "1y"},
                     {"source": "deploy", "lines": 0}, {"source": "deploy", "lines": "5"}, {"source": "deploy", "lines": 5000}, {}):
            self.assertEqual(self.a.post("/api/admin/logs", body).status_code, 400, body)
        self.assertEqual(os.listdir(self.req), [])

    def test_each_view_is_audited_without_the_text(self):
        self.a.post("/api/admin/logs", {"source": "backup", "lines": 9, "since": "6h"})
        row = db.list_audit(central(), 1)[0]
        self.assertEqual((row["action"], row["target_id"], row["detail"]), ("logs_view", "backup", "lines=9 since=6h"))

    def test_without_the_helper_the_page_says_so(self):
        os.rmdir(self.req)
        self.assertFalse(self.a.get("/api/admin/logs/sources").get_json()["installed"])
        r = self.a.post("/api/admin/logs", {"source": "deploy"})
        self.assertEqual((r.status_code, r.get_json()["code"]), (503, "bridge_missing"))

    def test_a_result_id_must_be_an_id(self):
        for bad in ("../../etc/passwd", "x" * 32, "0" * 31):
            self.assertEqual(self.a.get(f"/api/admin/logs/{bad}").status_code, 404, bad)

    def test_releases_show_what_the_helper_last_wrote_and_only_known_keys(self):
        self.assertIsNone(self.a.get("/api/admin/releases").get_json()["report"])
        report = {"current": "v0.2.0", "previous": None, "failed": ["v0.1.9"], "asterisk": "24.0.0-t1", "error": None,
                  "published": [{"version": "v0.3.0", "published_at": "2026-11-24T10:00:00Z", "newer": True, "failed": False, "extra": "x"}]}
        self.bridge.refresh_releases(out_dir=self.out, run=lambda *a, **k: subprocess.CompletedProcess(a, 0, json.dumps(report), ""))
        r = self.a.get("/api/admin/releases").get_json()
        self.assertEqual(r["report"]["current"], "v0.2.0")
        self.assertEqual(r["report"]["published"], [{"version": "v0.3.0", "published_at": "2026-11-24T10:00:00Z", "newer": True, "failed": False}])
        self.assertIn("at", r["report"])
        self.assertEqual(Person().get("/api/admin/releases").status_code, 404)

    def test_a_non_admin_cannot_ask_or_read(self):
        p = Person()
        self.assertEqual(p.post("/api/admin/logs", {"source": "deploy"}).status_code, 404)
        self.assertEqual(p.get("/api/admin/logs/" + "0" * 32).status_code, 404)
        self.assertEqual(p.get("/api/admin/logs/sources").status_code, 404)
        self.assertEqual(os.listdir(self.req), [])


class StepUp(unittest.TestCase):
    """Actions that change something need a fresh Google sign-in from the last 15 minutes, on top of a young admin session."""

    def setUp(self):
        import base64
        import time
        import urllib.parse
        from unittest import mock
        from treeline import google
        self.google, self.mock, self.b64, self.time, self.up = google, mock, base64, time, urllib.parse
        google.reset()
        patch = mock.patch.dict(os.environ, {"TREELINE_GOOGLE_CLIENT_ID": "cid-test", "TREELINE_GOOGLE_CLIENT_SECRET": "x" * 32})
        patch.start()
        self.addCleanup(patch.stop)
        self.a = make_admin()

    def start(self, person=None):
        r = (person or self.a).post("/api/admin/stepup")
        self.assertEqual(r.status_code, 200, r.get_json())
        q = self.up.parse_qs(self.up.urlparse(r.get_json()["url"]).query)
        return q

    def callback(self, q, cookie_jar=client, **claims):
        token_claims = {"iss": "https://accounts.google.com", "aud": "cid-test", "exp": self.time.time() + 600, "email": self.a.email,
                        "email_verified": True, "nonce": q["nonce"][0], "auth_time": int(self.time.time())}
        token_claims.update(claims)
        token_claims = {k: v for k, v in token_claims.items() if v is not None}
        jwt = "e30." + self.b64.urlsafe_b64encode(json.dumps(token_claims).encode()).rstrip(b"=").decode() + ".sig"
        with self.mock.patch.object(self.google, "post_form", lambda url, fields, timeout=10: {"id_token": jwt}):
            r = cookie_jar.get(f"/api/auth/google/callback?code=c&state={q['state'][0]}")
        return r.headers.get("Location", "")

    def stepped(self, person=None):
        return central().execute("SELECT stepped_up_at FROM session WHERE token_hash=?",
                                 (db.hash_token((person or self.a).token),)).fetchone()[0]

    def test_an_action_without_a_step_up_is_refused_and_says_why(self):
        target = new_email()
        r = self.a.post("/api/admin/admins", {"email": target})
        self.assertEqual((r.status_code, r.get_json()["code"]), (403, "needs_stepup"))
        self.assertFalse(db.is_admin(central(), target))

    def test_google_is_asked_to_ask_for_the_password_again(self):
        q = self.start()
        self.assertEqual((q["prompt"][0], q["max_age"][0], q["login_hint"][0]), ("login", "0", self.a.email))

    def test_a_fresh_google_sign_in_confirms_this_session_only_and_makes_no_new_one(self):
        other = make_admin()
        before = central().execute("SELECT count(*) FROM session").fetchone()[0]
        self.assertTrue(self.callback(self.start()).endswith("/parent/#/admin/stepup.ok"))
        self.assertIsNotNone(self.stepped())
        self.assertIsNone(self.stepped(other), "another admin's session is untouched")
        self.assertEqual(central().execute("SELECT count(*) FROM session").fetchone()[0], before, "no session was made")
        r = self.a.post("/api/admin/admins", {"email": "New@Example.com"})
        self.assertEqual(r.status_code, 200, r.get_json())
        self.assertTrue(db.is_admin(central(), "new@example.com"))
        self.assertEqual(db.list_audit(central(), 1)[0]["action"], "admin_add")

    def test_what_does_not_prove_a_fresh_sign_in_is_refused(self):
        start_t = int(self.time.time())
        for claims in ({"auth_time": None}, {"auth_time": start_t - 3600}, {"auth_time": "now"}, {"auth_time": start_t + 3600},
                       {"email": "someone-else@example.com"}):
            with self.subTest(claims=claims):
                self.assertTrue(self.callback(self.start(), **claims).endswith("/parent/#/admin/stepup.failed"))
                self.assertIsNone(self.stepped())

    def test_the_callback_in_another_browser_confirms_nothing(self):
        q = self.start()
        other_browser = api.app.test_client()
        loc = self.callback(q, cookie_jar=other_browser)
        self.assertNotIn("stepup.ok", loc)
        self.assertIsNone(self.stepped())

    def test_a_step_up_lasts_fifteen_minutes(self):
        self.callback(self.start())
        self.assertEqual(self.a.post("/api/admin/admins", {"email": "x1@example.com"}).status_code, 200)
        central().execute("UPDATE session SET stepped_up_at=? WHERE token_hash=?",
                          (db.iso(db.utcnow() - dt.timedelta(minutes=16)), db.hash_token(self.a.token)))
        self.assertEqual(self.a.post("/api/admin/admins", {"email": "x2@example.com"}).get_json()["code"], "needs_stepup")
        self.assertFalse(self.a.get("/api/admin/stepup").get_json()["confirmed"])

    def test_the_emailed_code_stands_in_for_google_outside_production_only(self):
        code = client.post("/api/auth/request", json={"email": self.a.email}).get_json()["dev_code"]
        r = self.a.post("/api/admin/stepup/code", {"code": code})
        self.assertEqual(r.status_code, 200, r.get_json())
        self.assertTrue(self.a.get("/api/admin/stepup").get_json()["confirmed"])
        from treeline import prod
        with self.mock.patch.object(prod, "is_production", lambda: True):
            self.assertEqual(self.a.post("/api/admin/stepup/code", {"code": "123456"}).status_code, 404)

    def test_removing_admins_needs_the_step_up_and_never_removes_the_last(self):
        code = client.post("/api/auth/request", json={"email": self.a.email}).get_json()["dev_code"]
        self.a.post("/api/admin/stepup/code", {"code": code})
        for e in [x["email"] for x in db.list_admins(central()) if x["email"] != self.a.email]:
            db.remove_admin(central(), e, "test")
        r = self.a.post("/api/admin/admins/remove", {"email": self.a.email})
        self.assertEqual((r.status_code, r.get_json()["code"]), (409, "admin_refused"))
        self.a.post("/api/admin/admins", {"email": "second@example.com"})
        self.assertEqual(self.a.post("/api/admin/admins/remove", {"email": "second@example.com"}).status_code, 200)
        self.assertEqual(self.a.post("/api/admin/admins", {"email": "not an address"}).status_code, 400)

    def test_a_non_admin_cannot_start_a_step_up_or_act(self):
        p = Person()
        self.assertEqual(p.post("/api/admin/stepup").status_code, 404)
        self.assertEqual(p.post("/api/admin/admins", {"email": "me@example.com"}).status_code, 404)


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
