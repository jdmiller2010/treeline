"""Sign in with Google (authorization-code flow with PKCE, done on the server) and the closed-beta access code.

The browser is sent to Google; Google sends it back with a one-time `code`; this server exchanges the code at Google's token
endpoint over TLS, with the client secret and the PKCE verifier, and reads the ID token from that response. Because the token
comes straight from Google over TLS to us, its signature is not checked (docs/DEPLOY_AWS.md work package 5); its claims are:
iss, aud, exp, nonce and email_verified. State, nonce and the verifier live in memory for ten minutes and are single use
(one gunicorn worker: the same assumption as the rate limits); a restart only means a person tries again.

The beta access code is one shared code, 8 characters, that lets someone CREATE a treehouse. Only its hash and an expiry are
configured (SSM, then the environment). Grown-ups a parent added sign in with Google alone.
"""

import base64
import hashlib
import json
import os
import re
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

ISSUERS = ("https://accounts.google.com", "accounts.google.com")
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"        # the ladder alphabet: no 0/O/1/I/L
STATE_TTL, GATE_TTL, EXCHANGE_TTL = 600, 900, 60
_lock = threading.Lock()
_store = {}


class GoogleError(Exception):
    """Sign-in with Google did not work; `reason` is a short word the web page turns into a message."""

    def __init__(self, reason, detail=""):
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason


def auth_url():
    return os.environ.get("TREELINE_GOOGLE_AUTH_URL", "https://accounts.google.com/o/oauth2/v2/auth")


def token_url():
    return os.environ.get("TREELINE_GOOGLE_TOKEN_URL", "https://oauth2.googleapis.com/token")


def configured():
    return bool(os.environ.get("TREELINE_GOOGLE_CLIENT_ID") and os.environ.get("TREELINE_GOOGLE_CLIENT_SECRET"))


# ------------------------------------------------------------------ single-use, short-lived state
def put(kind, ttl, data):
    key = secrets.token_urlsafe(24)
    with _lock:
        _prune()
        _store[(kind, key)] = (time.time() + ttl, data)
    return key


def take(kind, key):
    """The data for `key`, once. None if unknown, used or expired."""
    with _lock:
        item = _store.pop((kind, str(key or "")), None)
    return item[1] if item and item[0] > time.time() else None


def alive(kind, key):
    with _lock:
        item = _store.get((kind, str(key or "")))
    return bool(item and item[0] > time.time())


def _prune():
    now = time.time()
    for k in [k for k, v in _store.items() if v[0] <= now]:
        del _store[k]


def reset():
    with _lock:
        _store.clear()


# ------------------------------------------------------------------ the beta code
def normalize_code(value):
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def hash_code(value):
    return hashlib.sha256(normalize_code(value).encode()).hexdigest()


def new_code():
    c = "".join(secrets.choice(CODE_ALPHABET) for _ in range(8))
    return c[:4] + "-" + c[4:]


def check_code(value, now=None):
    """'ok', or a reason that is never shown to the person (wrong, expired and unset all read the same)."""
    want, expires = os.environ.get("TREELINE_BETA_CODE_HASH", ""), os.environ.get("TREELINE_BETA_CODE_EXPIRES", "")
    if not re.match(r"^[0-9a-f]{64}$", want) or not re.match(r"^\d{4}-\d{2}-\d{2}$", expires):
        return "unset"
    if len(normalize_code(value)) != 8:
        return "bad"
    ok = secrets.compare_digest(hash_code(value), want)
    today = time.strftime("%Y-%m-%d", time.gmtime(now or time.time()))
    if today > expires:
        return "expired"
    return "ok" if ok else "bad"


# ------------------------------------------------------------------ the OAuth round trip
def _b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def binding_hash(value):
    return hashlib.sha256(str(value or "").encode()).hexdigest()


def bound(saved, cookie):
    """True if this browser is the one that started the sign-in (its cookie matches the hash kept with the state)."""
    return bool(cookie) and secrets.compare_digest(saved.get("binding", ""), binding_hash(cookie))


STEPUP_SLACK = 5        # seconds: Google's clock against ours, for "the sign-in happened after we asked for it"


def start(redirect_uri, gate=None, binding=None, stepup=None):
    """The URL to send the browser to. Remembers the PKCE verifier, the nonce, the gate and the browser binding for the callback.
    `binding` is the hash of a random cookie set on the browser that started; without it, anyone who got hold of the callback URL
    could finish someone else's sign-in in their own browser (login CSRF, SECURITY.md R6-1)."""
    verifier = secrets.token_urlsafe(48)
    nonce = secrets.token_urlsafe(24)
    if stepup is not None:
        stepup = {"token_hash": stepup["token_hash"], "email": stepup["email"], "at": time.time()}
    state = put("state", STATE_TTL, {"verifier": verifier, "nonce": nonce, "gate": gate, "redirect_uri": redirect_uri,
                                     "binding": binding or "", "stepup": stepup})
    fields = {
        "client_id": os.environ["TREELINE_GOOGLE_CLIENT_ID"], "redirect_uri": redirect_uri, "response_type": "code",
        "scope": "openid email", "state": state, "nonce": nonce, "prompt": "select_account",
        "code_challenge": _b64url(hashlib.sha256(verifier.encode()).digest()), "code_challenge_method": "S256"}
    if stepup:
        # A step-up (docs/ADMIN.md): Google must ask for the password again (prompt=login), and say when it did (max_age=0 makes the
        # ID token carry auth_time, which finish() checks). An old Google session in the browser is not enough.
        fields.update({"prompt": "login", "max_age": "0", "login_hint": stepup["email"]})
    query = urllib.parse.urlencode(fields)
    return f"{auth_url()}?{query}"


def post_form(url, fields, timeout=10):
    """POST form fields; returns the decoded JSON body. Overridable in tests."""
    req = urllib.request.Request(url, data=urllib.parse.urlencode(fields).encode(),
                                 headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as err:
        raise GoogleError("exchange", f"HTTP {err.code}") from err
    except (urllib.error.URLError, OSError, ValueError) as err:
        raise GoogleError("exchange", str(err)) from err


def claims_of(id_token):
    try:
        return json.loads(base64.urlsafe_b64decode(id_token.split(".")[1] + "=" * (-len(id_token.split(".")[1]) % 4)))
    except (IndexError, ValueError, AttributeError) as err:
        raise GoogleError("token", "not a JWT") from err


def validate_claims(claims, nonce, client_id, now=None):
    """Raises GoogleError unless the token is for us, from Google, current, for this sign-in, and has a verified email."""
    if claims.get("iss") not in ISSUERS:
        raise GoogleError("token", "wrong issuer")
    aud = claims.get("aud")
    if client_id not in (aud if isinstance(aud, list) else [aud]):
        raise GoogleError("token", "wrong audience")
    if not isinstance(claims.get("exp"), (int, float)) or claims["exp"] <= (now or time.time()):
        raise GoogleError("token", "expired")
    if not secrets.compare_digest(str(claims.get("nonce", "")), str(nonce)):
        raise GoogleError("token", "wrong nonce")
    if claims.get("email_verified") not in (True, "true"):
        raise GoogleError("unverified", "email not verified")
    email = str(claims.get("email", "")).strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) or len(email) > 200:
        raise GoogleError("token", "no email")
    return email


def finish(code, state, cookie=None, now=None, post=None):
    """Complete the sign-in. Returns (email, gate, binding, stepup) or raises GoogleError. For a step-up, the token must say the person
    signed in to Google AFTER we asked (auth_time), and be for the same email. The state is used up even when this fails,
    and nothing is sent to Google unless this browser is the one that started (the binding cookie matches)."""
    saved = take("state", state)
    if saved is None:
        raise GoogleError("expired", "unknown or used state")
    if not bound(saved, cookie):
        raise GoogleError("expired", "not the browser that started this sign-in")
    if not code:
        raise GoogleError("denied", "no code")
    reply = (post or post_form)(token_url(), {
        "grant_type": "authorization_code", "code": code, "redirect_uri": saved["redirect_uri"],
        "client_id": os.environ["TREELINE_GOOGLE_CLIENT_ID"], "client_secret": os.environ["TREELINE_GOOGLE_CLIENT_SECRET"],
        "code_verifier": saved["verifier"]})
    if not isinstance(reply, dict) or not reply.get("id_token"):
        raise GoogleError("exchange", "no id_token")
    claims = claims_of(reply["id_token"])
    email = validate_claims(claims, saved["nonce"], os.environ["TREELINE_GOOGLE_CLIENT_ID"], now)
    stepup = saved.get("stepup")
    if stepup:
        at = claims.get("auth_time")
        if type(at) not in (int, float) or at < stepup["at"] - STEPUP_SLACK or at > (now or time.time()) + 60:
            raise GoogleError("stepup", "Google did not ask for the password again")
        if email != stepup["email"]:
            raise GoogleError("stepup", "a different Google account")
    return email, saved["gate"], saved["binding"], stepup
