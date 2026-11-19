import base64
import datetime as dt
import os
import unittest

from tests import helpers
from treeline import api, db, rules

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

    def delete(self, path, json=None):
        return client.delete(path, headers=self.h(), json=json or {})


def make_house(name="Bennett house", tz="America/Los_Angeles", email=None):
    p = Person(email)
    r = p.post("/api/treehouse", {"name": name, "timezone": tz, "ack_911": True, "consent": True, "your_name": "Pat"})
    assert r.status_code == 201, r.get_json()
    p.house = r.get_json()["treehouse"]
    return p


def string_up(a, b):
    code = a.post("/api/ladder-codes").get_json()["code"]
    s = b.post("/api/strings/redeem", {"code": code}).get_json()
    a.post(f"/api/strings/{s['id']}/approve")
    return s["id"]


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
        row = helpers.db.connect().execute("SELECT consent_at, consent_version FROM treehouse WHERE id=?",
                                           (r.get_json()["treehouse"]["id"],)).fetchone()
        self.assertTrue(row["consent_at"])
        self.assertEqual(row["consent_version"], api.PRIVACY_VERSION)

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

    def test_change_number_rests_the_old_one_and_tells_friends(self):
        a, b = make_house("A"), make_house("B")
        string_up(a, b)
        old = a.house["number"]
        new = a.post("/api/treehouse/number").get_json()["number"]
        self.assertNotEqual(old, new)
        self.assertFalse(db.number_is_free(helpers.db.connect(), old))
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
        self.assertEqual(sitter.post("/api/ladder-codes").status_code, 403)
        self.assertEqual(sitter.post("/api/handsets", {"kind": "softphone", "name": "x"}).status_code, 403)
        self.assertEqual(sitter.post("/api/grown-ups", {"email": "x@example.com"}).status_code, 403)
        self.assertEqual(sitter.get("/api/calls.csv").status_code, 403)

    def test_cannot_remove_the_last_parent(self):
        p = make_house()
        me = p.get("/api/grown-ups").get_json()["grown_ups"][0]
        self.assertEqual(p.delete(f"/api/grown-ups/{me['id']}").status_code, 409)

    def test_grown_up_in_another_treehouse(self):
        a, b = make_house(), make_house()
        self.assertEqual(a.post("/api/grown-ups", {"email": b.email}).status_code, 409)

    def test_leave_ends_strings_frees_nothing_and_tells_friends(self):
        a, b = make_house("Leaver"), make_house("Stayer")
        string_up(a, b)
        number = a.house["number"]
        self.assertEqual(a.post("/api/treehouse/leave", {"confirm": "nope"}).status_code, 400)
        self.assertEqual(a.post("/api/treehouse/leave", {"confirm": "leaver"}).status_code, 200)
        self.assertEqual(b.get("/api/strings").get_json()["strings"], [])
        self.assertIn("Leaver left the Treeline", [n["title"] for n in b.get("/api/home").get_json()["notices"]])
        self.assertFalse(db.number_is_free(helpers.db.connect(), number))
        self.assertIsNone(a.get("/api/me").get_json()["treehouse"])

    def test_delete_removes_everything(self):
        a, b = make_house("Gone"), make_house("Kept")
        string_up(a, b)
        c = helpers.db.connect()
        c.execute("INSERT INTO call(started_at,caller_treehouse,callee_treehouse,dialed,state,result) "
                  "VALUES(?,?,?,?,?,?)", (db.iso(), a.house["id"], b.house["id"], b.house["number"], "ended", "connected"))
        a.post("/api/handsets", {"kind": "softphone", "name": "Tablet"})
        self.assertEqual(a.delete("/api/treehouse", {"confirm": "gone"}).status_code, 200)
        for table, col in (("grown_up", "treehouse_id"), ("handset", "treehouse_id"), ("notice", "treehouse_id"),
                           ("parent_action", "treehouse_id")):
            self.assertEqual(c.execute(f"SELECT COUNT(*) n FROM {table} WHERE {col}=?",
                                       (a.house["id"],)).fetchone()["n"], 0, table)
        # The other family's log keeps its side of the call, without the deleted house's identity.
        calls = b.get("/api/calls?range=all").get_json()["calls"]
        self.assertEqual(len(calls), 1)
        self.assertEqual(a.get("/api/me").status_code, 401)  # sessions are gone


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

    def test_only_parents_can_disconnect_a_phone_and_only_their_own(self):
        a, b = make_house(), make_house()
        hid = a.post("/api/handsets", {"kind": "softphone", "name": "K"}).get_json()["handset"]["id"]
        self.assertEqual(b.patch(f"/api/handsets/{hid}", {"disabled": True}).status_code, 404)
        a.post("/api/grown-ups", {"email": "sit2@example.com", "role": "sitter"})
        sitter = Person("sit2@example.com")
        self.assertEqual(sitter.patch(f"/api/handsets/{hid}", {"disabled": True}).status_code, 403)
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
        cur = self.c.execute(
            "INSERT INTO call(started_at,caller_treehouse,callee_treehouse,dialed,state,result,reason,talk_sec)"
            " VALUES(?,?,?,?,?,?,?,?)", (db.iso(), caller["id"], callee["id"] if callee else None,
                                          dialed or (callee["number"] if callee else "9999"), "ended", result,
                                          reason, talk))
        return cur.lastrowid

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
        c.execute("INSERT INTO call(started_at,caller_treehouse,callee_treehouse,dialed,state,result,talk_sec) "
                  "VALUES(?,?,?,?,?,?,?)", (db.iso(), a.house["id"], b.house["id"], "x", "ended", "connected", 60))
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
