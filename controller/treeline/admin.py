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

from . import db, pjsip
from . import google
from .api import (ApiError, app, bearer, client_ip, conn, emailed_codes_allowed, now, rate_limit, set_signin_cookie,
                  drop_handset, drop_registration, log, set_stepup_cookie, signin_origin, stepup_cookie, use_login_code)

ADMIN_SESSION_HOURS = 12

# The root helper on the machine (deploy/native/bin/treeline_bridge.py) reads requests from BRIDGE_REQ and answers in BRIDGE_OUT. These
# two lists must equal its SOURCES and SINCE (a test compares them); the API and controller logs are deliberately absent.
BRIDGE_REQ = os.environ.get("TREELINE_BRIDGE_REQ", "/var/lib/treeline/bridge/req")
BRIDGE_DEPLOY_REQ = os.environ.get("TREELINE_BRIDGE_DEPLOY_REQ", "/var/lib/treeline/bridge/deploy-req")
VERSION = re.compile(r"v(0|[1-9][0-9]{0,4})\.(0|[1-9][0-9]{0,4})\.(0|[1-9][0-9]{0,4})")
BRIDGE_OUT = os.environ.get("TREELINE_BRIDGE_OUT", "/run/treeline/bridge")
LOG_SOURCES = ("deploy", "backup", "health", "certsync", "caddy", "bridge")
LOG_SINCE = ("15m", "1h", "6h", "24h", "boot")
LOG_ID = re.compile(r"[0-9a-f]{32}")


def admin_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        token = bearer()
        row = token and conn().execute("SELECT email, created_at, stepped_up_at, stepup_hash FROM session WHERE token_hash=? AND expires_at>?",
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
        g.session_hash, g.stepped_up_at, g.stepup_hash = db.hash_token(token), row["stepped_up_at"], row["stepup_hash"]
        return fn(*a, **kw)
    return wrapper


STEPUP_MINUTES = 15


def stepped_up():
    """Confirmed in the last STEPUP_MINUTES, by THIS browser: the step-up cookie it was given must match (a copy of the bearer token
    elsewhere has no such cookie)."""
    at = db.parse(g.stepped_up_at) if g.stepped_up_at else None
    proof = stepup_cookie()
    return (at is not None and at >= now() - dt.timedelta(minutes=STEPUP_MINUTES) and bool(proof) and bool(g.stepup_hash)
            and secrets.compare_digest(db.hash_token(proof), g.stepup_hash))


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
        return jsonify(running=RELEASE, report=None, installed=bridge_installed(), deploy=deploy_status(),
                       can_install=os.path.isdir(BRIDGE_DEPLOY_REQ))
    with os.fdopen(fd, "rb") as f:
        r = json.loads(f.read(1024 * 1024))
    report = {"at": r.get("at"), "current": r.get("current"), "previous": r.get("previous"), "asterisk": r.get("asterisk"),
              "failed": [v for v in r.get("failed") or [] if isinstance(v, str)][:50], "error": r.get("error"),
              "published": [{k: p.get(k) for k in RELEASE_KEYS} for p in (r.get("published") or [])[:30] if isinstance(p, dict)]}
    return jsonify(running=RELEASE, report=report, installed=bridge_installed(), deploy=deploy_status(),
                   can_install=os.path.isdir(BRIDGE_DEPLOY_REQ))


def read_answer(name, limit=64 * 1024):
    try:
        fd = os.open(os.path.join(BRIDGE_OUT, name), os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except FileNotFoundError:
        return None
    with os.fdopen(fd, "rb") as f:
        try:
            return json.loads(f.read(limit))
        except ValueError:
            return None


DEPLOY_STATUS_KEYS = ("id", "state", "reason", "version", "from", "exit", "output", "at")


def deploy_status():
    d = read_answer("deploy-status.json")
    return {k: d.get(k) for k in DEPLOY_STATUS_KEYS} if isinstance(d, dict) else None


@app.post("/api/admin/releases/install")
@admin_action
def admin_install():
    """Ask the machine to install a release: a request with the version only. The root helper checks it against what the deploy agent
    lists as published and newer, then runs the agent (signature, waiting for calls to end, health check, automatic rollback)."""
    data = request.get_json(silent=True) or {}
    version, retry = data.get("version"), data.get("retry", False)
    if type(version) is not str or not VERSION.fullmatch(version):
        raise ApiError("That is not a release version.", 400, "bad_version")
    if type(retry) is not bool:
        raise ApiError("Retry must be true or false.", 400, "bad_retry")
    if not os.path.isdir(BRIDGE_DEPLOY_REQ):
        raise ApiError("The helper on the machine is not installed yet (run install.sh from this release).", 503, "bridge_missing")
    rid = secrets.token_hex(16)
    body = json.dumps({"v": 1, "id": rid, "op": "deploy", "version": version, "retry": retry, "by": g.email, "t": int(time.time())}).encode()
    tmp, final = os.path.join(BRIDGE_DEPLOY_REQ, f".tmp-{rid}"), os.path.join(BRIDGE_DEPLOY_REQ, f"{rid}.json")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        os.write(fd, body)
    finally:
        os.close(fd)
    os.rename(tmp, final)
    db.log_admin(conn(), g.email, "release_install", "release", version, "retry" if retry else None)
    return jsonify(id=rid), 202


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
    proof = secrets.token_urlsafe(32)
    conn().execute("UPDATE session SET stepped_up_at=?, stepup_hash=? WHERE token_hash=?", (db.iso(now()), db.hash_token(proof), g.session_hash))
    return set_stepup_cookie(jsonify(confirmed=True), proof)


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


# ---------------------------------------------------------------- treehouses (docs/ADMIN.md: what an admin may see, and may not do)
REASONS = ("family_asked", "safety", "security", "cleanup")
LIST_LIMIT = 200


def _grown_ups(tid):
    return [{"id": r["id"], "email": r["email"], "role": r["role"]} for r in
            conn().execute("SELECT id, email, role FROM grown_up WHERE treehouse_id=? ORDER BY role, id", (tid,))]


def _treehouse_card(r):
    """Exactly what an admin may see of a family: name, number, when it was made, how many phones and when one last checked in, the
    grown-ups' emails, and the archive state. Never calls, strings, notes, settings, handset names or anything in the family's file."""
    phones = conn().execute("SELECT count(*) AS n, max(last_seen) AS seen FROM handset WHERE treehouse_id=? AND removed_at IS NULL",
                            (r["id"],)).fetchone()
    erase = (db.parse(r["archived_at"]) + dt.timedelta(days=db.ARCHIVE_DAYS)) if r["archived_at"] else None
    return {"id": r["id"], "name": r["name"], "number": r["number"], "created_at": r["created_at"], "handset_count": phones["n"],
            "last_checkin": phones["seen"], "grown_ups": _grown_ups(r["id"]), "archived_at": r["archived_at"],
            "erase_after": db.iso(erase) if erase else None, "yours": any(g_["email"] == g.email for g_ in _grown_ups(r["id"]))}


def _treehouse_row(tid):
    r = conn().execute("SELECT id, name, number, created_at, archived_at FROM treehouse WHERE id=? AND system=0 AND left_at IS NULL "
                       "AND deleted_at IS NULL", (tid,)).fetchone()
    if r is None:
        raise ApiError("That treehouse isn't there.", 404)
    return r


@app.get("/api/admin/treehouses")
@admin_required
def admin_treehouses():
    state = request.args.get("state", "active")
    if state not in ("active", "archived"):
        raise ApiError("Pick active or archived.", 400)
    q = str(request.args.get("q", "")).strip()[:60]
    where = "system=0 AND left_at IS NULL AND deleted_at IS NULL AND archived_at IS " + ("NULL" if state == "active" else "NOT NULL")
    args = []
    if q:
        # by name, number, or a grown-up's email: so an admin can find the family someone asked about
        where += " AND (name LIKE ? ESCAPE '\\' OR number=? OR id IN (SELECT treehouse_id FROM grown_up WHERE email=?))"
        like = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        args += [f"%{like}%", q, q.lower()]
    rows = conn().execute(f"SELECT id, name, number, created_at, archived_at FROM treehouse WHERE {where} ORDER BY id DESC LIMIT ?",
                          (*args, LIST_LIMIT)).fetchall()
    db.log_admin(conn(), g.email, "treehouses_viewed", "list", state, f"{len(rows)} shown" + (" (searched)" if q else ""))
    return jsonify(treehouses=[_treehouse_card(r) for r in rows], capped=len(rows) == LIST_LIMIT)


@app.get("/api/admin/treehouses/<int:tid>")
@admin_required
def admin_treehouse(tid):
    r = _treehouse_row(tid)
    card = _treehouse_card(r)
    # The phones by position and kind only: their names are often a child's ("Mia's room").
    card["handsets"] = [{"id": h["id"], "position": i + 1, "kind": h["kind"], "last_seen": h["last_seen"]} for i, h in enumerate(
        conn().execute("SELECT id, kind, last_seen FROM handset WHERE treehouse_id=? AND removed_at IS NULL ORDER BY id", (tid,)))]
    db.log_admin(conn(), g.email, "treehouse_viewed", "treehouse", tid)
    return jsonify(card)


def _reason():
    reason = (request.get_json(silent=True) or {}).get("reason")
    if reason not in REASONS:
        raise ApiError("Pick a reason.", 400, "bad_reason")
    return reason


@app.post("/api/admin/treehouses/<int:tid>/archive")
@admin_action
def admin_archive(tid):
    """Pause a family for ARCHIVE_DAYS (then it is erased). Its phones stop at once (live calls end), its grown-ups see a "paused"
    page, other families see a number nobody has. Silent for now: no email to the family (docs/ADMIN.md)."""
    r = _treehouse_row(tid)
    data = request.get_json(silent=True) or {}
    reason = _reason()
    if str(data.get("confirm", "")).strip().lower() != str(r["name"]).strip().lower():
        raise ApiError("Type the treehouse's name to confirm.", 400, "confirm")
    if any(x["email"] == g.email for x in _grown_ups(tid)):
        raise ApiError("That is your own treehouse: an admin cannot archive it.", 409, "own_treehouse")
    if not db.archive_treehouse(conn(), tid, g.email):
        raise ApiError("That treehouse is already archived.", 409, "already_archived")
    db.log_admin(conn(), g.email, "treehouse_archived", "treehouse", tid, f"reason={reason}")
    pjsip.write(conn())
    for h in conn().execute("SELECT sip_user FROM handset WHERE treehouse_id=? AND removed_at IS NULL", (tid,)).fetchall():
        try:
            drop_registration(h["sip_user"])            # a call in progress ends now
        except Exception:                                # Asterisk unreachable: the account is already gone from its config
            log.warning("could not drop a handset of treehouse %s from Asterisk", tid)
    return jsonify(_treehouse_card(_treehouse_row(tid)))


@app.post("/api/admin/treehouses/<int:tid>/restore")
@admin_action
def admin_restore(tid):
    _treehouse_row(tid)
    if not db.restore_treehouse(conn(), tid):
        raise ApiError(f"Only a treehouse archived in the last {db.ARCHIVE_DAYS} days can be brought back.", 409, "not_restorable")
    db.log_admin(conn(), g.email, "treehouse_restored", "treehouse", tid)
    pjsip.write(conn())
    return jsonify(_treehouse_card(_treehouse_row(tid)))


@app.post("/api/admin/treehouses/<int:tid>/grown-ups/<int:gid>/remove")
@admin_action
def admin_remove_grown_up(tid, gid):
    """Remove a grown-up from a family (never the last parent, never your own row). Their sessions and push subscriptions go with it."""
    _treehouse_row(tid)
    reason = _reason()
    row = conn().execute("SELECT id, email FROM grown_up WHERE id=? AND treehouse_id=?", (gid, tid)).fetchone()
    if row is None:
        raise ApiError("That person isn't in this treehouse.", 404)
    if row["email"] == g.email:
        raise ApiError("That is you: an admin cannot remove themselves from a family here.", 409, "own_row")
    # One statement: two admins removing the two parents at once cannot leave a family with none.
    cur = conn().execute("DELETE FROM grown_up WHERE id=? AND treehouse_id=? AND (role!='parent' OR EXISTS (SELECT 1 FROM grown_up o "
                         "WHERE o.treehouse_id=? AND o.role='parent' AND o.id!=?))", (gid, tid, tid, gid))
    if cur.rowcount != 1:
        raise ApiError("That is the family's last parent: archive the treehouse instead.", 409, "last_parent")
    conn().execute("DELETE FROM session WHERE email=?", (row["email"],))
    conn().execute("DELETE FROM push_subscription WHERE email=?", (row["email"],))
    db.log_admin(conn(), g.email, "grown_up_removed", "treehouse", tid, f"grown_up={gid} reason={reason}")
    return jsonify(_treehouse_card(_treehouse_row(tid)))


@app.post("/api/admin/treehouses/<int:tid>/handsets/<int:hid>/remove")
@admin_action
def admin_remove_handset(tid, hid):
    _treehouse_row(tid)
    reason = _reason()
    h = conn().execute("SELECT * FROM handset WHERE id=? AND treehouse_id=? AND removed_at IS NULL", (hid, tid)).fetchone()
    if h is None:
        raise ApiError("That phone isn't in this treehouse.", 404)
    drop_handset(h)
    db.log_admin(conn(), g.email, "handset_removed", "treehouse", tid, f"handset={hid} reason={reason}")
    return jsonify(_treehouse_card(_treehouse_row(tid)))
