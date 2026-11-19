"""Call history: the central ledger and each family's own redacted copy (docs/DATA_LAYER.md)."""
import datetime as dt
import os
import unittest
from unittest import mock

from tests import helpers
from treeline import calls, db, households, rules


def dump(tid):
    """Every row of every table in a household's file, as text: for asserting what is NOT in it."""
    return "\n".join(line for line in households.conn(tid).iterdump() if line.startswith("INSERT"))


def ledger(conn, caller, callee, result, reason=None, started=None, talk=0, dialed="9999", events=(), logged=0):
    """A finished call in the central ledger, as the engine leaves it. `events` are (event, handset_id)."""
    started = started or db.iso()
    cid = conn.execute(
        "INSERT INTO call(started_at,caller_treehouse,dialed,callee_treehouse,state,ended_at,talk_sec,result,reason,"
        "logged) VALUES(?,?,?,?,?,?,?,?,?,?)", (started, caller, dialed, callee, "ended", started, talk, result, reason, logged)).lastrowid
    for event, hid in events:
        conn.execute("INSERT INTO call_event(call_id,at,handset_id,event) VALUES(?,?,?,?)", (cid, started, hid, event))
    return cid


class World(unittest.TestCase):
    def setUp(self):
        self.c = helpers.fresh_conn()
        self.a = helpers.house(self.c, "Alex's", number="1111")
        self.b = helpers.house(self.c, "Sam's", number="2222")
        self.ah = db.create_handset(self.c, self.a, "ata", "A hall")[0]
        self.bh = db.create_handset(self.c, self.b, "ata", "B hall")[0]

    def log(self, tid):
        return households.conn(tid).execute("SELECT * FROM call_log ORDER BY id").fetchall()

    def events(self, tid):
        return households.conn(tid).execute("SELECT * FROM call_event ORDER BY id").fetchall()

    def logged(self, cid):
        return self.c.execute("SELECT logged FROM call WHERE id=?", (cid,)).fetchone()[0]


class Copies(World):
    def test_a_finished_call_is_copied_to_both_families_and_marked_logged(self):
        cid = ledger(self.c, self.a, self.b, rules.CONNECTED, talk=90,
                     events=[("dialed", self.ah), ("rang", self.bh), ("answered", self.bh), ("ended", None)])
        households.record_call(self.c, cid)
        for tid in (self.a, self.b):
            rows = self.log(tid)
            self.assertEqual([(r["id"], r["result"], r["talk_sec"]) for r in rows], [(cid, "connected", 90)])
            self.assertEqual([e["event"] for e in self.events(tid)], ["dialed", "rang", "answered", "ended"])
        self.assertEqual(self.logged(cid), 1)

    def test_writing_it_again_changes_nothing(self):
        cid = ledger(self.c, self.a, self.b, rules.CONNECTED, events=[("dialed", self.ah), ("ended", None)])
        households.record_call(self.c, cid)
        households.record_call(self.c, cid)
        self.assertEqual([len(self.log(t)) for t in (self.a, self.b)], [1, 1])
        self.assertEqual([len(self.events(t)) for t in (self.a, self.b)], [2, 2])

    def test_a_call_still_in_progress_is_not_copied(self):
        cid = self.c.execute("INSERT INTO call(started_at,caller_treehouse,callee_treehouse,state) VALUES(?,?,?,?)",
                             (db.iso(), self.a, self.b, "active")).lastrowid
        self.assertFalse(households.record_call(self.c, cid))
        self.assertEqual(self.log(self.a), [])

    def test_a_household_with_no_file_is_skipped_and_the_other_still_gets_its_copy(self):
        cid = ledger(self.c, self.a, self.b, rules.CONNECTED)
        households.remove(self.b)
        households.record_call(self.c, cid)
        self.assertEqual(len(self.log(self.a)), 1)
        self.assertEqual(self.logged(cid), 1)

    def test_a_write_that_fails_leaves_the_call_unlogged_and_the_next_try_completes_it(self):
        cid = ledger(self.c, self.a, self.b, rules.CONNECTED)
        real = households._write_copy
        calls_made = []

        def flaky(tid, *a, **kw):
            calls_made.append(tid)
            if tid == self.b:
                raise RuntimeError("disk hiccup")
            return real(tid, *a, **kw)
        with mock.patch.object(households, "_write_copy", flaky):
            with self.assertRaises(RuntimeError):
                households.record_call(self.c, cid)
        self.assertEqual((self.logged(cid), len(self.log(self.a)), len(self.log(self.b))), (0, 1, 0))
        households.record_call(self.c, cid)                                # the retry: A's is a no-op, B's is new
        self.assertEqual((self.logged(cid), len(self.log(self.a)), len(self.log(self.b))), (1, 1, 1))

    def test_a_call_already_past_a_familys_retention_is_not_brought_back(self):
        households.set_retention(self.a, 7)
        old = db.iso(db.utcnow() - dt.timedelta(days=20))
        cid = ledger(self.c, self.a, self.b, rules.CONNECTED, started=old)
        households.record_call(self.c, cid)
        self.assertEqual((len(self.log(self.a)), len(self.log(self.b))), (0, 1))
        self.assertEqual(self.logged(cid), 1)


class Resilience(World):
    def test_one_familys_damaged_file_does_not_keep_the_other_family_from_its_copy(self):
        households.forget_all()
        open(households.path(self.a), "wb").write(b"not a database at all, not even close, " * 50)   # the caller's file is damaged
        cid = ledger(self.c, self.a, self.b, rules.CONNECTED, talk=5)
        with self.assertLogs("treeline", "ERROR"), self.assertRaises(Exception):
            households.record_call(self.c, cid)
        self.assertEqual(len(self.log(self.b)), 1)                      # the callee still has theirs
        self.assertEqual(self.logged(cid), 0)                           # and the call is retried later

    def test_reconcile_does_not_bring_back_a_household_deleted_after_it_read_the_rows(self):
        households.remove(self.b)
        real = self.c.execute("SELECT 1").connection

        class Stale:                                                    # the delete commits between the two reads
            def __init__(s):
                s.n = 0

            def execute(s, sql, *a):
                cur = real.execute(sql, *a)
                if sql.startswith("SELECT id, left_at"):
                    real.execute("UPDATE treehouse SET deleted_at=? WHERE id=?", (db.iso(), self.b))
                return cur
        done = households.reconcile(Stale())
        self.assertEqual(done["recreated"], [])
        self.assertFalse(households.exists(self.b))


class Isolation(World):
    """One family's file must never hold another family's blocked attempts, rules or handsets."""

    CALLER_SIDE = [                                    # attempts the callee must never hear of
        (rules.NOT_STRUNG, "no_live_string"), (rules.QUIET_OR_PAUSED, "caller_quiet"),
        (rules.QUIET_OR_PAUSED, "caller_paused"), (rules.DAILY_LIMIT, "caller_daily_limit"),
        (rules.BUSY, "caller_in_use"), (rules.DISCONNECTED, "caller_phone_off"),
        (rules.REPEAT_LIMIT, "unstrung_limit"), (rules.REPEAT_LIMIT, "repeat_limit"),
    ]

    def test_the_callees_file_has_none_of_the_callers_blocked_attempts_or_rules(self):
        ids = [ledger(self.c, self.a, self.b, result, reason, dialed="2222") for result, reason in self.CALLER_SIDE]
        ids += [ledger(self.c, self.a, None, rules.NO_911, "911", dialed="911"),
                ledger(self.c, self.a, None, rules.NOT_IN_SERVICE, "no_such_number", dialed="5555"),
                ledger(self.c, self.a, None, rules.INCOMPLETE, "wrong_length", dialed="12")]
        for cid in ids:
            households.record_call(self.c, cid)
        self.assertEqual(self.log(self.b), [])                           # not one row
        text = dump(self.b)
        for word in ("caller_", "no_live_string", "unstrung_limit", "repeat_limit", "no_911", "911", "5555", "wrong_length"):
            self.assertNotIn(word, text)
        self.assertEqual(len(self.log(self.a)), len(ids))                # their own attempts are their own record

    def test_the_callers_file_never_says_why_the_callee_would_not_take_the_call(self):
        for reason in ("callee_paused", "callee_quiet", "callee_daily_limit"):
            households.record_call(self.c, ledger(self.c, self.a, self.b, rules.QUIET_OR_PAUSED, reason, dialed="2222"))
        rows = self.log(self.a)
        self.assertEqual({r["reason"] for r in rows}, {"callee_unavailable"})
        text = dump(self.a)
        for word in ("callee_paused", "callee_quiet", "callee_daily_limit"):
            self.assertNotIn(word, text)
        self.assertEqual({r["reason"] for r in self.log(self.b)}, {"callee_paused", "callee_quiet", "callee_daily_limit"})   # B's own rules are B's to see

    def test_an_unstrung_dial_does_not_record_whose_number_it_was(self):
        households.record_call(self.c, ledger(self.c, self.a, self.b, rules.NOT_STRUNG, "no_live_string", dialed="2222"))
        row = self.log(self.a)[0]
        self.assertIsNone(row["callee_treehouse"])
        self.assertEqual(row["dialed"], "2222")                          # only what they typed themselves

    def test_neither_file_holds_the_other_familys_handset_ids(self):
        cid = ledger(self.c, self.a, self.b, rules.CONNECTED, talk=30,
                     events=[("dialed", self.ah), ("rang", self.bh), ("answered", self.bh), ("left", self.bh), ("pips", None)])
        self.c.execute("UPDATE call SET caller_handset=?, answered_handset=? WHERE id=?", (self.ah, self.bh, cid))
        households.record_call(self.c, cid)
        mine, theirs = {self.a: self.ah, self.b: self.bh}, {self.a: self.bh, self.b: self.ah}
        for tid in (self.a, self.b):
            row = self.log(tid)[0]
            self.assertNotIn(theirs[tid], (row["caller_handset"], row["answered_handset"]))
            seen = [(e["event"], e["handset_id"], e["theirs"]) for e in self.events(tid)]
            self.assertNotIn(theirs[tid], [h for _, h, _ in seen])
            self.assertEqual(sum(1 for _, _, t in seen if t), 3 if tid == self.a else 1)     # B's three events, A's one
            self.assertIn(mine[tid], [h for _, h, _ in seen])

    def test_a_calls_that_the_callee_may_see_reaches_them_with_their_own_view(self):
        households.record_call(self.c, ledger(self.c, self.a, self.b, rules.NO_ANSWER, "not_answered", dialed="2222"))
        households.record_call(self.c, ledger(self.c, self.a, self.b, rules.BUSY, "callee_in_use", dialed="2222"))
        self.assertEqual([r["result"] for r in self.log(self.b)], ["no_answer", "busy"])

    def test_the_read_path_checks_again(self):
        # If a row that should never be there did get into a household file, reading hides it.
        households.conn(self.b).execute(
            "INSERT INTO call_log(id,started_at,caller_treehouse,callee_treehouse,state,result,reason) VALUES(?,?,?,?,?,?,?)",
            (77, db.iso(), self.a, self.b, "ended", rules.QUIET_OR_PAUSED, "caller_quiet"))
        th = db.get_treehouse(self.c, self.b)
        self.assertEqual(households.call_page(self.b, th)[0], [])


class Trimming(World):
    def test_lowering_retention_trims_that_family_at_once_and_only_that_family(self):
        old = db.iso(db.utcnow() - dt.timedelta(days=30))
        cid = ledger(self.c, self.a, self.b, rules.CONNECTED, started=old, events=[("dialed", self.ah), ("rang", self.bh)])
        households.record_call(self.c, cid)
        households.set_retention(self.a, 7)
        self.assertEqual(households.trim(self.a), 1)
        self.assertEqual((len(self.log(self.a)), len(self.events(self.a))), (0, 0))      # the events went with the call
        self.assertEqual((len(self.log(self.b)), len(self.events(self.b))), (1, 2))      # Sam's copy is untouched

    def test_trim_is_idempotent_and_keeps_what_is_inside_retention(self):
        keep = ledger(self.c, self.a, self.b, rules.CONNECTED, started=db.iso(db.utcnow() - dt.timedelta(days=5)))
        households.record_call(self.c, keep)
        self.assertEqual((households.trim(self.a), households.trim(self.a)), (0, 0))
        self.assertEqual(len(self.log(self.a)), 1)


class LedgerPruning(World):
    def test_old_logged_calls_leave_the_ledger_unlogged_ones_stay(self):
        old = db.iso(db.utcnow() - dt.timedelta(days=db.LEDGER_DAYS + 1))
        done = ledger(self.c, self.a, self.b, rules.CONNECTED, started=old, events=[("dialed", self.ah)], logged=1)
        waiting = ledger(self.c, self.a, self.b, rules.CONNECTED, started=old, logged=0)
        fresh = ledger(self.c, self.a, self.b, rules.CONNECTED, logged=1)
        db.prune_ledger(self.c)
        left = {r[0] for r in self.c.execute("SELECT id FROM call")}
        self.assertEqual(left, {waiting, fresh})
        self.assertEqual(self.c.execute("SELECT count(*) FROM call_event WHERE call_id=?", (done,)).fetchone()[0], 0)


class Reconcile(World):
    def test_a_crash_after_the_ledger_update_is_repaired(self):
        cid = ledger(self.c, self.a, self.b, rules.CONNECTED, talk=10, events=[("dialed", self.ah)])    # ended, never copied
        self.assertEqual(self.log(self.a), [])
        done = households.reconcile(self.c)
        self.assertEqual(done["logged"], 1)
        self.assertEqual((len(self.log(self.a)), len(self.log(self.b)), self.logged(cid)), (1, 1, 1))
        self.assertEqual(households.reconcile(self.c)["logged"], 0)                                    # and it is done

    def test_files_with_no_treehouse_are_removed_but_not_while_a_create_may_be_in_flight(self):
        households.create(900)                                  # no central row (yet): the API's create, mid-transaction
        households.create(901)
        old = dt.datetime.now(dt.timezone.utc).timestamp() - 2 * 3600
        os.utime(households.path(901), (old, old))               # one has sat there for hours: a crash left it
        done = households.reconcile(self.c)
        self.assertEqual(done["orphans"], [901])
        self.assertTrue(households.exists(900))
        self.assertTrue(households.exists(self.a))               # real households are never touched

    def test_a_deleted_treehouses_file_is_removed_at_once(self):
        self.c.execute("UPDATE treehouse SET deleted_at=? WHERE id=?", (db.iso(), self.b))
        households.reconcile(self.c)
        self.assertFalse(households.exists(self.b))
        self.assertTrue(households.exists(self.a))

    def test_an_active_treehouse_with_no_file_gets_an_empty_one_without_consent(self):
        households.remove(self.b)                                # central restored from a backup, files lost
        with self.assertLogs("treeline", "WARNING"):
            done = households.reconcile(self.c)
        self.assertEqual(done["recreated"], [self.b])
        meta = households.meta(self.b)
        self.assertEqual((meta["retention_days"], meta["consent_at"], meta["ack_911"]), (90, None, 0))

    def test_left_and_system_treehouses_are_not_given_a_file(self):
        left = self.c.execute("INSERT INTO treehouse(name,created_at,left_at) VALUES('Left',?,?)", (db.iso(), db.iso())).lastrowid
        system = db.create_treehouse(self.c, "Join line", number="0001", system=True)
        done = households.reconcile(self.c)
        self.assertEqual(done["recreated"], [])
        self.assertFalse(households.exists(left) or households.exists(system))

    def test_a_household_that_left_is_kept_until_past_retention_then_removed(self):
        now = db.utcnow()
        self.c.execute("UPDATE treehouse SET left_at=?, number=NULL WHERE id=?", (db.iso(now - dt.timedelta(days=60)), self.a))
        households.set_retention(self.a, 90)
        self.assertEqual(households.purge_left(self.c, now), [])                  # 60 days in, 90 kept
        self.assertTrue(households.exists(self.a))
        self.assertEqual(households.purge_left(self.c, now + dt.timedelta(days=31)), [self.a])
        self.assertFalse(households.exists(self.a))
        self.assertTrue(households.exists(self.b))

    def test_a_left_household_with_a_record_after_it_left_waits_for_that_record(self):
        now = db.utcnow()
        self.c.execute("UPDATE treehouse SET left_at=?, number=NULL WHERE id=?", (db.iso(now - dt.timedelta(days=100)), self.a))
        households.set_retention(self.a, 30)
        households.add_notice(self.a, "x", "a record from just now")               # something is newer than the leaving
        self.assertEqual(households.purge_left(self.c, now), [])
        self.assertTrue(households.exists(self.a))

    def test_stray_wal_files_and_old_copies_for_a_household_that_is_gone_are_removed(self):
        old = dt.datetime.now(dt.timezone.utc).timestamp() - 2 * 3600
        os.makedirs(households.pre_migrate_dir(), exist_ok=True)
        strays = [os.path.join(households.root(), "950.db-wal"), os.path.join(households.pre_migrate_dir(), "950-v1-20261101T000000-abc123.db")]
        mine = os.path.join(households.pre_migrate_dir(), f"{self.a}-v1-20261101T000000-abc123.db")
        for p in strays + [mine]:
            open(p, "w").close()
            os.utime(p, (old, old))
        households.reconcile(self.c)
        self.assertEqual([os.path.exists(p) for p in strays + [mine]], [False, False, True])


if __name__ == "__main__":
    unittest.main()
