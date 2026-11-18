"""Kid Phone Network control app.

Asterisk sends every call from a kid phone here (via ARI). This app decides
whether the call may connect, using the rules in family.json:

  - mutual approval: both households must approve each other's phone
  - speed dials: "1" on Sam's phone means Alex, and so on
  - quiet hours, per phone
  - a paused phone can't call or be called
  - a time limit per call, with a warning beep before hanging up

Every call attempt is written to a JSON-lines call log.
The rules file is re-read on every call, so edits take effect right away.
"""

import datetime as dt
import json
import logging
import os
import threading
import time
import uuid
from zoneinfo import ZoneInfo

import requests
import websocket

ARI_URL = os.environ.get("ARI_URL", "http://127.0.0.1:8088/ari")
ARI_USER = os.environ.get("ARI_USER", "kidphone")
ARI_PASS = os.environ.get("ARI_PASS", "kidphone-dev")
APP = "kidphone"
RULES_PATH = os.environ.get("KIDPHONE_RULES", "/config/family.json")
LOG_PATH = os.environ.get("KIDPHONE_LOG", "/data/calls.jsonl")
FAKE_TIME = os.environ.get("KIDPHONE_FAKE_TIME")  # "HH:MM", for testing quiet hours
RING_TIMEOUT = int(os.environ.get("KIDPHONE_RING_TIMEOUT", "30"))

# What the caller hears when a call is not allowed. These are Asterisk's
# built-in prompts; record friendlier kid-specific ones later.
DENY_SOUNDS = {
    "caller_paused": "sound:ss-noservice",
    "caller_quiet_hours": "sound:ss-noservice",
    "unknown_number": "sound:cannot-complete-as-dialed",
    "not_approved": "sound:cannot-complete-as-dialed",
    "callee_paused": "sound:vm-isunavail",
    "callee_quiet_hours": "sound:vm-isunavail",
}

log = logging.getLogger("kidphone")
session = requests.Session()
session.auth = (ARI_USER, ARI_PASS)

calls = {}        # caller channel id -> Call
leg_to_call = {}  # any channel id in a call -> Call
playbacks = {}    # playback id -> channel id to hang up when it ends
lock = threading.RLock()


# ---------------------------------------------------------------- ARI helpers

def ari(method, path, **params):
    resp = session.request(method, f"{ARI_URL}{path}", params=params, timeout=10)
    if resp.status_code >= 400 and resp.status_code != 404:
        log.warning("ARI %s %s -> %s %s", method, path, resp.status_code, resp.text[:200])
    try:
        return resp.json()
    except ValueError:
        return None


def hangup(channel_id):
    ari("DELETE", f"/channels/{channel_id}")


def play_then_hangup(channel_id, media):
    playback_id = str(uuid.uuid4())
    with lock:
        playbacks[playback_id] = channel_id
    ari("POST", f"/channels/{channel_id}/answer")
    ari("POST", f"/channels/{channel_id}/play/{playback_id}", media=media)


# ---------------------------------------------------------------- rules

def load_rules():
    with open(RULES_PATH, encoding="utf-8") as f:
        return json.load(f)


def now_local(rules):
    if FAKE_TIME:
        h, m = map(int, FAKE_TIME.split(":"))
        return dt.time(h, m)
    return dt.datetime.now(ZoneInfo(rules.get("timezone", "UTC"))).time()


def in_quiet_hours(phone, rules):
    qh = phone.get("quiet_hours")
    if not qh:
        return False
    start = dt.time.fromisoformat(qh["start"])
    end = dt.time.fromisoformat(qh["end"])
    t = now_local(rules)
    if start <= end:
        return start <= t < end
    return t >= start or t < end  # window crosses midnight


def mutually_approved(a, b, rules):
    phones, homes = rules["phones"], rules["households"]
    home_a = homes.get(phones[a]["household"], {})
    home_b = homes.get(phones[b]["household"], {})
    return b in home_a.get("approves", []) and a in home_b.get("approves", [])


def decide(caller, dialed, rules):
    """Return (callee, reason). reason is None if the call may connect."""
    phones = rules["phones"]
    me = phones.get(caller)
    if me is None:
        return None, "unknown_caller"
    if me.get("paused"):
        return None, "caller_paused"
    if in_quiet_hours(me, rules):
        return None, "caller_quiet_hours"

    callee = me.get("speed_dials", {}).get(dialed, dialed)
    them = phones.get(callee)
    if them is None or callee == caller:
        return callee, "unknown_number"
    if not mutually_approved(caller, callee, rules):
        return callee, "not_approved"
    if them.get("paused"):
        return callee, "callee_paused"
    if in_quiet_hours(them, rules):
        return callee, "callee_quiet_hours"
    return callee, None


# ---------------------------------------------------------------- call log

def write_log(entry):
    entry["time"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    os.makedirs(os.path.dirname(LOG_PATH) or ".", exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    log.info("call log: %s", entry)


# ---------------------------------------------------------------- calls

class Call:
    def __init__(self, caller_chan, caller, dialed, callee, rules):
        self.caller_chan = caller_chan
        self.callee_chan = None
        self.bridge = None
        self.caller = caller
        self.dialed = dialed
        self.callee = callee
        self.rules = rules
        self.answered_at = None
        self.result = None
        self.timers = []
        self.finished = False

    def limit_seconds(self):
        phones = self.rules["phones"]
        minutes = min(phones[self.caller].get("max_call_minutes", 30),
                      phones[self.callee].get("max_call_minutes", 30))
        return max(5, float(minutes) * 60)

    def names(self):
        phones = self.rules["phones"]
        return phones[self.caller]["name"], phones[self.callee]["name"]

    def finish(self, result):
        with lock:
            if self.finished:
                return
            self.finished = True
        for t in self.timers:
            t.cancel()
        for chan in (self.caller_chan, self.callee_chan):
            if chan:
                hangup(chan)
                leg_to_call.pop(chan, None)
        if self.bridge:
            ari("DELETE", f"/bridges/{self.bridge}")
        calls.pop(self.caller_chan, None)
        caller_name, callee_name = self.names()
        duration = round(time.time() - self.answered_at) if self.answered_at else 0
        write_log({
            "caller": self.caller, "caller_name": caller_name,
            "dialed": self.dialed,
            "callee": self.callee, "callee_name": callee_name,
            "result": self.result or result, "duration_sec": duration,
        })


def on_incoming(channel):
    """A kid phone dialed something."""
    chan_id = channel["id"]
    caller = channel["caller"]["number"]
    dialed = channel["dialplan"]["exten"]
    rules = load_rules()
    callee, reason = decide(caller, dialed, rules)

    if reason:
        phones = rules["phones"]
        write_log({
            "caller": caller, "caller_name": phones.get(caller, {}).get("name"),
            "dialed": dialed,
            "callee": callee, "callee_name": phones.get(callee, {}).get("name"),
            "result": "denied", "reason": reason, "duration_sec": 0,
        })
        play_then_hangup(chan_id, DENY_SOUNDS.get(reason, "sound:ss-noservice"))
        return

    call = Call(chan_id, caller, dialed, callee, rules)
    with lock:
        calls[chan_id] = call
        leg_to_call[chan_id] = call
    ari("POST", f"/channels/{chan_id}/ring")
    caller_name = rules["phones"][caller]["name"]
    out = ari("POST", "/channels",
              endpoint=f"PJSIP/{callee}", app=APP,
              appArgs=f"dialed,{chan_id}",
              callerId=f'"{caller_name}" <{caller}>',
              timeout=RING_TIMEOUT)
    if not out or "id" not in out:
        call.finish("callee_offline")
        return
    with lock:
        call.callee_chan = out["id"]
        leg_to_call[out["id"]] = call


def on_callee_answered(channel, caller_chan):
    with lock:
        call = calls.get(caller_chan)
    if call is None:
        hangup(channel["id"])
        return
    ari("POST", f"/channels/{caller_chan}/answer")
    bridge = ari("POST", "/bridges", type="mixing")
    call.bridge = bridge["id"]
    ari("POST", f"/bridges/{call.bridge}/addChannel",
        channel=f"{caller_chan},{channel['id']}")
    call.answered_at = time.time()

    limit = call.limit_seconds()
    warn_at = limit - min(60, limit * 0.2)

    def warn():
        ari("POST", f"/bridges/{call.bridge}/play", media="sound:beep")

    def cut_off():
        call.result = "time_limit"
        call.finish("time_limit")

    call.timers = [threading.Timer(warn_at, warn), threading.Timer(limit, cut_off)]
    for t in call.timers:
        t.daemon = True
        t.start()
    log.info("connected %s -> %s (limit %ss)", call.caller, call.callee, int(limit))


def on_channel_gone(chan_id):
    with lock:
        call = leg_to_call.get(chan_id)
    if call is None or call.finished:
        return
    if call.answered_at:
        call.finish("completed")
    elif chan_id == call.caller_chan:
        call.finish("caller_hung_up")
    else:
        call.finish("no_answer")


# ---------------------------------------------------------------- events

def handle(event):
    kind = event.get("type")
    if kind == "StasisStart":
        args = event.get("args", [])
        if args and args[0] == "dialed":
            on_callee_answered(event["channel"], args[1])
        else:
            on_incoming(event["channel"])
    elif kind in ("StasisEnd", "ChannelDestroyed"):
        on_channel_gone(event["channel"]["id"])
    elif kind == "PlaybackFinished":
        with lock:
            chan = playbacks.pop(event["playback"]["id"], None)
        if chan:
            hangup(chan)


def on_message(_ws, message):
    try:
        handle(json.loads(message))
    except Exception:
        log.exception("error handling event")


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    ws_url = ARI_URL.replace("http", "ws", 1) + \
        f"/events?app={APP}&api_key={ARI_USER}:{ARI_PASS}"
    while True:
        log.info("connecting to Asterisk at %s", ARI_URL)
        ws = websocket.WebSocketApp(
            ws_url, on_message=on_message,
            on_open=lambda _ws: log.info("connected; waiting for calls"),
            on_error=lambda _ws, err: log.warning("websocket: %s", err))
        ws.run_forever()
        time.sleep(3)  # Asterisk not up yet, or restarted; retry


if __name__ == "__main__":
    main()
