"""The Treeline API: everything the parent app and the softphone need.

Sign-in is an emailed six-digit code. Each request carries a bearer token.
Parents can do everything for their own treehouse; sitters can only look
and pause. Every change a grown-up makes is written to the parent action log.
"""

import base64
import csv
import datetime as dt
import io
import ipaddress
import json
import logging
import os
import re
import secrets
import threading
import time
from functools import wraps
from zoneinfo import ZoneInfo, available_timezones

from flask import Flask, Response, g, jsonify, redirect, request, send_from_directory

from . import ari as ari_mod
from . import db, mail, pjsip, rules

log = logging.getLogger("treeline")
app = Flask(__name__, static_folder=None)

WEB = os.environ.get("TREELINE_WEB", "/web")
DEV_CODES = os.environ.get("TREELINE_DEV_CODES") == "1"
CORS_ORIGINS = {o.strip() for o in os.environ.get("TREELINE_CORS_ORIGINS", "").split(",") if o.strip()}
PRIVACY_VERSION = "2026-11"      # bump when the privacy notes change in a way parents should re-read
SESSION_DAYS = 30
CODE_MINUTES = 10
LADDER_DAYS = 7
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
LADDER_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # no 0/O/1/I/L


class ApiError(Exception):
    def __init__(self, message, status=400, code=None):
        self.message, self.status, self.code = message, status, code


@app.errorhandler(ApiError)
def _api_error(e):
    return jsonify(error=e.message, code=e.code), e.status


@app.errorhandler(404)
def _not_found(_e):
    return jsonify(error="That page isn't here."), 404


@app.errorhandler(500)
def _server_error(_e):
    return jsonify(error="Something went wrong on our end. Try again in a moment."), 500


@app.after_request
def _cors(resp):
    origin = request.headers.get("Origin")
    if origin and origin in CORS_ORIGINS:
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, DELETE, OPTIONS"
        resp.headers["Vary"] = "Origin"
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    if not request.path.startswith("/api/"):
        # Second line of defense against injected markup: nothing but our own files may run.
        talk = " ws: wss:" if request.path.startswith("/phone/") else ""
        resp.headers.setdefault("Content-Security-Policy", (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            f"img-src 'self' data:; font-src 'self'; connect-src 'self'{talk}; media-src 'self' blob:; "
            "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"))
        resp.headers.setdefault("Referrer-Policy", "no-referrer")
    if request.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


@app.route("/api/<path:_p>", methods=["OPTIONS"])
def _preflight(_p):
    return ("", 204)


def conn():
    return db.local_conn()


_hits = {}
_hits_lock = threading.Lock()
_MAX_KEYS = 5000
_LONGEST_WINDOW = 3600


def rate_limit(key, count, seconds):
    now = time.time()
    with _hits_lock:
        hits = [t for t in _hits.get(key, []) if now - t < seconds]
        if len(hits) >= count:
            _hits[key] = hits
            raise ApiError("That's a lot of tries. Please wait a few minutes.", 429)
        hits.append(now)
        _hits[key] = hits
        if len(_hits) > _MAX_KEYS:  # forget anyone who hasn't been seen in the longest window
            for k in [k for k, v in _hits.items() if not v or now - v[-1] > _LONGEST_WINDOW]:
                del _hits[k]


TRUST_PROXY = os.environ.get("TREELINE_TRUST_PROXY") == "1"


def client_ip():
    """The caller's address. Only believe X-Forwarded-For when we're really
    behind our own proxy (TREELINE_TRUST_PROXY=1); otherwise anyone could
    dodge the rate limits by sending the header."""
    if TRUST_PROXY:
        fwd = request.headers.get("X-Forwarded-For", "")
        if fwd:
            return fwd.split(",")[-1].strip()  # the address our proxy saw
    return request.remote_addr or ""


def is_private(addr):
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        return False
    return ip.is_loopback or ip.is_private


def body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def bearer():
    h = request.headers.get("Authorization", "")
    return h[7:] if h.startswith("Bearer ") else None


def auth(parent=False, house=True):
    """Require a signed-in grown-up. `house=False` allows someone who hasn't
    made a treehouse yet; `parent=True` rules out sitters."""
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            token = bearer()
            row = token and conn().execute(
                "SELECT * FROM session WHERE token_hash=? AND expires_at>?",
                (db.hash_token(token), db.iso())).fetchone()
            if not row:
                raise ApiError("Please sign in again.", 401, "signed_out")
            g.email = row["email"]
            g.gu = conn().execute(
                "SELECT g.* FROM grown_up g JOIN treehouse t ON t.id=g.treehouse_id "
                "WHERE g.email=? AND t.left_at IS NULL", (g.email,)).fetchone()
            g.th = db.get_treehouse(conn(), g.gu["treehouse_id"]) if g.gu else None
            if house and g.th is None:
                raise ApiError("Set up your treehouse first.", 403, "no_treehouse")
            if parent and g.gu["role"] != "parent":
                raise ApiError("Only a parent can do that.", 403, "parents_only")
            return fn(*a, **kw)
        return wrapper
    return deco


def audit(action, target=None, before=None, after=None):
    db.log_action(conn(), g.th["id"] if g.th else None, g.email, action, target, before, after)


def now():
    return db.utcnow()


# ================================================================ JSON shapes

def quiet_now(th):
    return rules.in_quiet_hours(th, now())


def th_json(t):
    return {
        "id": t["id"], "name": t["name"], "number": t["number"], "timezone": t["timezone"],
        "quiet": {"enabled": bool(t["quiet_enabled"]), "start": t["quiet_start"],
                  "end": t["quiet_end"], "days": t["quiet_days"]},
        "paused": bool(t["paused"]), "max_call_minutes": t["max_call_minutes"],
        "daily_minutes": t["daily_minutes"], "retention_days": t["retention_days"],
        "quiet_now": quiet_now(t), "created_at": t["created_at"],
    }


def handset_json(h):
    return {"id": h["id"], "kind": h["kind"], "name": h["name"], "online": bool(h["online"]),
            "last_seen": h["last_seen"], "created_at": h["created_at"],
            "provisioned": bool(h["provision_token"]), "disabled": bool(h["disabled"])}


def side_of(s, tid):
    return "a" if s["a_id"] == tid else "b"


def string_json(s, tid):
    me = side_of(s, tid)
    other_id = s["b_id"] if me == "a" else s["a_id"]
    other = conn().execute("SELECT * FROM treehouse WHERE id=?", (other_id,)).fetchone()
    mine = s[f"{me}_approved_by"] is not None
    theirs = s[f"{'b' if me == 'a' else 'a'}_approved_by"] is not None
    return {
        "id": s["id"], "state": s["state"],
        "other": {"id": other["id"], "name": other["name"], "number": other["number"]},
        "mine_approved": mine, "theirs_approved": theirs,
        "paused_by_me": s["state"] == "paused" and s["paused_by"] == tid,
        "paused_by_them": s["state"] == "paused" and s["paused_by"] != tid,
        "created_at": s["created_at"], "updated_at": s["updated_at"],
    }


def my_strings(tid, include_cut=False):
    sql = "SELECT * FROM string WHERE (a_id=? OR b_id=?)" + ("" if include_cut else " AND state!='cut'")
    return conn().execute(sql + " ORDER BY updated_at DESC", (tid, tid)).fetchall()


def parse_ts(s):
    return dt.datetime.fromisoformat(s) if s else None


def local_str(ts, tz):
    t = parse_ts(ts)
    return t.astimezone(ZoneInfo(tz)).isoformat(timespec="minutes") if t else None


def describe_call(c, tid):
    """Plain-language label, detail and tone for one call, from one
    treehouse's side. Tones/icons name the design system's variants."""
    outgoing = c["caller_treehouse"] == tid
    r, why, talk = c["result"], c["reason"] or "", c["talk_sec"] or 0
    mins = max(1, round(talk / 60)) if talk else 0
    if r in (rules.CONNECTED, rules.TIME_LIMIT):
        base = {"label": "Connected", "tone": "canopy",
                "icon": "phone-outgoing" if outgoing else "phone-incoming",
                "detail": f"{mins} min" if mins else "Under a minute"}
        if r == rules.TIME_LIMIT:
            base.update(label="Time limit", tone="sky", icon="clock",
                        detail=f"Ended at {mins} min")
        return base
    if r in (rules.NO_ANSWER, rules.CALLER_HUNG_UP):
        return ({"label": "No answer", "tone": "bark", "icon": "phone-off", "detail": "Nobody picked up"}
                if outgoing else
                {"label": "Missed", "tone": "bark", "icon": "phone-off", "detail": "Nobody picked up"})
    if r == rules.BUSY:
        return {"label": "Busy", "tone": "bark", "icon": "phone-off",
                "detail": "The line was in use"}
    if r == rules.OFFLINE:
        return ({"label": "Couldn't reach", "tone": "bark", "icon": "phone-off",
                 "detail": "Nothing on that line was connected"} if outgoing else
                {"label": "Phone offline", "tone": "bark", "icon": "phone-off",
                 "detail": "No handset was connected to ring"})
    if r == rules.DISCONNECTED:
        return {"label": "Phone off", "tone": "bark", "icon": "pause",
                "detail": "That phone was disconnected"}
    if r == rules.NOT_IN_SERVICE:
        return {"label": "Not in service", "tone": "berry", "icon": "lock",
                "detail": f"No treehouse has {c['dialed']}"}
    if r == rules.NOT_STRUNG:
        return {"label": "Not strung", "tone": "berry", "icon": "lock",
                "detail": "Not strung to your treehouse"}
    if r == rules.INCOMPLETE:
        return {"label": "Couldn't complete", "tone": "berry", "icon": "lock",
                "detail": "The number dialed wasn't four digits"}
    if r == rules.NO_911:
        # The one entry in the log that is about safety: marked urgent, so the screen draws it louder than the rest.
        return {"label": "Tried to call 911", "tone": "berry", "icon": "alert", "urgent": True,
                "detail": "Treeline can't call 911. If it was an emergency, use another phone."}
    if r == rules.QUIET_OR_PAUSED:
        if why == "caller_quiet":
            return {"label": "Quiet hours", "tone": "sky", "icon": "moon", "detail": "During your quiet hours"}
        if why == "caller_paused":
            return {"label": "Paused", "tone": "bark", "icon": "pause", "detail": "Your line was paused"}
        if outgoing:
            return {"label": "Not taking calls", "tone": "sky", "icon": "moon",
                    "detail": "That treehouse isn't taking calls right now"}
        if why == "callee_paused":
            return {"label": "Blocked", "tone": "bark", "icon": "pause", "detail": "Your line was paused"}
        if why == "callee_daily_limit":
            return {"label": "Blocked", "tone": "sky", "icon": "clock", "detail": "Out of minutes today"}
        return {"label": "Blocked", "tone": "sky", "icon": "moon", "detail": "During your quiet hours"}
    if r in (rules.REPEAT_LIMIT, rules.DAILY_LIMIT):
        return {"label": "Limit reached", "tone": "sky", "icon": "clock",
                "detail": "Too many calls for now" if r == rules.REPEAT_LIMIT else "Out of minutes today"}
    return {"label": "Didn't connect", "tone": "bark", "icon": "phone-off", "detail": ""}


def visible_to_callee(c):
    """What the called treehouse's parents see. Attempts that never had a
    live string, and the caller's own rules, stay on the caller's side."""
    if c["result"] in (rules.NOT_IN_SERVICE, rules.NOT_STRUNG, rules.NO_911, rules.INCOMPLETE):
        return False
    why = c["reason"] or ""
    return not (why.startswith("caller_") or why in ("unstrung_limit", "repeat_limit"))


def call_json(c, th, detail=False):
    tid = th["id"]
    outgoing = c["caller_treehouse"] == tid
    other_id = c["callee_treehouse"] if outgoing else c["caller_treehouse"]
    other = None
    if other_id:
        row = conn().execute("SELECT name, number FROM treehouse WHERE id=?", (other_id,)).fetchone()
        if row and (not outgoing or c["result"] not in (rules.NOT_STRUNG,)):
            other = {"name": row["name"], "number": row["number"]}
    if outgoing and other is None:
        other = {"name": None, "number": c["dialed"]}
    out = {"id": c["id"], "direction": "out" if outgoing else "in", "other": other,
           "started_at": c["started_at"], "started_local": local_str(c["started_at"], th["timezone"]),
           "talk_sec": c["talk_sec"], "result": c["result"], "reason": c["reason"],
           **describe_call(c, tid)}
    if detail:
        names = {h["id"]: h["name"] for h in conn().execute(
            "SELECT id, name FROM handset WHERE treehouse_id=?", (tid,))}
        out["events"] = [
            {"at": e["at"], "event": e["event"],
             "handset": names.get(e["handset_id"]) if e["handset_id"] else None,
             "theirs": bool(e["handset_id"]) and e["handset_id"] not in names}
            for e in conn().execute("SELECT * FROM call_event WHERE call_id=? ORDER BY id", (c["id"],))]
        out["hung_up_first"] = (None if not c["hung_up_first"] else
                                ("you" if (c["hung_up_first"] == "caller") == outgoing else "them"))
    return out


def calls_for(th, since=None, limit=300):
    tid = th["id"]
    args = [tid, tid]
    sql = "SELECT * FROM call WHERE (caller_treehouse=? OR callee_treehouse=?) AND state='ended'"
    if since:
        sql += " AND started_at>=?"
        args.append(db.iso(since))
    sql += " ORDER BY id DESC LIMIT ?"
    args.append(limit)
    rows = conn().execute(sql, args).fetchall()
    return [c for c in rows if c["caller_treehouse"] == tid or visible_to_callee(c)]


# ================================================================ health

@app.get("/api/health")
def health():
    """For an uptime monitor: 200 only if the database answers and Asterisk is reachable."""
    rate_limit(f"health:{client_ip()}", 120, 60)          # a monitor polls; a flood doesn't
    conn().execute("SELECT 1")
    asterisk = ari_mod.Ari().online_users(timeout=2) is not None     # never hold a thread long
    return jsonify(ok=asterisk, database=True, asterisk=asterisk), (200 if asterisk else 503)


# ================================================================ sign-in

@app.post("/api/auth/request")
def auth_request():
    email = str(body().get("email", "")).strip().lower()
    if not EMAIL_RE.match(email) or len(email) > 200:
        raise ApiError("That doesn't look like an email address. Check it and try again.")
    rate_limit(f"code-ip:{client_ip()}", 20, 3600)
    rate_limit(f"code:{email}", 5, 3600)
    code = f"{secrets.randbelow(1_000_000):06d}"
    conn().execute(
        "INSERT INTO login_code(email,code_hash,expires_at,attempts) VALUES(?,?,?,0) "
        "ON CONFLICT(email) DO UPDATE SET code_hash=excluded.code_hash, "
        "expires_at=excluded.expires_at, attempts=0",
        (email, db.hash_token(f"{email}:{code}"), db.iso(now() + dt.timedelta(minutes=CODE_MINUTES))))
    mail.send(email, "Your Treeline sign-in code",
              f"Your Treeline code is {code}.\n\nIt works for {CODE_MINUTES} minutes. "
              "If you didn't ask for it, you can ignore this email.")
    out = {"sent": True}
    if DEV_CODES and is_private(client_ip()):
        out["dev_code"] = code   # a test server on your own network only; never over the internet
    return jsonify(out)


@app.post("/api/auth/verify")
def auth_verify():
    data = body()
    email = str(data.get("email", "")).strip().lower()
    code = "".join(c for c in str(data.get("code", "")) if c.isdigit())
    rate_limit(f"verify-ip:{client_ip()}", 30, 3600)
    row = conn().execute("SELECT * FROM login_code WHERE email=?", (email,)).fetchone()
    bad = ApiError("That code didn't match. Check your email and try again.", 400, "bad_code")
    if not row or row["expires_at"] < db.iso():
        raise ApiError("That code has expired. Ask for a new one.", 400, "expired_code")
    if row["attempts"] >= 5:
        raise ApiError("Too many tries. Ask for a new code.", 429, "expired_code")
    if not secrets.compare_digest(row["code_hash"], db.hash_token(f"{email}:{code}")):
        conn().execute("UPDATE login_code SET attempts=attempts+1 WHERE email=?", (email,))
        raise bad
    conn().execute("DELETE FROM login_code WHERE email=?", (email,))
    token = secrets.token_urlsafe(32)
    conn().execute("INSERT INTO session(token_hash,email,expires_at) VALUES(?,?,?)",
                   (db.hash_token(token), email, db.iso(now() + dt.timedelta(days=SESSION_DAYS))))
    return jsonify(token=token)


@app.post("/api/auth/signout")
@auth(house=False)
def auth_signout():
    conn().execute("DELETE FROM session WHERE token_hash=?", (db.hash_token(bearer()),))
    return jsonify(ok=True)


def me_json():
    return {"email": g.email,
            "grown_up": {"id": g.gu["id"], "name": g.gu["name"], "role": g.gu["role"]} if g.gu else None,
            "treehouse": th_json(g.th) if g.th else None,
            "dev": DEV_CODES}


@app.get("/api/me")
@auth(house=False)
def me():
    return jsonify(me_json())


@app.get("/api/timezones")
def timezones():
    common = ["America/New_York", "America/Chicago", "America/Denver", "America/Phoenix",
              "America/Los_Angeles", "America/Anchorage", "Pacific/Honolulu", "America/Toronto",
              "America/Vancouver", "Europe/London", "Europe/Paris", "Australia/Sydney"]
    return jsonify(common=common, all=sorted(available_timezones()))


# ================================================================ treehouse

def clean_name(value, what="name", limit=40):
    v = " ".join(str(value or "").split())
    if not v or len(v) > limit:
        raise ApiError(f"Add a {what} of 1 to {limit} characters.")
    return v


def valid_tz(tz):
    if tz not in available_timezones():
        raise ApiError("Pick a time zone from the list.")
    return tz


@app.post("/api/treehouse")
@auth(house=False)
def treehouse_create():
    if g.gu:
        raise ApiError("You already have a treehouse.", 409)
    data = body()
    if not data.get("ack_911"):
        raise ApiError("Please tick the box to say you understand Treeline can't call 911.",
                       400, "ack_911")
    if not data.get("consent"):
        raise ApiError("Please tick the box to say you've read how Treeline handles your family's information.",
                       400, "consent")
    name = clean_name(data.get("name"), "treehouse name")
    tz = valid_tz(data.get("timezone") or "America/Los_Angeles")
    who = " ".join(str(data.get("your_name") or "").split())[:60] or None
    tid = db.create_treehouse(conn(), name, timezone=tz, ack_911=True,
                              consent_at=db.iso(), consent_version=PRIVACY_VERSION)
    conn().execute("INSERT INTO grown_up(email,name,treehouse_id,role,created_at) VALUES(?,?,?,?,?)",
                   (g.email, who, tid, "parent", db.iso()))
    db.log_action(conn(), tid, g.email, "treehouse_created", name)
    g.gu = conn().execute("SELECT * FROM grown_up WHERE email=?", (g.email,)).fetchone()
    g.th = db.get_treehouse(conn(), tid)
    return jsonify(me_json()), 201


RULE_FIELDS = ("name", "timezone", "quiet", "paused", "max_call_minutes", "daily_minutes",
               "retention_days")


@app.patch("/api/treehouse")
@auth()
def treehouse_update():
    data = body()
    th = g.th
    if g.gu["role"] == "sitter" and set(data) - {"paused"}:
        raise ApiError("Sitters can pause the line, but only a parent can change this.", 403, "parents_only")
    changes = {}
    if "name" in data:
        changes["name"] = clean_name(data["name"], "treehouse name")
    if "timezone" in data:
        changes["timezone"] = valid_tz(data["timezone"])
    if "paused" in data:
        changes["paused"] = int(bool(data["paused"]))
    if "max_call_minutes" in data:
        try:
            m = float(data["max_call_minutes"])
        except (TypeError, ValueError):
            raise ApiError("Pick a call length between 1 and 120 minutes.")
        if not 1 <= m <= 120:
            raise ApiError("Pick a call length between 1 and 120 minutes.")
        changes["max_call_minutes"] = m
    if "daily_minutes" in data:
        d = data["daily_minutes"]
        if d in (None, "", 0):
            changes["daily_minutes"] = None
        else:
            try:
                d = float(d)
            except (TypeError, ValueError):
                raise ApiError("Pick daily minutes between 5 and 600, or no limit.")
            if not 5 <= d <= 600:
                raise ApiError("Pick daily minutes between 5 and 600, or no limit.")
            changes["daily_minutes"] = d
    if "retention_days" in data:
        try:
            r = int(data["retention_days"])
        except (TypeError, ValueError):
            raise ApiError("Keep call records for 7 to 365 days.")
        if not 7 <= r <= 365:
            raise ApiError("Keep call records for 7 to 365 days.")
        changes["retention_days"] = r
    if "quiet" in data:
        q = data["quiet"] if isinstance(data["quiet"], dict) else {}
        for key in ("start", "end"):
            if key in q:
                if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", str(q[key])):
                    raise ApiError("Use a time like 7:30 pm.")
                changes[f"quiet_{key}"] = q[key]
        if "days" in q:
            if not re.fullmatch(r"[01]{7}", str(q["days"])):
                raise ApiError("Pick at least one day.")
            changes["quiet_days"] = q["days"]
        if "enabled" in q:
            changes["quiet_enabled"] = int(bool(q["enabled"]))
    for k, v in changes.items():
        if th[k] != v:
            audit(f"changed_{k}", None, th[k], v)
    if changes:
        sets = ",".join(f"{k}=?" for k in changes)
        conn().execute(f"UPDATE treehouse SET {sets} WHERE id=?", (*changes.values(), th["id"]))
    return jsonify(th_json(db.get_treehouse(conn(), th["id"])))


@app.post("/api/treehouse/number")
@auth(parent=True)
def treehouse_number():
    th = g.th
    wanted = str(body().get("number") or "").strip()
    if wanted:
        if not db.number_is_free(conn(), wanted):
            raise ApiError("That number isn't available. Try another, or let Treeline pick one.", 409)
        new = wanted
    else:
        new = db.assign_number(conn())
    conn().execute("UPDATE treehouse SET number=? WHERE id=?", (new, th["id"]))
    audit("changed_number", None, th["number"], new)
    for s in my_strings(th["id"]):
        if s["state"] in ("live", "paused"):
            other = s["b_id"] if side_of(s, th["id"]) == "a" else s["a_id"]
            db.add_notice(conn(), other, "number_changed", f"{th['name']} has a new number",
                          f"You can reach them at {new} now.")
    return jsonify(th_json(db.get_treehouse(conn(), th["id"])))


def end_all_strings(tid, left_title):
    for s in my_strings(tid):
        other = s["b_id"] if side_of(s, tid) == "a" else s["a_id"]
        conn().execute("UPDATE string SET state='cut', updated_at=? WHERE id=?", (db.iso(), s["id"]))
        if s["state"] in ("live", "paused"):
            db.add_notice(conn(), other, "string_ended", left_title,
                          "The string between your treehouses has ended.")


@app.post("/api/treehouse/leave")
@auth(parent=True)
def treehouse_leave():
    th = g.th
    if str(body().get("confirm", "")).strip().lower() != th["name"].lower():
        raise ApiError("Type your treehouse name to confirm.", 400, "confirm")
    end_all_strings(th["id"], f"{th['name']} left the Treeline")
    audit("left_treeline")
    db.leave_treehouse(conn(), th["id"])
    conn().execute("DELETE FROM grown_up WHERE treehouse_id=?", (th["id"],))
    pjsip.write(conn())
    return jsonify(ok=True)


@app.delete("/api/treehouse")
@auth(parent=True)
def treehouse_delete():
    """Leave the Treeline and delete every record for this treehouse."""
    th = g.th
    if str(body().get("confirm", "")).strip().lower() != th["name"].lower():
        raise ApiError("Type your treehouse name to confirm.", 400, "confirm")
    tid = th["id"]
    end_all_strings(tid, f"{th['name']} left the Treeline")
    db.leave_treehouse(conn(), tid)
    c = conn()
    c.execute("DELETE FROM call_event WHERE call_id IN (SELECT id FROM call WHERE "
              "caller_treehouse=? AND callee_treehouse IS NULL)", (tid,))
    c.execute("DELETE FROM call WHERE (caller_treehouse=? AND callee_treehouse IS NULL) OR "
              "(callee_treehouse=? AND caller_treehouse IS NULL)", (tid, tid))
    c.execute("UPDATE call SET caller_treehouse=NULL, caller_handset=NULL WHERE caller_treehouse=?", (tid,))
    c.execute("UPDATE call SET callee_treehouse=NULL, answered_handset=NULL WHERE callee_treehouse=?", (tid,))
    c.execute("DELETE FROM call_event WHERE call_id IN (SELECT id FROM call WHERE "
              "caller_treehouse IS NULL AND callee_treehouse IS NULL)")
    c.execute("DELETE FROM call WHERE caller_treehouse IS NULL AND callee_treehouse IS NULL")
    emails = [r["email"] for r in c.execute("SELECT email FROM grown_up WHERE treehouse_id=?", (tid,))]
    for e in emails:
        c.execute("DELETE FROM session WHERE email=?", (e,))
        c.execute("DELETE FROM push_subscription WHERE email=?", (e,))
    for sql in ("DELETE FROM grown_up WHERE treehouse_id=?", "DELETE FROM notice WHERE treehouse_id=?",
                "DELETE FROM parent_action WHERE treehouse_id=?", "DELETE FROM ladder_code WHERE treehouse_id=?",
                "DELETE FROM handset WHERE treehouse_id=?",
                "DELETE FROM string WHERE a_id=? OR b_id=?"):
        c.execute(sql, (tid,) * sql.count("?"))
    c.execute("UPDATE treehouse SET name='(deleted)' WHERE id=?", (tid,))
    pjsip.write(c)
    return jsonify(ok=True)


# ================================================================ home

@app.get("/api/home")
@auth()
def home():
    th, tid = g.th, g.th["id"]
    t = now()
    strings = [string_json(s, tid) for s in my_strings(tid)]
    waiting_on_me = [s for s in strings if s["state"] == "waiting" and not s["mine_approved"]]
    waiting_on_them = [s for s in strings if s["state"] == "waiting" and s["mine_approved"]]
    live = [s for s in strings if s["state"] == "live"]
    handsets = db.handsets_of(conn(), tid)
    notices = conn().execute(
        "SELECT * FROM notice WHERE treehouse_id=? AND dismissed_at IS NULL ORDER BY id DESC LIMIT 20",
        (tid,)).fetchall()

    def tally(since):
        rows = [c for c in calls_for(th, since) if c["result"] in (rules.CONNECTED, rules.TIME_LIMIT)]
        return {"calls": len(rows), "minutes": round(sum(c["talk_sec"] for c in rows) / 60)}

    local = rules.local_now(th, t)
    midnight = local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(dt.timezone.utc)
    all_week = calls_for(th, t - dt.timedelta(days=7))
    blocked_week = sum(1 for c in all_week if c["result"] not in
                       (rules.CONNECTED, rules.TIME_LIMIT, rules.NO_ANSWER, rules.CALLER_HUNG_UP))
    return jsonify({
        "treehouse": th_json(th),
        "strings": {"live": len(live), "waiting_on_me": waiting_on_me, "waiting_on_them": waiting_on_them,
                    "newest_live": live[0] if live else None},
        "handsets": [handset_json(h) for h in handsets],
        "notices": [{"id": n["id"], "kind": n["kind"], "title": n["title"], "body": n["body"],
                     "created_at": n["created_at"]} for n in notices],
        "today": tally(midnight), "week": {**tally(t - dt.timedelta(days=7)), "blocked": blocked_week},
        "line_state": rules.line_state(conn(), th, t),
        "sitter": g.gu["role"] == "sitter",
    })


@app.post("/api/notices/<int:nid>/dismiss")
@auth()
def notice_dismiss(nid):
    conn().execute("UPDATE notice SET dismissed_at=? WHERE id=? AND treehouse_id=?",
                   (db.iso(), nid, g.th["id"]))
    return jsonify(ok=True)


# ================================================================ strings

@app.get("/api/strings")
@auth()
def strings_list():
    return jsonify(strings=[string_json(s, g.th["id"]) for s in my_strings(g.th["id"])])


@app.get("/api/ladder-codes")
@auth(parent=True)
def ladder_list():
    rows = conn().execute("SELECT * FROM ladder_code WHERE treehouse_id=? AND used_at IS NULL "
                          "AND expires_at>? ORDER BY expires_at DESC", (g.th["id"], db.iso())).fetchall()
    return jsonify(codes=[{"code": r["code"], "expires_at": r["expires_at"]} for r in rows])


@app.post("/api/ladder-codes")
@auth(parent=True)
def ladder_create():
    outstanding = conn().execute("SELECT COUNT(*) n FROM ladder_code WHERE treehouse_id=? AND used_at IS NULL "
                                 "AND expires_at>?", (g.th["id"], db.iso())).fetchone()["n"]
    if outstanding >= 5:
        raise ApiError("You have 5 codes waiting. Use or delete one first.", 409)
    code = "".join(secrets.choice(LADDER_ALPHABET) for _ in range(8))
    exp = db.iso(now() + dt.timedelta(days=LADDER_DAYS))
    conn().execute("INSERT INTO ladder_code(code,treehouse_id,expires_at) VALUES(?,?,?)",
                   (code, g.th["id"], exp))
    audit("ladder_code_created")
    return jsonify(code=f"{code[:4]}-{code[4:]}", expires_at=exp), 201


@app.delete("/api/ladder-codes/<code>")
@auth(parent=True)
def ladder_delete(code):
    code = code.replace("-", "").upper()
    conn().execute("DELETE FROM ladder_code WHERE code=? AND treehouse_id=? AND used_at IS NULL",
                   (code, g.th["id"]))
    return jsonify(ok=True)


@app.post("/api/strings/redeem")
@auth(parent=True)
def string_redeem():
    rate_limit(f"redeem:{g.email}", 10, 3600)
    code = str(body().get("code", "")).replace("-", "").replace(" ", "").upper()
    row = conn().execute("SELECT * FROM ladder_code WHERE code=?", (code,)).fetchone()
    if not row or row["used_at"] or row["expires_at"] < db.iso():
        raise ApiError("That string code didn't work. It may have been used or expired. "
                       "Ask for a new one.", 400, "bad_ladder")
    them = db.get_treehouse(conn(), row["treehouse_id"])
    me = g.th
    if them is None or them["id"] == me["id"]:
        raise ApiError("That string code didn't work. Ask for a new one.", 400, "bad_ladder")
    if db.get_string(conn(), me["id"], them["id"]):
        raise ApiError(f"You and {them['name']} already have a string.", 409)
    a, b = db.ordered(me["id"], them["id"])
    mine_col = "a_approved_by" if a == me["id"] else "b_approved_by"
    cur = conn().execute(
        f"INSERT INTO string(a_id,b_id,state,asked_by,{mine_col},created_at,updated_at) "
        "VALUES(?,?,?,?,?,?,?)", (a, b, "waiting", g.gu["id"], g.gu["id"], db.iso(), db.iso()))
    conn().execute("UPDATE ladder_code SET used_by=?, used_at=? WHERE code=?",
                   (me["id"], db.iso(), code))
    db.add_notice(conn(), them["id"], "string_request", f"{me['name']} would like to string with you",
                  "Open Strings to approve. Calls connect once both families say yes.")
    audit("string_requested", them["name"])
    return jsonify(string_json(conn().execute("SELECT * FROM string WHERE id=?",
                                              (cur.lastrowid,)).fetchone(), me["id"])), 201


def string_for(sid):
    s = conn().execute("SELECT * FROM string WHERE id=? AND (a_id=? OR b_id=?)",
                       (sid, g.th["id"], g.th["id"])).fetchone()
    if not s or s["state"] == "cut":
        raise ApiError("That string isn't there anymore.", 404)
    return s


def other_id_of(s):
    return s["b_id"] if side_of(s, g.th["id"]) == "a" else s["a_id"]


@app.post("/api/strings/<int:sid>/approve")
@auth(parent=True)
def string_approve(sid):
    s = string_for(sid)
    if s["state"] != "waiting":
        raise ApiError("That string is already set up.", 409)
    me = side_of(s, g.th["id"])
    if s[f"{me}_approved_by"] is not None:
        raise ApiError("You've already approved this one. Calls connect once their family does too.", 409)
    conn().execute(f"UPDATE string SET {me}_approved_by=?, state='live', updated_at=? WHERE id=?",
                   (g.gu["id"], db.iso(), sid))
    other = db.get_treehouse(conn(), other_id_of(s))
    db.add_notice(conn(), other["id"], "string_live", f"{g.th['name']} approved",
                  f"Your kids can call {g.th['name']} on {g.th['number']} now.")
    audit("string_approved", other["name"])
    return jsonify(string_json(string_for(sid), g.th["id"]))


@app.post("/api/strings/<int:sid>/pause")
@auth(parent=True)
def string_pause(sid):
    s = string_for(sid)
    if s["state"] != "live":
        raise ApiError("Only a live string can be paused.", 409)
    conn().execute("UPDATE string SET state='paused', paused_by=?, updated_at=? WHERE id=?",
                   (g.th["id"], db.iso(), sid))
    audit("string_paused", db.get_treehouse(conn(), other_id_of(s))["name"])
    return jsonify(string_json(string_for(sid), g.th["id"]))


@app.post("/api/strings/<int:sid>/resume")
@auth(parent=True)
def string_resume(sid):
    s = string_for(sid)
    if s["state"] != "paused" or s["paused_by"] != g.th["id"]:
        raise ApiError("Only the family that paused a string can turn it back on.", 409)
    conn().execute("UPDATE string SET state='live', paused_by=NULL, updated_at=? WHERE id=?",
                   (db.iso(), sid))
    audit("string_resumed", db.get_treehouse(conn(), other_id_of(s))["name"])
    return jsonify(string_json(string_for(sid), g.th["id"]))


@app.post("/api/strings/<int:sid>/cut")
@auth(parent=True)
def string_cut(sid):
    """Cut a live string, decline a request, or withdraw one you sent."""
    s = string_for(sid)
    other = db.get_treehouse(conn(), other_id_of(s))
    conn().execute("UPDATE string SET state='cut', updated_at=? WHERE id=?", (db.iso(), sid))
    if s["state"] in ("live", "paused"):
        db.add_notice(conn(), other["id"], "string_ended", f"{g.th['name']} ended the string",
                      "Calls between your treehouses won't connect anymore.")
    audit("string_cut", other["name"], s["state"], "cut")
    return jsonify(ok=True)


# ================================================================ handsets

def public_host():
    host = os.environ.get("TREELINE_PUBLIC_HOST")
    return host or request.host.split(":")[0]


def public_origin():
    """The address parents should open (the one in the pairing QR code): the configured one, else the secure address this
    request came in on, else None and the browser uses the address it was loaded from. Without this, a tablet opened on
    the plain-HTTP port prints a QR code that sends a parent's phone to that port, not the secure one."""
    fixed = os.environ.get("TREELINE_PUBLIC_ORIGIN", "").rstrip("/")
    if fixed:
        return fixed
    if request.headers.get("X-Forwarded-Proto", "").split(",")[0].strip() == "https":
        return f"https://{request.host}"
    return None


def ws_url():
    """Where a browser softphone opens its WebSocket. A page served over HTTPS (through our proxy,
    which passes the original Host and X-Forwarded-Proto) must use wss on the same host and port:
    browsers refuse plain ws from a secure page. Believing the header only changes the URL handed
    back to whoever sent it, so it needs no trust check."""
    fixed = os.environ.get("TREELINE_PUBLIC_WS_URL")
    if fixed:
        return fixed
    if request.headers.get("X-Forwarded-Proto", "").split(",")[0].strip() == "https":
        return f"wss://{request.host}/ws"
    return f"ws://{public_host()}:8088/ws"


def handset_for(hid):
    h = conn().execute("SELECT * FROM handset WHERE id=? AND treehouse_id=? AND removed_at IS NULL",
                       (hid, g.th["id"])).fetchone()
    if not h:
        raise ApiError("That handset isn't there anymore.", 404)
    return h


def credentials(sip_user, secret):
    return {"sip_user": sip_user, "secret": secret, "server": public_host(),
            "realm": db.SIP_REALM, "ws_url": ws_url()}


@app.get("/api/handsets")
@auth()
def handsets_list():
    return jsonify(handsets=[handset_json(h) for h in db.handsets_of(conn(), g.th["id"])])


@app.post("/api/handsets")
@auth(parent=True)
def handset_create():
    data = body()
    kind = data.get("kind")
    if kind not in ("rotary", "ata", "softphone"):
        raise ApiError("Pick a rotary phone, a phone adapter or a softphone.")
    name = clean_name(data.get("name"), "handset name")
    if len(db.handsets_of(conn(), g.th["id"])) >= 8:
        raise ApiError("A treehouse can have up to 8 handsets.", 409)
    hid, user, secret = db.create_handset(conn(), g.th["id"], kind, name)
    if kind in ("rotary", "ata"):
        # The adapter fetches its settings by a private link, so its secret is kept for that.
        conn().execute("UPDATE handset SET provision_token=?, provision_secret=? WHERE id=?",
                       (secrets.token_urlsafe(24), secret, hid))
    pjsip.write(conn())
    audit("handset_added", name)
    h = conn().execute("SELECT * FROM handset WHERE id=?", (hid,)).fetchone()
    return jsonify(handset=handset_json(h), credentials=credentials(user, secret)), 201


@app.patch("/api/handsets/<int:hid>")
@auth(parent=True)
def handset_update(hid):
    """Rename a phone, and/or disconnect or reconnect it. A disconnected phone doesn't ring and
    can't place calls; schedules and limits don't matter to it; the treehouse's other phones carry on."""
    data = body()
    h = handset_for(hid)
    if "name" not in data and "disabled" not in data:
        raise ApiError("Nothing to change.")
    if "name" in data:
        name = clean_name(data["name"], "handset name")
        conn().execute("UPDATE handset SET name=? WHERE id=?", (name, hid))
        audit("handset_renamed", name, h["name"], name)
    if "disabled" in data:
        off = 1 if data["disabled"] else 0
        if off != h["disabled"]:
            conn().execute("UPDATE handset SET disabled=? WHERE id=?", (off, hid))
            audit("handset_disconnected" if off else "handset_reconnected", h["name"])
    return jsonify(handset_json(handset_for(hid)))


def drop_registration(sip_user):
    """Kick a removed handset off at once, even if it's mid-call."""
    client = ari_mod.Ari()
    for ch in client.request("GET", "/channels") or []:
        if ch.get("name", "").startswith(f"PJSIP/{sip_user}-"):
            client.request("DELETE", f"/channels/{ch['id']}")


@app.delete("/api/handsets/<int:hid>")
@auth(parent=True)
def handset_remove(hid):
    h = handset_for(hid)
    conn().execute("UPDATE handset SET removed_at=?, provision_secret=NULL, provision_token=NULL WHERE id=?",
                   (db.iso(), hid))
    pjsip.write(conn())
    drop_registration(h["sip_user"])
    audit("handset_removed", h["name"])
    return jsonify(ok=True)


@app.post("/api/handsets/<int:hid>/ring-test")
@auth(parent=True)
def handset_ring_test(hid):
    h = handset_for(hid)
    if h["disabled"]:
        raise ApiError("That phone is disconnected. Reconnect it to ring it.", 409)
    rate_limit(f"ringtest:{hid}", 3, 60)
    out = ari_mod.Ari().request("POST", "/channels", endpoint=f"PJSIP/{h['sip_user']}",
                                app=ari_mod.APP, appArgs="ringtest", callerId='"" <0000>', timeout=15)
    if not (out and "id" in out):
        raise ApiError("That handset isn't connected right now, so it can't ring.", 409)
    return jsonify(ok=True)


# ---- ATA settings file (Phase 5)

def provision_xml(h):
    """Settings for a Grandstream HT801-style adapter. Only the SIP account
    and dial plan are filled in; see docs/ADAPTER.md for the rest."""
    th = db.get_treehouse(conn(), h["treehouse_id"])
    vals = {
        "P47": public_host(),             # SIP server
        "P35": h["sip_user"],             # SIP user ID
        "P36": h["sip_user"],             # authenticate ID
        "P34": h["provision_secret"],     # authenticate password
        "P3": f"Treeline {th['name']}"[:30],  # account name
        "P290": "{ [1-9]xxx | 0001 | 911 | x+ }",  # send after four digits
    }
    items = "\n".join(f"    <{k}>{escape_xml(v)}</{k}>" for k, v in vals.items())
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<gs_provision version="1">\n'
            f'  <config version="1">\n{items}\n  </config>\n</gs_provision>\n')


def escape_xml(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


@app.get("/api/handsets/<int:hid>/provision")
@auth(parent=True)
def handset_provision_link(hid):
    h = handset_for(hid)
    if not h["provision_token"]:
        raise ApiError("Only phone adapters have a settings file.", 400)
    url = f"{request.host_url.rstrip('/')}/api/provision/{h['provision_token']}.xml"
    return jsonify(url=url, handset=handset_json(h))


@app.get("/api/provision/<token>.xml")
def provision_file(token):
    rate_limit(f"prov:{client_ip()}", 60, 600)
    h = conn().execute("SELECT * FROM handset WHERE provision_token=? AND removed_at IS NULL",
                       (token,)).fetchone()
    if not h:
        raise ApiError("That settings link isn't valid.", 404)
    return Response(provision_xml(h), mimetype="text/xml")


# ================================================================ softphone

def pair_token_row(token):
    return conn().execute("SELECT * FROM pairing WHERE token_hash=?", (db.hash_token(token),)).fetchone()


@app.get("/api/phone/config")
def phone_config():
    try:
        ice = json.loads(os.environ.get("TREELINE_ICE_SERVERS", "[]"))
    except ValueError:
        ice = []
    return jsonify(ws_url=ws_url(), domain=public_host(), realm=db.SIP_REALM, ice_servers=ice)


@app.post("/api/pair/start")
def pair_start():
    """A softphone asks for a code to show as a QR. No sign-in: the
    handset isn't a handset until a parent approves it."""
    rate_limit(f"pair:{client_ip()}", 20, 600)
    for _ in range(20):
        code = f"{secrets.randbelow(1_000_000):06d}"
        if not conn().execute("SELECT 1 FROM pairing WHERE code=?", (code,)).fetchone():
            break
    token = secrets.token_urlsafe(24)
    exp = db.iso(now() + dt.timedelta(minutes=10))
    conn().execute("INSERT INTO pairing(code,token_hash,created_at,expires_at) VALUES(?,?,?,?)",
                   (code, db.hash_token(token), db.iso(), exp))
    return jsonify(code=code, token=token, expires_at=exp, origin=public_origin()), 201


FACTORY_KEY = os.environ.get("TREELINE_FACTORY_KEY", "")


@app.post("/api/factory/devices")
def factory_register():
    """Called by the factory (or you, with the programming jig) to register a Treeline phone's
    pairing code and secret before it ships. Off unless TREELINE_FACTORY_KEY is set.

    The code printed under the phone is at least 10 digits: unlike a softphone's code, it lives for
    years, so it must not be guessable by another family trying codes."""
    rate_limit(f"factory:{client_ip()}", 20, 600)
    given = request.headers.get("X-Factory-Key", "")
    if not FACTORY_KEY or not secrets.compare_digest(given.encode(), FACTORY_KEY.encode()):
        raise ApiError("That page isn't here.", 404)
    data = body()
    code = "".join(c for c in str(data.get("code", "")) if c.isdigit())
    token = str(data.get("token", ""))
    if not (10 <= len(code) <= 12) or len(token) < 24:
        raise ApiError("Use a code of 10 to 12 digits and a device secret of at least 24 characters.")
    if conn().execute("SELECT 1 FROM pairing WHERE code=?", (code,)).fetchone():
        raise ApiError("That code is already registered.", 409)
    conn().execute("INSERT INTO pairing(code,token_hash,created_at,expires_at) VALUES(?,?,?,?)",
                   (code, db.hash_token(token), db.iso(), db.iso(now() + dt.timedelta(days=3 * 365))))
    return jsonify(ok=True), 201


@app.get("/api/pair/status")
def pair_status():
    token = request.args.get("token", "")
    row = pair_token_row(token) if token else None
    if not row or row["expires_at"] < db.iso():
        return jsonify(status="expired")
    if not row["sip_user"]:
        return jsonify(status="waiting")
    out = {"status": "paired", **credentials(row["sip_user"], row["sip_secret"])}
    conn().execute("DELETE FROM pairing WHERE code=?", (row["code"],))  # the secret leaves the server
    return jsonify(out)


@app.post("/api/pair/claim")
@auth(parent=True)
def pair_claim():
    rate_limit(f"claim:{g.email}", 10, 600)
    rate_limit(f"claim-ip:{client_ip()}", 60, 3600)
    data = body()
    code = "".join(c for c in str(data.get("code", "")) if c.isdigit())
    kind = data.get("kind") or "softphone"
    if kind not in ("softphone", "rotary"):
        raise ApiError("Pick a softphone or a Treeline phone.")
    name = clean_name(data.get("name") or "Softphone", "handset name")
    row = conn().execute("SELECT * FROM pairing WHERE code=?", (code,)).fetchone()
    if not row or row["expires_at"] < db.iso() or row["sip_user"]:
        raise ApiError("That code didn't work. Ask the softphone for a new one.", 400, "bad_pair")
    if len(db.handsets_of(conn(), g.th["id"])) >= 8:
        raise ApiError("A treehouse can have up to 8 handsets.", 409)
    hid, user, secret = db.create_handset(conn(), g.th["id"], kind, name)
    conn().execute("UPDATE pairing SET sip_user=?, sip_secret=?, handset_id=?, claimed_at=? WHERE code=?",
                   (user, secret, hid, db.iso(), code))
    pjsip.write(conn())
    audit("handset_added", name)
    return jsonify(handset=handset_json(conn().execute("SELECT * FROM handset WHERE id=?", (hid,)).fetchone())), 201


def handset_auth():
    """HTTP Basic with the handset's own SIP account."""
    h = request.headers.get("Authorization", "")
    try:
        user, secret = base64.b64decode(h[6:]).decode().split(":", 1) if h.startswith("Basic ") else (None, None)
    except (ValueError, UnicodeDecodeError):
        user = secret = None
    row = user and db.handset_by_user(conn(), user)
    if not row or not secrets.compare_digest(row["sip_md5"], db.sip_digest(user, secret or "")):
        raise ApiError("This phone was removed from its treehouse.", 401, "removed")
    return row


@app.get("/api/line")
def line_state():
    """What a handset should do on pickup: dial tone, join a call, or fast busy."""
    rate_limit(f"line:{client_ip()}", 600, 600)
    h = handset_auth()
    th = db.get_treehouse(conn(), h["treehouse_id"])
    if th is None:
        raise ApiError("This phone was removed from its treehouse.", 401, "removed")
    conn().execute("UPDATE handset SET last_seen=? WHERE id=?", (db.iso(), h["id"]))
    # The softphone's room: its card file holds the strings this treehouse can call now (both families
    # approved, not paused), and its sticky note shows its own quiet hours. Nothing about the other side's rules.
    live = [string_json(s, th["id"])["other"] for s in my_strings(th["id"]) if s["state"] == "live"]
    return jsonify(state=rules.line_state(conn(), th, now(), h), name=h["name"], number=th["number"],
                   treehouse=th["name"],
                   strings=sorted(({"name": o["name"], "number": o["number"]} for o in live), key=lambda o: o["name"].lower()),
                   quiet={"enabled": bool(th["quiet_enabled"]), "start": th["quiet_start"], "end": th["quiet_end"]})


# ================================================================ calls

@app.get("/api/calls")
@auth()
def calls_list():
    rng = request.args.get("range", "week")
    th, t = g.th, now()
    since = None
    if rng == "today":
        local = rules.local_now(th, t)
        since = local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(dt.timezone.utc)
    elif rng == "week":
        since = t - dt.timedelta(days=7)
    return jsonify(calls=[call_json(c, th) for c in calls_for(th, since)])


@app.get("/api/calls/<int:cid>")
@auth()
def call_detail(cid):
    c = conn().execute("SELECT * FROM call WHERE id=? AND (caller_treehouse=? OR callee_treehouse=?)",
                       (cid, g.th["id"], g.th["id"])).fetchone()
    if not c or (c["caller_treehouse"] != g.th["id"] and not visible_to_callee(c)):
        raise ApiError("That call isn't there anymore.", 404)
    return jsonify(call_json(c, g.th, detail=True))


def csv_safe(value):
    """A spreadsheet runs a cell that starts with = + - @ as a formula. Names come
    from other families, so make such a cell plain text."""
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


@app.get("/api/calls.csv")
@auth(parent=True)
def calls_csv():
    th = g.th
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["When", "Direction", "Other treehouse", "Number", "Result", "Detail", "Talk seconds"])
    for c in calls_for(th, None, 5000):
        j = call_json(c, th)
        other = j["other"] or {}
        w.writerow([csv_safe(v) for v in (
            j["started_local"], "Out" if j["direction"] == "out" else "In", other.get("name") or "",
            other.get("number") or "", j["label"], j["detail"], j["talk_sec"])])
    audit("calls_exported")
    return Response(out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=treeline-calls.csv"})


@app.get("/api/actions")
@auth()
def actions_list():
    rows = conn().execute("SELECT * FROM parent_action WHERE treehouse_id=? ORDER BY id DESC LIMIT 200",
                          (g.th["id"],)).fetchall()
    return jsonify(actions=[{"at": r["at"], "at_local": local_str(r["at"], g.th["timezone"]),
                             "email": r["email"], "action": r["action"], "target": r["target"],
                             "before": r["before"], "after": r["after"]} for r in rows])


@app.get("/api/phonebook")
@auth()
def phonebook():
    th = g.th
    entries = []
    for s in my_strings(th["id"]):
        if s["state"] in ("live", "paused"):
            j = string_json(s, th["id"])
            entries.append({"name": j["other"]["name"], "number": j["other"]["number"], "state": s["state"]})
    entries.sort(key=lambda e: e["name"].lower())
    return jsonify(treehouse=th["name"], number=th["number"], entries=entries)


# ================================================================ grown-ups

@app.get("/api/grown-ups")
@auth()
def grown_ups_list():
    rows = conn().execute("SELECT * FROM grown_up WHERE treehouse_id=? ORDER BY id", (g.th["id"],)).fetchall()
    return jsonify(grown_ups=[{"id": r["id"], "email": r["email"], "name": r["name"], "role": r["role"],
                               "you": r["id"] == g.gu["id"]} for r in rows])


@app.post("/api/grown-ups")
@auth(parent=True)
def grown_up_add():
    data = body()
    email = str(data.get("email", "")).strip().lower()
    role = data.get("role", "parent")
    if not EMAIL_RE.match(email):
        raise ApiError("That doesn't look like an email address.")
    if role not in ("parent", "sitter"):
        raise ApiError("Pick parent or sitter.")
    if conn().execute("SELECT 1 FROM grown_up WHERE email=?", (email,)).fetchone():
        raise ApiError("That email is already part of a treehouse.", 409)
    name = " ".join(str(data.get("name") or "").split())[:60] or None
    conn().execute("INSERT INTO grown_up(email,name,treehouse_id,role,created_at) VALUES(?,?,?,?,?)",
                   (email, name, g.th["id"], role, db.iso()))
    audit("grown_up_added", email, None, role)
    mail.send(email, f"You've been added to {g.th['name']} on Treeline",
              f"{g.gu['name'] or g.email} added you as a {role} for {g.th['name']}.\n\n"
              "Open Treeline and sign in with this email address to see it.")
    return jsonify(ok=True), 201


@app.delete("/api/grown-ups/<int:gid>")
@auth(parent=True)
def grown_up_remove(gid):
    row = conn().execute("SELECT * FROM grown_up WHERE id=? AND treehouse_id=?", (gid, g.th["id"])).fetchone()
    if not row:
        raise ApiError("They aren't part of this treehouse.", 404)
    if row["role"] == "parent" and conn().execute(
            "SELECT COUNT(*) n FROM grown_up WHERE treehouse_id=? AND role='parent'",
            (g.th["id"],)).fetchone()["n"] <= 1:
        raise ApiError("A treehouse needs at least one parent.", 409)
    conn().execute("DELETE FROM grown_up WHERE id=?", (gid,))
    conn().execute("DELETE FROM session WHERE email=?", (row["email"],))
    audit("grown_up_removed", row["email"], row["role"], None)
    return jsonify(ok=True)


# ================================================================ push notifications

VAPID_PUBLIC = os.environ.get("TREELINE_VAPID_PUBLIC", "")


@app.get("/api/push/key")
def push_key():
    if not VAPID_PUBLIC:
        raise ApiError("Notifications aren't set up on this server.", 404)
    return jsonify(key=VAPID_PUBLIC)


@app.post("/api/push/subscribe")
@auth()
def push_subscribe():
    data = body()
    keys = data.get("keys") if isinstance(data.get("keys"), dict) else {}
    endpoint = str(data.get("endpoint", ""))
    if not (endpoint.startswith("https://") and keys.get("p256dh") and keys.get("auth")) or len(endpoint) > 1000:
        raise ApiError("That device couldn't turn on notifications.")
    conn().execute("INSERT INTO push_subscription(email,endpoint,p256dh,auth,created_at) VALUES(?,?,?,?,?) "
                   "ON CONFLICT(endpoint) DO UPDATE SET email=excluded.email, p256dh=excluded.p256dh, auth=excluded.auth",
                   (g.email, endpoint, keys["p256dh"], keys["auth"], db.iso()))
    return jsonify(ok=True), 201


@app.delete("/api/push/subscribe")
@auth()
def push_unsubscribe():
    conn().execute("DELETE FROM push_subscription WHERE endpoint=? AND email=?",
                   (str(body().get("endpoint", "")), g.email))
    return jsonify(ok=True)


# ================================================================ pages

def _send(root, path):
    full = os.path.normpath(os.path.join(root, path))
    if not full.startswith(os.path.normpath(root) + os.sep) and full != os.path.normpath(root):
        raise ApiError("That page isn't here.", 404)
    if os.path.isdir(full):
        path = os.path.join(path, "index.html")
    return send_from_directory(root, path)


@app.get("/ui/<path:path>")
def ui_files(path):
    return _send(os.path.join(WEB, "ui"), path)


@app.get("/", defaults={"path": ""})
@app.get("/<path:path>")
def site_files(path):
    if path.startswith("api/"):
        raise ApiError("That page isn't here.", 404)
    root = os.path.join(WEB, "site")
    target = path or "parent/"
    if path in ("", "index.html"):
        return redirect("/parent/", 302)
    return _send(root, target)
