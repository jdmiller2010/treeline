"""Sign in with Google (authorization code + PKCE) and the closed-beta access code. Google itself is replaced by a function that
returns an ID token we build: what is tested is everything WE do with what Google sends."""

import base64
import hashlib
import json
import os
import time
import unittest
import urllib.parse
from unittest import mock

from tests import helpers  # noqa: F401
from treeline import api, db, google, prod

client = api.app.test_client()
CLIENT_ID = "123-abc.apps.googleusercontent.com"
CODE = "K7MQ-2XPR"


_n = [0]


def jwt(**over):
    _n[0] += 1       # a new person each time: the test database is shared by the tests in this module
    claims = {"iss": "https://accounts.google.com", "aud": CLIENT_ID, "exp": time.time() + 600, "email": f"newparent{_n[0]}@example.com",
              "email_verified": True, "nonce": None}
    claims.update(over)
    body = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
    return f"e30.{body}.sig"


class Base(unittest.TestCase):
    def setUp(self):
        self.c = api.app.test_client()            # one browser, with its own cookies
        api._hits.clear()
        google.reset()
        patch = mock.patch.dict(os.environ, {
            "TREELINE_GOOGLE_CLIENT_ID": CLIENT_ID, "TREELINE_GOOGLE_CLIENT_SECRET": "secret-for-tests-only-0123456789",
            "TREELINE_BETA_CODE_HASH": google.hash_code(CODE), "TREELINE_BETA_CODE_EXPIRES": "2099-12-31"})
        patch.start()
        self.addCleanup(patch.stop)
        self.sent = []          # what we POSTed to "Google"
        self.reply = None       # what "Google" answers; a function of (fields) or a dict

    def fake_google(self, **claim_overrides):
        def post(url, fields, timeout=10):
            self.sent.append((url, fields))
            if callable(self.reply):
                return self.reply(fields)
            nonce = self.nonce
            return {"id_token": jwt(nonce=nonce, **claim_overrides)}
        return mock.patch.object(google, "post_form", post)

    def begin(self):
        r = self.c.get("/api/auth/google/start")
        self.assertEqual(r.status_code, 302, r.data)
        q = urllib.parse.parse_qs(urllib.parse.urlparse(r.headers["Location"]).query)
        self.nonce, self.state, self.challenge = q["nonce"][0], q["state"][0], q["code_challenge"][0]
        return r.headers["Location"], q

    def callback(self, code="google-code", state=None, **extra):
        r = self.c.get("/api/auth/google/callback?" + urllib.parse.urlencode({"code": code, "state": state or self.state, **extra}))
        self.assertEqual(r.status_code, 302)
        return r.headers["Location"].split("#/signin/")[1]

    def pending(self, **claims):
        """A new person back from Google, waiting at the beta screen: the one-time word for it."""
        self.begin()
        with self.fake_google(**claims):
            word = self.callback()
        self.assertTrue(word.startswith("p."), word)
        return word[2:]

    def beta(self, pending, code=CODE):
        return self.c.post("/api/auth/beta", json={"pending": pending, "code": code})

    def exchange(self, word):
        return self.c.post("/api/auth/exchange", json={"code": word})


class BetaCode(Base):
    def test_the_right_code_in_any_case_and_with_or_without_the_dash_lets_them_in(self):
        for text in (CODE, CODE.lower(), CODE.replace("-", ""), f" {CODE} "):
            api._hits.clear()
            r = self.beta(self.pending(), text)
            self.assertEqual(r.status_code, 200, text)
            self.assertTrue(r.get_json()["token"])

    def test_wrong_expired_and_unset_codes_read_exactly_the_same_and_leave_the_sign_in_waiting(self):
        word, outcomes = self.pending(), []
        for env, code in (({}, "AAAA-AAAA"), ({"TREELINE_BETA_CODE_EXPIRES": "2020-01-01"}, CODE), ({"TREELINE_BETA_CODE_HASH": ""}, CODE), ({}, "AB")):
            api._hits.clear()
            with mock.patch.dict(os.environ, env):
                r = self.beta(word, code)
            outcomes.append((r.status_code, r.get_json()["error"], r.get_json()["code"]))
        self.assertEqual(len(set(outcomes)), 1, outcomes)
        self.assertEqual(outcomes[0][:1] + outcomes[0][2:], (400, "bad_beta_code"))
        self.assertEqual(self.beta(word).status_code, 200, "after wrong tries the right code still works")

    def test_guessing_is_limited_per_address_and_one_stranger_cannot_lock_everyone_out(self):
        word = self.pending()
        for _ in range(10):
            self.beta(word, "AAAA-AAAA")
        self.assertEqual(self.beta(word).status_code, 429, "even the right code waits once the address is over its limit")
        # many junk tries from many addresses: an invited family at another address still gets in (no shared limit)
        api._hits.clear()
        for i in range(200):
            with mock.patch.object(api, "client_ip", lambda i=i: f"198.51.100.{i % 250}"):
                self.beta(word, "AAAA-AAAA")
        with mock.patch.object(api, "client_ip", lambda: "203.0.113.200"):
            self.assertEqual(self.beta(word).status_code, 200)

    def test_the_code_without_a_waiting_sign_in_does_nothing(self):
        r = self.c.post("/api/auth/beta", json={"code": CODE})
        self.assertEqual((r.status_code, r.get_json()["code"]), (400, "expired_signin"))
        r = self.c.post("/api/auth/beta", json={"code": CODE, "pending": "made-up"})
        self.assertEqual(r.get_json()["code"], "expired_signin")

    def test_nothing_about_a_new_person_is_saved_until_the_code_is_accepted(self):
        word = self.pending()
        email = self.c.post("/api/auth/pending", json={"pending": word}).get_json()["email"]
        self.assertTrue(email.startswith("newparent"))
        c = db.local_conn()
        self.assertIsNone(c.execute("SELECT 1 FROM session WHERE email=?", (email,)).fetchone(), "no session before the code")
        self.beta(word, "AAAA-AAAA")
        self.assertIsNone(c.execute("SELECT 1 FROM session WHERE email=?", (email,)).fetchone(), "nor after a wrong code")
        self.assertEqual(self.beta(word).status_code, 200)
        self.assertIsNotNone(c.execute("SELECT 1 FROM session WHERE email=?", (email,)).fetchone())
        self.assertEqual(self.beta(word).status_code, 400, "a waiting sign-in is used once")

    def test_the_waiting_sign_in_is_useless_in_another_browser(self):
        word = self.pending()
        other = api.app.test_client()
        self.assertEqual(other.post("/api/auth/pending", json={"pending": word}).status_code, 400)
        self.assertEqual(other.post("/api/auth/beta", json={"pending": word, "code": CODE}).status_code, 400)
        self.assertEqual(self.beta(word).status_code, 200, "and it still works in the browser that started it")

    def test_starting_over_forgets_an_unfinished_setup_and_the_same_code_works_again(self):
        word = self.pending(email="startover@example.com")
        old = self.beta(word).get_json()["token"]
        self.assertEqual(self.c.get("/api/me", headers={"Authorization": f"Bearer {old}"}).status_code, 200)
        word = self.pending(email="startover@example.com")      # left without making a treehouse, then came back
        new = self.beta(word).get_json()["token"]
        self.assertEqual(self.c.get("/api/me", headers={"Authorization": f"Bearer {old}"}).status_code, 401, "the old sign-in is gone")
        self.assertEqual(self.c.get("/api/me", headers={"Authorization": f"Bearer {new}"}).status_code, 200)

    def test_a_generated_code_is_eight_characters_from_the_unambiguous_alphabet_and_checks_out(self):
        for _ in range(50):
            c = google.new_code()
            self.assertRegex(c, r"^[ABCDEFGHJKMNPQRSTUVWXYZ23456789]{4}-[ABCDEFGHJKMNPQRSTUVWXYZ23456789]{4}$")
            with mock.patch.dict(os.environ, {"TREELINE_BETA_CODE_HASH": google.hash_code(c)}):
                self.assertEqual(google.check_code(c), "ok")


class GrownUpInvite(Base):
    def test_in_production_the_invite_says_to_use_google_with_that_address(self):
        from tests import test_api
        sent = []
        p = test_api.Person()                       # signed in the development way, then the server behaves as production
        p.post("/api/treehouse", {"name": "Invite house 2", "timezone": "America/Los_Angeles", "ack_911": True, "consent": True, "your_name": "Pat"})
        with mock.patch.object(api.mail, "send", lambda to, subj, body: sent.append(body) or True), \
                mock.patch.object(prod, "is_production", lambda env=None: True):
            r = p.post("/api/grown-ups", {"email": f"sitter-invite{time.time_ns()}@example.com", "role": "sitter"})
        self.assertEqual(r.status_code, 201, r.data)
        self.assertIn("Continue with Google", sent[-1])
        self.assertIn("has to be a Google account", sent[-1])


class Flow(Base):
    def test_the_redirect_to_google_carries_pkce_state_nonce_and_only_the_scopes_we_need(self):
        url, q = self.begin()
        self.assertTrue(url.startswith("https://accounts.google.com/o/oauth2/v2/auth?"))
        self.assertEqual(q["response_type"], ["code"])
        self.assertEqual(q["scope"], ["openid email"])
        self.assertEqual(q["code_challenge_method"], ["S256"])
        self.assertEqual(q["client_id"], [CLIENT_ID])
        self.assertTrue(q["redirect_uri"][0].endswith("/api/auth/google/callback"))
        self.assertNotIn("client_secret", url)
        self.assertGreaterEqual(len(self.state), 24)

    def test_a_new_person_signs_in_then_gives_the_code_and_can_make_a_treehouse(self):
        self.begin()
        with self.fake_google():
            word = self.callback()
        self.assertTrue(word.startswith("p."), "a new person is asked for the code after Google")
        # the code and the verifier went to Google, and the verifier is the one behind the challenge
        url, fields = self.sent[0]
        self.assertEqual(url, "https://oauth2.googleapis.com/token")
        self.assertEqual(fields["client_secret"], os.environ["TREELINE_GOOGLE_CLIENT_SECRET"])
        digest = base64.urlsafe_b64encode(hashlib.sha256(fields["code_verifier"].encode()).digest()).rstrip(b"=").decode()
        self.assertEqual(digest, self.challenge)
        self.assertEqual(self.exchange(word[2:]).status_code, 400, "a waiting sign-in is not a session")
        r = self.beta(word[2:])
        self.assertEqual(r.status_code, 200)
        token = r.get_json()["token"]
        me = self.c.get("/api/me", headers={"Authorization": f"Bearer {token}"}).get_json()
        self.assertTrue(me["email"].startswith("newparent"))
        self.assertIsNone(me["treehouse"])
        made = self.c.post("/api/treehouse", headers={"Authorization": f"Bearer {token}"},
                           json={"name": "Google house", "ack_911": True, "consent": True, "timezone": "America/Los_Angeles"})
        self.assertEqual(made.status_code, 201)
        self.assertEqual(self.beta(word[2:]).status_code, 400, "the one-time word works once")

    def test_a_grown_up_a_parent_added_signs_in_with_google_alone(self):
        _n[0] += 1
        c = db.local_conn()
        tid = db.create_treehouse(c, "Added house", timezone="America/Los_Angeles")
        c.execute("INSERT INTO grown_up(email,name,treehouse_id,role,created_at) VALUES(?,?,?,?,?)",
                  (f"sitter{_n[0]}@example.com", "Sam", tid, "sitter", db.iso()))
        self.begin()
        with self.fake_google(email=f"Sitter{_n[0]}@Example.com"):
            word = self.callback()
        self.assertTrue(word.startswith("x."), word)
        token = self.exchange(word[2:]).get_json()["token"]
        me = self.c.get("/api/me", headers={"Authorization": f"Bearer {token}"}).get_json()
        self.assertEqual(me["grown_up"]["role"], "sitter")

    def test_a_callback_url_opened_in_another_browser_signs_nobody_in(self):
        """Login CSRF (R6-1): an attacker who starts a sign-in with their own Google account and sends the callback URL to someone
        else must not get that person signed in as the attacker. The other browser has no binding cookie."""
        self.begin()
        attacker = self.c
        self.c = api.app.test_client()                # the victim's browser: never visited /start
        with self.fake_google():
            self.assertEqual(self.callback(), "e.expired")
        self.assertEqual(self.sent, [], "nothing may be sent to Google for a browser that did not start the sign-in")
        self.c = attacker
        with self.fake_google():
            self.assertEqual(self.callback(), "e.expired", "and the state is used up")

    def test_a_callback_with_someone_elses_binding_cookie_is_refused(self):
        self.begin()
        self.c.set_cookie(api.SIGNIN_COOKIE, "a-value-that-was-never-issued", domain="localhost")
        with self.fake_google():
            self.assertEqual(self.callback(), "e.expired")
        self.assertEqual(self.sent, [])

    def test_the_one_time_word_is_useless_in_another_browser(self):
        _n[0] += 1
        c = db.local_conn()
        tid = db.create_treehouse(c, f"Word house {_n[0]}", timezone="America/Los_Angeles")
        c.execute("INSERT INTO grown_up(email,name,treehouse_id,role,created_at) VALUES(?,?,?,?,?)",
                  (f"known{_n[0]}@example.com", "Kim", tid, "parent", db.iso()))
        self.begin()
        with self.fake_google(email=f"known{_n[0]}@example.com"):
            word = self.callback()
        self.assertTrue(word.startswith("x."))
        other = api.app.test_client()
        self.assertEqual(other.post("/api/auth/exchange", json={"code": word[2:]}).status_code, 400)
        self.assertEqual(self.exchange(word[2:]).status_code, 400, "and a word tried in the wrong browser is used up")

    def test_the_binding_cookie_is_http_only_lax_and_short_lived_and_secure_on_https(self):
        r = self.c.get("/api/auth/google/start", headers={"X-Forwarded-Proto": "https"})
        cookie = r.headers["Set-Cookie"]
        self.assertTrue(cookie.startswith("__Host-tl_signin="), cookie)
        for part in ("HttpOnly", "SameSite=Lax", "Path=/", "Secure", "Max-Age=600"):
            self.assertIn(part, cookie)
        self.assertNotIn("Domain=", cookie)

    def test_nothing_is_sent_to_the_token_endpoint_for_an_unknown_or_replayed_state(self):
        with self.fake_google():
            self.assertEqual(self.callback(state="made-up"), "e.expired")
            self.begin()
            first = self.callback()
            self.assertTrue(first.startswith("p."))
            sent = len(self.sent)
            self.assertEqual(self.callback(), "e.expired", "a state works once")
            self.assertEqual(len(self.sent), sent)

    def test_google_saying_no_ends_the_attempt(self):
        self.begin()
        with self.fake_google():
            word = self.callback(error="access_denied")
        self.assertEqual(word, "e.denied")
        self.assertEqual(self.sent, [])
        self.assertFalse(google.alive("state", self.state), "the state is used up")

    def test_each_bad_token_is_refused_and_creates_no_session(self):
        cases = {
            "the wrong audience": dict(aud="someone-elses-app.apps.googleusercontent.com"),
            "an expired token": dict(exp=time.time() - 10),
            "a token that does not say it is Google's": dict(iss="https://evil.example.invalid"),
            "an unverified email": dict(email_verified=False),
            "no email": dict(email=""),
            "an email that is not an address": dict(email="not-an-email"),
            "a nonce from another sign-in": dict(nonce="somebody-elses-nonce"),
        }
        for what, over in cases.items():
            with self.subTest(what):
                google.reset()
                self.begin()
                nonce_given = over.get("nonce") or self.nonce
                self.reply = lambda f, o=over, n=nonce_given: {"id_token": jwt(**{"nonce": n, **o})}
                with mock.patch.object(google, "post_form", lambda url, fields, timeout=10: self.reply(fields)):
                    word = self.callback()
                self.assertTrue(word.startswith("e."), f"{what} was accepted: {word}")

    def test_a_failed_exchange_and_a_reply_without_a_token_are_refused(self):
        for reply in ({}, {"error": "invalid_grant"}, None):
            google.reset()
            self.begin()
            with mock.patch.object(google, "post_form", lambda url, fields, timeout=10, r=reply: r):
                self.assertEqual(self.callback(), "e.exchange")
        google.reset()
        self.begin()
        def boom(url, fields, timeout=10):
            raise google.GoogleError("exchange", "HTTP 400")
        with mock.patch.object(google, "post_form", boom):
            self.assertEqual(self.callback(), "e.exchange")

    def test_the_emailed_code_routes_are_gone_in_production_and_still_work_for_the_test_suites(self):
        with mock.patch.object(prod, "is_production", lambda env=None: True):
            self.assertEqual(self.c.post("/api/auth/request", json={"email": "a@example.com"}).status_code, 404)
            self.assertEqual(self.c.post("/api/auth/verify", json={"email": "a@example.com", "code": "123456"}).status_code, 404)
            self.assertEqual(self.c.get("/api/auth/config").get_json(), {"google": True, "email_code": False, "dev": True})
        r = self.c.post("/api/auth/request", json={"email": "devperson@example.com"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("dev_code", r.get_json())

    def test_google_is_off_until_it_is_configured(self):
        with mock.patch.dict(os.environ, {"TREELINE_GOOGLE_CLIENT_SECRET": ""}):
            self.assertFalse(self.c.get("/api/auth/config").get_json()["google"])
            self.assertEqual(self.c.get("/api/auth/google/start").status_code, 404)

    def test_the_one_time_word_expires(self):
        key = google.put("exchange", 60, {"email": "late@example.com"})
        google._store[("exchange", key)] = (time.time() - 1, {"email": "late@example.com", "binding": ""})
        self.assertEqual(self.exchange(key).status_code, 400)


if __name__ == "__main__":
    unittest.main()


class StringCodeIsABetaPass(Base):
    """A family's string code lets one new person into the closed beta, and their treehouse is strung to that family when it's made."""

    def setUp(self):
        super().setUp()
        from tests.test_api import make_house
        self.inviter = make_house("Inviter house")
        api._hits.clear()
        self.code = self.inviter.post("/api/ladder-codes").get_json()["code"]
        api._hits.clear()

    def signed_in(self, code=None, **claims):
        """A new person back from Google who gets past the beta screen with `code`: their bearer headers and email."""
        word = self.pending(**claims)
        email = self.c.post("/api/auth/pending", json={"pending": word}).get_json()["email"]
        r = self.beta(word, code or self.code)
        self.assertEqual(r.status_code, 200, r.data)
        return {"Authorization": "Bearer " + r.get_json()["token"]}, email

    def setup(self, headers, **extra):
        return self.c.post("/api/treehouse", headers=headers,
                           json={"name": "Newcomer house", "ack_911": True, "consent": True, **extra})

    def row(self):
        return db.local_conn().execute("SELECT * FROM ladder_code WHERE code=?", (self.code.replace("-", ""),)).fetchone()

    def test_the_string_code_lets_them_in_and_setup_sends_the_string_request(self):
        headers, email = self.signed_in(self.code.lower().replace("-", ""))
        self.assertEqual(self.row()["claimed_by"], email)
        self.assertIsNone(self.row()["used_at"], "claimed, not used: it is used when the string request goes")
        r = self.setup(headers)
        self.assertEqual(r.status_code, 201, r.data)
        made = r.get_json()["string"]
        self.assertEqual((made["state"], made["other"]["name"], made["mine_approved"], made["theirs_approved"]),
                         ("waiting", "Inviter house", True, False))          # the inviting family still approves
        self.assertTrue(self.row()["used_at"])
        self.assertEqual((self.row()["claimed_by"], self.row()["claimed_at"]), (None, None), "used: the newcomer's address is not kept on it")
        theirs = self.inviter.get("/api/home").get_json()
        self.assertIn("Newcomer house would like to string with you", [n["title"] for n in theirs["notices"]])

    def test_a_claimed_code_is_nobody_elses_pass_or_string_but_the_same_person_can_sign_in_again(self):
        headers, email = self.signed_in()
        api._hits.clear()
        other = self.beta(self.pending(), self.code)
        self.assertEqual((other.status_code, other.get_json()["code"]), (400, "bad_beta_code"))
        api._hits.clear()
        word = self.pending(email=email)                                   # the same person, back after their session lapsed
        self.assertEqual(self.beta(word, self.code).status_code, 200)
        from tests.test_api import make_house
        family = make_house("Someone else")
        r = family.post("/api/strings/redeem", {"code": self.code})
        self.assertEqual((r.status_code, r.get_json()["code"]), (400, "bad_ladder"), "an existing family can't take a claimed code")

    def test_used_expired_and_paused_family_codes_read_like_a_wrong_code(self):
        c = db.local_conn()
        outcomes = []
        for change in ("UPDATE ladder_code SET used_at='2026-01-01T00:00:00+00:00' WHERE code=?",
                       "UPDATE ladder_code SET expires_at='2020-01-01T00:00:00+00:00' WHERE code=?",
                       None):
            api._hits.clear()
            code = self.inviter.post("/api/ladder-codes").get_json()["code"]
            if change:
                c.execute(change, (code.replace("-", ""),))
            else:
                c.execute("UPDATE treehouse SET archived_at=? WHERE id=?", (db.iso(), self.inviter.house["id"]))
            api._hits.clear()
            r = self.beta(self.pending(), code)
            outcomes.append((r.status_code, r.get_json()["code"], r.get_json()["error"]))
        c.execute("UPDATE treehouse SET archived_at=NULL WHERE id=?", (self.inviter.house["id"],))
        api._hits.clear()
        wrong = self.beta(self.pending(), "AAAA-AAAA")
        self.assertEqual(set(outcomes), {(400, "bad_beta_code", wrong.get_json()["error"])})

    def test_the_real_beta_code_still_works_and_a_scanned_code_can_come_with_setup(self):
        headers, _ = self.signed_in(CODE)
        self.assertIsNone(self.row()["claimed_by"])
        r = self.setup(headers, string_code=self.code)                     # scanned before signing in: the page kept it
        self.assertEqual(r.get_json()["string"]["other"]["name"], "Inviter house")

    def test_other_codes_they_claimed_are_let_go_once_their_treehouse_is_made(self):
        """Security review note: a second claimed code kept the newcomer's address, and stayed unusable, for up to 7 days."""
        api._hits.clear()
        other = self.inviter.post("/api/ladder-codes").get_json()["code"]
        headers, email = self.signed_in()
        api._hits.clear()
        word = self.pending(email=email)
        r = self.beta(word, other)                                              # the same person claims a second code too
        self.assertEqual(r.status_code, 200)
        headers = {"Authorization": "Bearer " + r.get_json()["token"]}           # (signing in again starts their session over)
        self.assertEqual(self.setup(headers).status_code, 201)
        rows = [db.local_conn().execute("SELECT * FROM ladder_code WHERE code=?", (c.replace("-", ""),)).fetchone() for c in (self.code, other)]
        self.assertEqual(sorted(bool(r["used_at"]) for r in rows), [False, True], "one of the two is used for the string")
        self.assertEqual([(r["claimed_by"], r["claimed_at"]) for r in rows], [(None, None)] * 2, "and neither keeps their address")

    def test_setup_still_makes_the_treehouse_when_the_string_cant_be_made(self):
        headers, _ = self.signed_in()
        db.local_conn().execute("UPDATE treehouse SET archived_at=? WHERE id=?", (db.iso(), self.inviter.house["id"]))
        try:
            r = self.setup(headers)
        finally:
            db.local_conn().execute("UPDATE treehouse SET archived_at=NULL WHERE id=?", (self.inviter.house["id"],))
        self.assertEqual(r.status_code, 201)
        self.assertTrue(r.get_json()["treehouse"]["number"])
        self.assertNotIn("string", r.get_json())
        self.assertIn("didn't work", r.get_json()["string_error"])


    def test_a_claim_by_someone_who_never_made_a_treehouse_is_forgotten_after_a_day(self):
        import datetime as dt
        from treeline import jobs
        self.signed_in()
        jobs.forget_unfinished_setups(db.local_conn(), db.utcnow() + dt.timedelta(hours=23))
        self.assertIsNotNone(self.row()["claimed_by"], "within the day it stays theirs")
        jobs.forget_unfinished_setups(db.local_conn(), db.utcnow() + dt.timedelta(hours=25))
        self.assertEqual((self.row()["claimed_by"], self.row()["claimed_at"], self.row()["used_at"]), (None, None, None),
                         "after a day: their address is gone and the code is free again")
        api._hits.clear()
        self.assertEqual(self.beta(self.pending(), self.code).status_code, 200, "so someone else can use it now")


class LadderClaimMigration(unittest.TestCase):
    """Rule 6 of DATA_LAYER.md for central step 4: a file at version 4, with a string code in it, moved forward."""

    def test_step_4_adds_the_claim_and_keeps_the_codes(self):
        import tempfile
        path = os.path.join(tempfile.mkdtemp(prefix="treeline-claim-"), "t.db")
        c = db.connect(path, migrations=db.MIGRATIONS[:3])                     # the release before step 4
        self.assertEqual(c.execute("PRAGMA user_version").fetchone()[0], 4)
        tid = db.create_treehouse(c, "Old house")
        c.execute("INSERT INTO ladder_code(code,treehouse_id,expires_at) VALUES('ABCD2345',?,'2999-01-01T00:00:00+00:00')", (tid,))
        c.close()
        c = db.connect(path)
        self.assertEqual(c.execute("PRAGMA user_version").fetchone()[0], len(db.MIGRATIONS) + 1)
        row = c.execute("SELECT * FROM ladder_code").fetchone()
        self.assertEqual((row["code"], row["treehouse_id"], row["claimed_by"], row["claimed_at"]), ("ABCD2345", tid, None, None))
        c.close()
        c = db.connect(path)                                                    # again: nothing to do
        self.assertEqual(c.execute("PRAGMA user_version").fetchone()[0], len(db.MIGRATIONS) + 1)
        c.close()
