"""Background chores: handset check-ins, alerts by email, and cleanup."""

import datetime as dt
import json
import logging
import os
import time

from . import db, households, mail, pjsip, removal

log = logging.getLogger("treeline")


def _safe(fn, *args):
    """A note for one household must never stop the check for all the others (a damaged file is that family's problem)."""
    try:
        return fn(*args)
    except Exception:
        log.exception("household note failed (%s)", args[:1])


def check_handsets(conn, ari, now=None):
    """Mark handsets online or offline, and raise a note when one has been
    offline a while."""
    now = now or db.utcnow()
    online = ari.online_users()
    if online is None:
        return  # Asterisk unreachable; learn nothing
    wait = dt.timedelta(minutes=int(db.get_setting(conn, "offline_alert_minutes")))
    rows = conn.execute("SELECT h.*, t.name AS house FROM handset h JOIN treehouse t "
                        "ON t.id=h.treehouse_id WHERE h.removed_at IS NULL AND t.left_at IS NULL AND t.archived_at IS NULL")
    for h in rows.fetchall():
        key = f"offline:{h['id']}"
        if h["disabled"]:                    # switched off on purpose: nothing to worry about
            _safe(households.dismiss_key, h["treehouse_id"], key, db.iso(now))
            continue
        if h["sip_user"] in online:
            conn.execute("UPDATE handset SET online=1, last_seen=? WHERE id=?", (db.iso(now), h["id"]))
            _safe(households.dismiss_key, h["treehouse_id"], key, db.iso(now))
            continue
        conn.execute("UPDATE handset SET online=0 WHERE id=?", (h["id"],))
        since = db.parse(h["last_seen"]) or db.parse(h["created_at"])
        if now - since >= wait:
            _safe(households.add_notice, h["treehouse_id"], "handset_offline", f"{h['name']} is offline",
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
    Home either way.) The notes are in each household's own file, so this visits each in turn."""
    since = db.iso(db.utcnow() - dt.timedelta(days=1))
    for tid in [r["id"] for r in conn.execute("SELECT id FROM treehouse WHERE left_at IS NULL AND archived_at IS NULL")]:
        try:
            hc = households.conn(tid)
        except households.HouseholdGone:
            continue
        except Exception:                                       # a damaged household file: the others still get their alerts
            log.exception("household %s: could not open to send alerts", tid)
            continue
        rows = hc.execute("SELECT * FROM notice WHERE emailed_at IS NULL AND dismissed_at IS NULL "
                          "AND created_at >= ?", (since,)).fetchall()
        for n in rows:
            hc.execute("UPDATE notice SET emailed_at=? WHERE id=?", (db.iso(), n["id"]))
            parents = conn.execute("SELECT email FROM grown_up WHERE treehouse_id=? AND role='parent'",
                                   (tid,)).fetchall()
            for p in parents:
                if not mail.send(p["email"], f"Treeline: {n['title']}",
                                 f"{n['title']}\n\n{n['body'] or ''}\n\nOpen the Treeline app to see more."):
                    log.warning("couldn't email %s about %r", p["email"], n["title"])
                push(conn, p["email"], n["title"], n["body"])


def purge_archived(conn, now=None):
    """A treehouse Treeline staff archived more than ARCHIVE_DAYS ago is erased, as a family's own "Delete everything" would: one central
    transaction (re-checked inside it, so a restore that just happened wins), then the other families' notes, then its file."""
    now = now or db.utcnow()
    cutoff = db.iso(now - dt.timedelta(days=db.ARCHIVE_DAYS))
    old = ("SELECT id, name FROM treehouse WHERE archived_at IS NOT NULL AND archived_at < ? AND left_at IS NULL AND deleted_at IS NULL")
    erased = []
    for r in conn.execute(old, (cutoff,)).fetchall():
        tid = r["id"]
        conn.execute("BEGIN IMMEDIATE")
        try:
            if conn.execute(old + " AND id=?", (cutoff, tid)).fetchone() is None:
                conn.execute("ROLLBACK")
                continue
            tell = removal.erase_central(conn, tid)
            db.log_admin(conn, "treeline", "treehouse_erased", "treehouse", tid, f"archived over {db.ARCHIVE_DAYS} days")
            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        removal.tell_ended(tell, f"{r['name']} left the Treeline")
        households.remove(tid)
        erased.append(tid)
    if erased:
        try:
            pjsip.write(conn)
        except Exception:                                      # Asterisk may be down: the accounts were already off (archived)
            log.exception("could not rewrite the handset accounts after erasing %s", erased)
    return erased


UNFINISHED_HOURS = 24


def forget_unfinished_setups(conn, now=None):
    """Someone who got past the beta code but never made their treehouse: after a day their sign-in is forgotten, and next
    time they start again from the code. (A grown-up of a treehouse, and a Treeline admin, are never touched.)"""
    now = now or db.utcnow()
    conn.execute("DELETE FROM session WHERE created_at IS NOT NULL AND created_at < ? "
                 "AND email NOT IN (SELECT g.email FROM grown_up g JOIN treehouse t ON t.id=g.treehouse_id WHERE t.left_at IS NULL) "
                 "AND email NOT IN (SELECT email FROM app_admin WHERE removed_at IS NULL)",
                 (db.iso(now - dt.timedelta(hours=UNFINISHED_HOURS)),))


def purge(conn, now=None):
    """Forget old records. Each family's retention trims only its own file: nobody's setting touches anyone else's
    copy of a call. Notes and the action log age out inside each file too. The central ledger keeps only the last
    few days (what the rules compute from), and only calls already copied to the households. A treehouse that left
    keeps its file until its records are past its own retention. Expired logins and old pre-migration copies go."""
    now = now or db.utcnow()
    for tid in households.ids():
        try:
            households.trim(tid, now)
        except Exception:                                       # one damaged file must not stop the rest
            log.exception("household %s: could not trim", tid)
    households.purge_left(conn, now)
    try:
        purge_archived(conn, now)
    except Exception:
        log.exception("could not erase old archived treehouses")
    db.trim_admin_audit(conn)
    db.prune_ledger(conn, now)
    for table in ("session", "login_code", "pairing"):
        conn.execute(f"DELETE FROM {table} WHERE expires_at < ?", (db.iso(now),))
    forget_unfinished_setups(conn, now)
    db.prune_pre_migrate(os.path.join(os.path.dirname(db.DB_PATH) or ".", "pre-migrate"), now)
    db.prune_pre_migrate(households.pre_migrate_dir(), now)


def run_forever(ari):
    conn = db.connect()  # made here: a connection belongs to one thread
    last_purge = 0.0
    while True:
        try:
            check_handsets(conn, ari)
            send_alert_emails(conn)
            if time.time() - last_purge > 3600:
                purge(conn)
                households.reconcile(conn)             # (also once at startup: run_controller.py)
                last_purge = time.time()
        except Exception:
            log.exception("background job failed")
        time.sleep(20)
