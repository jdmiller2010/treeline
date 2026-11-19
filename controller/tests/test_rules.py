import datetime as dt
import unittest

from tests import helpers
from treeline import db, rules

LA = "America/Los_Angeles"


def utc(y, mo, d, h, mi=0):
    return dt.datetime(y, mo, d, h, mi, tzinfo=dt.timezone.utc)


def house(c, name, number, **kw):
    return db.create_treehouse(c, name, number=number, timezone=LA, quiet_enabled=0, **kw)


class QuietHours(unittest.TestCase):
    def setUp(self):
        self.c = helpers.fresh_conn()

    _n = 1000

    def th(self, **kw):
        QuietHours._n += 1
        tid = house(self.c, "x", str(QuietHours._n))
        sets = ",".join(f"{k}=?" for k in kw)
        self.c.execute(f"UPDATE treehouse SET {sets} WHERE id=?", (*kw.values(), tid))
        return db.get_treehouse(self.c, tid)

    def test_overnight_window(self):
        t = self.th(quiet_enabled=1, quiet_start="20:00", quiet_end="07:00")
        # 2026-11-18 is a Wednesday. 21:00 PST = 05:00 UTC next day.
        self.assertTrue(rules.in_quiet_hours(t, utc(2026, 11, 19, 5)))     # 9 pm
        self.assertTrue(rules.in_quiet_hours(t, utc(2026, 11, 18, 10)))    # 2 am
        self.assertFalse(rules.in_quiet_hours(t, utc(2026, 11, 18, 20)))   # noon
        self.assertFalse(rules.in_quiet_hours(t, utc(2026, 11, 18, 15, 30)))  # 7:30 am

    def test_boundaries_start_inclusive_end_exclusive(self):
        t = self.th(quiet_enabled=1, quiet_start="20:00", quiet_end="07:00")
        self.assertTrue(rules.in_quiet_hours(t, utc(2026, 11, 19, 4, 0)))   # 8:00 pm exactly
        self.assertFalse(rules.in_quiet_hours(t, utc(2026, 11, 19, 3, 59)))  # 7:59 pm
        self.assertFalse(rules.in_quiet_hours(t, utc(2026, 11, 18, 15, 0)))  # 7:00 am exactly

    def test_same_day_window(self):
        t = self.th(quiet_enabled=1, quiet_start="16:00", quiet_end="17:00")
        self.assertTrue(rules.in_quiet_hours(t, utc(2026, 11, 19, 0, 30)))  # 4:30 pm
        self.assertFalse(rules.in_quiet_hours(t, utc(2026, 11, 19, 1, 30)))  # 5:30 pm

    def test_disabled(self):
        t = self.th(quiet_enabled=0, quiet_start="00:00", quiet_end="23:59")
        self.assertFalse(rules.in_quiet_hours(t, utc(2026, 11, 18, 12)))

    def test_days_apply_to_the_day_the_window_starts(self):
        # Only Friday nights (Mon=0 ... Fri=4).
        t = self.th(quiet_enabled=1, quiet_start="20:00", quiet_end="07:00", quiet_days="0000100")
        # Friday 2026-11-20 at 9 pm PST is quiet; so is Saturday 2 am (the same night).
        self.assertTrue(rules.in_quiet_hours(t, utc(2026, 11, 21, 5)))
        self.assertTrue(rules.in_quiet_hours(t, utc(2026, 11, 21, 10)))
        # Thursday night is not.
        self.assertFalse(rules.in_quiet_hours(t, utc(2026, 11, 20, 5)))
        # Friday 2 am is the end of Thursday night: not quiet.
        self.assertFalse(rules.in_quiet_hours(t, utc(2026, 11, 20, 10)))

    def test_follows_the_treehouses_own_time_zone_and_dst(self):
        # Summer: PDT is UTC-7, so 21:00 PDT = 04:00 UTC.
        t = self.th(quiet_enabled=1, quiet_start="20:00", quiet_end="07:00")
        self.assertTrue(rules.in_quiet_hours(t, utc(2026, 7, 2, 4)))
        self.assertFalse(rules.in_quiet_hours(t, utc(2026, 7, 2, 2, 30)))   # 7:30 pm PDT
        east = self.th(quiet_enabled=1, quiet_start="20:00", quiet_end="07:00", timezone="America/New_York")
        self.assertTrue(rules.in_quiet_hours(east, utc(2026, 11, 19, 1)))   # 8 pm EST


class Decide(unittest.TestCase):
    NOON = utc(2026, 11, 18, 20)  # noon Pacific, a Wednesday

    def setUp(self):
        self.c = helpers.fresh_conn()
        self.sam = house(self.c, "Sam's", "2001")
        self.alex = house(self.c, "Alex's", "2002")
        self.riley = house(self.c, "Riley's", "2003")
        self.sam_h = self.handset(self.sam, "sam")
        self.alex_h = self.handset(self.alex, "alex")
        self.string(self.sam, self.alex, "live")
        self.string(self.sam, self.riley, "waiting")

    def handset(self, tid, name):
        hid, _, _ = db.create_handset(self.c, tid, "ata", name)
        return self.c.execute("SELECT * FROM handset WHERE id=?", (hid,)).fetchone()

    def string(self, x, y, state):
        a, b = db.ordered(x, y)
        self.c.execute("INSERT INTO string(a_id,b_id,state,created_at,updated_at) VALUES(?,?,?,?,?)",
                       (a, b, state, db.iso(), db.iso()))

    def decide(self, dialed, caller=None, **kw):
        return rules.decide(self.c, caller or self.sam_h, dialed, kw.pop("now", self.NOON), **kw)

    def set(self, tid, **kw):
        sets = ",".join(f"{k}=?" for k in kw)
        self.c.execute(f"UPDATE treehouse SET {sets} WHERE id=?", (*kw.values(), tid))

    def test_rings_when_strung(self):
        d = self.decide("2002")
        self.assertTrue(d.allowed)
        self.assertEqual([h["id"] for h in d.handsets], [self.alex_h["id"]])

    def test_911_gets_its_own_message(self):
        d = self.decide("911")
        self.assertEqual((d.result, d.sound), (rules.NO_911, rules.SOUND_NO_911))

    def test_911_tells_the_parents_at_once_with_the_phone_and_the_time(self):
        kind, title, body, key = self.decide("911").notify_caller_parents
        self.assertEqual(kind, "no_911")
        self.assertIn("911", title)
        self.assertIn(self.sam_h["name"], body)
        self.assertIn("call 911 from another phone", body)
        self.assertRegex(body, r"\d{1,2}:\d\d (am|pm)")

    def test_911_notes_are_one_per_phone_per_hour(self):
        same = {self.decide("911").notify_caller_parents[3], self.decide("911").notify_caller_parents[3]}
        self.assertEqual(len(same), 1)                                       # pressing it again doesn't pile up notes
        later = self.decide("911", now=self.NOON + dt.timedelta(hours=2)).notify_caller_parents[3]
        self.assertNotIn(later, same)                                        # but a new hour is a new note
        other = self.decide("911", caller=self.alex_h).notify_caller_parents[3]
        self.assertNotIn(other, same)                                        # and another phone is its own

    def test_911_note_is_even_raised_when_the_line_is_paused_or_the_phone_is_off(self):
        self.set(self.sam, paused=1)
        self.assertEqual(self.decide("911").notify_caller_parents[0], "no_911")

    def test_any_other_wrong_length_cannot_be_completed_as_dialed(self):
        for dialed in ("0", "12", "20", "20021", "abcd", "", "91"):
            d = self.decide(dialed)
            self.assertEqual((d.result, d.reason, d.sound), (rules.INCOMPLETE, "wrong_length", rules.SOUND_CANNOT_COMPLETE), dialed)

    def test_four_digits_that_nobody_has_say_the_same_thing(self):
        d = self.decide("9111")
        self.assertEqual((d.result, d.sound), (rules.NOT_IN_SERVICE, rules.SOUND_CANNOT_COMPLETE))

    def test_fumbled_dials_do_not_count_toward_the_hunting_limit(self):
        db.set_setting(self.c, "unstrung_limit_count", 2)
        for _ in range(5):
            self.c.execute("INSERT INTO call(started_at,caller_treehouse,dialed,state,result) VALUES(?,?,?,?,?)",
                           (db.iso(self.NOON), self.sam, "0", "ended", "incomplete"))
        self.assertTrue(self.decide("2002").allowed)

    def test_911_beats_everything_even_when_paused(self):
        self.set(self.sam, paused=1)
        self.assertEqual(self.decide("911").result, rules.NO_911)

    def test_no_such_number(self):
        d = self.decide("2999")
        self.assertEqual((d.result, d.sound), (rules.NOT_IN_SERVICE, rules.SOUND_CANNOT_COMPLETE))

    def test_own_number_and_system_numbers_are_not_in_service(self):
        self.assertEqual(self.decide("2001").result, rules.NOT_IN_SERVICE)
        db.create_treehouse(self.c, "System", number="0900", system=True)
        self.assertEqual(self.decide("0900").result, rules.NOT_IN_SERVICE)

    def test_waiting_string_does_not_connect(self):
        d = self.decide("2003")
        self.assertEqual(d.result, rules.NOT_STRUNG)
        self.assertEqual(d.notify_caller_parents[0], "not_strung_attempt")

    def test_paused_or_cut_string_does_not_connect(self):
        self.c.execute("UPDATE string SET state='paused'")
        self.assertEqual(self.decide("2002").result, rules.NOT_STRUNG)
        self.c.execute("UPDATE string SET state='cut'")
        self.assertEqual(self.decide("2002").result, rules.NOT_STRUNG)

    def test_callers_own_line_first(self):
        self.set(self.sam, paused=1)
        d = self.decide("2002")
        self.assertEqual((d.result, d.reason, d.sound), (rules.QUIET_OR_PAUSED, "caller_paused", rules.SOUND_FAST_BUSY))
        self.set(self.sam, paused=0, quiet_enabled=1, quiet_start="11:00", quiet_end="13:00")
        self.assertEqual(self.decide("2002").reason, "caller_quiet")

    def test_other_line_quiet_or_paused_says_the_same_thing(self):
        self.set(self.alex, paused=1)
        a = self.decide("2002")
        self.set(self.alex, paused=0, quiet_enabled=1, quiet_start="11:00", quiet_end="13:00")
        b = self.decide("2002")
        self.assertEqual((a.sound, b.sound), (rules.SOUND_NOT_TAKING_CALLS, rules.SOUND_NOT_TAKING_CALLS))
        self.assertEqual((a.reason, b.reason), ("callee_paused", "callee_quiet"))

    def test_quiet_hours_apply_on_both_sides(self):
        self.set(self.alex, quiet_enabled=1, quiet_start="20:00", quiet_end="07:00")
        self.assertEqual(self.decide("2002", now=utc(2026, 11, 19, 5)).reason, "callee_quiet")
        self.assertTrue(self.decide("2002").allowed)

    def test_busy_when_other_line_in_use(self):
        carol = house(self.c, "Carol's", "2004")
        self.string(carol, self.alex, "live")
        carol_h = self.handset(carol, "carol")
        self.c.execute("INSERT INTO call(started_at,caller_treehouse,callee_treehouse,state) VALUES(?,?,?,?)",
                       (db.iso(), self.sam, self.alex, "active"))
        d = self.decide("2002", caller=carol_h)
        self.assertEqual((d.result, d.sound), (rules.BUSY, rules.SOUND_BUSY))

    def test_busy_covers_calls_the_line_started_too(self):
        carol = house(self.c, "Carol's", "2004")
        self.string(carol, self.sam, "live")
        carol_h = self.handset(carol, "carol")
        self.c.execute("INSERT INTO call(started_at,caller_treehouse,callee_treehouse,state) VALUES(?,?,?,?)",
                       (db.iso(), self.sam, self.alex, "ringing"))
        self.assertEqual(self.decide("2001", caller=carol_h).result, rules.BUSY)

    def test_offline_when_nothing_registered(self):
        d = self.decide("2002", online=set())
        self.assertEqual((d.result, d.sound), (rules.OFFLINE, rules.SOUND_FAST_BUSY))
        d = self.decide("2002", online={self.alex_h["sip_user"]})
        self.assertTrue(d.allowed)

    def test_rings_every_online_handset(self):
        alex2 = self.handset(self.alex, "alex2")
        d = self.decide("2002", online={self.alex_h["sip_user"], alex2["sip_user"]})
        self.assertEqual({h["id"] for h in d.handsets}, {self.alex_h["id"], alex2["id"]})
        d = self.decide("2002", online={alex2["sip_user"]})
        self.assertEqual([h["id"] for h in d.handsets], [alex2["id"]])

    def disconnect(self, handset):
        self.c.execute("UPDATE handset SET disabled=1 WHERE id=?", (handset["id"],))

    def test_a_disconnected_phone_does_not_ring_but_the_others_do(self):
        alex2 = self.handset(self.alex, "alex2")
        self.disconnect(self.alex_h)
        d = self.decide("2002")
        self.assertTrue(d.allowed)
        self.assertEqual([h["id"] for h in d.handsets], [alex2["id"]])

    def test_when_every_phone_is_disconnected_the_line_is_offline(self):
        self.disconnect(self.alex_h)
        d = self.decide("2002")
        self.assertEqual((d.result, d.reason), (rules.OFFLINE, "callee_offline"))

    def test_disconnecting_ignores_schedules_it_is_simply_off(self):
        # Even with the line's quiet hours, limits and pause all off, a disconnected phone gets nothing.
        self.disconnect(self.alex_h)
        self.set(self.alex, quiet_enabled=0, paused=0, daily_minutes=None)
        self.assertEqual(self.decide("2002").result, rules.OFFLINE)

    def test_a_disconnected_phone_cannot_place_calls(self):
        self.disconnect(self.sam_h)
        sam_h = self.c.execute("SELECT * FROM handset WHERE id=?", (self.sam_h["id"],)).fetchone()
        d = self.decide("2002", caller=sam_h)
        self.assertEqual((d.result, d.reason, d.sound), (rules.DISCONNECTED, "caller_phone_off", rules.SOUND_FAST_BUSY))

    def test_a_disconnected_phone_is_not_counted_as_a_call_attempt(self):
        # It's stopped before any of the line's counters, so it can't trip the hunting limit or leave a note.
        self.disconnect(self.sam_h)
        sam_h = self.c.execute("SELECT * FROM handset WHERE id=?", (self.sam_h["id"],)).fetchone()
        d = self.decide("2999", caller=sam_h)
        self.assertEqual(d.result, rules.DISCONNECTED)
        self.assertIsNone(d.notify_caller_parents)

    def test_911_still_gets_its_message_from_a_disconnected_phone(self):
        self.disconnect(self.sam_h)
        sam_h = self.c.execute("SELECT * FROM handset WHERE id=?", (self.sam_h["id"],)).fetchone()
        self.assertEqual(self.decide("911", caller=sam_h).result, rules.NO_911)

    def test_line_state_for_a_disconnected_phone(self):
        sam = db.get_treehouse(self.c, self.sam)
        self.assertEqual(rules.line_state(self.c, sam, self.NOON, self.sam_h), "idle")
        self.disconnect(self.sam_h)
        off = self.c.execute("SELECT * FROM handset WHERE id=?", (self.sam_h["id"],)).fetchone()
        self.assertEqual(rules.line_state(self.c, sam, self.NOON, off), "disconnected")
        sam2 = self.handset(self.sam, "sam2")                     # its sibling is unaffected
        self.assertEqual(rules.line_state(self.c, sam, self.NOON, sam2), "idle")

    def test_removed_handsets_do_not_ring(self):
        self.c.execute("UPDATE handset SET removed_at=? WHERE id=?", (db.iso(), self.alex_h["id"]))
        self.assertEqual(self.decide("2002").result, rules.OFFLINE)

    def test_repeat_limit(self):
        db.set_setting(self.c, "repeat_limit_count", 2)
        for _ in range(2):
            self.c.execute("INSERT INTO call(started_at,caller_treehouse,callee_treehouse,state,result) "
                           "VALUES(?,?,?,?,?)", (db.iso(self.NOON), self.sam, self.alex, "ended", "connected"))
        self.assertEqual(self.decide("2002").result, rules.REPEAT_LIMIT)

    def test_old_calls_do_not_count_toward_the_repeat_limit(self):
        db.set_setting(self.c, "repeat_limit_count", 1)
        self.c.execute("INSERT INTO call(started_at,caller_treehouse,callee_treehouse,state,result) "
                       "VALUES(?,?,?,?,?)", (db.iso(self.NOON - dt.timedelta(minutes=30)), self.sam,
                                             self.alex, "ended", "connected"))
        self.assertTrue(self.decide("2002").allowed)

    def test_blocked_retries_do_not_keep_the_repeat_limit_locked(self):
        db.set_setting(self.c, "repeat_limit_count", 2)
        for result in ("repeat_limit", "quiet_or_paused", "busy", "offline"):
            self.c.execute("INSERT INTO call(started_at,caller_treehouse,callee_treehouse,state,result) "
                           "VALUES(?,?,?,?,?)", (db.iso(self.NOON), self.sam, self.alex, "ended", result))
        self.assertTrue(self.decide("2002").allowed)

    def test_a_second_handset_cannot_start_another_call_on_a_busy_line(self):
        sam2 = self.handset(self.sam, "sam2")
        carol = house(self.c, "Carol's", "2004")
        self.string(self.sam, carol, "live")
        self.handset(carol, "carol")
        self.c.execute("INSERT INTO call(started_at,caller_treehouse,callee_treehouse,state) VALUES(?,?,?,?)",
                       (db.iso(), self.sam, self.alex, "active"))
        d = self.decide("2004", caller=sam2)
        self.assertEqual((d.result, d.reason), (rules.BUSY, "caller_in_use"))

    def test_unstrung_hunting_is_stopped_and_flagged(self):
        db.set_setting(self.c, "unstrung_limit_count", 3)
        for n in ("2900", "2901", "2902"):
            self.c.execute("INSERT INTO call(started_at,caller_treehouse,dialed,state,result) VALUES(?,?,?,?,?)",
                           (db.iso(self.NOON), self.sam, n, "ended", "not_in_service"))
        d = self.decide("2002")
        self.assertEqual((d.result, d.reason), (rules.REPEAT_LIMIT, "unstrung_limit"))
        self.assertEqual(d.notify_caller_parents[0], "unstrung_dials")

    def test_daily_minutes_count_both_directions(self):
        self.set(self.sam, daily_minutes=10)
        self.c.execute("INSERT INTO call(started_at,caller_treehouse,callee_treehouse,state,result,talk_sec) "
                       "VALUES(?,?,?,?,?,?)", (db.iso(self.NOON), self.alex, self.sam, "ended", "connected", 600))
        self.assertEqual(self.decide("2002").result, rules.DAILY_LIMIT)

    def test_daily_limit_on_the_other_line_uses_the_gentle_message(self):
        self.set(self.alex, daily_minutes=5)
        self.c.execute("INSERT INTO call(started_at,caller_treehouse,callee_treehouse,state,result,talk_sec) "
                       "VALUES(?,?,?,?,?,?)", (db.iso(self.NOON), self.sam, self.alex, "ended", "connected", 400))
        d = self.decide("2002")
        self.assertEqual((d.result, d.sound), (rules.QUIET_OR_PAUSED, rules.SOUND_NOT_TAKING_CALLS))

    def test_daily_minutes_reset_at_local_midnight(self):
        self.set(self.sam, daily_minutes=1)
        # 11:30 pm Pacific the night before is not "today" at noon.
        self.c.execute("INSERT INTO call(started_at,caller_treehouse,callee_treehouse,state,result,talk_sec) "
                       "VALUES(?,?,?,?,?,?)", (db.iso(utc(2026, 11, 18, 7, 30)), self.sam, self.alex,
                                               "ended", "connected", 3000))
        self.assertTrue(self.decide("2002").allowed)

    def test_call_limit_is_the_shortest_of_everything(self):
        self.set(self.sam, max_call_minutes=30)
        self.set(self.alex, max_call_minutes=20, daily_minutes=10)
        sam, alex = db.get_treehouse(self.c, self.sam), db.get_treehouse(self.c, self.alex)
        self.assertEqual(rules.call_limit_seconds(self.c, sam, alex, self.NOON), 600)
        self.c.execute("INSERT INTO call(started_at,caller_treehouse,callee_treehouse,state,result,talk_sec) "
                       "VALUES(?,?,?,?,?,?)", (db.iso(self.NOON), self.alex, self.sam, "ended", "connected", 420))
        self.assertEqual(rules.call_limit_seconds(self.c, sam, alex, self.NOON), 180)

    def test_line_state(self):
        sam = db.get_treehouse(self.c, self.sam)
        self.assertEqual(rules.line_state(self.c, sam, self.NOON), "idle")
        cur = self.c.execute("INSERT INTO call(started_at,caller_treehouse,callee_treehouse,state) VALUES(?,?,?,?)",
                             (db.iso(), self.sam, self.alex, "ringing"))
        self.assertEqual(rules.line_state(self.c, sam, self.NOON), "ringing")
        self.c.execute("UPDATE call SET state='active' WHERE id=?", (cur.lastrowid,))
        self.assertEqual(rules.line_state(self.c, sam, self.NOON), "in_call")
        self.set(self.sam, paused=1)
        self.assertEqual(rules.line_state(self.c, db.get_treehouse(self.c, self.sam), self.NOON), "quiet")


class Numbers(unittest.TestCase):
    def test_numbers_are_four_digits_and_never_start_with_zero(self):
        c = helpers.fresh_conn()
        for _ in range(200):
            n = db.assign_number(c)
            self.assertRegex(n, r"^[1-9]\d{3}$")

    def test_a_released_number_can_be_claimed_right_away(self):
        c = helpers.fresh_conn()
        tid = db.create_treehouse(c, "x", number="4321")
        self.assertFalse(db.number_is_free(c, "4321"))                       # taken while it is someone's
        db.leave_treehouse(c, tid)
        self.assertTrue(db.number_is_free(c, "4321"))                        # and free the moment it is let go
        self.assertEqual(db.create_treehouse(c, "y", number="4321") is not None, True)


if __name__ == "__main__":
    unittest.main()
