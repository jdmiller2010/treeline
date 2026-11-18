import datetime as dt
import unittest

from tests import helpers
from treeline import db, jobs


class FakeAri:
    def __init__(self, online):
        self.online = online

    def online_users(self):
        return self.online


class Jobs(unittest.TestCase):
    def setUp(self):
        self.c = helpers.fresh_conn()
        self.tid = db.create_treehouse(self.c, "Sam's", number="2001")
        self.hid, self.user, _ = db.create_handset(self.c, self.tid, "ata", "Hall phone")
        db.set_setting(self.c, "offline_alert_minutes", 10)

    def notes(self):
        return self.c.execute("SELECT * FROM notice WHERE kind='handset_offline' AND dismissed_at IS NULL").fetchall()

    def test_offline_for_a_while_raises_one_note_and_recovery_clears_it(self):
        t0 = db.utcnow()
        self.c.execute("UPDATE handset SET last_seen=?", (db.iso(t0 - dt.timedelta(minutes=30)),))
        jobs.check_handsets(self.c, FakeAri(set()), t0)
        jobs.check_handsets(self.c, FakeAri(set()), t0)           # again: still just one
        self.assertEqual(len(self.notes()), 1)
        jobs.check_handsets(self.c, FakeAri({self.user}), t0)
        self.assertEqual(self.notes(), [])
        self.assertEqual(self.c.execute("SELECT online FROM handset").fetchone()["online"], 1)

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

    def test_purge_keeps_each_treehouses_retention(self):
        old = db.iso(db.utcnow() - dt.timedelta(days=100))
        self.c.execute("UPDATE treehouse SET retention_days=90")
        other = db.create_treehouse(self.c, "Alex's", number="2002", retention_days=200)
        for caller in (self.tid, other):
            self.c.execute("INSERT INTO call(started_at,caller_treehouse,state,result) VALUES(?,?,?,?)",
                           (old, caller, "ended", "connected"))
        jobs.purge(self.c)
        left = [r["caller_treehouse"] for r in self.c.execute("SELECT caller_treehouse FROM call")]
        self.assertEqual(left, [other])

    def test_one_familys_short_retention_does_not_erase_the_others_history(self):
        old = db.iso(db.utcnow() - dt.timedelta(days=30))
        a = db.create_treehouse(self.c, "A", number="2003", retention_days=7)
        b = db.create_treehouse(self.c, "B", number="2004", retention_days=365)
        cur = self.c.execute("INSERT INTO call(started_at,caller_treehouse,callee_treehouse,state,result) "
                             "VALUES(?,?,?,?,?)", (old, a, b, "ended", "connected"))
        jobs.purge(self.c)
        row = self.c.execute("SELECT * FROM call WHERE id=?", (cur.lastrowid,)).fetchone()
        self.assertIsNone(row["caller_treehouse"])         # A's side is gone
        self.assertEqual(row["callee_treehouse"], b)       # B still has its record
        self.c.execute("UPDATE treehouse SET retention_days=7 WHERE id=?", (b,))
        jobs.purge(self.c)                                  # now both are past retention
        self.assertIsNone(self.c.execute("SELECT 1 FROM call WHERE id=?", (cur.lastrowid,)).fetchone())

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
        db.add_notice(self.c, self.tid, "x", "Something happened", "Details")
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
        db.add_notice(self.c, self.tid, "x", "Something happened", "Details")
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
