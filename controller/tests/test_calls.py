"""The call engine, with a fake Asterisk."""
import unittest

from tests import helpers
from treeline import ari as ari_mod
from treeline import calls, db, rules


class FakeAri:
    def __init__(self, bridge_ok=True):
        self.sent = []
        self.bridge_ok = bridge_ok

    def request(self, method, path, **params):
        self.sent.append((method, path, params))
        if path == "/bridges" and method == "POST":
            return {"id": "br1"} if self.bridge_ok else None
        if path == "/endpoints/PJSIP":
            return []
        return {}

    def online_users(self):
        return None


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.conn = db.local_conn()
        self.sam = db.create_treehouse(self.conn, "Sam's", number=None, timezone="America/Los_Angeles", quiet_enabled=0)
        self.alex = db.create_treehouse(self.conn, "Alex's", number=None, timezone="America/Los_Angeles", quiet_enabled=0)
        self.alex_h = db.create_handset(self.conn, self.alex, "ata", "Hall")[0]
        self.sam_h = db.create_handset(self.conn, self.sam, "ata", "Kitchen")[0]
        cur = self.conn.execute("INSERT INTO call(started_at,caller_treehouse,callee_treehouse,dialed,state) "
                                "VALUES(?,?,?,?,?)", (db.iso(), self.sam, self.alex, "x", "ringing"))
        self.call_id = cur.lastrowid

    def engine(self, **kw):
        e = calls.Engine(FakeAri(**kw))
        call = calls.Call(self.call_id, db.get_treehouse(self.conn, self.sam), db.get_treehouse(self.conn, self.alex), "x")
        e.calls[self.call_id] = call
        return e, call

    def add_legs(self, e, call, with_caller=True):
        if with_caller:
            call.legs["c1"] = calls.Leg("c1", self.sam_h, "caller")
            e.by_chan["c1"] = call
        call.legs["a1"] = calls.Leg("a1", self.alex_h, "callee")
        e.by_chan["a1"] = call

    def row(self):
        return self.conn.execute("SELECT * FROM call WHERE id=?", (self.call_id,)).fetchone()

    def test_answer_bridges_both_and_starts_the_limit_timers(self):
        e, call = self.engine()
        self.add_legs(e, call)
        e.connect(call, call.legs["a1"])
        self.assertEqual(self.row()["state"], "active")
        self.assertEqual(call.bridge, "br1")
        self.assertEqual(len(call.timers), 2)
        for t in call.timers:
            t.cancel()

    def test_caller_hanging_up_as_someone_answers_ends_the_call_cleanly(self):
        e, call = self.engine()
        self.add_legs(e, call, with_caller=False)            # the caller's leg is already gone
        e.connect(call, call.legs["a1"])                      # must not raise
        r = self.row()
        self.assertEqual((r["state"], r["result"]), ("ended", rules.CALLER_HUNG_UP))
        self.assertIn(("DELETE", "/channels/a1", {}), e.ari.sent)

    def test_a_failed_bridge_ends_the_call_instead_of_leaving_it_half_open(self):
        e, call = self.engine(bridge_ok=False)
        self.add_legs(e, call)
        e.connect(call, call.legs["a1"])
        r = self.row()
        self.assertEqual((r["state"], r["reason"]), ("ended", "bridge_failed"))
        self.assertFalse(rules.line_in_use(self.conn, self.alex))
        self.assertEqual(call.timers, [])

    def test_joining_before_the_bridge_exists_is_treated_as_no_call(self):
        e, call = self.engine()
        self.add_legs(e, call)
        call.answered_at = 1.0                                # answered, bridge not made yet
        h = self.conn.execute("SELECT * FROM handset WHERE id=?", (self.sam_h,)).fetchone()
        e.join_call("j1", h)
        self.assertNotIn("j1", call.legs)

    def test_sound_plans(self):
        self.assertEqual(calls.sound_plan("busy")[0][0], "tone:busy")
        self.assertEqual(calls.sound_plan("fast_busy")[0][0], "tone:congestion")
        for media, _ in calls.TONES.values():
            self.assertNotIn(",", media)      # ARI would split it into separate "files"
        plan = calls.sound_plan(rules.SOUND_NO_911)
        self.assertEqual(plan[0][0], calls.TONES["sit"][0])
        self.assertEqual(plan[1][0], "sound:treeline/no_911")


if __name__ == "__main__":
    unittest.main()
