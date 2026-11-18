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
from treeline import db, pjsip  # noqa: E402

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
                self.conn, f"{name} test", number=number, timezone=TZ,
                quiet_enabled=0, ack_911=1)
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
            self.conn.execute("DELETE FROM notice WHERE treehouse_id=?", (tid,))
            self.conn.execute("DELETE FROM treehouse WHERE id=?", (tid,))
        pjsip.write(self.conn, client=self.ari)

    def reset(self):
        """Back to a clean slate between scenarios."""
        self.conn.execute("UPDATE handset SET disabled=0 WHERE treehouse_id IN (%s)" % ",".join(str(i) for i in self.house.values()))
        for tid in self.house.values():
            self.conn.execute(
                "UPDATE treehouse SET quiet_enabled=0, paused=0, max_call_minutes=30, daily_minutes=NULL "
                "WHERE id=?", (tid,))
            self.conn.execute("DELETE FROM notice WHERE treehouse_id=?", (tid,))
        ids = ",".join(str(i) for i in self.house.values())
        where = f"caller_treehouse IN ({ids}) OR callee_treehouse IN ({ids})"
        self.conn.execute(f"DELETE FROM call_event WHERE call_id IN (SELECT id FROM call WHERE {where})")
        self.conn.execute(f"DELETE FROM call WHERE {where}")
        self.conn.execute("DELETE FROM setting")

    def set(self, house, **cols):
        sets = ",".join(f"{k}=?" for k in cols)
        self.conn.execute(f"UPDATE treehouse SET {sets} WHERE id=?", (*cols.values(), self.house[house]))

    def calls(self):
        return self.conn.execute("SELECT * FROM call ORDER BY id").fetchall()

    def last_call(self, wait=20):
        """The newest call row once it has ended."""
        deadline = time.time() + wait
        while time.time() < deadline:
            row = self.conn.execute("SELECT * FROM call ORDER BY id DESC LIMIT 1").fetchone()
            if row and row["state"] == "ended":
                return row
            time.sleep(0.4)
        return self.conn.execute("SELECT * FROM call ORDER BY id DESC LIMIT 1").fetchone()

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
    return (c["result"] == "connected" and c["talk_sec"] >= 2 and
            ev[:1] == ["dialed"] and "rang" in ev and "answered" in ev and ev[-1] == "ended"), dict(c)


def not_in_service(w):
    """Sam dials a number nobody has."""
    c = call_and_check(w, "sam", "0199")
    return c["result"] == "not_in_service", dict(c)


def not_strung(w):
    """Riley dials Sam, but the string isn't live yet: blocked, and Riley's parents get a note."""
    c = call_and_check(w, "riley", "0101", ["sam"])
    notes = w.conn.execute("SELECT * FROM notice WHERE treehouse_id=?", (w.house["riley"],)).fetchall()
    return c["result"] == "not_strung" and len(notes) == 1, dict(c)


def no_911(w):
    """911 and a wrong-length number both get the 911 message."""
    c1 = call_and_check(w, "sam", "911")
    c2 = call_and_check(w, "sam", "12")
    return c1["result"] == "no_911" and c2["result"] == "no_911", [dict(c1), dict(c2)]


def callee_paused(w):
    """Alex's line is paused: Sam is blocked."""
    w.set("alex", paused=1)
    c = call_and_check(w, "sam", "0102", ["alex"])
    return c["result"] == "quiet_or_paused" and c["reason"] == "callee_paused", dict(c)


def caller_quiet_hours(w):
    """Sam's own quiet hours cover right now: blocked on Sam's side."""
    now = dt.datetime.now(ZoneInfo(TZ))
    w.set("sam", quiet_enabled=1,
          quiet_start=(now - dt.timedelta(hours=1)).strftime("%H:%M"),
          quiet_end=(now + dt.timedelta(hours=1)).strftime("%H:%M"))
    c = call_and_check(w, "sam", "0102", ["alex"])
    return c["result"] == "quiet_or_paused" and c["reason"] == "caller_quiet", dict(c)


def callee_quiet_hours(w):
    """Alex's quiet hours cover right now: Sam is blocked."""
    now = dt.datetime.now(ZoneInfo(TZ))
    w.set("alex", quiet_enabled=1,
          quiet_start=(now - dt.timedelta(hours=1)).strftime("%H:%M"),
          quiet_end=(now + dt.timedelta(hours=1)).strftime("%H:%M"))
    c = call_and_check(w, "sam", "0102", ["alex"])
    return c["result"] == "quiet_or_paused" and c["reason"] == "callee_quiet", dict(c)


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
        w.conn.execute("INSERT INTO call(started_at,caller_treehouse,callee_treehouse,dialed,state,result)"
                       " VALUES(?,?,?,?,?,?)", (db.iso(), w.house["sam"], w.house["alex"], "0102",
                                                "ended", "connected"))
    c = call_and_check(w, "sam", "0102", ["alex"])
    return c["result"] == "repeat_limit", dict(c)


def unstrung_hunting(w):
    """A kid trying lots of numbers that aren't strung is stopped, and parents are told."""
    db.set_setting(w.conn, "unstrung_limit_count", 3)
    for n in ("0190", "0191", "0192"):
        w.conn.execute("INSERT INTO call(started_at,caller_treehouse,dialed,state,result)"
                       " VALUES(?,?,?,?,?)", (db.iso(), w.house["sam"], n, "ended", "not_in_service"))
    c = call_and_check(w, "sam", "0102", ["alex"])
    notes = w.conn.execute("SELECT * FROM notice WHERE treehouse_id=? AND kind='unstrung_dials'",
                           (w.house["sam"],)).fetchall()
    return c["result"] == "repeat_limit" and c["reason"] == "unstrung_limit" and len(notes) == 1, dict(c)


def daily_minutes(w):
    """Sam used up today's minutes: blocked."""
    w.set("sam", daily_minutes=1)
    w.conn.execute("INSERT INTO call(started_at,caller_treehouse,callee_treehouse,dialed,state,result,talk_sec)"
                   " VALUES(?,?,?,?,?,?,?)", (db.iso(), w.house["sam"], w.house["alex"], "0102",
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
        cid = w.conn.execute("SELECT id FROM call ORDER BY id DESC LIMIT 1").fetchone()["id"]
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


SCENARIOS = [dial_by_number, not_in_service, not_strung, no_911, callee_paused,
             caller_quiet_hours, callee_quiet_hours, busy_line, callee_offline,
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
