"""Scripted test phones for Treeline.

Builds a small test world in the database (treehouses numbered 0101-0105,
a range real families never get), starts fake handsets (baresip, no sound
card needed), makes real SIP calls through Asterisk and the control app,
and checks the call audit to confirm each call went the way the rules say.

Usage:
  python3 run_scenarios.py                # run every scenario
  python3 run_scenarios.py --list         # list scenarios
  python3 run_scenarios.py dial_by_number # run one

Environment:
  SIP_SERVER   address of Asterisk (default 127.0.0.1)
  TREELINE_DB  the database the control app uses (default /data/treeline.db)
"""

import datetime as dt
import math
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import wave
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from treeline import ari as ari_mod  # noqa: E402
from treeline import db, households, pjsip  # noqa: E402

SERVER = os.environ.get("SIP_SERVER", "127.0.0.1")
TZ = "America/Los_Angeles"

# name -> (number, [handset names]); one fake handset per name.
HOUSES = {
    "sam": ("0101", ["sam", "sam2"]),
    "alex": ("0102", ["alex", "alex2"]),
    "riley": ("0103", ["riley"]),
    "grandma": ("0104", ["grandma"]),
}
STRINGS = [("sam", "alex", "live"), ("sam", "grandma", "live"),
           ("alex", "grandma", "live"), ("sam", "riley", "waiting")]

CONFIG_TEMPLATE = """\
sip_listen 0.0.0.0:{port}
audio_player aubridge,sink{n}
audio_source aufile,{tone}
audio_alert aubridge,alert{n}
module_path /usr/lib/baresip/modules
module g711.so
module aufile.so
module aubridge.so
module_app account.so
module_app menu.so
"""

_port = [15100]


def make_tone(path, seconds=90, freq=440, rate=8000):
    """A plain 8 kHz test tone that stands in for a kid talking."""
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(
            struct.pack("<h", int(8000 * math.sin(2 * math.pi * freq * i / rate)))
            for i in range(seconds * rate)))


# ---------------------------------------------------------------- the world

class World:
    def __init__(self):
        self.conn = db.connect()
        self.ari = ari_mod.Ari()
        self.house = {}      # name -> treehouse id
        self.handset = {}    # name -> (handset id, sip_user, secret)

    def build(self):
        self.destroy()
        for name, (number, handsets) in HOUSES.items():
            self.house[name] = db.create_treehouse(
                self.conn, f"{name} test", number=number, timezone=TZ, quiet_enabled=0)
            households.create(self.house[name], ack_911=True)
            for h in handsets:
                hid, user, secret = db.create_handset(
                    self.conn, self.house[name], "ata", h, secret=f"test-{h}")
                self.handset[h] = (hid, user, secret)
        for a, b, state in STRINGS:
            x, y = db.ordered(self.house[a], self.house[b])
            self.conn.execute(
                "INSERT INTO string(a_id,b_id,state,created_at,updated_at) VALUES(?,?,?,?,?)",
                (x, y, state, db.iso(), db.iso()))
        pjsip.write(self.conn, client=self.ari)
        time.sleep(1.5)

    def destroy(self):
        ids = [r[0] for r in self.conn.execute(
            "SELECT id FROM treehouse WHERE number LIKE '01%' AND system=0")]
        for tid in ids:
            self.conn.execute("DELETE FROM call_event WHERE call_id IN "
                              "(SELECT id FROM call WHERE caller_treehouse=? OR callee_treehouse=?)", (tid, tid))
            for sql in ("DELETE FROM call WHERE caller_treehouse=? OR callee_treehouse=?",
                        "DELETE FROM string WHERE a_id=? OR b_id=?"):
                self.conn.execute(sql, (tid, tid))
            self.conn.execute("DELETE FROM handset WHERE treehouse_id=?", (tid,))
            self.conn.execute("DELETE FROM treehouse WHERE id=?", (tid,))
            households.remove(tid)
        pjsip.write(self.conn, client=self.ari)

    def reset(self):
        """Back to a clean slate between scenarios."""
        self.conn.execute("UPDATE handset SET disabled=0 WHERE treehouse_id IN (%s)" % ",".join(str(i) for i in self.house.values()))
        for tid in self.house.values():
            self.conn.execute(
                "UPDATE treehouse SET quiet_enabled=0, paused=0, max_call_minutes=30, daily_minutes=NULL "
                "WHERE id=?", (tid,))
            h = households.conn(tid)            # each test family's own file: back to empty (call_event goes with call_log)
            for table in ("notice", "call_log", "parent_action"):
                h.execute(f"DELETE FROM {table}")
        ids = ",".join(str(i) for i in self.house.values())
        where = f"caller_treehouse IN ({ids}) OR callee_treehouse IN ({ids})"
        self.conn.execute(f"DELETE FROM call_event WHERE call_id IN (SELECT id FROM call WHERE {where})")
        self.conn.execute(f"DELETE FROM call WHERE {where}")
        self.conn.execute("DELETE FROM setting")

    def set(self, house, **cols):
        sets = ",".join(f"{k}=?" for k in cols)
        self.conn.execute(f"UPDATE treehouse SET {sets} WHERE id=?", (*cols.values(), self.house[house]))

    def _mine(self):
        """SQL that limits a query to calls involving this test world. The dev database may hold real
        families too (someone trying the app while the tests run), and their calls aren't ours."""
        ids = ",".join(str(i) for i in self.house.values())
        return f"(caller_treehouse IN ({ids}) OR callee_treehouse IN ({ids}))"

    def calls(self):
        return self.conn.execute(f"SELECT * FROM call WHERE {self._mine()} ORDER BY id").fetchall()

    def newest(self):
        return self.conn.execute(f"SELECT * FROM call WHERE {self._mine()} ORDER BY id DESC LIMIT 1").fetchone()

    def last_call(self, wait=20):
        """The newest of our calls once it has ended."""
        deadline = time.time() + wait
        while time.time() < deadline:
            row = self.newest()
            if row and row["state"] == "ended" and row["logged"]:       # ended, and copied into the families' files
                return row
            time.sleep(0.4)
        return self.newest()

    def hh(self, name):
        """A test family's own file (the control app writes to it too: a different process)."""
        return households.conn(self.house[name])

    def copies(self, name):
        return self.hh(name).execute("SELECT * FROM call_log ORDER BY id").fetchall()

    def notes(self, name, kind=None):
        sql, args = "SELECT * FROM notice WHERE dismissed_at IS NULL", ()
        if kind:
            sql, args = sql + " AND kind=?", (kind,)
        return self.hh(name).execute(sql, args).fetchall()

    def events(self, call_id):
        return [r["event"] for r in self.conn.execute(
            "SELECT event FROM call_event WHERE call_id=? ORDER BY id", (call_id,))]

    def wait_online(self, users, timeout=20):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if set(users) <= (self.ari.online_users() or set()):
                return True
            time.sleep(0.5)
        return False


class FakePhone:
    """One baresip process registered as a handset."""

    def __init__(self, world, name, workdir, auto_answer=True):
        self.world, self.name = world, name
        _, self.user, secret = world.handset[name]
        self.dir = os.path.join(workdir, name)
        os.makedirs(self.dir, exist_ok=True)
        _port[0] += 10
        tone = os.path.join(self.dir, "tone.wav")
        make_tone(tone)
        with open(os.path.join(self.dir, "config"), "w") as f:
            f.write(CONFIG_TEMPLATE.format(port=_port[0], n=name, tone=tone))
        answer = ";answermode=auto" if auto_answer else ""
        with open(os.path.join(self.dir, "accounts"), "w") as f:
            f.write(f"<sip:{self.user}@{SERVER}>;auth_pass={secret}{answer}\n")
        self.proc = None

    def start(self, dial=None, run_for=None):
        cmd = ["baresip", "-4", "-f", self.dir]
        if dial:
            cmd += ["-e", f"/dial {dial}"]
        if run_for:
            cmd += ["-t", str(run_for)]
        log = open(os.path.join(self.dir, "baresip.log"), "w")
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT)
        return self

    def wait(self):
        try:
            self.proc.wait(timeout=120)
        except subprocess.TimeoutExpired:
            self.stop()

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()


class Session:
    """Fake handsets for one scenario, cleaned up afterwards."""

    def __init__(self, world):
        self.world = world
        self.dir = tempfile.mkdtemp(prefix="treeline-")
        self.phones = []

    def answering(self, *names):
        phones = [FakePhone(self.world, n, self.dir).start() for n in names]
        self.phones += phones
        self.world.wait_online([p.user for p in phones])
        return phones

    def ringing(self, name):
        """Registered but never picks up."""
        p = FakePhone(self.world, name, self.dir, auto_answer=False).start()
        self.phones.append(p)
        self.world.wait_online([p.user])
        return p

    def dial(self, name, number, seconds=6, wait=True):
        p = FakePhone(self.world, name, self.dir, auto_answer=False)
        p.start(dial=number, run_for=seconds + 4)
        self.phones.append(p)
        if wait:
            p.wait()
        return p

    def close(self):
        for p in self.phones:
            p.stop()
        shutil.rmtree(self.dir, ignore_errors=True)


def call_and_check(world, caller, number, callee_handsets=(), seconds=6):
    s = Session(world)
    try:
        if callee_handsets:
            s.answering(*callee_handsets)
        s.dial(caller, number, seconds=seconds)
        return world.last_call()
    finally:
        s.close()


# ---------------------------------------------------------------- scenarios

def dial_by_number(w):
    """Sam dials Alex's number; both houses approved the string, so it connects."""
    c = call_and_check(w, "sam", "0102", ["alex"])
    ev = w.events(c["id"])
    # Both families have their own copy, written by the control app when the call ended; neither holds the other's phones.
    mine, theirs = w.copies("sam"), w.copies("alex")
    sam_h, alex_h = w.handset["sam"][0], w.handset["alex"][0]
    copies_ok = (
        [r["id"] for r in mine] == [c["id"]] and [r["id"] for r in theirs] == [c["id"]]
        and mine[0]["answered_handset"] is None and theirs[0]["caller_handset"] is None
        and mine[0]["caller_handset"] == sam_h and theirs[0]["answered_handset"] == alex_h
        and "rang" in [e["event"] for e in w.hh("alex").execute("SELECT * FROM call_event WHERE theirs=0")]
        and all(e["handset_id"] in (None, sam_h) for e in w.hh("sam").execute("SELECT * FROM call_event")))
    return (c["result"] == "connected" and c["talk_sec"] >= 2 and copies_ok and
            ev[:1] == ["dialed"] and "rang" in ev and "answered" in ev and ev[-1] == "ended"), \
        {"call": dict(c), "sam": [dict(r) for r in mine], "alex": [dict(r) for r in theirs]}


def not_in_service(w):
    """Sam dials a number nobody has."""
    c = call_and_check(w, "sam", "0199")
    return c["result"] == "not_in_service" and [r["id"] for r in w.copies("sam")] == [c["id"]], dict(c)


def not_strung(w):
    """Riley dials Sam, but the string isn't live yet: blocked, and Riley's parents get a note."""
    c = call_and_check(w, "riley", "0101", ["sam"])
    notes = w.notes("riley")
    mine = w.copies("riley")
    # Riley's family keeps the attempt (without whose number it was); Sam's family never hears of it.
    return (c["result"] == "not_strung" and len(notes) == 1 and len(mine) == 1 and mine[0]["callee_treehouse"] is None
            and mine[0]["dialed"] == "0101" and w.copies("sam") == [] and w.notes("sam") == []), dict(c)


def no_911(w):
    """Dialing 911 gets the message that this phone can't call 911, and the parents get a note on Home at once
    (the alert job then emails them and pushes). A second try in the same hour doesn't pile up a second note."""
    w.hh("sam").execute("DELETE FROM notice WHERE kind='no_911'")
    c = call_and_check(w, "sam", "911")
    c2 = call_and_check(w, "sam", "911")
    notes = w.notes("sam", "no_911")
    ok = (c["result"] == "no_911" and c2["result"] == "no_911" and len(notes) == 1
          and "911" in notes[0]["title"] and "dialed 911" in notes[0]["body"]
          and len(w.copies("sam")) == 2 and all(w.copies(n) == [] for n in ("alex", "grandma", "riley")))
    return ok, {"calls": [dict(c), dict(c2)], "notes": [dict(n) for n in notes]}


def incomplete_number(w):
    """A number that isn't four digits 'cannot be completed as dialed', not the 911 message."""
    c1 = call_and_check(w, "sam", "12")
    c2 = call_and_check(w, "sam", "01020")
    return (c1["result"] == "incomplete" and c2["result"] == "incomplete"), [dict(c1), dict(c2)]


def callee_paused(w):
    """Alex's line is paused: Sam is blocked."""
    w.set("alex", paused=1)
    c = call_and_check(w, "sam", "0102", ["alex"])
    # Alex's family sees why (their own pause); Sam's family is told only that Alex's line isn't taking calls.
    mine, theirs = w.copies("sam"), w.copies("alex")
    ok = (c["result"] == "quiet_or_paused" and c["reason"] == "callee_paused"
          and [r["reason"] for r in mine] == ["callee_unavailable"] and [r["reason"] for r in theirs] == ["callee_paused"])
    return ok, {"call": dict(c), "sam": [dict(r) for r in mine], "alex": [dict(r) for r in theirs]}


def caller_quiet_hours(w):
    """Sam's own quiet hours cover right now: blocked on Sam's side."""
    now = dt.datetime.now(ZoneInfo(TZ))
    w.set("sam", quiet_enabled=1,
          quiet_start=(now - dt.timedelta(hours=1)).strftime("%H:%M"),
          quiet_end=(now + dt.timedelta(hours=1)).strftime("%H:%M"))
    c = call_and_check(w, "sam", "0102", ["alex"])
    # Sam's own quiet hours are Sam's business: Alex's family has no record of the attempt.
    return (c["result"] == "quiet_or_paused" and c["reason"] == "caller_quiet"
            and len(w.copies("sam")) == 1 and w.copies("alex") == []), dict(c)


def callee_quiet_hours(w):
    """Alex's quiet hours cover right now: Sam is blocked."""
    now = dt.datetime.now(ZoneInfo(TZ))
    w.set("alex", quiet_enabled=1,
          quiet_start=(now - dt.timedelta(hours=1)).strftime("%H:%M"),
          quiet_end=(now + dt.timedelta(hours=1)).strftime("%H:%M"))
    c = call_and_check(w, "sam", "0102", ["alex"])
    return (c["result"] == "quiet_or_paused" and c["reason"] == "callee_quiet"
            and [r["reason"] for r in w.copies("sam")] == ["callee_unavailable"]
            and [r["reason"] for r in w.copies("alex")] == ["callee_quiet"]), dict(c)


def busy_line(w):
    """Alex is on a call with Sam; Grandma calls Alex and gets a busy signal."""
    s = Session(w)
    try:
        s.answering("alex")
        s.dial("sam", "0102", seconds=14, wait=False)
        time.sleep(6)
        s.dial("grandma", "0102", seconds=3)
        rows = w.conn.execute("SELECT * FROM call WHERE caller_treehouse=?",
                              (w.house["grandma"],)).fetchall()
        s.phones[1].wait()
        return len(rows) == 1 and rows[0]["result"] == "busy", [dict(r) for r in rows]
    finally:
        s.close()


def callee_offline(w):
    """Nothing on Alex's line is registered: fast busy."""
    c = call_and_check(w, "sam", "0102")
    return c["result"] == "offline", dict(c)


def _channels_of(w, user):
    return [c for c in (w.ari.request("GET", "/channels") or []) if c.get("name", "").startswith(f"PJSIP/{user}-")]


def busy_tone_plays_until_hangup(w):
    """A busy / fast-busy tone is not cut off after a few seconds: the caller's line is still up, still hearing it, well past the old
    4 s limit, and it ends when the caller hangs up (nobody is on Alex's line, so Sam gets fast busy)."""
    s = Session(w)
    try:
        p = s.dial("sam", "0102", seconds=10, wait=False)
        time.sleep(7.5)
        still = len(_channels_of(w, p.user))
        p.stop()
        time.sleep(2.5)
        after = len(_channels_of(w, p.user))
        return still == 1 and after == 0, {"line_up_at_7_5s": still, "line_up_after_hangup": after}
    finally:
        s.close()


def ring_timeout(w):
    """Alex's phone rings and nobody answers: a missed call after the ring timeout."""
    db.set_setting(w.conn, "ring_timeout_sec", 5)
    s = Session(w)
    try:
        s.ringing("alex")
        s.dial("sam", "0102", seconds=14)
        c = w.last_call()
        return c["result"] == "no_answer", dict(c)
    finally:
        s.close()


def time_limit(w):
    """A 9-second call limit cuts the call off on time."""
    w.set("sam", max_call_minutes=0.15)
    c = call_and_check(w, "sam", "0102", ["alex"], seconds=22)
    return c["result"] == "time_limit" and 6 <= c["talk_sec"] <= 12, dict(c)


def repeat_limit(w):
    """Too many calls to the same treehouse in a short time are stopped."""
    db.set_setting(w.conn, "repeat_limit_count", 2)
    for _ in range(2):
        w.conn.execute("INSERT INTO call(started_at,caller_treehouse,callee_treehouse,dialed,state,result,logged)"
                       " VALUES(?,?,?,?,?,?,1)", (db.iso(), w.house["sam"], w.house["alex"], "0102",
                                                  "ended", "connected"))
    c = call_and_check(w, "sam", "0102", ["alex"])
    return c["result"] == "repeat_limit", dict(c)


def unstrung_hunting(w):
    """A kid trying lots of numbers that aren't strung is stopped, and parents are told."""
    db.set_setting(w.conn, "unstrung_limit_count", 3)
    for n in ("0190", "0191", "0192"):
        w.conn.execute("INSERT INTO call(started_at,caller_treehouse,dialed,state,result,logged)"
                       " VALUES(?,?,?,?,?,1)", (db.iso(), w.house["sam"], n, "ended", "not_in_service"))
    c = call_and_check(w, "sam", "0102", ["alex"])
    notes = w.notes("sam", "unstrung_dials")
    return (c["result"] == "repeat_limit" and c["reason"] == "unstrung_limit" and len(notes) == 1
            and w.copies("alex") == []), dict(c)


def daily_minutes(w):
    """Sam used up today's minutes: blocked."""
    w.set("sam", daily_minutes=1)
    w.conn.execute("INSERT INTO call(started_at,caller_treehouse,callee_treehouse,dialed,state,result,talk_sec,logged)"
                   " VALUES(?,?,?,?,?,?,?,1)", (db.iso(), w.house["sam"], w.house["alex"], "0102",
                                                "ended", "connected", 120))
    c = call_and_check(w, "sam", "0102", ["alex"])
    return c["result"] == "daily_limit", dict(c)


def shared_line(w):
    """Both of Alex's handsets ring; one answers and the other stops ringing."""
    c = call_and_check(w, "sam", "0102", ["alex", "alex2"])
    ev = w.events(c["id"])
    return c["result"] == "connected" and ev.count("rang") == 2 and ev.count("answered") == 1, \
        {"call": dict(c), "events": ev}


def join_mid_call(w):
    """A second handset on Sam's line picks up mid-call and joins; everyone hears the join tone."""
    s = Session(w)
    try:
        s.answering("alex")
        s.dial("sam", "0102", seconds=16, wait=False)
        time.sleep(7)
        s.dial("sam2", "0001", seconds=4, wait=False)
        time.sleep(5)
        cid = w.newest()["id"]
        ev = w.events(cid)
        for p in s.phones:
            p.wait()
        c = w.last_call()
        return "joined" in ev and c["result"] == "connected", {"events": w.events(cid), "call": dict(c)}
    finally:
        s.close()


def disconnected_phone_is_skipped(w):
    """Alex disconnects one of his two phones: only the other one rings, and it can take the call."""
    w.conn.execute("UPDATE handset SET disabled=1 WHERE id=?", (w.handset["alex"][0],))
    c = call_and_check(w, "sam", "0102", ["alex", "alex2"])
    ev = w.conn.execute("SELECT handset_id FROM call_event WHERE call_id=? AND event='rang'", (c["id"],)).fetchall()
    return (c["result"] == "connected" and [r["handset_id"] for r in ev] == [w.handset["alex2"][0]]), \
        {"call": dict(c), "rang": [r["handset_id"] for r in ev]}


def every_phone_disconnected(w):
    """Both of Alex's phones are disconnected: the line is simply offline, as if nothing were plugged in."""
    for name in ("alex", "alex2"):
        w.conn.execute("UPDATE handset SET disabled=1 WHERE id=?", (w.handset[name][0],))
    c = call_and_check(w, "sam", "0102", ["alex", "alex2"])
    return c["result"] == "offline", dict(c)


def disconnected_phone_cannot_call(w):
    """A disconnected phone gets fast busy when it dials, even to a friend who is home."""
    w.conn.execute("UPDATE handset SET disabled=1 WHERE id=?", (w.handset["sam"][0],))
    c = call_and_check(w, "sam", "0102", ["alex"])
    return c["result"] == "disconnected" and c["reason"] == "caller_phone_off", dict(c)


def join_with_no_call(w):
    """Dialing 0001 with no call in progress just gets a fast busy."""
    s = Session(w)
    try:
        s.dial("sam2", "0001", seconds=3)
        return len(w.calls()) == 0, [dict(r) for r in w.calls()]
    finally:
        s.close()


SCENARIOS = [dial_by_number, not_in_service, not_strung, no_911, incomplete_number, callee_paused,
             caller_quiet_hours, callee_quiet_hours, busy_line, busy_tone_plays_until_hangup, callee_offline,
             ring_timeout, time_limit, repeat_limit, unstrung_hunting, daily_minutes,
             shared_line, join_mid_call, join_with_no_call, disconnected_phone_is_skipped,
             every_phone_disconnected, disconnected_phone_cannot_call]


def main(argv):
    if "--list" in argv:
        for s in SCENARIOS:
            print(f"{s.__name__:20} {s.__doc__}")
        return 0
    chosen = [s for s in SCENARIOS if not argv or s.__name__ in argv]
    world = World()
    world.build()
    failures = 0
    try:
        for s in chosen:
            world.reset()
            ok, detail = s(world)
            failures += not ok
            print(f"[{'PASS' if ok else 'FAIL'}] {s.__name__}: {s.__doc__}", flush=True)
            if not ok:
                print(f"        {detail}", flush=True)
    finally:
        world.reset()
        world.destroy()
    print(f"\n{len(chosen) - failures}/{len(chosen)} scenarios passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
