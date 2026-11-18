"""Who may call whom. Pure logic over the database, no Asterisk in here.

`decide()` follows the call flow in docs/PLAN.md, in this order:
  0. 911 or a wrong-length number
  1. the caller's own line is paused, in quiet hours or over a limit
  2. the number exists
  3. there is a live string between the two treehouses
  4. the other line is paused, in quiet hours or over its daily limit
  5. the other line is already in use
  6. no handset on the other line is registered
  7. ring every handset on the other line
"""

import datetime as dt
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo

from . import db

# Results written to the call audit.
CONNECTED = "connected"
NO_ANSWER = "no_answer"
BUSY = "busy"
NOT_IN_SERVICE = "not_in_service"
NOT_STRUNG = "not_strung"
QUIET_OR_PAUSED = "quiet_or_paused"
OFFLINE = "offline"
NO_911 = "no_911"
TIME_LIMIT = "time_limit"
REPEAT_LIMIT = "repeat_limit"
DAILY_LIMIT = "daily_limit"
CALLER_HUNG_UP = "caller_hung_up"

# What the caller hears for each result. "tone:" names are Asterisk
# indications (US tones); "msg:" is a short recording after the SIT tones.
SOUND_FAST_BUSY = "fast_busy"
SOUND_BUSY = "busy"
SOUND_NOT_IN_SERVICE = "not_in_service"
SOUND_ASK_GROWN_UP = "ask_grown_up"
SOUND_NOT_TAKING_CALLS = "not_taking_calls"
SOUND_NO_911 = "no_911"

SYSTEM_JOIN_NUMBER = "0001"  # a handset dials this to join its line's call in progress


@dataclass
class Decision:
    result: str | None = None          # None means ring the callee
    reason: str | None = None
    sound: str | None = None
    callee: object = None              # treehouse row
    handsets: list = field(default_factory=list)   # handset rows to ring
    notify_caller_parents: tuple | None = None     # (kind, title, body, key)

    @property
    def allowed(self):
        return self.result is None


def local_now(th, now):
    return now.astimezone(ZoneInfo(th["timezone"]))


def in_quiet_hours(th, now):
    """True if the treehouse's quiet hours cover `now` (a UTC datetime)."""
    if not th["quiet_enabled"]:
        return False
    local = local_now(th, now)
    start = dt.time.fromisoformat(th["quiet_start"])
    end = dt.time.fromisoformat(th["quiet_end"])
    t = local.time().replace(second=0, microsecond=0)
    days = th["quiet_days"] or "1111111"
    if start == end:
        return False
    if start < end:
        return start <= t < end and days[local.weekday()] == "1"
    if t >= start:
        return days[local.weekday()] == "1"
    if t < end:  # after midnight: the window began yesterday
        return days[(local.weekday() - 1) % 7] == "1"
    return False


def talk_seconds_today(conn, th, now):
    """Talk time today (in the treehouse's own day), as caller or callee."""
    local = local_now(th, now)
    midnight = local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(dt.timezone.utc)
    row = conn.execute(
        "SELECT COALESCE(SUM(talk_sec),0) AS s FROM call WHERE started_at >= ? "
        "AND (caller_treehouse=? OR callee_treehouse=?)",
        (db.iso(midnight), th["id"], th["id"])).fetchone()
    return row["s"]


def over_daily_limit(conn, th, now):
    limit = th["daily_minutes"]
    return bool(limit) and talk_seconds_today(conn, th, now) >= limit * 60


def remaining_daily_seconds(conn, th, now):
    limit = th["daily_minutes"]
    if not limit:
        return None
    return max(0, limit * 60 - talk_seconds_today(conn, th, now))


def line_in_use(conn, treehouse_id):
    return conn.execute(
        "SELECT 1 FROM call WHERE state IN ('ringing','active') "
        "AND (caller_treehouse=? OR callee_treehouse=?)",
        (treehouse_id, treehouse_id)).fetchone() is not None


def active_call_of(conn, treehouse_id):
    return conn.execute(
        "SELECT * FROM call WHERE state='active' AND (caller_treehouse=? OR callee_treehouse=?) "
        "ORDER BY id DESC", (treehouse_id, treehouse_id)).fetchone()


# Calls that actually rang or ran. Blocked attempts don't count toward the repeat
# limit, or a child who keeps redialing would never be let through again.
RANG = "AND (state!='ended' OR result IN ('connected','no_answer','time_limit','caller_hung_up'))"


def _recent(conn, treehouse_id, minutes, now, extra="", args=()):
    since = db.iso(now - dt.timedelta(minutes=minutes))
    return conn.execute(
        f"SELECT COUNT(*) AS n FROM call WHERE caller_treehouse=? AND started_at>=? {extra}",
        (treehouse_id, since, *args)).fetchone()["n"]


def line_state(conn, th, now):
    """What a handset on this line should do when picked up."""
    if th["paused"] or in_quiet_hours(th, now) or over_daily_limit(conn, th, now):
        return "quiet"
    call = conn.execute("SELECT * FROM call WHERE state IN ('ringing','active') "
                        "AND (caller_treehouse=? OR callee_treehouse=?) ORDER BY id DESC",
                        (th["id"], th["id"])).fetchone()
    if call is None:
        return "idle"
    return "in_call" if call["state"] == "active" else "ringing"


def decide(conn, caller_handset, dialed, now=None, online=None):
    """Decide what happens when `caller_handset` dials `dialed`.

    `online` is a set of sip_user names currently registered, or None to
    treat every handset as online.
    """
    now = now or db.utcnow()
    caller = db.get_treehouse(conn, caller_handset["treehouse_id"])
    if caller is None:
        return Decision(NOT_IN_SERVICE, "unknown_caller", SOUND_FAST_BUSY)

    # 0. 911 or a wrong-length dial.
    if dialed == "911" or not (len(dialed) == 4 and dialed.isdigit()):
        return Decision(NO_911, "911_or_wrong_length", SOUND_NO_911)

    # 1. The caller's own line.
    if caller["paused"]:
        return Decision(QUIET_OR_PAUSED, "caller_paused", SOUND_FAST_BUSY)
    if in_quiet_hours(caller, now):
        return Decision(QUIET_OR_PAUSED, "caller_quiet", SOUND_FAST_BUSY)
    if over_daily_limit(conn, caller, now):
        return Decision(DAILY_LIMIT, "caller_daily_limit", SOUND_FAST_BUSY)
    if line_in_use(conn, caller["id"]):
        # One call per line: a second handset can't start another call (it can join this one).
        return Decision(BUSY, "caller_in_use", SOUND_BUSY)
    ucount = int(db.get_setting(conn, "unstrung_limit_count"))
    umin = int(db.get_setting(conn, "unstrung_limit_minutes"))
    if _recent(conn, caller["id"], umin, now,
               "AND result IN ('not_in_service','not_strung')") >= ucount:
        return Decision(
            REPEAT_LIMIT, "unstrung_limit", SOUND_FAST_BUSY,
            notify_caller_parents=(
                "unstrung_dials", "Lots of numbers dialed that aren't strung",
                "Someone on your line has tried several numbers that aren't connected to you. "
                "Calls are paused for a few minutes.", "unstrung_dials"))

    # 2. Does the number exist?
    callee = db.treehouse_by_number(conn, dialed)
    if callee is None or callee["id"] == caller["id"] or callee["system"]:
        return Decision(NOT_IN_SERVICE, "no_such_number", SOUND_NOT_IN_SERVICE)

    # 3. Is there a live string?
    if db.live_string(conn, caller["id"], callee["id"]) is None:
        return Decision(
            NOT_STRUNG, "no_live_string", SOUND_ASK_GROWN_UP, callee=callee,
            notify_caller_parents=(
                "not_strung_attempt", f"A call to {dialed} didn't connect",
                f"Someone on your line dialed {dialed}, which isn't strung to your treehouse.",
                f"not_strung:{dialed}"))

    # Repeat limit: too many calls to the same treehouse in a short time.
    rcount = int(db.get_setting(conn, "repeat_limit_count"))
    rmin = int(db.get_setting(conn, "repeat_limit_minutes"))
    if _recent(conn, caller["id"], rmin, now, RANG + " AND callee_treehouse=?", (callee["id"],)) >= rcount:
        return Decision(REPEAT_LIMIT, "repeat_limit", SOUND_FAST_BUSY, callee=callee)

    # 4. The other line's own rules. Same message for each, so one family's
    #    schedule isn't revealed to another.
    if callee["paused"]:
        return Decision(QUIET_OR_PAUSED, "callee_paused", SOUND_NOT_TAKING_CALLS, callee=callee)
    if in_quiet_hours(callee, now):
        return Decision(QUIET_OR_PAUSED, "callee_quiet", SOUND_NOT_TAKING_CALLS, callee=callee)
    if over_daily_limit(conn, callee, now):
        return Decision(QUIET_OR_PAUSED, "callee_daily_limit", SOUND_NOT_TAKING_CALLS, callee=callee)

    # 5. Is the other line in use?
    if line_in_use(conn, callee["id"]):
        return Decision(BUSY, "callee_in_use", SOUND_BUSY, callee=callee)

    # 6. Is anything on the other line registered?
    handsets = db.handsets_of(conn, callee["id"])
    if online is not None:
        handsets = [h for h in handsets if h["sip_user"] in online]
    if not handsets:
        return Decision(OFFLINE, "callee_offline", SOUND_FAST_BUSY, callee=callee)

    # 7. Ring.
    return Decision(None, None, None, callee=callee, handsets=list(handsets))


def call_limit_seconds(conn, caller, callee, now=None):
    """How long this call may last: the shorter of both treehouses' limits,
    and whatever is left of either one's daily minutes."""
    now = now or db.utcnow()
    limits = [max(5.0, float(caller["max_call_minutes"]) * 60),
              max(5.0, float(callee["max_call_minutes"]) * 60)]
    for th in (caller, callee):
        left = remaining_daily_seconds(conn, th, now)
        if left is not None:
            limits.append(max(5.0, left))
    return min(limits)
