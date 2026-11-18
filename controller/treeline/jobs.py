"""Background chores: handset check-ins, alerts by email, and cleanup."""

import datetime as dt
import json
import logging
import os
import time

from . import db, mail

log = logging.getLogger("treeline")


def check_handsets(conn, ari, now=None):
    """Mark handsets online or offline, and raise a note when one has been
    offline a while."""
    now = now or db.utcnow()
    online = ari.online_users()
    if online is None:
        return  # Asterisk unreachable; learn nothing
    wait = dt.timedelta(minutes=int(db.get_setting(conn, "offline_alert_minutes")))
    rows = conn.execute("SELECT h.*, t.name AS house FROM handset h JOIN treehouse t "
                        "ON t.id=h.treehouse_id WHERE h.removed_at IS NULL AND t.left_at IS NULL")
    for h in rows.fetchall():
        key = f"offline:{h['id']}"
        if h["disabled"]:                    # switched off on purpose: nothing to worry about
            conn.execute("UPDATE notice SET dismissed_at=? WHERE treehouse_id=? AND key=? AND dismissed_at IS NULL",
                         (db.iso(now), h["treehouse_id"], key))
            continue
        if h["sip_user"] in online:
            conn.execute("UPDATE handset SET online=1, last_seen=? WHERE id=?", (db.iso(now), h["id"]))
            conn.execute("UPDATE notice SET dismissed_at=? WHERE treehouse_id=? AND key=? "
                         "AND dismissed_at IS NULL", (db.iso(now), h["treehouse_id"], key))
            continue
        conn.execute("UPDATE handset SET online=0 WHERE id=?", (h["id"],))
        since = db.parse(h["last_seen"]) or db.parse(h["created_at"])
        if now - since >= wait:
            db.add_notice(
                conn, h["treehouse_id"], "handset_offline", f"{h['name']} is offline",
                "It hasn't checked in for a while, so calls can't reach it.", key)


VAPID_PRIVATE = os.environ.get("TREELINE_VAPID_PRIVATE", "")
VAPID_SUBJECT = os.environ.get("TREELINE_VAPID_SUBJECT", "mailto:admin@treeline.invalid")


def push_to(conn, email, title, body, send=None):
    """Send a Web Push to every device this grown-up turned notifications on for.
    Devices that have gone away (404 or 410) are forgotten."""
    if not VAPID_PRIVATE:
        return 0
    if send is None:
        try:
            from pywebpush import WebPushException, webpush
        except ImportError:
            return 0

        def send(sub, payload):
            try:
                webpush(subscription_info=sub, data=payload, vapid_private_key=VAPID_PRIVATE,
                        vapid_claims={"sub": VAPID_SUBJECT}, ttl=3600, timeout=5)
            except WebPushException as err:
                code = getattr(err.response, "status_code", None)
                if code in (404, 410):
                    raise LookupError("gone") from err
                raise
    sent = 0
    for row in conn.execute("SELECT * FROM push_subscription WHERE email=?", (email,)).fetchall():
        sub = {"endpoint": row["endpoint"], "keys": {"p256dh": row["p256dh"], "auth": row["auth"]}}
        try:
            send(sub, json.dumps({"title": title, "body": body or "", "tag": "treeline"}))
            sent += 1
        except LookupError:
            conn.execute("DELETE FROM push_subscription WHERE id=?", (row["id"],))
        except Exception:
            log.exception("push to %s failed", email)
    return sent


def send_alert_emails(conn, push=push_to):
    """Tell a treehouse's parents about each new note, by email and, where they've turned it on,
    push. Each note is sent once: it's marked before anything goes out, so a slow or failing mail
    or push service can't make a parent get the same alert every 20 seconds. (The note stays on
    Home either way.)"""
    rows = conn.execute("SELECT * FROM notice WHERE emailed_at IS NULL AND dismissed_at IS NULL "
                        "AND created_at >= ?", (db.iso(db.utcnow() - dt.timedelta(days=1)),)).fetchall()
    for n in rows:
        conn.execute("UPDATE notice SET emailed_at=? WHERE id=?", (db.iso(), n["id"]))
        parents = conn.execute("SELECT email FROM grown_up WHERE treehouse_id=? AND role='parent'",
                               (n["treehouse_id"],)).fetchall()
        for p in parents:
            if not mail.send(p["email"], f"Treeline: {n['title']}",
                             f"{n['title']}\n\n{n['body'] or ''}\n\nOpen the Treeline app to see more."):
                log.warning("couldn't email %s about %r", p["email"], n["title"])
            push(conn, p["email"], n["title"], n["body"])


def purge(conn, now=None):
    """Forget old records. A call involves two families, and each sets its own
    retention, so when one family's time is up we remove *its side* of the record
    (the other family still sees the call, without a name) and delete the row once
    neither side is left. Parent actions go after a year, expired logins sooner."""
    now = now or db.utcnow()
    for th in conn.execute("SELECT id, retention_days FROM treehouse").fetchall():
        cutoff = db.iso(now - dt.timedelta(days=th["retention_days"]))
        conn.execute("UPDATE call SET caller_treehouse=NULL, caller_handset=NULL WHERE caller_treehouse=? "
                     "AND started_at < ? AND state='ended'", (th["id"], cutoff))
        conn.execute("UPDATE call SET callee_treehouse=NULL, answered_handset=NULL WHERE callee_treehouse=? "
                     "AND started_at < ? AND state='ended'", (th["id"], cutoff))
    conn.execute("DELETE FROM call WHERE state='ended' AND caller_treehouse IS NULL AND callee_treehouse IS NULL")
    conn.execute("DELETE FROM parent_action WHERE at < ?", (db.iso(now - dt.timedelta(days=365)),))
    conn.execute("DELETE FROM notice WHERE created_at < ?", (db.iso(now - dt.timedelta(days=90)),))
    for table in ("session", "login_code", "pairing"):
        conn.execute(f"DELETE FROM {table} WHERE expires_at < ?", (db.iso(now),))


def run_forever(ari):
    conn = db.connect()  # made here: a connection belongs to one thread
    last_purge = 0.0
    while True:
        try:
            check_handsets(conn, ari)
            send_alert_emails(conn)
            if time.time() - last_purge > 3600:
                purge(conn)
                last_purge = time.time()
        except Exception:
            log.exception("background job failed")
        time.sleep(20)
