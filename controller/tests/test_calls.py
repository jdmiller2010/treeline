"""The call engine, with a fake Asterisk."""
import unittest
from unittest import mock

from tests import helpers
from treeline import ari as ari_mod
from treeline import calls, db, households, rules


class FakeAri:
    def __init__(self, bridge_ok=True, play_ok=True):
        self.sent = []
        self.bridge_ok = bridge_ok
        self.play_ok = play_ok

    def request(self, method, path, **params):
        self.sent.append((method, path, params))
        if path == "/bridges" and method == "POST":
            return {"id": "br1"} if self.bridge_ok else None
        if path == "/endpoints/PJSIP":
            return []
        if path.endswith("/play"):
            return {"id": "pb-%d" % len(self.sent)} if self.play_ok else None   # a started playback has an id
        return {}

    def online_users(self):
        return None


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.conn = db.local_conn()
        self.sam = db.create_treehouse(self.conn, "Sam's", number=None, timezone="America/Los_Angeles", quiet_enabled=0)
        self.alex = db.create_treehouse(self.conn, "Alex's", number=None, timezone="America/Los_Angeles", quiet_enabled=0)
        households.create(self.sam)
        households.create(self.alex)
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

    def test_a_disconnected_phone_cannot_join_a_call(self):
        e, call = self.engine()
        self.add_legs(e, call)
        e.connect(call, call.legs["a1"])
        for t in call.timers:
            t.cancel()
        self.conn.execute("UPDATE handset SET disabled=1 WHERE id=?", (self.sam_h,))
        handset = self.conn.execute("SELECT * FROM handset WHERE id=?", (self.sam_h,)).fetchone()
        e.on_incoming({"id": "j1", "name": f"PJSIP/{handset['sip_user']}-0001", "dialplan": {"exten": rules.SYSTEM_JOIN_NUMBER}})
        self.assertNotIn("j1", call.legs)
        self.assertTrue(any(m == "POST" and path.startswith("/channels/j1/play/") for m, path, _ in e.ari.sent))   # fast busy

    def call_events(self):
        return [r["event"] for r in self.conn.execute("SELECT event FROM call_event WHERE call_id=? ORDER BY id", (self.call_id,))]

    def connected_engine(self, **kw):
        e, call = self.engine(**kw)
        self.add_legs(e, call)
        e.connect(call, call.legs["a1"])
        for t in call.timers:
            t.cancel()
        return e, call

    def test_the_time_limit_pips_are_audited_only_when_asterisk_started_them(self):
        e, call = self.connected_engine()
        e.warn(call)
        self.assertIn("pips", self.call_events())
        self.assertNotIn("pips_failed", self.call_events())

    def test_pips_that_asterisk_could_not_play_are_audited_as_failed_not_as_played(self):
        # A build without the module that plays into a bridge (chan_bridge_media) answers with an error and nobody hears the
        # warning: the audit must not claim they did.
        e, call = self.connected_engine(play_ok=False)
        e.warn(call)
        self.assertIn("pips_failed", self.call_events())
        self.assertNotIn("pips", self.call_events())

    def test_a_join_tone_that_asterisk_could_not_play_is_audited_but_the_join_still_counts(self):
        e, call = self.connected_engine(play_ok=False)
        h = self.conn.execute("SELECT * FROM handset WHERE id=?", (self.sam_h,)).fetchone()
        e.join_call("j1", h)
        self.assertIn("j1", call.legs)
        self.assertIn("joined", self.call_events())
        self.assertIn("join_tone_failed", self.call_events())

    def test_a_join_tone_that_played_is_not_reported_as_failed(self):
        e, call = self.connected_engine()
        h = self.conn.execute("SELECT * FROM handset WHERE id=?", (self.sam_h,)).fetchone()
        e.join_call("j1", h)
        self.assertIn("joined", self.call_events())
        self.assertNotIn("join_tone_failed", self.call_events())

    def test_busy_tones_play_until_the_caller_hangs_up(self):
        for name in ("busy", "fast_busy"):
            media, seconds = calls.sound_plan(name)[0]
            self.assertGreaterEqual(seconds, 30, name)          # not cut off after a few seconds: only a safety net for a phone that never hangs up

    def test_a_caller_hanging_up_mid_tone_leaves_nothing_playing_or_queued(self):
        e = calls.Engine(FakeAri())
        e.play_plan("c9", calls.sound_plan("busy"))
        self.assertEqual(len(e.playing), 1)
        e.on_channel_gone("c9")
        self.assertEqual(e.playing, {})

    def test_sound_plans(self):
        self.assertEqual(calls.sound_plan("busy")[0][0], "tone:busy")
        self.assertEqual(calls.sound_plan("fast_busy")[0][0], "tone:congestion")
        for media, _ in calls.TONES.values():
            self.assertNotIn(",", media)      # ARI would split it into separate "files"
        plan = calls.sound_plan(rules.SOUND_NO_911)
        self.assertEqual(plan[0][0], calls.TONES["sit"][0])
        self.assertEqual(plan[1][0], "sound:treeline/no_911")

    # ---- the households' copies

    def copies(self, tid):
        return households.conn(tid).execute("SELECT * FROM call_log WHERE id=?", (self.call_id,)).fetchall()

    def test_finishing_a_call_copies_it_to_both_families_with_their_own_view(self):
        e, call = self.engine()
        self.add_legs(e, call)
        self.conn.execute("INSERT INTO call_event(call_id,at,handset_id,event) VALUES(?,?,?,?)",
                          (self.call_id, db.iso(), self.sam_h, "dialed"))
        e.connect(call, call.legs["a1"])
        for t in call.timers:
            t.cancel()
        e.finish(call, rules.CONNECTED, None)
        self.assertEqual(self.row()["logged"], 1)
        mine, theirs = self.copies(self.sam)[0], self.copies(self.alex)[0]
        self.assertEqual((mine["result"], theirs["result"]), ("connected", "connected"))
        self.assertEqual((mine["answered_handset"], theirs["caller_handset"]), (None, None))       # the other family's phones
        events = households.conn(self.alex).execute("SELECT event, handset_id, theirs FROM call_event WHERE call_id=? ORDER BY id",
                                                    (self.call_id,)).fetchall()
        self.assertEqual([(r["event"], r["handset_id"], r["theirs"]) for r in events],
                         [("dialed", None, 1), ("answered", self.alex_h, 0), ("ended", None, 0)])

    def test_an_error_writing_the_copies_never_breaks_ending_the_call_and_reconcile_repairs_it(self):
        e, call = self.engine()
        self.add_legs(e, call)
        with mock.patch.object(households, "record_call", side_effect=RuntimeError("disk full")), \
                self.assertLogs("treeline", "ERROR"):
            e.finish(call, rules.NO_ANSWER, "not_answered")
        self.assertEqual((self.row()["state"], self.row()["logged"]), ("ended", 0))                  # the call itself ended fine
        self.assertEqual(self.copies(self.sam), [])
        households.reconcile(self.conn)
        self.assertEqual((len(self.copies(self.sam)), len(self.copies(self.alex)), self.row()["logged"]), (1, 1, 1))

    def dial(self, e, number, handset=None):
        handset = self.conn.execute("SELECT * FROM handset WHERE id=?", (handset or self.sam_h,)).fetchone()
        before = self.conn.execute("SELECT COALESCE(MAX(id),0) FROM call").fetchone()[0]
        e.on_incoming({"id": "d1", "name": f"PJSIP/{handset['sip_user']}-0001", "dialplan": {"exten": number}})
        return self.conn.execute("SELECT * FROM call WHERE id>? ORDER BY id", (before,)).fetchall()

    def test_blocked_attempts_are_copied_to_the_callers_file_only(self):
        e, _ = self.engine()
        self.conn.execute("UPDATE call SET state='ended', logged=1 WHERE id=?", (self.call_id,))    # the line is free
        alex_number = db.get_treehouse(self.conn, self.alex)["number"]
        for number in (alex_number, "911", "5555", "12"):                   # not strung, 911, no such number, too short
            rows = self.dial(e, number)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["state"], "ended")
            self.assertEqual(rows[0]["logged"], 1, number)
        got = households.conn(self.sam).execute("SELECT dialed, result, callee_treehouse FROM call_log ORDER BY id").fetchall()
        self.assertEqual([(r["dialed"], r["result"]) for r in got][-4:],
                         [(alex_number, "not_strung"), ("911", "no_911"), ("5555", "not_in_service"), ("12", "incomplete")])
        self.assertIsNone(got[-4]["callee_treehouse"])                         # not whose number it was
        self.assertEqual(households.conn(self.alex).execute("SELECT count(*) FROM call_log").fetchone()[0], 0)
        notes = [n["kind"] for n in households.notices(self.sam)]
        self.assertIn("no_911", notes)
        self.assertIn("not_strung_attempt", notes)
        self.assertEqual(households.notices(self.alex), [])                    # and Alex's family heard of none of it


if __name__ == "__main__":
    unittest.main()
