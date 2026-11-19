import base64
import datetime as dt
import os
import tempfile
import threading
import unittest
from unittest import mock

from tests import helpers
from treeline import api, db, households, rules

client = api.app.test_client()
_n = [0]


def read_pjsip():
    with open(os.environ["TREELINE_PJSIP_FILE"]) as f:
        return f.read()


def new_email():
    _n[0] += 1
    return f"parent{_n[0]}@example.com"


class Person:
    """A grown-up using the API."""

    def __init__(self, email=None):
        api._hits.clear()  # each test starts with fresh rate limits
        self.email = email or new_email()
        r = client.post("/api/auth/request", json={"email": self.email})
        code = r.get_json()["dev_code"]
        self.token = client.post("/api/auth/verify", json={"email": self.email, "code": code}).get_json()["token"]

    def h(self):
        return {"Authorization": f"Bearer {self.token}"}

    def get(self, path, **kw):
        return client.get(path, headers=self.h(), **kw)

    def post(self, path, json=None):
        return client.post(path, headers=self.h(), json=json or {})

    def patch(self, path, json=None):
        return client.patch(path, headers=self.h(), json=json or {})

    def put(self, path, json=None):
        return client.put(path, headers=self.h(), json=json or {})

    def delete(self, path, json=None):
        return client.delete(path, headers=self.h(), json=json or {})


PIN = "2468"


def make_house(name="Bennett house", tz="America/Los_Angeles", email=None):
    p = Person(email)
    r = p.post("/api/treehouse", {"name": name, "timezone": tz, "ack_911": True, "consent": True, "your_name": "Pat"})
    assert r.status_code == 201, r.get_json()
    p.house = r.get_json()["treehouse"]
    assert p.put("/api/treehouse/parent-code", {"code": PIN}).status_code == 200      # a softphone can't be added without one
    return p


def string_up(a, b):
    code = a.post("/api/ladder-codes").get_json()["code"]
    s = b.post("/api/strings/redeem", {"code": code}).get_json()
    a.post(f"/api/strings/{s['id']}/approve")
    return s["id"]


def add_call(c, caller, callee, started=None, dialed=None, result="connected", reason=None, talk=0, caller_handset=None):
    """A finished call as the engine leaves it: a row in the central ledger, copied into each family's file by the
    real households.record_call. `caller` and `callee` are treehouse ids (callee may be None)."""
    cid = c.execute(
        "INSERT INTO call(started_at,caller_treehouse,caller_handset,callee_treehouse,dialed,state,ended_at,result,reason,talk_sec)"
        " VALUES(?,?,?,?,?,?,?,?,?,?)", (started or db.iso(), caller, caller_handset, callee, dialed or "9999", "ended",
                                        started or db.iso(), result, reason, talk)).lastrowid
    households.record_call(c, cid)
    return cid


class SignIn(unittest.TestCase):
    def test_wrong_code_then_right_code(self):
        email = new_email()
        code = client.post("/api/auth/request", json={"email": email}).get_json()["dev_code"]
        bad = "000000" if code != "000000" else "111111"
        r = client.post("/api/auth/verify", json={"email": email, "code": bad})
        self.assertEqual(r.status_code, 400)
        r = client.post("/api/auth/verify", json={"email": email, "code": code})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_json()["token"])

    def test_code_works_once(self):
        email = new_email()
        code = client.post("/api/auth/request", json={"email": email}).get_json()["dev_code"]
        client.post("/api/auth/verify", json={"email": email, "code": code})
        self.assertEqual(client.post("/api/auth/verify", json={"email": email, "code": code}).status_code, 400)

    def test_five_wrong_tries_lock_the_code(self):
        email = new_email()
        code = client.post("/api/auth/request", json={"email": email}).get_json()["dev_code"]
        bad = "000000" if code != "000000" else "111111"
        for _ in range(5):
            client.post("/api/auth/verify", json={"email": email, "code": bad})
        self.assertEqual(client.post("/api/auth/verify", json={"email": email, "code": code}).status_code, 429)

    def test_expired_code(self):
        email = new_email()
        code = client.post("/api/auth/request", json={"email": email}).get_json()["dev_code"]
        helpers.db.connect().execute("UPDATE login_code SET expires_at=? WHERE email=?",
                                     (db.iso(db.utcnow() - dt.timedelta(minutes=1)), email))
        self.assertEqual(client.post("/api/auth/verify", json={"email": email, "code": code}).status_code, 400)

    def test_bad_email(self):
        self.assertEqual(client.post("/api/auth/request", json={"email": "nope"}).status_code, 400)

    def test_needs_a_token(self):
        self.assertEqual(client.get("/api/me").status_code, 401)
        self.assertEqual(client.get("/api/me", headers={"Authorization": "Bearer nope"}).status_code, 401)

    def test_sign_out(self):
        p = Person()
        self.assertEqual(p.get("/api/me").status_code, 200)
        p.post("/api/auth/signout")
        self.assertEqual(p.get("/api/me").status_code, 401)

    def test_emails_are_rate_limited(self):
        api._hits.clear()
        email = new_email()
        codes = [client.post("/api/auth/request", json={"email": email}).status_code for _ in range(7)]
        self.assertEqual(codes[:5], [200] * 5)
        self.assertEqual(codes[5], 429)


class Treehouse(unittest.TestCase):
    def test_setup_requires_the_911_box(self):
        p = Person()
        r = p.post("/api/treehouse", {"name": "Pine house", "ack_911": False, "consent": True})
        self.assertEqual((r.status_code, r.get_json()["code"]), (400, "ack_911"))

    def test_setup_requires_agreeing_to_the_privacy_notes_and_records_when(self):
        p = Person()
        r = p.post("/api/treehouse", {"name": "Pine house", "ack_911": True})
        self.assertEqual((r.status_code, r.get_json()["code"]), (400, "consent"))
        r = p.post("/api/treehouse", {"name": "Pine house", "ack_911": True, "consent": True})
        self.assertEqual(r.status_code, 201)
        meta = households.meta(r.get_json()["treehouse"]["id"])          # consent lives in the household's own file
        self.assertTrue(meta["consent_at"])
        self.assertEqual(meta["consent_version"], api.PRIVACY_VERSION)
        self.assertEqual(meta["ack_911"], 1)

    def test_setup_gives_a_number_and_safe_defaults(self):
        p = make_house()
        t = p.house
        self.assertRegex(t["number"], r"^[1-9]\d{3}$")
        self.assertEqual(t["quiet"], {"enabled": True, "start": "20:00", "end": "07:00", "days": "1111111"})
        self.assertEqual(t["max_call_minutes"], 30)
        self.assertFalse(t["paused"])

    def test_one_treehouse_per_email(self):
        p = make_house()
        self.assertEqual(p.post("/api/treehouse", {"name": "x", "ack_911": True, "consent": True}).status_code, 409)

    def test_no_treehouse_yet(self):
        p = Person()
        self.assertEqual(p.get("/api/home").status_code, 403)
        self.assertIsNone(p.get("/api/me").get_json()["treehouse"])

    def test_update_rules_and_log_it(self):
        p = make_house()
        r = p.patch("/api/treehouse", {"quiet": {"start": "21:00", "end": "06:30", "days": "1111100"},
                                       "max_call_minutes": 20, "daily_minutes": 60, "paused": True})
        t = r.get_json()
        self.assertEqual((t["quiet"]["start"], t["quiet"]["days"], t["max_call_minutes"], t["daily_minutes"],
                          t["paused"]), ("21:00", "1111100", 20, 60, True))
        actions = p.get("/api/actions").get_json()["actions"]
        kinds = {a["action"] for a in actions}
        self.assertIn("changed_quiet_start", kinds)
        self.assertIn("changed_paused", kinds)
        a = next(a for a in actions if a["action"] == "changed_max_call_minutes")
        self.assertEqual((a["before"], a["after"]), ("30.0", "20.0"))

    def test_validation(self):
        p = make_house()
        for bad in ({"max_call_minutes": 0}, {"max_call_minutes": 500}, {"max_call_minutes": "x"},
                    {"daily_minutes": 1}, {"quiet": {"start": "25:00"}}, {"quiet": {"days": "111"}},
                    {"timezone": "Mars/Base"}, {"name": "  "}, {"retention_days": 3}):
            self.assertEqual(p.patch("/api/treehouse", bad).status_code, 400, bad)

    def test_pause_now(self):
        p = make_house()
        self.assertTrue(p.patch("/api/treehouse", {"paused": True}).get_json()["paused"])
        self.assertTrue(p.get("/api/home").get_json()["treehouse"]["paused"])

    def test_change_number_frees_the_old_one_at_once_and_tells_friends(self):
        a, b = make_house("A"), make_house("B")
        string_up(a, b)
        old = a.house["number"]
        new = a.post("/api/treehouse/number").get_json()["number"]
        self.assertNotEqual(old, new)
        self.assertTrue(db.number_is_free(helpers.db.connect(), old))
        taker = make_house("Taker")
        self.assertEqual(taker.post("/api/treehouse/number", {"number": old}).status_code, 200)     # another family can take it now
        titles = [n["title"] for n in b.get("/api/home").get_json()["notices"]]
        self.assertIn("A has a new number", titles)
        self.assertEqual(a.post("/api/treehouse/number", {"number": b.house["number"]}).status_code, 409)
        self.assertEqual(a.post("/api/treehouse/number", {"number": "0123"}).status_code, 409)

    def test_sitters_can_pause_but_not_change_things(self):
        parent = make_house()
        parent.post("/api/grown-ups", {"email": "sitter@example.com", "role": "sitter"})
        sitter = Person("sitter@example.com")
        self.assertEqual(sitter.get("/api/home").status_code, 200)
        self.assertEqual(sitter.patch("/api/treehouse", {"paused": True}).status_code, 200)
        self.assertEqual(sitter.patch("/api/treehouse", {"max_call_minutes": 5}).status_code, 403)
        self.assertEqual(sitter.patch("/api/treehouse", {"name": "Nope"}).status_code, 403)
        self.assertEqual(sitter.post("/api/ladder-codes").status_code, 403)
        self.assertEqual(sitter.post("/api/handsets", {"kind": "softphone", "name": "x"}).status_code, 403)
        self.assertEqual(sitter.post("/api/grown-ups", {"email": "x@example.com"}).status_code, 403)
        self.assertEqual(sitter.get("/api/calls.csv").status_code, 403)

    def test_sitters_can_turn_quiet_hours_on_and_off_and_nothing_else_about_them(self):
        parent = make_house()
        parent.post("/api/grown-ups", {"email": "sitter-q@example.com", "role": "sitter"})
        sitter = Person("sitter-q@example.com")
        before = parent.get("/api/home").get_json()["treehouse"]["quiet"]
        # the switch: on and off
        self.assertEqual(sitter.patch("/api/treehouse", {"quiet": {"enabled": False}}).status_code, 200)
        self.assertFalse(parent.get("/api/home").get_json()["treehouse"]["quiet"]["enabled"])
        self.assertEqual(sitter.patch("/api/treehouse", {"quiet": {"enabled": True}}).status_code, 200)
        self.assertTrue(parent.get("/api/home").get_json()["treehouse"]["quiet"]["enabled"])
        # the times, the nights and the limits stay with a parent, alone or hidden beside the switch
        for change in ({"quiet": {"start": "21:00"}}, {"quiet": {"end": "06:00"}}, {"quiet": {"days": "1000000"}},
                       {"quiet": {"enabled": False, "start": "21:00"}}, {"quiet": "off"},
                       {"max_call_minutes": 5}, {"daily_minutes": 30}, {"timezone": "America/New_York"},
                       {"paused": True, "retention_days": 30}):
            self.assertEqual(sitter.patch("/api/treehouse", change).status_code, 403, change)
        after = parent.get("/api/home").get_json()["treehouse"]["quiet"]
        self.assertEqual((after["start"], after["end"], after["days"]), (before["start"], before["end"], before["days"]))
        # a parent still can
        self.assertEqual(parent.patch("/api/treehouse", {"quiet": {"start": "21:00", "days": "1000000"}}).status_code, 200)

    def test_a_sitter_has_no_action_log_and_sees_only_todays_calls(self):
        parent = make_house("Parents")
        other = make_house("Friends")
        string_up(parent, other)
        parent.post("/api/grown-ups", {"email": "sitter-c@example.com", "role": "sitter"})
        sitter = Person("sitter-c@example.com")
        c = helpers.db.connect()
        old = (db.utcnow() - dt.timedelta(days=3))
        for when, talk in ((old, 60), (db.utcnow(), 120)):
            add_call(c, parent.house["id"], other.house["id"], db.iso(when), other.house["number"], talk=talk)
        self.assertEqual(parent.get("/api/actions").status_code, 200)
        self.assertEqual(sitter.get("/api/actions").status_code, 403)
        for rng in ("today", "week", "all", ""):
            calls = sitter.get(f"/api/calls?range={rng}").get_json()["calls"]
            self.assertEqual([x["talk_sec"] for x in calls], [120], rng)                 # only today's, whatever they ask for
        self.assertEqual(len(parent.get("/api/calls?range=all").get_json()["calls"]), 2)     # a parent still sees the history
        ids = {x["talk_sec"]: x["id"] for x in parent.get("/api/calls?range=all").get_json()["calls"]}
        self.assertEqual(sitter.get(f"/api/calls/{ids[120]}").status_code, 200)
        self.assertEqual(sitter.get(f"/api/calls/{ids[60]}").status_code, 404)              # an older call isn't theirs to open
        self.assertEqual(parent.get(f"/api/calls/{ids[60]}").status_code, 200)
        self.assertEqual(sitter.get("/api/calls.csv").status_code, 403)

    def test_cannot_remove_the_last_parent(self):
        p = make_house()
        me = p.get("/api/grown-ups").get_json()["grown_ups"][0]
        self.assertEqual(p.delete(f"/api/grown-ups/{me['id']}").status_code, 409)

    def test_grown_up_in_another_treehouse(self):
        a, b = make_house(), make_house()
        self.assertEqual(a.post("/api/grown-ups", {"email": b.email}).status_code, 409)

    def test_leave_ends_strings_frees_the_number_and_tells_friends(self):
        a, b = make_house("Leaver"), make_house("Stayer")
        string_up(a, b)
        number = a.house["number"]
        self.assertEqual(a.post("/api/treehouse/leave", {"confirm": "nope"}).status_code, 400)
        self.assertEqual(a.post("/api/treehouse/leave", {"confirm": "leaver"}).status_code, 200)
        self.assertEqual(b.get("/api/strings").get_json()["strings"], [])
        self.assertIn("Leaver left the Treeline", [n["title"] for n in b.get("/api/home").get_json()["notices"]])
        self.assertTrue(db.number_is_free(helpers.db.connect(), number))
        self.assertIsNone(a.get("/api/me").get_json()["treehouse"])

    def test_delete_removes_everything(self):
        a, b = make_house("Gone"), make_house("Kept")
        string_up(a, b)
        c = helpers.db.connect()
        add_call(c, a.house["id"], b.house["id"], dialed=b.house["number"])
        a.post("/api/handsets", {"kind": "softphone", "name": "Tablet"})
        self.assertEqual(a.delete("/api/treehouse", {"confirm": "gone"}).status_code, 200)
        for table, col in (("grown_up", "treehouse_id"), ("handset", "treehouse_id")):
            self.assertEqual(c.execute(f"SELECT COUNT(*) n FROM {table} WHERE {col}=?",
                                       (a.house["id"],)).fetchone()["n"], 0, table)
        self.assertFalse(households.exists(a.house["id"]))               # notes, action log and history went with the file
        self.assertTrue(households.exists(b.house["id"]))
        # The other family's log keeps its side of the call, without the deleted house's identity.
        calls = b.get("/api/calls?range=all").get_json()["calls"]
        self.assertEqual(len(calls), 1)
        self.assertEqual(a.get("/api/me").status_code, 401)  # sessions are gone


class Ownership(unittest.TestCase):
    """Each family's notes, audit log and consent are in its own file, and nowhere else."""

    def titles(self, tid):
        return [n["title"] for n in households.conn(tid).execute("SELECT * FROM notice")]

    def test_central_has_no_notes_audit_log_consent_or_retention(self):
        c = helpers.db.connect()
        tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({"notice", "parent_action"}.isdisjoint(tables))
        cols = {r[1] for r in c.execute("PRAGMA table_info(treehouse)")}
        self.assertTrue({"retention_days", "ack_911", "consent_at", "consent_version"}.isdisjoint(cols))

    def test_a_string_request_lands_in_the_other_familys_file_only(self):
        a, b = make_house("Alex's"), make_house("Sam's")
        code = a.post("/api/ladder-codes").get_json()["code"]
        b.post("/api/strings/redeem", {"code": code})                      # Sam's asks Alex's for a string
        self.assertIn("Sam's would like to string with you", self.titles(a.house["id"]))
        self.assertNotIn("Sam's would like to string with you", self.titles(b.house["id"]))
        actions = lambda t: [r["action"] for r in households.conn(t).execute("SELECT * FROM parent_action")]    # noqa: E731
        self.assertIn("string_requested", actions(b.house["id"]))          # the asker's action is the asker's record
        self.assertNotIn("string_requested", actions(a.house["id"]))
        self.assertIn("treehouse_created", actions(a.house["id"]))
        self.assertEqual(b.get("/api/actions").get_json()["actions"][0]["action"], "string_requested")

    def test_changing_retention_is_logged_and_kept_in_the_household(self):
        a = make_house("Alex's")
        r = a.patch("/api/treehouse", {"retention_days": 30})
        self.assertEqual(r.get_json()["retention_days"], 30)
        self.assertEqual(households.retention_days(a.house["id"]), 30)
        self.assertEqual(a.get("/api/me").get_json()["treehouse"]["retention_days"], 30)
        last = households.conn(a.house["id"]).execute(
            "SELECT * FROM parent_action WHERE action='changed_retention_days'").fetchone()
        self.assertEqual((last["before"], last["after"]), ("90", "30"))

    def test_a_failure_while_making_the_household_leaves_no_central_rows_and_no_file(self):
        p = Person()
        before = set(households.ids())
        with mock.patch.object(households, "create", side_effect=RuntimeError("disk full")):
            r = p.post("/api/treehouse", {"name": "Fails house", "ack_911": True, "consent": True})
        self.assertEqual(r.status_code, 500)
        c = helpers.db.connect()
        self.assertIsNone(c.execute("SELECT 1 FROM treehouse WHERE name='Fails house'").fetchone())
        self.assertIsNone(c.execute("SELECT 1 FROM grown_up WHERE email=?", (p.email,)).fetchone())
        self.assertEqual(set(households.ids()), before)
        self.assertEqual(p.get("/api/me").get_json()["treehouse"], None)          # and they can simply try again
        self.assertEqual(p.post("/api/treehouse", {"name": "Works house", "ack_911": True, "consent": True}).status_code, 201)

    def test_a_failure_after_the_file_exists_removes_it(self):
        p = Person()
        c = helpers.db.connect()
        # A stale grown-up row for this email (on a treehouse that left): the insert fails once the file is made.
        old = c.execute("INSERT INTO treehouse(name,number,created_at,left_at) VALUES('Old',NULL,?,?)", (db.iso(), db.iso())).lastrowid
        c.execute("INSERT INTO grown_up(email,treehouse_id,role,created_at) VALUES(?,?,?,?)", (p.email, old, "parent", db.iso()))
        files, houses = set(households.ids()), c.execute("SELECT count(*) FROM treehouse").fetchone()[0]
        r = p.post("/api/treehouse", {"name": "Late fail", "ack_911": True, "consent": True})
        self.assertEqual(r.status_code, 500)
        self.assertEqual(set(households.ids()), files)                              # the file that had been made is gone
        self.assertEqual(c.execute("SELECT count(*) FROM treehouse").fetchone()[0], houses)


class History(unittest.TestCase):
    """Each family's call history is its own file: retention, paging, deleting and leaving."""

    def setUp(self):
        self.a, self.b = make_house("Alex's"), make_house("Sam's")
        string_up(self.a, self.b)
        self.c = helpers.db.connect()
        self.aid, self.bid = self.a.house["id"], self.b.house["id"]

    def call(self, days_ago=0, caller=None, callee=None, **kw):
        started = db.iso(db.utcnow() - dt.timedelta(days=days_ago, seconds=1))
        return add_call(self.c, caller or self.aid, callee or self.bid, started, self.b.house["number"], **kw)

    def ids(self, who, query="range=all"):
        return [x["id"] for x in who.get(f"/api/calls?{query}").get_json()["calls"]]

    def test_both_families_see_a_real_call_and_each_file_holds_only_its_own_records(self):
        cid = self.call(talk=40)
        self.assertEqual((self.ids(self.a), self.ids(self.b)), ([cid], [cid]))
        self.assertEqual(self.a.get(f"/api/calls/{cid}").status_code, 200)
        for tid in (self.aid, self.bid):
            raw = households.conn(tid)
            self.assertEqual({r[0] for r in raw.execute("SELECT treehouse_id FROM meta")}, {tid})
            self.assertEqual({r[0] for r in raw.execute("SELECT name FROM sqlite_master WHERE type='table'")},
                             {"meta", "call_log", "call_event", "notice", "parent_action"})

    def test_lowering_retention_removes_older_calls_at_once_and_only_for_that_family(self):
        old, recent = self.call(days_ago=30), self.call(days_ago=2)
        self.assertEqual(self.ids(self.a), [recent, old])
        self.assertEqual(self.a.patch("/api/treehouse", {"retention_days": 7}).status_code, 200)
        self.assertEqual(self.ids(self.a), [recent])                                   # gone now, not at the next purge
        self.assertEqual(self.ids(self.b), [recent, old])                              # Sam's copy is Sam's own
        self.assertEqual(households.conn(self.aid).execute("SELECT count(*) FROM call_event").fetchone()[0],
                         households.conn(self.aid).execute("SELECT count(*) FROM call_event WHERE call_id=?", (recent,)).fetchone()[0])

    def test_paging_newest_first_with_before_limit_and_more(self):
        made = [self.call(days_ago=0) for _ in range(7)]
        newest_first = list(reversed(made))
        page = self.a.get("/api/calls?range=all&limit=3").get_json()
        self.assertEqual(([x["id"] for x in page["calls"]], page["more"]), (newest_first[:3], True))
        page = self.a.get(f"/api/calls?range=all&limit=3&before={newest_first[2]}").get_json()
        self.assertEqual(([x["id"] for x in page["calls"]], page["more"]), (newest_first[3:6], True))
        page = self.a.get(f"/api/calls?range=all&limit=3&before={newest_first[5]}").get_json()
        self.assertEqual(([x["id"] for x in page["calls"]], page["more"]), (newest_first[6:], False))
        self.assertEqual(self.a.get(f"/api/calls?range=all&before={newest_first[-1]}").get_json(), {"calls": [], "more": False})

    def test_all_defaults_to_fifty_and_a_page_never_exceeds_three_hundred(self):
        h = households.conn(self.aid)
        h.execute("BEGIN")
        for i in range(1, 361):
            h.execute("INSERT INTO call_log(id,started_at,caller_treehouse,dialed,state,result) VALUES(?,?,?,?,?,?)",
                      (10 ** 6 + i, db.iso(db.utcnow()), self.aid, "9999", "ended", "no_answer"))
        h.execute("COMMIT")
        everything = self.a.get("/api/calls?range=all").get_json()
        self.assertEqual((len(everything["calls"]), everything["more"]), (50, True))
        self.assertEqual(len(self.a.get("/api/calls?range=all&limit=5000").get_json()["calls"]), 300)
        self.assertEqual(len(self.a.get("/api/calls?range=week").get_json()["calls"]), 300)
        self.assertEqual(len(self.a.get("/api/calls?range=all&limit=0").get_json()["calls"]), 50)

    def test_deleting_removes_the_file_and_the_other_family_sees_a_deleted_house(self):
        cid = self.call(talk=20)
        self.assertEqual(self.a.delete("/api/treehouse", {"confirm": "alex's"}).status_code, 200)
        self.assertFalse(households.exists(self.aid))
        self.assertEqual(os.listdir(households.root()).count(f"{self.aid}.db-wal"), 0)
        shown = self.b.get("/api/calls?range=all").get_json()["calls"]
        self.assertEqual([(x["id"], x["other"]["name"], x["other"]["number"]) for x in shown], [(cid, "(deleted)", None)])
        self.assertIn("Alex's left the Treeline", [n["title"] for n in households.notices(self.bid)])
        row = self.c.execute("SELECT name, deleted_at, number FROM treehouse WHERE id=?", (self.aid,)).fetchone()
        self.assertEqual((row["name"], bool(row["deleted_at"]), row["number"]), ("(deleted)", True, None))
        self.assertEqual(households.reconcile(self.c)["orphans"], [])                  # nothing left over

    def test_a_handle_in_another_thread_cannot_write_to_a_household_deleted_through_the_api(self):
        seen = {}
        ready, go, done = threading.Event(), threading.Event(), threading.Event()

        def worker():
            households.conn(self.aid)                                                  # e.g. the jobs thread, mid-sweep
            ready.set()
            go.wait()
            seen["note"] = households.add_notice(self.aid, "x", "late note")
            households.log_action(self.aid, "x@example.com", "late")
            households.forget_all()
            done.set()
        t = threading.Thread(target=worker)
        t.start()
        ready.wait()
        self.assertEqual(self.a.delete("/api/treehouse", {"confirm": "alex's"}).status_code, 200)
        go.set()
        done.wait()
        t.join()
        self.assertIsNone(seen["note"])
        self.assertFalse(households.exists(self.aid))
        self.assertEqual([n for n in os.listdir(households.root()) if n.startswith(f"{self.aid}.")], [])

    def test_a_delete_that_fails_part_way_changes_nothing(self):
        real = db.leave_treehouse

        def fail(c, tid):
            real(c, tid)
            raise RuntimeError("crash after the first statements")
        with mock.patch.object(db, "leave_treehouse", fail):
            r = self.a.delete("/api/treehouse", {"confirm": "alex's"})
        self.assertEqual(r.status_code, 500)
        self.assertTrue(households.exists(self.aid))                                   # nothing was removed
        row = self.c.execute("SELECT name, left_at, number FROM treehouse WHERE id=?", (self.aid,)).fetchone()
        self.assertEqual((row["name"], row["left_at"], row["number"]), ("Alex's", None, self.a.house["number"]))
        self.assertEqual(len(self.a.get("/api/strings").get_json()["strings"]), 1)      # and the string is still there
        self.assertNotIn("Alex's left the Treeline", [n["title"] for n in households.notices(self.bid)])
        self.assertEqual(self.a.get("/api/me").status_code, 200)

    def test_changing_retention_when_the_file_is_missing_is_a_clean_error_and_not_logged(self):
        households.remove(self.aid)
        r = self.a.patch("/api/treehouse", {"retention_days": 30})
        self.assertEqual(r.status_code, 503)
        self.assertIn("records file", r.get_json()["error"])

    def test_an_orphan_file_from_a_crash_during_delete_is_removed_by_reconcile(self):
        self.c.execute("UPDATE treehouse SET deleted_at=?, name='(deleted)' WHERE id=?", (db.iso(), self.aid))   # crashed before the file went
        self.assertTrue(households.exists(self.aid))
        self.assertEqual(households.reconcile(self.c)["orphans"], [self.aid])
        self.assertFalse(households.exists(self.aid))

    def test_leaving_keeps_the_file_until_past_retention_then_the_purge_removes_it(self):
        cid = self.call(talk=20)
        self.assertEqual(self.a.post("/api/treehouse/leave", {"confirm": "alex's"}).status_code, 200)
        self.assertTrue(households.exists(self.aid))
        self.assertIn("left_treeline", [r["action"] for r in households.actions(self.aid)])
        self.assertEqual([n["title"] for n in households.notices(self.bid)][0], "Alex's left the Treeline")
        self.assertEqual(self.ids(self.b), [cid])
        self.assertEqual(self.a.get("/api/me").get_json()["treehouse"], None)          # nobody left to read it
        from treeline import jobs
        households.set_retention(self.bid, 365)                                        # Sam's family keeps theirs for a year
        jobs.purge(self.c, db.utcnow() + dt.timedelta(days=60))
        self.assertTrue(households.exists(self.aid))                                   # 90 days not up
        jobs.purge(self.c, db.utcnow() + dt.timedelta(days=91))
        self.assertFalse(households.exists(self.aid))
        self.assertTrue(households.exists(self.bid))
        self.assertEqual(households.conn(self.bid).execute("SELECT id FROM call_log").fetchall()[0][0], cid)   # Sam's own copy is Sam's

    def test_health_fails_while_a_household_is_below_the_current_version(self):
        def step(c):
            c.execute("ALTER TABLE notice ADD COLUMN seen TEXT")
        # Its own directory: migrating the shared test directory would leave every file newer than the code.
        with mock.patch.dict(os.environ, {"TREELINE_HOUSEHOLDS_DIR": tempfile.mkdtemp()}):
            households.create(1)
            households.create(2)
            api._behind["at"] = 0
            api._hits.clear()
            self.assertEqual(client.get("/api/health").get_json()["households_behind"], 0)
            with mock.patch.object(households, "HOUSEHOLD_MIGRATIONS", [step]):
                api._behind["at"] = 0
                api._hits.clear()
                r = client.get("/api/health")
                self.assertEqual((r.status_code, r.get_json()["ok"], r.get_json()["households_behind"]), (503, False, 2))
                self.assertEqual(households.sweep(), {})                                  # the startup sweep migrates them
                api._behind["at"] = 0
                api._hits.clear()
                r = client.get("/api/health")
                self.assertEqual((r.status_code, r.get_json()["households_behind"]), (200, 0))
            households.forget_all()
        api._behind["at"] = 0


class Strings(unittest.TestCase):
    def test_full_flow_needs_both_families(self):
        a, b = make_house("Alex's"), make_house("Sam's")
        code = a.post("/api/ladder-codes").get_json()["code"]
        self.assertRegex(code, r"^[A-Z2-9]{4}-[A-Z2-9]{4}$")
        s = b.post("/api/strings/redeem", {"code": code.lower()}).get_json()
        self.assertEqual((s["state"], s["mine_approved"], s["theirs_approved"]), ("waiting", True, False))
        # Alex's house sees a request and a note, and hasn't approved.
        home = a.get("/api/home").get_json()
        self.assertEqual(len(home["strings"]["waiting_on_me"]), 1)
        self.assertIn("Sam's would like to string with you", [n["title"] for n in home["notices"]])
        # Not strung yet: the rules say no.
        c = helpers.db.connect()
        self.assertIsNone(db.live_string(c, a.house["id"], b.house["id"]))
        r = a.post(f"/api/strings/{s['id']}/approve").get_json()
        self.assertEqual(r["state"], "live")
        self.assertIsNotNone(db.live_string(c, a.house["id"], b.house["id"]))
        self.assertIn("Alex's approved", [n["title"] for n in b.get("/api/home").get_json()["notices"]])

    def test_a_code_works_once_and_expires(self):
        a, b, c3 = make_house(), make_house(), make_house()
        code = a.post("/api/ladder-codes").get_json()["code"]
        self.assertEqual(b.post("/api/strings/redeem", {"code": code}).status_code, 201)
        self.assertEqual(c3.post("/api/strings/redeem", {"code": code}).status_code, 400)
        code2 = a.post("/api/ladder-codes").get_json()["code"]
        helpers.db.connect().execute("UPDATE ladder_code SET expires_at=?",
                                     (db.iso(db.utcnow() - dt.timedelta(minutes=1)),))
        self.assertEqual(c3.post("/api/strings/redeem", {"code": code2}).status_code, 400)

    def test_cannot_string_with_yourself_or_twice(self):
        a, b = make_house(), make_house()
        mine = a.post("/api/ladder-codes").get_json()["code"]
        self.assertEqual(a.post("/api/strings/redeem", {"code": mine}).status_code, 400)
        string_up(a, b)
        again = a.post("/api/ladder-codes").get_json()["code"]
        self.assertEqual(b.post("/api/strings/redeem", {"code": again}).status_code, 409)

    def test_cannot_approve_your_own_request(self):
        a, b = make_house(), make_house()
        s = b.post("/api/strings/redeem", {"code": a.post("/api/ladder-codes").get_json()["code"]}).get_json()
        self.assertEqual(b.post(f"/api/strings/{s['id']}/approve").status_code, 409)

    def test_pause_resume_and_cut(self):
        a, b = make_house(), make_house()
        sid = string_up(a, b)
        c = helpers.db.connect()
        self.assertEqual(a.post(f"/api/strings/{sid}/pause").get_json()["state"], "paused")
        self.assertIsNone(db.live_string(c, a.house["id"], b.house["id"]))
        self.assertEqual(b.post(f"/api/strings/{sid}/resume").status_code, 409)   # only the pauser
        self.assertEqual(a.post(f"/api/strings/{sid}/resume").get_json()["state"], "live")
        b.post(f"/api/strings/{sid}/cut")
        self.assertIsNone(db.live_string(c, a.house["id"], b.house["id"]))
        self.assertEqual(a.get("/api/strings").get_json()["strings"], [])

    def test_strangers_cannot_touch_a_string(self):
        a, b, x = make_house(), make_house(), make_house()
        sid = string_up(a, b)
        self.assertEqual(x.post(f"/api/strings/{sid}/cut").status_code, 404)
        self.assertEqual(x.post(f"/api/strings/{sid}/pause").status_code, 404)

    def test_phone_book(self):
        a, b, c3 = make_house("Zed's"), make_house("Alex's"), make_house("Pat's")
        string_up(a, b)
        string_up(a, c3)
        book = a.get("/api/phonebook").get_json()
        self.assertEqual([e["name"] for e in book["entries"]], ["Alex's", "Pat's"])
        self.assertEqual(book["number"], a.house["number"])

    def test_code_limit(self):
        a = make_house()
        codes = [a.post("/api/ladder-codes").status_code for _ in range(6)]
        self.assertEqual(codes, [201] * 5 + [409])


class Handsets(unittest.TestCase):
    def test_create_gives_the_secret_once_and_writes_asterisk_config(self):
        p = make_house()
        r = p.post("/api/handsets", {"kind": "softphone", "name": "Kitchen tablet"})
        self.assertEqual(r.status_code, 201)
        creds = r.get_json()["credentials"]
        self.assertGreaterEqual(len(creds["secret"]), 20)
        listed = p.get("/api/handsets").get_json()["handsets"]
        self.assertNotIn("secret", str(listed))
        cfg = read_pjsip()
        self.assertIn(f"[{creds['sip_user']}](webrtc-endpoint)", cfg)
        self.assertIn(f"md5_cred={db.sip_digest(creds['sip_user'], creds['secret'])}", cfg)
        self.assertNotIn(creds["secret"], cfg)        # Asterisk only gets the digest
        self.assertIn(("PUT", "/asterisk/modules/res_pjsip.so"), [(m, p) for m, p, _ in helpers.CALLS_TO_ARI])  # asked Asterisk to reload

    def test_remove_is_immediate(self):
        p = make_house()
        h = p.post("/api/handsets", {"kind": "softphone", "name": "Tab"}).get_json()
        hid, user = h["handset"]["id"], h["credentials"]["sip_user"]
        self.assertIn(f"[{user}]", read_pjsip())
        self.assertEqual(p.delete(f"/api/handsets/{hid}").status_code, 200)
        self.assertNotIn(f"[{user}]", read_pjsip())
        self.assertEqual(p.get("/api/handsets").get_json()["handsets"], [])

    def test_disconnect_and_reconnect_a_phone(self):
        p = make_house()
        hid = p.post("/api/handsets", {"kind": "softphone", "name": "Kitchen"}).get_json()["handset"]["id"]
        r = p.patch(f"/api/handsets/{hid}", {"disabled": True}).get_json()
        self.assertTrue(r["disabled"])
        self.assertTrue(p.get("/api/handsets").get_json()["handsets"][0]["disabled"])
        self.assertFalse(p.patch(f"/api/handsets/{hid}", {"disabled": False}).get_json()["disabled"])
        kinds = [a["action"] for a in p.get("/api/actions").get_json()["actions"]]
        self.assertIn("handset_disconnected", kinds)
        self.assertIn("handset_reconnected", kinds)

    def test_setting_it_to_what_it_already_is_logs_nothing_new(self):
        p = make_house()
        hid = p.post("/api/handsets", {"kind": "softphone", "name": "K"}).get_json()["handset"]["id"]
        p.patch(f"/api/handsets/{hid}", {"disabled": False})
        kinds = [a["action"] for a in p.get("/api/actions").get_json()["actions"]]
        self.assertNotIn("handset_reconnected", kinds)

    def test_a_sitter_can_disconnect_reconnect_and_ring_a_phone_but_not_add_rename_or_remove_one(self):
        a, b = make_house(), make_house()
        hid = a.post("/api/handsets", {"kind": "softphone", "name": "K"}).get_json()["handset"]["id"]
        self.assertEqual(b.patch(f"/api/handsets/{hid}", {"disabled": True}).status_code, 404)        # only your own treehouse's
        self.assertEqual(b.post(f"/api/handsets/{hid}/ring-test").status_code, 404)
        a.post("/api/grown-ups", {"email": "sit2@example.com", "role": "sitter"})
        sitter = Person("sit2@example.com")
        self.assertEqual(sitter.get("/api/handsets").status_code, 200)
        self.assertEqual(sitter.patch(f"/api/handsets/{hid}", {"disabled": True}).status_code, 200)    # disconnect...
        self.assertEqual(sitter.post(f"/api/handsets/{hid}/ring-test").status_code, 409)               # ... a disconnected phone can't ring (not "parents only")
        self.assertEqual(sitter.patch(f"/api/handsets/{hid}", {"disabled": False}).status_code, 200)   # ... and reconnect
        self.assertNotEqual(sitter.post(f"/api/handsets/{hid}/ring-test").status_code, 403)            # the ring test is allowed
        self.assertEqual(sitter.patch(f"/api/handsets/{hid}", {"name": "Renamed"}).status_code, 403)   # but not rename,
        self.assertEqual(sitter.patch(f"/api/handsets/{hid}", {"name": "Renamed", "disabled": True}).status_code, 403)
        self.assertEqual(sitter.delete(f"/api/handsets/{hid}").status_code, 403)                       # remove,
        self.assertEqual(sitter.post("/api/handsets", {"kind": "softphone", "name": "New"}).status_code, 403)   # or add
        self.assertEqual(sitter.get(f"/api/handsets/{hid}/provision").status_code, 403)                # nor see a phone's sign-in
        self.assertEqual(a.get("/api/handsets").get_json()["handsets"][0]["name"], "K")
        self.assertEqual(a.patch(f"/api/handsets/{hid}", {}).status_code, 400)

    def test_a_disconnected_phone_cannot_be_rung_and_reports_itself_to_the_tablet(self):
        parent = make_house()
        parent.patch("/api/treehouse", {"quiet": {"enabled": False}})
        start = client.post("/api/pair/start").get_json()
        parent.post("/api/pair/claim", {"code": start["code"], "name": "Tab"})
        got = client.get("/api/pair/status", query_string={"token": start["token"]}).get_json()
        hid = parent.get("/api/handsets").get_json()["handsets"][0]["id"]

        def line():
            hdr = {"Authorization": "Basic " + base64.b64encode(f"{got['sip_user']}:{got['secret']}".encode()).decode()}
            return client.get("/api/line", headers=hdr).get_json()["state"]
        self.assertEqual(line(), "idle")
        parent.patch(f"/api/handsets/{hid}", {"disabled": True})
        self.assertEqual(line(), "disconnected")
        self.assertEqual(parent.post(f"/api/handsets/{hid}/ring-test").status_code, 409)

    def test_kinds_and_limits(self):
        p = make_house()
        self.assertEqual(p.post("/api/handsets", {"kind": "toaster", "name": "x"}).status_code, 400)
        for i in range(8):
            self.assertEqual(p.post("/api/handsets", {"kind": "softphone", "name": f"T{i}"}).status_code, 201)
        self.assertEqual(p.post("/api/handsets", {"kind": "softphone", "name": "T9"}).status_code, 409)

    def test_other_families_cannot_touch_my_handsets(self):
        a, b = make_house(), make_house()
        hid = a.post("/api/handsets", {"kind": "softphone", "name": "T"}).get_json()["handset"]["id"]
        self.assertEqual(b.delete(f"/api/handsets/{hid}").status_code, 404)
        self.assertEqual(b.patch(f"/api/handsets/{hid}", {"name": "mine now"}).status_code, 404)
        self.assertEqual(b.post(f"/api/handsets/{hid}/ring-test").status_code, 404)

    def test_adapter_settings_file(self):
        p = make_house()
        h = p.post("/api/handsets", {"kind": "ata", "name": "Hall phone"}).get_json()
        creds = h["credentials"]
        link = p.get(f"/api/handsets/{h['handset']['id']}/provision").get_json()["url"]
        path = link[link.index("/api/"):]
        xml = client.get(path).get_data(as_text=True)
        self.assertIn(f"<P35>{creds['sip_user']}</P35>", xml)
        self.assertIn(f"<P34>{creds['secret']}</P34>", xml)
        self.assertIn("<P290>", xml)
        # A bad token gets nothing, and removing the handset kills the link.
        self.assertEqual(client.get("/api/provision/nope.xml").status_code, 404)
        p.delete(f"/api/handsets/{h['handset']['id']}")
        self.assertEqual(client.get(path).status_code, 404)

    def test_softphones_have_no_settings_file(self):
        p = make_house()
        h = p.post("/api/handsets", {"kind": "softphone", "name": "T"}).get_json()
        self.assertEqual(p.get(f"/api/handsets/{h['handset']['id']}/provision").status_code, 400)


class Pairing(unittest.TestCase):
    def test_qr_pairing_flow(self):
        parent = make_house()
        start = client.post("/api/pair/start").get_json()
        self.assertEqual(client.get("/api/pair/status", query_string={"token": start["token"]}).get_json()["status"],
                         "waiting")
        r = parent.post("/api/pair/claim", {"code": start["code"], "name": "Living room"})
        self.assertEqual(r.status_code, 201)
        got = client.get("/api/pair/status", query_string={"token": start["token"]}).get_json()
        self.assertEqual(got["status"], "paired")
        self.assertTrue(got["sip_user"] and got["secret"] and got["ws_url"])
        # The secret is handed over once.
        again = client.get("/api/pair/status", query_string={"token": start["token"]}).get_json()
        self.assertEqual(again["status"], "expired")
        self.assertEqual(parent.get("/api/handsets").get_json()["handsets"][0]["name"], "Living room")

    def test_code_cannot_be_claimed_twice_or_after_expiry(self):
        a, b = make_house(), make_house()
        start = client.post("/api/pair/start").get_json()
        self.assertEqual(a.post("/api/pair/claim", {"code": start["code"]}).status_code, 201)
        self.assertEqual(b.post("/api/pair/claim", {"code": start["code"]}).status_code, 400)
        start = client.post("/api/pair/start").get_json()
        helpers.db.connect().execute("UPDATE pairing SET expires_at=?", (db.iso(db.utcnow() - dt.timedelta(seconds=1)),))
        self.assertEqual(a.post("/api/pair/claim", {"code": start["code"]}).status_code, 400)

    def test_only_signed_in_parents_can_claim(self):
        start = client.post("/api/pair/start").get_json()
        self.assertEqual(client.post("/api/pair/claim", json={"code": start["code"]}).status_code, 401)

    def test_line_state_needs_the_handsets_own_account(self):
        parent = make_house()
        parent.patch("/api/treehouse", {"quiet": {"enabled": False}})  # don't depend on the time of day
        start = client.post("/api/pair/start").get_json()
        parent.post("/api/pair/claim", {"code": start["code"], "name": "Tab"})
        got = client.get("/api/pair/status", query_string={"token": start["token"]}).get_json()

        def basic(user, secret):
            return {"Authorization": "Basic " + base64.b64encode(f"{user}:{secret}".encode()).decode()}
        r = client.get("/api/line", headers=basic(got["sip_user"], got["secret"]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["state"], "idle")
        self.assertEqual(r.get_json()["number"], parent.house["number"])
        self.assertEqual(client.get("/api/line", headers=basic(got["sip_user"], "wrong")).status_code, 401)
        # The softphone's room: its own quiet hours, and a card for each live string, none for a pending one.
        self.assertEqual(r.get_json()["treehouse"], parent.house["name"])
        self.assertEqual(r.get_json()["strings"], [])
        self.assertFalse(r.get_json()["quiet"]["enabled"])
        friend, waiting = make_house(), make_house()
        string_up(parent, friend)
        waiting.post("/api/strings/redeem", {"code": parent.post("/api/ladder-codes").get_json()["code"]})
        cards = client.get("/api/line", headers=basic(got["sip_user"], got["secret"])).get_json()["strings"]
        self.assertEqual(cards, [{"name": friend.house["name"], "number": friend.house["number"]}])
        # Remove it: the tablet finds out.
        hid = parent.get("/api/handsets").get_json()["handsets"][0]["id"]
        parent.delete(f"/api/handsets/{hid}")
        r = client.get("/api/line", headers=basic(got["sip_user"], got["secret"]))
        self.assertEqual((r.status_code, r.get_json()["code"]), (401, "removed"))


class FactoryDevices(unittest.TestCase):
    KEY = "factory-secret-key"

    def setUp(self):
        api.FACTORY_KEY = self.KEY

    def tearDown(self):
        api.FACTORY_KEY = ""

    def register(self, code="1234567890", token="t" * 32, key=None):
        return client.post("/api/factory/devices", json={"code": code, "token": token},
                           headers={"X-Factory-Key": key if key is not None else self.KEY})

    def test_a_registered_phone_pairs_with_its_printed_code(self):
        parent = make_house()
        self.assertEqual(self.register().status_code, 201)
        r = parent.post("/api/pair/claim", {"code": "123 456 7890", "name": "Hall phone", "kind": "rotary"})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.get_json()["handset"]["kind"], "rotary")
        got = client.get("/api/pair/status", query_string={"token": "t" * 32}).get_json()
        self.assertEqual(got["status"], "paired")
        self.assertIn(f"[{got['sip_user']}](phone-endpoint)", read_pjsip())        # a phone, not a browser

    def test_off_without_the_key_and_closed_to_the_wrong_one(self):
        self.assertEqual(self.register(key="nope").status_code, 404)
        self.assertEqual(self.register(key="").status_code, 404)
        api.FACTORY_KEY = ""
        self.assertEqual(self.register(key="").status_code, 404)

    def test_codes_must_be_long_and_secrets_strong(self):
        self.assertEqual(self.register(code="123456").status_code, 400)
        self.assertEqual(self.register(token="short").status_code, 400)
        self.assertEqual(self.register(code="1" * 13).status_code, 400)

    def test_a_code_registers_once(self):
        self.assertEqual(self.register(code="5555555555").status_code, 201)
        self.assertEqual(self.register(code="5555555555").status_code, 409)

    def test_a_claimed_phone_cannot_be_claimed_again(self):
        a, b = make_house(), make_house()
        self.register(code="4444444444")
        self.assertEqual(a.post("/api/pair/claim", {"code": "4444444444", "kind": "rotary"}).status_code, 201)
        self.assertEqual(b.post("/api/pair/claim", {"code": "4444444444", "kind": "rotary"}).status_code, 400)

    def test_tablet_pairing_still_only_takes_a_tablet_or_a_treeline_phone(self):
        p = make_house()
        start = client.post("/api/pair/start").get_json()
        self.assertEqual(p.post("/api/pair/claim", {"code": start["code"], "kind": "ata"}).status_code, 400)


class CallLogs(unittest.TestCase):
    def setUp(self):
        self.a, self.b = make_house("Alex's"), make_house("Sam's")
        string_up(self.a, self.b)
        self.c = helpers.db.connect()

    def call(self, caller, callee, result, reason=None, talk=0, dialed=None):
        return add_call(self.c, caller["id"], callee["id"] if callee else None, None,
                        dialed or (callee["number"] if callee else "9999"), result, reason, talk)

    def test_both_families_see_a_connected_call(self):
        self.call(self.a.house, self.b.house, "connected", talk=125)
        out = self.a.get("/api/calls").get_json()["calls"][0]
        inn = self.b.get("/api/calls").get_json()["calls"][0]
        self.assertEqual((out["direction"], out["other"]["name"], out["label"], out["detail"]),
                         ("out", "Sam's", "Connected", "2 min"))
        self.assertEqual((inn["direction"], inn["other"]["name"]), ("in", "Alex's"))

    def test_the_caller_sees_a_generic_message_when_the_other_line_is_quiet(self):
        self.call(self.a.house, self.b.house, "quiet_or_paused", "callee_quiet")
        out = self.a.get("/api/calls").get_json()["calls"][0]
        self.assertEqual(out["detail"], "That treehouse isn't taking calls right now")
        self.assertNotIn("quiet", out["detail"].lower())
        # ...and the quiet side sees it as blocked.
        inn = self.b.get("/api/calls").get_json()["calls"][0]
        self.assertEqual((inn["label"], inn["detail"]), ("Blocked", "During your quiet hours"))

    def test_the_callers_json_never_carries_why_the_callee_would_not_take_the_call(self):
        """R1-3: the JSON's raw `reason` used to be `callee_paused`, `callee_quiet` or `callee_daily_limit`."""
        for reason in ("callee_paused", "callee_quiet", "callee_daily_limit"):
            self.call(self.a.house, self.b.house, "quiet_or_paused", reason)
        calls = self.a.get("/api/calls?range=all").get_json()["calls"]
        self.assertEqual({c["reason"] for c in calls}, {"callee_unavailable"})
        detail = self.a.get(f"/api/calls/{calls[0]['id']}").get_json()
        self.assertEqual(detail["reason"], "callee_unavailable")
        body = self.a.get("/api/calls?range=all").get_data(as_text=True) + self.a.get("/api/calls.csv").get_data(as_text=True)
        for word in ("callee_paused", "callee_quiet", "callee_daily_limit"):
            self.assertNotIn(word, body)
        self.assertEqual({c["reason"] for c in self.b.get("/api/calls?range=all").get_json()["calls"]},
                         {"callee_paused", "callee_quiet", "callee_daily_limit"})        # the callee sees its own rules

    def test_the_other_family_never_sees_unstrung_or_callers_own_blocks(self):
        stranger = make_house("Stranger's")
        self.call(stranger.house, self.b.house, "not_strung", "no_live_string")
        self.call(self.a.house, self.b.house, "quiet_or_paused", "caller_quiet")
        self.call(self.a.house, None, "not_in_service", "no_such_number", dialed="4444")
        self.call(self.a.house, self.b.house, "repeat_limit", "repeat_limit")
        self.assertEqual(self.b.get("/api/calls?range=all").get_json()["calls"], [])
        mine = self.a.get("/api/calls?range=all").get_json()["calls"]
        self.assertEqual(len(mine), 3)
        ns = next(c for c in mine if c["result"] == "not_in_service")
        self.assertEqual(ns["other"], {"name": None, "number": "4444"})

    def test_a_not_strung_attempt_does_not_reveal_the_other_treehouse(self):
        stranger = make_house("Secret house")
        self.call(self.a.house, stranger.house, "not_strung", "no_live_string")
        c = self.a.get("/api/calls").get_json()["calls"][0]
        self.assertIsNone(c["other"]["name"])
        self.assertEqual(c["other"]["number"], stranger.house["number"])

    def test_call_detail_hides_the_other_sides_handsets(self):
        hid, _, _ = db.create_handset(self.c, self.a.house["id"], "ata", "Hall phone")
        other, _, _ = db.create_handset(self.c, self.b.house["id"], "ata", "Their phone")
        cid = self.call(self.a.house, self.b.house, "connected", talk=30)
        for h, e in ((hid, "dialed"), (other, "rang"), (other, "answered")):
            self.c.execute("INSERT INTO call_event(call_id,at,handset_id,event) VALUES(?,?,?,?)",
                           (cid, db.iso(), h, e))
        households.record_call(self.c, cid)               # the events came after the call was first copied: the copy takes them
        events = self.a.get(f"/api/calls/{cid}").get_json()["events"]
        self.assertEqual(events[0]["handset"], "Hall phone")
        self.assertIsNone(events[1]["handset"])
        self.assertTrue(events[1]["theirs"])

    def test_other_families_cannot_read_a_call(self):
        x = make_house("X")
        cid = self.call(self.a.house, self.b.house, "connected")
        self.assertEqual(x.get(f"/api/calls/{cid}").status_code, 404)

    def test_csv_export(self):
        self.call(self.a.house, self.b.house, "connected", talk=60)
        r = self.a.get("/api/calls.csv")
        self.assertEqual(r.mimetype, "text/csv")
        lines = r.get_data(as_text=True).strip().splitlines()
        self.assertEqual(lines[0], "When,Direction,Other treehouse,Number,Result,Detail,Talk seconds")
        self.assertIn("Out,Sam's", lines[1])

    def test_home_counts(self):
        self.call(self.a.house, self.b.house, "connected", talk=600)
        self.call(self.b.house, self.a.house, "connected", talk=300)
        self.call(self.a.house, self.b.house, "no_answer")
        home = self.a.get("/api/home").get_json()
        self.assertEqual(home["today"], {"calls": 2, "minutes": 15})
        self.assertEqual(home["week"]["calls"], 2)

    def test_describe_every_result(self):
        for r in (rules.CONNECTED, rules.NO_ANSWER, rules.BUSY, rules.NOT_IN_SERVICE, rules.NOT_STRUNG,
                  rules.QUIET_OR_PAUSED, rules.OFFLINE, rules.NO_911, rules.INCOMPLETE, rules.TIME_LIMIT, rules.REPEAT_LIMIT,
                  rules.DAILY_LIMIT, rules.CALLER_HUNG_UP, rules.DISCONNECTED, "dropped"):
            for tid in (1, 2):
                d = api.describe_call({"caller_treehouse": 1, "result": r, "reason": "", "talk_sec": 90,
                                       "dialed": "1234"}, tid)
                self.assertTrue(d["label"] and d["tone"] and d["icon"], (r, tid))
                self.assertIn(d["tone"], ("canopy", "bark", "sky", "berry"))


class PairingOrigin(unittest.TestCase):
    """The QR code on a softphone must send a parent to the secure address, not to whatever port the tablet loaded."""
    def test_a_configured_address_wins(self):
        os.environ["TREELINE_PUBLIC_ORIGIN"] = "https://192.168.1.20:8443/"
        try:
            self.assertEqual(Person().post("/api/pair/start").get_json()["origin"], "https://192.168.1.20:8443")
        finally:
            del os.environ["TREELINE_PUBLIC_ORIGIN"]

    def test_behind_the_secure_proxy_it_is_the_address_the_request_came_in_on(self):
        with api.app.test_request_context("/", base_url="https://192.168.1.20:8443", headers={"X-Forwarded-Proto": "https"}):
            self.assertEqual(api.public_origin(), "https://192.168.1.20:8443")

    def test_otherwise_the_browser_uses_its_own_address(self):
        with api.app.test_request_context("/", base_url="http://192.168.1.20:8080"):
            self.assertIsNone(api.public_origin())


class Urgent911(unittest.TestCase):
    def test_a_911_attempt_is_marked_urgent_in_the_log_and_nothing_else_is(self):
        for r in (rules.CONNECTED, rules.NO_ANSWER, rules.BUSY, rules.NOT_IN_SERVICE, rules.NOT_STRUNG, rules.QUIET_OR_PAUSED,
                  rules.OFFLINE, rules.INCOMPLETE, rules.TIME_LIMIT, rules.REPEAT_LIMIT, rules.DAILY_LIMIT, rules.CALLER_HUNG_UP,
                  rules.DISCONNECTED):
            d = api.describe_call({"caller_treehouse": 1, "result": r, "reason": "", "talk_sec": 90, "dialed": "1234"}, 1)
            self.assertFalse(d.get("urgent"), r)
        d = api.describe_call({"caller_treehouse": 1, "result": rules.NO_911, "reason": "911", "talk_sec": 0, "dialed": "911"}, 1)
        self.assertTrue(d["urgent"])
        self.assertIn("911", d["label"])

    def test_the_note_reaches_home_and_the_log_marks_the_call_urgent(self):
        a = make_house("Pat's house")
        c = helpers.db.connect()
        hid, _, _ = db.create_handset(c, a.house["id"], "ata", "Hall phone")
        handset = c.execute("SELECT * FROM handset WHERE id=?", (hid,)).fetchone()
        d = rules.decide(c, handset, "911", db.utcnow())
        add_call(c, a.house["id"], None, dialed="911", result=d.result, reason=d.reason, caller_handset=hid)
        households.add_notice(a.house["id"], *d.notify_caller_parents)
        notes = [n for n in a.get("/api/home").get_json()["notices"] if n["kind"] == "no_911"]
        self.assertEqual(len(notes), 1)
        self.assertIn("Hall phone", notes[0]["body"])
        row = [x for x in a.get("/api/calls?range=all").get_json()["calls"] if x["result"] == rules.NO_911][0]
        self.assertTrue(row["urgent"])


class Alerts(unittest.TestCase):
    def test_dismiss_only_your_own_notices(self):
        a, b = make_house(), make_house()
        string_up(a, b)
        n = a.get("/api/home").get_json()["notices"][0]
        self.assertEqual(b.post(f"/api/notices/{n['id']}/dismiss").status_code, 200)   # no effect on a's
        self.assertEqual(len(a.get("/api/home").get_json()["notices"]), 1)
        a.post(f"/api/notices/{n['id']}/dismiss")
        self.assertEqual(a.get("/api/home").get_json()["notices"], [])


class Health(unittest.TestCase):
    def test_ok_when_asterisk_answers_and_503_when_it_does_not(self):
        self.assertEqual(client.get("/api/health").status_code, 200)
        real = api.ari_mod.Ari.online_users
        api.ari_mod.Ari.online_users = lambda self, timeout=10: None          # Asterisk unreachable
        try:
            r = client.get("/api/health")
            self.assertEqual(r.status_code, 503)
            self.assertEqual((r.get_json()["database"], r.get_json()["asterisk"]), (True, False))
        finally:
            api.ari_mod.Ari.online_users = real


class Push(unittest.TestCase):
    SUB = {"endpoint": "https://push.example.net/abc", "keys": {"p256dh": "k", "auth": "a"}}

    def test_subscribe_replaces_and_unsubscribe_removes(self):
        p = make_house()
        self.assertEqual(p.post("/api/push/subscribe", self.SUB).status_code, 201)
        self.assertEqual(p.post("/api/push/subscribe", self.SUB).status_code, 201)     # same device again
        c = helpers.db.connect()
        self.assertEqual(c.execute("SELECT COUNT(*) n FROM push_subscription WHERE email=?", (p.email,)).fetchone()["n"], 1)
        p.delete("/api/push/subscribe", {"endpoint": self.SUB["endpoint"]})
        self.assertEqual(c.execute("SELECT COUNT(*) n FROM push_subscription WHERE email=?", (p.email,)).fetchone()["n"], 0)

    def test_rejects_junk_and_needs_a_sign_in(self):
        p = make_house()
        for bad in ({}, {"endpoint": "http://insecure/x", "keys": {"p256dh": "k", "auth": "a"}}, {"endpoint": "https://x/y"}):
            self.assertEqual(p.post("/api/push/subscribe", bad).status_code, 400)
        self.assertEqual(client.post("/api/push/subscribe", json=self.SUB).status_code, 401)

    def test_nobody_can_remove_someone_elses_device(self):
        a, b = make_house(), make_house()
        a.post("/api/push/subscribe", self.SUB)
        b.delete("/api/push/subscribe", {"endpoint": self.SUB["endpoint"]})
        n = helpers.db.connect().execute("SELECT COUNT(*) n FROM push_subscription WHERE email=?", (a.email,)).fetchone()["n"]
        self.assertEqual(n, 1)

    def test_key_is_only_offered_when_configured(self):
        self.assertEqual(client.get("/api/push/key").status_code, 404)
        old = api.VAPID_PUBLIC
        api.VAPID_PUBLIC = "BKEY"
        try:
            self.assertEqual(client.get("/api/push/key").get_json(), {"key": "BKEY"})
        finally:
            api.VAPID_PUBLIC = old


class Limits(unittest.TestCase):
    def test_health_is_rate_limited_and_never_waits_long_for_asterisk(self):
        api._hits.clear()
        seen = {}
        real = api.ari_mod.Ari.online_users
        api.ari_mod.Ari.online_users = lambda self, timeout=10: seen.setdefault("timeout", timeout) and []
        try:
            self.assertEqual(client.get("/api/health").status_code, 200)
            self.assertLessEqual(seen["timeout"], 2)
            codes = [client.get("/api/health").status_code for _ in range(125)]
        finally:
            api.ari_mod.Ari.online_users = real
        self.assertEqual(codes[-1], 429)

    def test_factory_key_guessing_is_throttled(self):
        api._hits.clear()
        api.FACTORY_KEY = "real-key"
        try:
            codes = [client.post("/api/factory/devices", json={}, headers={"X-Factory-Key": f"guess{i}"}).status_code
                     for i in range(25)]
        finally:
            api.FACTORY_KEY = ""
        self.assertEqual(set(codes[:20]), {404})
        self.assertEqual(codes[-1], 429)

    def test_one_parent_flooding_claims_cannot_lock_everyone_else_out(self):
        api._hits.clear()
        flood = make_house()
        for _ in range(12):                                      # their own limit (10 per 10 minutes) stops them
            flood.post("/api/pair/claim", {"code": "000000"})
        self.assertEqual(flood.post("/api/pair/claim", {"code": "000000"}).status_code, 429)
        other = make_house()                                      # a different parent is unaffected
        start = client.post("/api/pair/start").get_json()
        self.assertEqual(other.post("/api/pair/claim", {"code": start["code"]}).status_code, 201)


class Pages(unittest.TestCase):
    def test_unknown_api_path_is_json_404(self):
        r = client.get("/api/nope")
        self.assertEqual(r.status_code, 404)
        self.assertIn("error", r.get_json())

    def test_cannot_escape_the_web_folder(self):
        r = client.get("/ui/../../etc/passwd")
        self.assertIn(r.status_code, (404,))
        r = client.get("/%2e%2e/%2e%2e/etc/passwd")
        self.assertEqual(r.status_code, 404)


if __name__ == "__main__":
    unittest.main()


class ClientAddress(unittest.TestCase):
    def test_forwarded_header_is_ignored_unless_behind_our_proxy(self):
        with api.app.test_request_context("/", headers={"X-Forwarded-For": "6.6.6.6"},
                                          environ_base={"REMOTE_ADDR": "10.0.0.1"}):
            self.assertEqual(api.client_ip(), "10.0.0.1")
            api.TRUST_PROXY = True
            try:
                self.assertEqual(api.client_ip(), "6.6.6.6")
            finally:
                api.TRUST_PROXY = False


class WebSocketUrl(unittest.TestCase):
    def test_plain_page_uses_ws_on_the_asterisk_port(self):
        with api.app.test_request_context("/", base_url="http://192.168.1.5:8080"):
            self.assertEqual(api.ws_url(), "ws://192.168.1.5:8088/ws")

    def test_https_page_gets_wss_on_its_own_host_and_port(self):
        with api.app.test_request_context("/", base_url="https://192.168.1.5:8443",
                                          headers={"X-Forwarded-Proto": "https"}):
            self.assertEqual(api.ws_url(), "wss://192.168.1.5:8443/ws")

    def test_a_configured_url_wins(self):
        os.environ["TREELINE_PUBLIC_WS_URL"] = "wss://phone.example.com/ws"
        try:
            with api.app.test_request_context("/", headers={"X-Forwarded-Proto": "http"}):
                self.assertEqual(api.ws_url(), "wss://phone.example.com/ws")
        finally:
            del os.environ["TREELINE_PUBLIC_WS_URL"]


class Hardening(unittest.TestCase):
    def test_csv_cells_that_look_like_formulas_are_made_plain_text(self):
        for evil in ("=HYPERLINK(\"http://evil\",\"x\")", "+1+1", "-2", "@SUM(A1)", "\tfoo"):
            self.assertTrue(api.csv_safe(evil).startswith("'"), evil)
        self.assertEqual(api.csv_safe("Alex's house"), "Alex's house")
        self.assertEqual(api.csv_safe(None), "")

    def test_exported_csv_neutralises_a_hostile_treehouse_name(self):
        a, b = make_house("Alex's"), make_house("=cmd|' /C calc'!A0")
        string_up(a, b)
        c = helpers.db.connect()
        add_call(c, a.house["id"], b.house["id"], dialed="x", talk=60)
        text = a.get("/api/calls.csv").get_data(as_text=True)
        self.assertIn("'=cmd", text)
        self.assertNotIn(",=cmd", text)

    def test_pages_carry_a_content_security_policy(self):
        r = client.get("/nope")
        csp = r.headers["Content-Security-Policy"]
        self.assertIn("script-src 'self';", csp)     # no 'unsafe-inline' for scripts
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertNotIn("Content-Security-Policy", client.get("/api/health").headers)

    def test_only_the_phone_page_may_open_websockets(self):
        self.assertNotIn("ws:", client.get("/parent/x").headers["Content-Security-Policy"])
        self.assertIn("ws:", client.get("/phone/x").headers["Content-Security-Policy"])

    def test_dev_codes_only_go_to_private_addresses(self):
        api._hits.clear()
        email = new_email()
        near = client.post("/api/auth/request", json={"email": email}, environ_base={"REMOTE_ADDR": "192.168.1.5"})
        self.assertIn("dev_code", near.get_json())
        far = client.post("/api/auth/request", json={"email": new_email()}, environ_base={"REMOTE_ADDR": "8.8.8.8"})
        self.assertEqual(far.status_code, 200)
        self.assertNotIn("dev_code", far.get_json())

    def test_rate_limit_table_is_pruned(self):
        api._hits.clear()
        old = api._MAX_KEYS
        api._MAX_KEYS = 50
        try:
            stale = time_ago = __import__("time").time() - 2 * api._LONGEST_WINDOW
            for i in range(60):
                api._hits[f"old:{i}"] = [stale]
            api.rate_limit("fresh", 5, 60)
            self.assertLess(len(api._hits), 10)
            self.assertIn("fresh", api._hits)
        finally:
            api._MAX_KEYS = old

    def test_daily_limit_on_the_called_side_is_not_called_quiet_hours(self):
        d = api.describe_call({"caller_treehouse": 1, "result": rules.QUIET_OR_PAUSED, "reason": "callee_daily_limit",
                               "talk_sec": 0, "dialed": "1"}, 2)
        self.assertEqual(d["detail"], "Out of minutes today")


class ParentCode(unittest.TestCase):
    """The parent code: set once by a parent, needed before a softphone, and the only way a softphone leaves phone mode."""

    def bare_house(self):
        p = Person()
        r = p.post("/api/treehouse", {"name": "No code house", "ack_911": True, "consent": True})
        self.assertEqual(r.status_code, 201)
        return p

    def softphone(self, p):
        made = p.post("/api/handsets", {"kind": "softphone", "name": "Tablet"}).get_json()
        c = made["credentials"]
        basic = {"Authorization": "Basic " + base64.b64encode(f"{c['sip_user']}:{c['secret']}".encode()).decode()}
        return made["handset"]["id"], basic

    def leave(self, basic, code):
        return client.post("/api/phone/leave", headers=basic, json={"code": code})

    def test_a_softphone_needs_a_code_first_and_other_phones_do_not(self):
        p = self.bare_house()
        self.assertFalse(p.get("/api/me").get_json()["treehouse"]["has_parent_code"])
        r = p.post("/api/handsets", {"kind": "softphone", "name": "Tablet"})
        self.assertEqual((r.status_code, r.get_json()["code"]), (409, "needs_pin"))
        self.assertEqual(p.post("/api/handsets", {"kind": "ata", "name": "Hall"}).status_code, 201)
        # pairing a softphone by QR is held to the same rule
        start = client.post("/api/pair/start").get_json()
        r = p.post("/api/pair/claim", {"code": start["code"], "name": "Tab"})
        self.assertEqual((r.status_code, r.get_json()["code"]), (409, "needs_pin"))
        self.assertEqual(p.put("/api/treehouse/parent-code", {"code": "4821"}).status_code, 200)
        self.assertTrue(p.get("/api/me").get_json()["treehouse"]["has_parent_code"])
        self.assertEqual(p.post("/api/pair/claim", {"code": start["code"], "name": "Tab"}).status_code, 201)

    def test_the_code_is_4_to_6_digits_and_stored_only_as_a_salted_hash(self):
        p = self.bare_house()
        for bad in ("123", "1234567", "12a4", "", " 1234", "12 34"):
            self.assertEqual(p.put("/api/treehouse/parent-code", {"code": bad}).status_code, 400, bad)
        self.assertEqual(p.put("/api/treehouse/parent-code", {"code": "13579"}).status_code, 200)
        row = db.connect(os.environ["TREELINE_DB"]).execute("SELECT parent_pin_hash FROM treehouse WHERE name='No code house' ORDER BY id DESC").fetchone()
        self.assertNotIn("13579", row[0])
        self.assertTrue(row[0].startswith("scrypt$"))
        self.assertTrue(db.check_pin(row[0], "13579") and not db.check_pin(row[0], "13580"))
        self.assertNotIn("13579", p.get("/api/me").get_data(as_text=True))

    def age(self, person, minutes=60):
        """Make a person's session look like it started a while ago (a session lasts 30 days; its expiry tells when it began)."""
        db.connect(os.environ["TREELINE_DB"]).execute("UPDATE session SET expires_at=? WHERE token_hash=?",
            (db.iso(dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=api.SESSION_DAYS) - dt.timedelta(minutes=minutes)), db.hash_token(person.token)))

    def test_changing_the_code_needs_the_current_one_and_only_a_parent_can(self):
        p = make_house()                                                 # make_house sets "2468"
        self.age(p)
        r = p.put("/api/treehouse/parent-code", {"code": "1111"})
        self.assertEqual((r.status_code, r.get_json()["code"]), (403, "needs_current"))
        self.assertEqual(p.put("/api/treehouse/parent-code", {"code": "1111", "current": "0000"}).status_code, 403)
        self.assertEqual(p.put("/api/treehouse/parent-code", {"code": "1111", "current": PIN}).status_code, 200)
        sitter = Person("pin-sitter@example.com")
        self.age(sitter)
        p.post("/api/grown-ups", {"email": sitter.email, "name": "Sit", "role": "sitter"})
        self.assertEqual(sitter.put("/api/treehouse/parent-code", {"code": "9999", "current": "1111"}).status_code, 403)

    def test_leaving_phone_mode_takes_the_code_and_removes_the_handset(self):
        p = make_house()
        hid, basic = self.softphone(p)
        r = self.leave(basic, "0000")
        self.assertEqual((r.status_code, r.get_json()["code"]), (403, "bad_pin"))
        self.assertEqual(len(p.get("/api/handsets").get_json()["handsets"]), 1)            # still a phone
        self.assertEqual(self.leave({"Authorization": "Basic " + base64.b64encode(b"nobody:x").decode()}, PIN).status_code, 401)
        self.assertEqual(self.leave(basic, PIN).status_code, 200)
        self.assertEqual(p.get("/api/handsets").get_json()["handsets"], [])
        self.assertEqual(client.get("/api/line", headers=basic).status_code, 401)            # its sign-in no longer works
        log = [a["action"] for a in p.get("/api/actions").get_json()["actions"]]
        self.assertIn("handset_left", log)

    def test_only_a_softphone_can_leave_this_way(self):
        p = make_house()
        made = p.post("/api/handsets", {"kind": "ata", "name": "Hall"}).get_json()
        c = made["credentials"]
        basic = {"Authorization": "Basic " + base64.b64encode(f"{c['sip_user']}:{c['secret']}".encode()).decode()}
        self.assertEqual(self.leave(basic, PIN).status_code, 400)

    def test_wrong_codes_lock_it_even_for_the_right_one_and_a_restart_does_not_forgive(self):
        p = make_house()
        _, basic = self.softphone(p)
        for _ in range(4):
            self.assertEqual(self.leave(basic, "0000").status_code, 403)
        r = self.leave(basic, "0000")
        self.assertEqual((r.status_code, r.get_json()["code"]), (429, "pin_locked"))
        api._hits.clear()                                                                     # (the in-memory limit is not what holds)
        r = self.leave(basic, PIN)
        self.assertEqual((r.status_code, r.get_json()["code"]), (429, "pin_locked"))
        self.assertIn("minute", r.get_json()["error"])
        # the lock also stops a parent changing the code by guessing the current one
        self.assertEqual(p.put("/api/treehouse/parent-code", {"code": "1111", "current": PIN}).status_code, 429)
        # after the lock runs out, the right code works again and the count starts over
        db.connect(os.environ["TREELINE_DB"]).execute("UPDATE treehouse SET pin_locked_until=?", (db.iso(dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=1)),))
        self.assertEqual(self.leave(basic, PIN).status_code, 200)

    def test_a_right_code_forgives_earlier_wrong_ones(self):
        p = make_house()
        _, basic = self.softphone(p)
        for _ in range(3):
            self.leave(basic, "0000")
        self.assertEqual(p.put("/api/treehouse/parent-code", {"code": "2222", "current": PIN}).status_code, 200)   # a right code resets the count
        for _ in range(4):
            self.assertEqual(self.leave(basic, "0000").status_code, 403)                      # four more is still not a lock

    def test_leaving_without_a_code_set_says_so(self):
        p = self.bare_house()
        made = p.post("/api/handsets", {"kind": "ata", "name": "Hall"}).get_json()           # (a softphone can't exist without a code)
        db.connect(os.environ["TREELINE_DB"]).execute("UPDATE handset SET kind='softphone' WHERE id=?", (made["handset"]["id"],))
        c = made["credentials"]
        basic = {"Authorization": "Basic " + base64.b64encode(f"{c['sip_user']}:{c['secret']}".encode()).decode()}
        r = self.leave(basic, "1234")
        self.assertEqual((r.status_code, r.get_json()["code"]), (409, "no_pin"))

    def test_a_parent_who_forgot_the_code_can_set_a_new_one_right_after_signing_in_again(self):
        p = make_house()
        _, basic = self.softphone(p)
        self.age(p)
        self.assertEqual(p.put("/api/treehouse/parent-code", {"code": "7777"}).status_code, 403)      # an old session can't
        again = Person(p.email)                                                                        # a fresh sign-in by emailed code can
        self.assertEqual(again.put("/api/treehouse/parent-code", {"code": "7777"}).status_code, 200)
        self.assertEqual(self.leave(basic, PIN).status_code, 403)                                      # the old code no longer works
        self.assertEqual(self.leave(basic, "7777").status_code, 200)

    def test_signing_a_phone_out_needs_no_code_and_opens_nothing(self):
        p = make_house()
        hid, basic = self.softphone(p)
        self.assertEqual(client.post("/api/phone/sign-out", json={}).status_code, 401)                  # it has to be the phone itself
        self.assertEqual(client.post("/api/phone/sign-out", headers=basic, json={}).status_code, 200)
        self.assertEqual(p.get("/api/handsets").get_json()["handsets"], [])                             # the handset is removed
        self.assertEqual(client.get("/api/line", headers=basic).status_code, 401)                       # and its sign-in is dead
        self.assertEqual(p.get("/api/me").status_code, 200)                                              # nobody was signed in or out of a parent session by it
        self.assertIn("handset_signed_out", [a["action"] for a in p.get("/api/actions").get_json()["actions"]])

    def test_signing_out_is_only_for_softphones_and_a_session_cannot_stand_in_for_the_code(self):
        p = make_house()
        made = p.post("/api/handsets", {"kind": "ata", "name": "Hall"}).get_json()
        c = made["credentials"]
        ata = {"Authorization": "Basic " + base64.b64encode(f"{c['sip_user']}:{c['secret']}".encode()).decode()}
        self.assertEqual(client.post("/api/phone/sign-out", headers=ata, json={}).status_code, 400)
        hid, basic = self.softphone(p)
        r = client.post("/api/phone/leave", headers=basic, json={"session": Person(p.email).token})   # a parent's sign-in is not the code
        self.assertEqual((r.status_code, r.get_json()["code"]), (403, "bad_pin"))
        self.assertEqual(len(p.get("/api/handsets").get_json()["handsets"]), 2)
