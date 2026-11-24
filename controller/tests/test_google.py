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
