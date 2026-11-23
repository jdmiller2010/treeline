"""The Treeline Admin API (docs/ADMIN.md): for the people who run Treeline, never for a family.

What keeps an admin from becoming a way into a family, by construction:
- An admin is an email in `app_admin`, not a role of a grown-up. These routes never set g.th or g.gu, never open a household file
  (no `households` import, enforced by a test), and nothing here inserts a grown-up, a handset, a session, a pairing or a ladder code.
- The server is the only gate. The menu flag in /api/me only hides a link. A person who is not an admin gets exactly the answer an
  unknown address gets (404), on every route here.
- An admin's session must be young: a session older than ADMIN_SESSION_HOURS (or one that predates the column) gets 401
  `needs_fresh_signin`, so a stolen token from last month is not an admin token.
- Responses are built from explicit column lists, never from a row that may grow a column later.
"""
import datetime as dt
import json
import os
import re
import secrets
import time
from functools import wraps

from flask import g, jsonify, request

from . import db
from . import google
from .api import (ApiError, app, bearer, client_ip, conn, emailed_codes_allowed, now, rate_limit, set_signin_cookie,
                  signin_origin, use_login_code)

ADMIN_SESSION_HOURS = 12

# The root helper on the machine (deploy/native/bin/treeline_bridge.py) reads requests from BRIDGE_REQ and answers in BRIDGE_OUT. These
# two lists must equal its SOURCES and SINCE (a test compares them); the API and controller logs are deliberately absent.
BRIDGE_REQ = os.environ.get("TREELINE_BRIDGE_REQ", "/var/lib/treeline/bridge/req")
BRIDGE_OUT = os.environ.get("TREELINE_BRIDGE_OUT", "/run/treeline/bridge")
LOG_SOURCES = ("deploy", "backup", "health", "certsync", "caddy", "bridge")
LOG_SINCE = ("15m", "1h", "6h", "24h", "boot")
LOG_ID = re.compile(r"[0-9a-f]{32}")


def admin_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        token = bearer()
        row = token and conn().execute("SELECT email, created_at, stepped_up_at FROM session WHERE token_hash=? AND expires_at>?",
                                       (db.hash_token(token), db.iso())).fetchone()
        if not row:
            raise ApiError("Please sign in again.", 401, "signed_out")
        if not db.is_admin(conn(), row["email"]):
            raise ApiError("That page isn't here.", 404)
        started = db.parse(row["created_at"]) if row["created_at"] else None
        if started is None or started < now() - dt.timedelta(hours=ADMIN_SESSION_HOURS):
            raise ApiError("Please sign in again to use the admin page.", 401, "needs_fresh_signin")
        rate_limit("admin:" + row["email"], 120, 600)
        g.email, g.admin = row["email"], True
        g.session_hash, g.stepped_up_at = db.hash_token(token), row["stepped_up_at"]
        return fn(*a, **kw)
    return wrapper


STEPUP_MINUTES = 15


def stepped_up():
    at = db.parse(g.stepped_up_at) if g.stepped_up_at else None
    return at is not None and at >= now() - dt.timedelta(minutes=STEPUP_MINUTES)


def admin_action(fn):
    """An admin route that CHANGES something: an admin session (admin_required) that has also proved, with a fresh Google sign-in
    in the last STEPUP_MINUTES, that the person is still there. A token taken from a browser is not enough on its own."""
    @admin_required
    @wraps(fn)
    def wrapper(*a, **kw):
        if not stepped_up():
            raise ApiError("Confirm it's you to do that: sign in with Google again.", 403, "needs_stepup")
        rate_limit("adminact:" + g.email, 30, 600)
        return fn(*a, **kw)
    return wrapper


@app.get("/api/admin/admins")
@admin_required
def admin_admins():
    return jsonify(admins=db.list_admins(conn()))


@app.get("/api/admin/audit")
@admin_required
def admin_audit():
    try:
        before = int(request.args["before"]) if request.args.get("before") else None
    except ValueError:
        raise ApiError("That is not a page.", 400)
    rows = db.list_audit(conn(), 100, before)
    return jsonify(audit=rows, next=rows[-1]["id"] if len(rows) == 100 else None)


# ---------------------------------------------------------------- logs, through the root helper
def bridge_installed():
    return os.path.isdir(BRIDGE_REQ) and os.path.isdir(BRIDGE_OUT)


@app.get("/api/admin/logs/sources")
@admin_required
def admin_log_sources():
    return jsonify(sources=list(LOG_SOURCES), since=list(LOG_SINCE), installed=bridge_installed())


@app.post("/api/admin/logs")
@admin_required
def admin_log_request():
    data = request.get_json(silent=True) or {}
    source, since, lines = data.get("source"), data.get("since", "1h"), data.get("lines", 200)
    if source not in LOG_SOURCES:
        raise ApiError("Pick one of the listed logs.", 400, "bad_source")
    if since not in LOG_SINCE:
        raise ApiError("Pick one of the listed time ranges.", 400, "bad_since")
    if type(lines) is not int or not 1 <= lines <= 1000:
        raise ApiError("Lines must be between 1 and 1000.", 400, "bad_lines")
    if not bridge_installed():
        raise ApiError("The helper on the machine is not installed yet (run install.sh from this release).", 503, "bridge_missing")
    rate_limit("adminlogs:" + g.email, 20, 60)
    rid = secrets.token_hex(16)
    body = json.dumps({"v": 1, "id": rid, "op": "logs", "source": source, "lines": lines, "since": since, "by": g.email,
                       "t": int(time.time())}).encode()
    tmp, final = os.path.join(BRIDGE_REQ, f".tmp-{rid}"), os.path.join(BRIDGE_REQ, f"{rid}.json")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        os.write(fd, body)
    finally:
        os.close(fd)
    os.rename(tmp, final)                                   # the helper only looks at <id>.json: it never sees half a request
    db.log_admin(conn(), g.email, "logs_view", "log_source", source, f"lines={lines} since={since}")
    return jsonify(id=rid), 202


@app.get("/api/admin/logs/<rid>")
@admin_required
def admin_log_result(rid):
    if not LOG_ID.fullmatch(rid):
        raise ApiError("That page isn't here.", 404)
    try:
        fd = os.open(os.path.join(BRIDGE_OUT, f"{rid}.json"), os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except FileNotFoundError:
        return jsonify(status="pending")
    with os.fdopen(fd, "rb") as f:
        result = json.loads(f.read(4 * 1024 * 1024))    # 256 KiB of text can grow when JSON-escaped (non-ASCII becomes \\uXXXX)
    keep = ("status", "reason", "source", "lines", "since", "truncated", "text")
    return jsonify({k: result[k] for k in keep if k in result})


# ---------------------------------------------------------------- releases (read-only here; installing comes with its own review)
RELEASE_KEYS = ("version", "published_at", "newer", "failed")


@app.get("/api/admin/releases")
@admin_required
def admin_releases():
    """What the deploy agent last reported (the helper refreshes it every 15 minutes), and the release this API process runs."""
    from .api import RELEASE
    try:
        fd = os.open(os.path.join(BRIDGE_OUT, "releases.json"), os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except FileNotFoundError:
        return jsonify(running=RELEASE, report=None, installed=bridge_installed())
    with os.fdopen(fd, "rb") as f:
        r = json.loads(f.read(1024 * 1024))
    report = {"at": r.get("at"), "current": r.get("current"), "previous": r.get("previous"), "asterisk": r.get("asterisk"),
              "failed": [v for v in r.get("failed") or [] if isinstance(v, str)][:50], "error": r.get("error"),
              "published": [{k: p.get(k) for k in RELEASE_KEYS} for p in (r.get("published") or [])[:30] if isinstance(p, dict)]}
    return jsonify(running=RELEASE, report=report, installed=bridge_installed())


# ---------------------------------------------------------------- the step-up (a fresh Google sign-in for actions that change things)
@app.get("/api/admin/stepup")
@admin_required
def admin_stepup_status():
    until = (db.parse(g.stepped_up_at) + dt.timedelta(minutes=STEPUP_MINUTES)) if stepped_up() else None
    return jsonify(confirmed=until is not None, until=db.iso(until) if until else None, google=google.configured())


@app.post("/api/admin/stepup")
@admin_required
def admin_stepup_start():
    """Where to send the browser to confirm. Google asks for the password again (prompt=login) and the callback marks THIS session
    only. The binding cookie ties the callback to this browser, as for a sign-in (R6-1)."""
    if not google.configured():
        raise ApiError("Sign in with Google isn't set up here: use the emailed code (development only).", 404, "no_google")
    binding = secrets.token_urlsafe(32)
    url = google.start(f"{signin_origin()}/api/auth/google/callback", None, google.binding_hash(binding),
                       stepup={"token_hash": g.session_hash, "email": g.email})
    return set_signin_cookie(jsonify(url=url), binding, google.STATE_TTL)


@app.post("/api/admin/stepup/code")
@admin_required
def admin_stepup_code():
    """The development and test-suite stand-in for Google: the emailed code of the same person. A 404 in production."""
    emailed_codes_allowed()
    rate_limit(f"verify-ip:{client_ip()}", 30, 3600)
    use_login_code(g.email, "".join(c for c in str((request.get_json(silent=True) or {}).get("code", "")) if c.isdigit()))
    conn().execute("UPDATE session SET stepped_up_at=? WHERE token_hash=?", (db.iso(now()), g.session_hash))
    return jsonify(confirmed=True)


# ---------------------------------------------------------------- admins, from the page
@app.post("/api/admin/admins")
@admin_action
def admin_add():
    email = (request.get_json(silent=True) or {}).get("email")
    try:
        e = db.add_admin(conn(), email, g.email)
    except db.AdminError as err:
        raise ApiError(str(err).capitalize() + ".", 400, "bad_email")
    db.log_admin(conn(), g.email, "admin_add", "admin", e)
    return jsonify(admins=db.list_admins(conn()))


@app.post("/api/admin/admins/remove")
@admin_action
def admin_remove():
    email = (request.get_json(silent=True) or {}).get("email")
    try:
        e = db.remove_admin(conn(), email, g.email)
    except db.AdminError as err:
        raise ApiError(str(err).capitalize() + ".", 409 if "last admin" in str(err) else 400, "admin_refused")
    db.log_admin(conn(), g.email, "admin_remove", "admin", e)
    return jsonify(admins=db.list_admins(conn()))
