"""Scripted test phones for the Kid Phone Network.

Starts fake "house phones" (baresip, no sound card needed), makes calls
through the server, and checks the call log to confirm each call was
allowed or blocked as the rules say.

Usage:
  python3 run_scenarios.py                # run every scenario
  python3 run_scenarios.py --list         # list scenarios
  python3 run_scenarios.py approved_call  # run one

Environment:
  SIP_SERVER      address of Asterisk (default 127.0.0.1)
  KIDPHONE_LOG    call log the control app writes (default /data/calls.jsonl)
  KIDPHONE_RULES  rules file the control app reads (default /config/family.json)
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import math
import struct
import wave

SERVER = os.environ.get("SIP_SERVER", "127.0.0.1")
LOG_PATH = os.environ.get("KIDPHONE_LOG", "/data/calls.jsonl")
RULES_PATH = os.environ.get("KIDPHONE_RULES", "/config/family.json")

PHONES = {
    "1001": {"name": "Sam", "password": "dev-1001", "port": 15100},
    "1002": {"name": "Alex", "password": "dev-1002", "port": 15110},
    "1003": {"name": "Riley", "password": "dev-1003", "port": 15120},
    "1004": {"name": "Grandma", "password": "dev-1004", "port": 15130},
}

CONFIG_TEMPLATE = """\
sip_listen 0.0.0.0:{port}
audio_player aubridge,sink{ext}
audio_source aufile,{tone}
audio_alert aubridge,alert{ext}
module_path /usr/lib/baresip/modules
module g711.so
module aufile.so
module aubridge.so
module_app account.so
module_app menu.so
"""


def make_tone(path, seconds=90, freq=440, rate=8000):
    """A plain 8 kHz test tone that stands in for a kid talking."""
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(
            struct.pack("<h", int(8000 * math.sin(2 * math.pi * freq * i / rate)))
            for i in range(seconds * rate)))


class FakePhone:
    """One baresip process registered as a kid phone."""

    def __init__(self, ext, workdir, auto_answer=True):
        self.ext = ext
        self.dir = os.path.join(workdir, ext)
        os.makedirs(self.dir, exist_ok=True)
        p = PHONES[ext]
        with open(os.path.join(self.dir, "config"), "w") as f:
            tone = os.path.join(self.dir, "tone.wav")
            make_tone(tone)
            f.write(CONFIG_TEMPLATE.format(port=p["port"], ext=ext, tone=tone))
        answer = ";answermode=auto" if auto_answer else ""
        with open(os.path.join(self.dir, "accounts"), "w") as f:
            f.write(f"<sip:{ext}@{SERVER}>;auth_pass={p['password']}{answer}\n")
        self.proc = None

    def start(self, dial=None, run_for=None):
        cmd = ["baresip", "-4", "-f", self.dir]
        if dial:
            cmd += ["-e", f"/dial {dial}"]
        if run_for:
            cmd += ["-t", str(run_for)]
        self.log = open(os.path.join(self.dir, "baresip.log"), "w")
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                                     stdout=self.log, stderr=subprocess.STDOUT)
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


def read_log():
    if not os.path.exists(LOG_PATH):
        return []
    with open(LOG_PATH) as f:
        return [json.loads(line) for line in f if line.strip()]


def run_call(caller, dialed, callee, talk_seconds=6, callee_online=True):
    """Have `caller` dial `dialed` while `callee` waits to auto-answer.
    Returns the new call-log entry."""
    work = tempfile.mkdtemp(prefix="kidphone-")
    before = len(read_log())
    answering = None
    try:
        if callee_online and callee:
            answering = FakePhone(callee, work).start()
            time.sleep(3)  # let it register
        FakePhone(caller, work, auto_answer=False).start(
            dial=dialed, run_for=talk_seconds + 4).wait()
        deadline = time.time() + 15
        while time.time() < deadline:
            entries = read_log()
            if len(entries) > before:
                return entries[-1]
            time.sleep(0.5)
        return None
    finally:
        if answering:
            answering.stop()
        shutil.rmtree(work, ignore_errors=True)


def with_rules(change):
    """Temporarily edit the rules file; returns a function that restores it."""
    with open(RULES_PATH) as f:
        original = f.read()
    rules = json.loads(original)
    change(rules)
    with open(RULES_PATH, "w") as f:
        json.dump(rules, f, indent=2)

    def restore():
        with open(RULES_PATH, "w") as f:
            f.write(original)
    return restore


# ---------------------------------------------------------------- scenarios

def approved_call():
    """Sam presses 1 (Alex). Both houses approved each other -> connects."""
    e = run_call("1001", "1", "1002")
    return e and e["result"] == "completed" and e["callee"] == "1002" \
        and e["duration_sec"] >= 2, e


def one_sided_approval():
    """Sam presses 3 (Riley). Jordan approved Riley, Riley's house hasn't -> blocked."""
    e = run_call("1001", "3", "1003")
    return e and e["result"] == "denied" and e["reason"] == "not_approved", e


def stranger_calls_in():
    """Riley dials Sam directly. Not mutually approved -> blocked."""
    e = run_call("1003", "1001", "1001")
    return e and e["result"] == "denied" and e["reason"] == "not_approved", e


def unknown_number():
    """Sam dials a number that isn't a phone on the network -> blocked."""
    e = run_call("1001", "5555", None, callee_online=False)
    return e and e["result"] == "denied" and e["reason"] == "unknown_number", e


def paused_phone():
    """A parent pauses Alex's phone. Sam presses 1 -> blocked."""
    restore = with_rules(lambda r: r["phones"]["1002"].update(paused=True))
    try:
        e = run_call("1001", "1", "1002")
    finally:
        restore()
    return e and e["result"] == "denied" and e["reason"] == "callee_paused", e


def quiet_hours():
    """Sam's quiet hours are set to cover right now. Sam presses 1 -> blocked."""
    import datetime as dt
    from zoneinfo import ZoneInfo

    def cover_now(r):
        now = dt.datetime.now(ZoneInfo(r.get("timezone", "UTC")))
        start = (now - dt.timedelta(hours=1)).strftime("%H:%M")
        end = (now + dt.timedelta(hours=1)).strftime("%H:%M")
        r["phones"]["1001"]["quiet_hours"] = {"start": start, "end": end}
    restore = with_rules(cover_now)
    try:
        e = run_call("1001", "1", "1002")
    finally:
        restore()
    return e and e["result"] == "denied" and e["reason"] == "caller_quiet_hours", e


def grandma_call():
    """Sam presses 2 (Grandma). Approved both ways -> connects."""
    e = run_call("1001", "2", "1004")
    return e and e["result"] == "completed" and e["callee"] == "1004", e


def time_limit():
    """Calls are capped at 0.15 minutes (9 s) for this test -> cut off."""
    def shorten(r):
        r["phones"]["1001"]["max_call_minutes"] = 0.15
    restore = with_rules(shorten)
    try:
        e = run_call("1001", "1", "1002", talk_seconds=20)
    finally:
        restore()
    return e and e["result"] == "time_limit" and 7 <= e["duration_sec"] <= 12, e


def callee_offline():
    """Sam presses 1 but Alex's phone is unplugged -> no connection."""
    e = run_call("1001", "1", "1002", callee_online=False)
    return e and e["result"] in ("callee_offline", "no_answer"), e


SCENARIOS = [approved_call, one_sided_approval, stranger_calls_in,
             unknown_number, paused_phone, quiet_hours, grandma_call, time_limit,
             callee_offline]


def main(argv):
    if "--list" in argv:
        for s in SCENARIOS:
            print(f"{s.__name__:20} {s.__doc__}")
        return 0
    chosen = [s for s in SCENARIOS if not argv or s.__name__ in argv]
    failures = 0

    # Turn quiet hours off while testing, so results don't depend on the
    # time of day. The quiet_hours scenario sets its own window.
    def no_quiet_hours(r):
        for phone in r["phones"].values():
            phone["quiet_hours"] = None
    restore = with_rules(no_quiet_hours)
    try:
        for s in chosen:
            ok, entry = s()
            status = "PASS" if ok else "FAIL"
            failures += not ok
            print(f"[{status}] {s.__name__}: {s.__doc__}")
            print(f"        log: {json.dumps(entry)}")
    finally:
        restore()
    print(f"\n{len(chosen) - failures}/{len(chosen)} scenarios passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
