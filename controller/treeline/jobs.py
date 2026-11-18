"""Background chores: handset check-ins, alerts by email, and cleanup."""

import datetime as dt
import logging
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


def send_alert_emails(conn):
    """Email new notes to the treehouse's parents."""
    rows = conn.execute("SELECT * FROM notice WHERE emailed_at IS NULL AND dismissed_at IS NULL "
                        "AND created_at >= ?", (db.iso(db.utcnow() - dt.timedelta(days=1)),)).fetchall()
    for n in rows:
        parents = conn.execute("SELECT email FROM grown_up WHERE treehouse_id=? AND role='parent'",
                               (n["treehouse_id"],)).fetchall()
        ok = True
        for p in parents:
            ok = mail.send(p["email"], f"Treeline: {n['title']}",
                           f"{n['title']}\n\n{n['body'] or ''}\n\nOpen the Treeline app to see more.") and ok
        if ok:
            conn.execute("UPDATE notice SET emailed_at=? WHERE id=?", (db.iso(), n["id"]))


def purge(conn, now=None):
    """Delete old records: call records after each treehouse's retention days
    (90 by default), parent actions after a year, and expired logins."""
    now = now or db.utcnow()
    for th in conn.execute("SELECT id, retention_days FROM treehouse").fetchall():
        cutoff = db.iso(now - dt.timedelta(days=th["retention_days"]))
        conn.execute("DELETE FROM call WHERE started_at < ? AND state='ended' "
                     "AND (caller_treehouse=? OR callee_treehouse=?)", (cutoff, th["id"], th["id"]))
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
