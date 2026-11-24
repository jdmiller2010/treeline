import datetime as dt
import unittest

from tests import helpers
from treeline import db, households, jobs


class FakeAri:
    def __init__(self, online):
        self.online = online

    def online_users(self):
        return self.online


class Jobs(unittest.TestCase):
    def setUp(self):
        self.c = helpers.fresh_conn()
        self.tid = helpers.house(self.c, "Sam's", number="2001")
        self.hid, self.user, _ = db.create_handset(self.c, self.tid, "ata", "Hall phone")
        db.set_setting(self.c, "offline_alert_minutes", 10)

    def notes(self):
        return households.conn(self.tid).execute(
            "SELECT * FROM notice WHERE kind='handset_offline' AND dismissed_at IS NULL").fetchall()

    def test_offline_for_a_while_raises_one_note_and_recovery_clears_it(self):
        t0 = db.utcnow()
        self.c.execute("UPDATE handset SET last_seen=?", (db.iso(t0 - dt.timedelta(minutes=30)),))
        jobs.check_handsets(self.c, FakeAri(set()), t0)
        jobs.check_handsets(self.c, FakeAri(set()), t0)           # again: still just one
        self.assertEqual(len(self.notes()), 1)
        jobs.check_handsets(self.c, FakeAri({self.user}), t0)
        self.assertEqual(self.notes(), [])
        self.assertEqual(self.c.execute("SELECT online FROM handset").fetchone()["online"], 1)

    def test_a_disconnected_phone_never_raises_an_offline_note(self):
        t0 = db.utcnow()
        self.c.execute("UPDATE handset SET last_seen=?, disabled=1", (db.iso(t0 - dt.timedelta(hours=5)),))
        jobs.check_handsets(self.c, FakeAri(set()), t0)
        self.assertEqual(self.notes(), [])

    def test_disconnecting_a_phone_clears_its_existing_offline_note(self):
        t0 = db.utcnow()
        self.c.execute("UPDATE handset SET last_seen=?", (db.iso(t0 - dt.timedelta(hours=5)),))
        jobs.check_handsets(self.c, FakeAri(set()), t0)
        self.assertEqual(len(self.notes()), 1)
        self.c.execute("UPDATE handset SET disabled=1")
        jobs.check_handsets(self.c, FakeAri(set()), t0)
        self.assertEqual(self.notes(), [])

    def test_a_brief_blip_raises_nothing(self):
        t0 = db.utcnow()
        self.c.execute("UPDATE handset SET last_seen=?", (db.iso(t0 - dt.timedelta(minutes=2)),))
        jobs.check_handsets(self.c, FakeAri(set()), t0)
        self.assertEqual(self.notes(), [])

    def test_asterisk_down_means_no_conclusions(self):
        t0 = db.utcnow()
        self.c.execute("UPDATE handset SET last_seen=?", (db.iso(t0 - dt.timedelta(hours=5)),))
        jobs.check_handsets(self.c, FakeAri(None), t0)
        self.assertEqual(self.notes(), [])

    def put_call(self, tid, started, caller=None, callee=None):
        households.conn(tid).execute(
            "INSERT INTO call_log(id,started_at,caller_treehouse,callee_treehouse,state,result) VALUES(?,?,?,?,?,?)",
            (abs(hash((tid, started))) % 10 ** 9, started, caller, callee, "ended", "connected"))

    def calls_in(self, tid):
        return households.conn(tid).execute("SELECT count(*) FROM call_log").fetchone()[0]

    def test_an_unfinished_setup_is_forgotten_after_a_day_and_nobody_else_is(self):
        t0 = db.utcnow()
        old, fresh = db.iso(t0 - dt.timedelta(hours=25)), db.iso(t0 - dt.timedelta(hours=2))
        far = db.iso(t0 + dt.timedelta(days=30))
        self.c.execute("INSERT INTO grown_up(email,name,treehouse_id,role,created_at) VALUES(?,?,?,?,?)",
                       ("parent@example.com", "Pat", self.tid, "parent", db.iso()))
        self.c.execute("INSERT INTO app_admin(email,added_by,created_at) VALUES(?,?,?)", ("staff@example.com", "ssh:test", db.iso()))
        rows = [("t-left", "left@example.com", old), ("t-new", "new@example.com", fresh), ("t-parent", "parent@example.com", old),
                ("t-staff", "staff@example.com", old), ("t-legacy", "legacy@example.com", None)]
        for tok, email, created in rows:
            self.c.execute("INSERT INTO session(token_hash,email,expires_at,created_at) VALUES(?,?,?,?)", (tok, email, far, created))
        jobs.purge(self.c, t0)
        left = {r["token_hash"] for r in self.c.execute("SELECT token_hash FROM session")}
        self.assertEqual(left, {"t-new", "t-parent", "t-staff", "t-legacy"})

    def test_purge_keeps_each_treehouses_retention(self):
        old = db.iso(db.utcnow() - dt.timedelta(days=100))
        other = helpers.house(self.c, "Alex's", number="2002", retention_days=200)
        for tid in (self.tid, other):
            self.put_call(tid, old, caller=tid)
        jobs.purge(self.c)
        self.assertEqual((self.calls_in(self.tid), self.calls_in(other)), (0, 1))     # 90 days forgets it, 200 keeps it

    def test_one_familys_short_retention_does_not_erase_the_others_history(self):
        old = db.iso(db.utcnow() - dt.timedelta(days=30))
        a = helpers.house(self.c, "A", number="2003", retention_days=7)
        b = helpers.house(self.c, "B", number="2004", retention_days=365)
        for tid in (a, b):
            self.put_call(tid, old, caller=a, callee=b)                                # the same call, each family's copy
        jobs.purge(self.c)
        self.assertEqual((self.calls_in(a), self.calls_in(b)), (0, 1))
        households.set_retention(b, 7)
        jobs.purge(self.c)                                                             # now B's time is up as well
        self.assertEqual(self.calls_in(b), 0)

    def test_a_damaged_household_file_does_not_stop_the_purge_of_the_others(self):
        old = db.iso(db.utcnow() - dt.timedelta(days=100))
        other = helpers.house(self.c, "Alex's", number="2002")
        self.put_call(other, old, caller=other)
        households.forget_all()
        open(households.path(self.tid), "wb").write(b"not a database at all, not even close, " * 50)
        with self.assertLogs("treeline", "ERROR"):
            jobs.purge(self.c)
        self.assertEqual(self.calls_in(other), 0)

    def test_a_damaged_household_file_does_not_stop_the_alerts_of_the_others(self):
        other = helpers.house(self.c, "Alex's", number="2002")
        self.c.execute("INSERT INTO grown_up(email,treehouse_id,role,created_at) VALUES(?,?,?,?)",
                       ("alex@example.com", other, "parent", db.iso()))
        households.add_notice(other, "x", "Hello", "Body")
        households.forget_all()
        open(households.path(self.tid), "wb").write(b"not a database at all, not even close, " * 50)
        sent = []
        real = jobs.mail.send
        jobs.mail.send = lambda to, subj, body: sent.append(to) or True
        try:
            with self.assertLogs("treeline", "ERROR"):
                jobs.send_alert_emails(self.c, push=lambda *a: None)
        finally:
            jobs.mail.send = real
        self.assertEqual(sent, ["alex@example.com"])

    def test_push_goes_to_each_device_and_forgets_dead_ones(self):
        self.c.execute("INSERT INTO push_subscription(email,endpoint,p256dh,auth,created_at) VALUES(?,?,?,?,?)",
                       ("mom@example.com", "https://push/a", "k", "a", db.iso()))
        self.c.execute("INSERT INTO push_subscription(email,endpoint,p256dh,auth,created_at) VALUES(?,?,?,?,?)",
                       ("mom@example.com", "https://push/gone", "k", "a", db.iso()))
        seen = []

        def send(sub, payload):
            if sub["endpoint"].endswith("gone"):
                raise LookupError("gone")
            seen.append((sub["endpoint"], payload))
        old = jobs.VAPID_PRIVATE
        jobs.VAPID_PRIVATE = "configured"
        try:
            n = jobs.push_to(self.c, "mom@example.com", "Hello", "Body", send=send)
        finally:
            jobs.VAPID_PRIVATE = old
        self.assertEqual(n, 1)
        self.assertIn('"title": "Hello"', seen[0][1])
        left = [r["endpoint"] for r in self.c.execute("SELECT endpoint FROM push_subscription")]
        self.assertEqual(left, ["https://push/a"])

    def test_no_push_without_keys(self):
        self.assertEqual(jobs.push_to(self.c, "mom@example.com", "x", "y", send=lambda *a: 1 / 0), 0)

    def test_a_failing_mail_service_does_not_repeat_the_alert_every_pass(self):
        self.c.execute("INSERT INTO grown_up(email,treehouse_id,role,created_at) VALUES(?,?,?,?)",
                       ("mom@example.com", self.tid, "parent", db.iso()))
        households.add_notice(self.tid, "x", "Something happened", "Details")
        tries, pushes = [], []
        real = jobs.mail.send
        jobs.mail.send = lambda to, subj, body: tries.append(to) or False        # SMTP is down
        try:
            for _ in range(3):                                                    # three 20-second passes
                jobs.send_alert_emails(self.c, push=lambda *a: pushes.append(a))
        finally:
            jobs.mail.send = real
        self.assertEqual(len(tries), 1)
        self.assertEqual(len(pushes), 1)

    def test_emails_go_to_parents_once(self):
        self.c.execute("INSERT INTO grown_up(email,treehouse_id,role,created_at) VALUES(?,?,?,?)",
                       ("mom@example.com", self.tid, "parent", db.iso()))
        self.c.execute("INSERT INTO grown_up(email,treehouse_id,role,created_at) VALUES(?,?,?,?)",
                       ("sitter@example.com", self.tid, "sitter", db.iso()))
        households.add_notice(self.tid, "x", "Something happened", "Details")
        sent = []
        real = jobs.mail.send
        jobs.mail.send = lambda to, subj, body: sent.append(to) or True
        try:
            jobs.send_alert_emails(self.c)
            jobs.send_alert_emails(self.c)
        finally:
            jobs.mail.send = real
        self.assertEqual(sent, ["mom@example.com"])


if __name__ == "__main__":
    unittest.main()
