"""The call engine: Asterisk sends every call here (via ARI) and this
decides what happens, using rules.decide().

One call can have several handsets on each side. All handsets on the
called line ring; the first to answer joins the caller in a bridge. Any
other handset on either line can join the call later by dialing 0001
(the softphone does this when you lift it mid-call). The call lasts
until every handset on one side has hung up.
"""

import json
import logging
import threading
import time
import uuid

from . import ari as ari_mod
from . import db, rules

log = logging.getLogger("treeline")

# Tones are named in asterisk/config/indications.conf and played as "tone:<name>".
# (Not as raw strings: ARI splits a media list on commas, which tone strings are full of.)
TONES = {
    "busy": ("tone:busy", 4.0),
    "fast_busy": ("tone:congestion", 4.0),
    "sit": ("tone:sit", 1.2),
    "pips": ("tone:pips", 1.0),
    "join": ("tone:join", 0.6),
    "ringtest": ("tone:ringtest", 1.6),
}
# Recordings after the three rising tones.
MESSAGES = {
    rules.SOUND_CANNOT_COMPLETE: "sound:treeline/cannot_complete",
    rules.SOUND_ASK_GROWN_UP: "sound:treeline/ask_grown_up",
    rules.SOUND_NOT_TAKING_CALLS: "sound:treeline/not_taking_calls",
    rules.SOUND_NO_911: "sound:treeline/no_911",
}


def sound_plan(sound):
    """The sequence of (media, seconds-or-None) to play for a denial."""
    if sound in ("busy", "fast_busy"):
        return [TONES[sound]]
    return [TONES["sit"], (MESSAGES[sound], None)]


class Leg:
    """One channel in a call."""

    def __init__(self, chan_id, handset_id, side):
        self.chan_id = chan_id
        self.handset_id = handset_id
        self.side = side            # "caller" or "callee"
        self.in_bridge = False


class Call:
    def __init__(self, call_id, caller_th, callee_th, dialed):
        self.id = call_id
        self.caller_th = caller_th
        self.callee_th = callee_th
        self.dialed = dialed
        self.legs = {}              # chan id -> Leg
        self.bridge = None
        self.answered_at = None
        self.finished = False
        self.result = None
        self.hung_up_first = None
        self.timers = []


class Engine:
    def __init__(self, ari=None):
        self.ari = ari or ari_mod.Ari()
        self.lock = threading.RLock()
        self.calls = {}             # call id -> Call
        self.by_chan = {}           # chan id -> Call
        self.playing = {}           # playback id -> (chan id, remaining plan)
        self.ringtests = {}         # chan id -> True

    @property
    def conn(self):
        return db.local_conn()

    # ------------------------------------------------------------ helpers

    def audit(self, call_id, event, handset_id=None):
        self.conn.execute("INSERT INTO call_event(call_id,at,handset_id,event) VALUES(?,?,?,?)",
                          (call_id, db.iso(), handset_id, event))

    def handset_for(self, channel):
        """Who is on this channel? From the channel name (PJSIP/<user>-<n>),
        which can't be faked the way a caller ID could."""
        name = channel.get("name", "")
        if not name.startswith("PJSIP/"):
            return None
        sip_user = name[len("PJSIP/"):].rsplit("-", 1)[0]
        return db.handset_by_user(self.conn, sip_user)

    def hangup(self, chan_id):
        self.ari.request("DELETE", f"/channels/{chan_id}")

    # ------------------------------------------------------------ sounds

    def play_plan(self, chan_id, plan):
        """Play tones and recordings in order, then hang up."""
        if not plan:
            self.hangup(chan_id)
            return
        (media, seconds), rest = plan[0], plan[1:]
        pb_id = str(uuid.uuid4())
        with self.lock:
            self.playing[pb_id] = (chan_id, rest)
        self.ari.request("POST", f"/channels/{chan_id}/play/{pb_id}", media=media)
        if seconds is not None:
            t = threading.Timer(seconds, self.stop_playback, args=(pb_id,))
            t.daemon = True
            t.start()
        else:
            # A recording ends by itself; this is only a safety net.
            t = threading.Timer(30, self.stop_playback, args=(pb_id,))
            t.daemon = True
            t.start()

    def stop_playback(self, pb_id):
        with self.lock:
            entry = self.playing.pop(pb_id, None)
        if entry is None:
            return
        chan_id, rest = entry
        self.ari.request("DELETE", f"/playbacks/{pb_id}")
        self.play_plan(chan_id, rest)

    def on_playback_finished(self, pb_id):
        with self.lock:
            entry = self.playing.pop(pb_id, None)
        if entry is None:
            return
        chan_id, rest = entry
        self.play_plan(chan_id, rest)

    # ------------------------------------------------------------ incoming

    def on_incoming(self, channel):
        chan_id = channel["id"]
        handset = self.handset_for(channel)
        dialed = channel.get("dialplan", {}).get("exten", "")
        if handset is None:
            log.warning("call from unknown channel %s", channel.get("name"))
            self.hangup(chan_id)
            return
        self.conn.execute("UPDATE handset SET last_seen=?, online=1 WHERE id=?",
                          (db.iso(), handset["id"]))
        if dialed == rules.SYSTEM_JOIN_NUMBER:
            if handset["disabled"]:                     # a disconnected phone can't join either
                self.ari.request("POST", f"/channels/{chan_id}/answer")
                self.play_plan(chan_id, sound_plan("fast_busy"))
                return
            self.join_call(chan_id, handset)
            return

        now = db.utcnow()
        online = self.ari.online_users()
        if online is not None:
            online = set(online) | {handset["sip_user"]}
        decision = rules.decide(self.conn, handset, dialed, now, online)
        callee_id = decision.callee["id"] if decision.callee else None
        cur = self.conn.execute(
            "INSERT INTO call(started_at,caller_treehouse,caller_handset,dialed,callee_treehouse,"
            "state,result,reason) VALUES(?,?,?,?,?,?,?,?)",
            (db.iso(now), handset["treehouse_id"], handset["id"], dialed, callee_id,
             "ringing" if decision.allowed else "ended", decision.result, decision.reason))
        call_id = cur.lastrowid
        if not decision.allowed:
            self.conn.execute("UPDATE call SET ended_at=? WHERE id=?", (db.iso(now), call_id))
            if decision.notify_caller_parents:
                kind, title, body, key = decision.notify_caller_parents
                db.add_notice(self.conn, handset["treehouse_id"], kind, title, body, key)
            log.info("blocked %s -> %s: %s", handset["sip_user"], dialed, decision.reason)
            self.ari.request("POST", f"/channels/{chan_id}/answer")
            self.play_plan(chan_id, sound_plan(decision.sound))
            return

        caller_th = db.get_treehouse(self.conn, handset["treehouse_id"])
        call = Call(call_id, caller_th, decision.callee, dialed)
        leg = Leg(chan_id, handset["id"], "caller")
        with self.lock:
            self.calls[call_id] = call
            call.legs[chan_id] = leg
            self.by_chan[chan_id] = call
        self.audit(call_id, "dialed", handset["id"])
        self.ari.request("POST", f"/channels/{chan_id}/ring")

        timeout = int(db.get_setting(self.conn, "ring_timeout_sec"))
        rang = 0
        for h in decision.handsets:
            out = self.ari.request(
                "POST", "/channels", endpoint=f"PJSIP/{h['sip_user']}", app=ari_mod.APP,
                appArgs=f"dialed,{call_id},{h['id']}", callerId='"" <0000>', timeout=timeout)
            if out and "id" in out:
                with self.lock:
                    call.legs[out["id"]] = Leg(out["id"], h["id"], "callee")
                    self.by_chan[out["id"]] = call
                self.audit(call_id, "rang", h["id"])
                rang += 1
        if rang == 0:
            self.finish(call, rules.OFFLINE, "originate_failed")
            return
        # Caller hears ringback; stop and log a missed call after the timeout.
        t = threading.Timer(timeout + 2, self.ring_timeout, args=(call,))
        t.daemon = True
        call.timers.append(t)
        t.start()

    def ring_timeout(self, call):
        if not call.answered_at:
            self.finish(call, rules.NO_ANSWER, "ring_timeout")

    # ------------------------------------------------------------ answers

    def on_callee_leg(self, channel, call_id, handset_id):
        chan_id = channel["id"]
        with self.lock:
            call = self.calls.get(int(call_id))
            if call is None or call.finished:
                self.hangup(chan_id)
                return
            first = call.answered_at is None
            leg = call.legs.get(chan_id) or Leg(chan_id, int(handset_id), "callee")
            call.legs[chan_id] = leg
            self.by_chan[chan_id] = call
        if not first:
            # Someone else already answered; this one came late.
            self.hangup(chan_id)
            return
        self.connect(call, leg)

    def connect(self, call, answering):
        caller_leg = next((l for l in call.legs.values() if l.side == "caller"), None)
        if caller_leg is None:
            # The caller hung up just as someone answered.
            self.hangup(answering.chan_id)
            self.finish(call, rules.CALLER_HUNG_UP, None)
            return
        self.ari.request("POST", f"/channels/{caller_leg.chan_id}/answer")
        bridge = self.ari.request("POST", "/bridges", type="mixing")
        if not bridge or "id" not in bridge:
            log.error("call %s: could not create a bridge", call.id)
            self.finish(call, rules.NO_ANSWER, "bridge_failed")
            return
        with self.lock:
            for t in call.timers:
                t.cancel()
            call.timers = []
            call.bridge = bridge["id"]
            call.answered_at = time.time()
        self.ari.request("POST", f"/bridges/{call.bridge}/addChannel",
                         channel=f"{caller_leg.chan_id},{answering.chan_id}")
        caller_leg.in_bridge = answering.in_bridge = True
        # Everyone else on that line stops ringing.
        for leg in list(call.legs.values()):
            if leg.side == "callee" and not leg.in_bridge:
                self.hangup(leg.chan_id)
        self.conn.execute("UPDATE call SET state='active', answered_at=?, answered_handset=? WHERE id=?",
                          (db.iso(), answering.handset_id, call.id))
        self.audit(call.id, "answered", answering.handset_id)

        limit = rules.call_limit_seconds(self.conn, call.caller_th, call.callee_th)
        warn_in = max(1.0, limit - 60 if limit > 120 else limit * 0.8)
        for delay, fn in ((warn_in, self.warn), (limit, self.cut_off)):
            t = threading.Timer(delay, fn, args=(call,))
            t.daemon = True
            call.timers.append(t)
            t.start()
        log.info("connected call %s (limit %ss)", call.id, int(limit))

    def warn(self, call):
        if call.bridge and not call.finished:
            self.ari.request("POST", f"/bridges/{call.bridge}/play", media=TONES["pips"][0])
            self.audit(call.id, "pips")

    def cut_off(self, call):
        self.finish(call, rules.TIME_LIMIT, "call_length_limit")

    # ------------------------------------------------------------ joining

    def join_call(self, chan_id, handset):
        """A handset on a line that is on a call picks up and joins it."""
        call = None
        with self.lock:
            for c in self.calls.values():
                if c.answered_at and c.bridge and not c.finished and handset["treehouse_id"] in (
                        c.caller_th["id"], c.callee_th["id"]):
                    call = c
                    break
        if call is None:
            self.ari.request("POST", f"/channels/{chan_id}/answer")
            self.play_plan(chan_id, sound_plan("fast_busy"))
            return
        side = "caller" if handset["treehouse_id"] == call.caller_th["id"] else "callee"
        leg = Leg(chan_id, handset["id"], side)
        with self.lock:
            call.legs[chan_id] = leg
            self.by_chan[chan_id] = call
        self.ari.request("POST", f"/channels/{chan_id}/answer")
        self.ari.request("POST", f"/bridges/{call.bridge}/addChannel", channel=chan_id)
        leg.in_bridge = True
        # Everyone hears a click and a soft tone.
        self.ari.request("POST", f"/bridges/{call.bridge}/play", media=TONES["join"][0])
        self.audit(call.id, "joined", handset["id"])

    # ------------------------------------------------------------ ending

    def on_channel_gone(self, chan_id):
        with self.lock:
            self.ringtests.pop(chan_id, None)
            call = self.by_chan.pop(chan_id, None)
            if call is None or call.finished:
                return
            leg = call.legs.pop(chan_id, None)
        if leg is None:
            return
        if call.answered_at:
            if leg.in_bridge:
                self.audit(call.id, "left", leg.handset_id)
            with self.lock:
                side_left = any(l.side == leg.side and l.in_bridge for l in call.legs.values())
            if not side_left:
                call.hung_up_first = call.hung_up_first or leg.side
                self.finish(call, rules.CONNECTED, None)
        else:
            if leg.side == "caller":
                call.hung_up_first = "caller"
                self.finish(call, rules.CALLER_HUNG_UP, None)
            else:
                self.audit(call.id, "declined", leg.handset_id)
                with self.lock:
                    ringing = [l for l in call.legs.values() if l.side == "callee"]
                if not ringing:
                    self.finish(call, rules.NO_ANSWER, "not_answered")

    def finish(self, call, result, reason):
        with self.lock:
            if call.finished:
                return
            call.finished = True
            legs = list(call.legs.values())
        for t in call.timers:
            t.cancel()
        for leg in legs:
            self.hangup(leg.chan_id)
        with self.lock:
            for leg in legs:
                self.by_chan.pop(leg.chan_id, None)
            self.calls.pop(call.id, None)
        if call.bridge:
            self.ari.request("DELETE", f"/bridges/{call.bridge}")
        talk = round(time.time() - call.answered_at) if call.answered_at else 0
        final = call.result or result
        self.conn.execute(
            "UPDATE call SET state='ended', ended_at=?, talk_sec=?, result=?, reason=?, hung_up_first=? "
            "WHERE id=?", (db.iso(), talk, final, reason, call.hung_up_first, call.id))
        self.audit(call.id, "ended")
        log.info("call %s ended: %s (%ss)", call.id, final, talk)

    # ------------------------------------------------------------ ring test

    def on_ringtest_answered(self, chan_id):
        """A parent tapped 'ring test' and someone picked up: say hello and hang up."""
        self.play_plan(chan_id, [TONES["ringtest"]])

    # ------------------------------------------------------------ events

    def handle(self, event):
        kind = event.get("type")
        if kind == "StasisStart":
            args = event.get("args", [])
            if args and args[0] == "dialed":
                self.on_callee_leg(event["channel"], args[1], args[2])
            elif args and args[0] == "ringtest":
                self.on_ringtest_answered(event["channel"]["id"])
            else:
                self.on_incoming(event["channel"])
        elif kind in ("StasisEnd", "ChannelDestroyed"):
            self.on_channel_gone(event["channel"]["id"])
        elif kind == "PlaybackFinished":
            self.on_playback_finished(event["playback"]["id"])

    def on_message(self, _ws, message):
        try:
            self.handle(json.loads(message))
        except Exception:
            log.exception("error handling event")

    def clean_up_after_restart(self):
        """Calls that were open when the server stopped are over."""
        self.conn.execute("UPDATE call SET state='ended', ended_at=?, result=COALESCE(result,'dropped'), "
                          "reason='server_restart' WHERE state IN ('ringing','active')", (db.iso(),))
