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
from functools import wraps

from flask import g, jsonify, request

from . import db
from .api import ApiError, app, bearer, conn, now, rate_limit

ADMIN_SESSION_HOURS = 12


def admin_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        token = bearer()
        row = token and conn().execute("SELECT email, created_at FROM session WHERE token_hash=? AND expires_at>?",
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
