"""Production mode: refuse to start with anything that is only meant for development.

TREELINE_ENV=production turns the checks on. The VM's services set it; the dev stack and the test suites
never do, so the dev sign-in code (TREELINE_DEV_CODES) and the default ARI login keep working there and
nowhere else. `enforce()` is called when the API module is imported and when the controller starts, so a
bad setting stops the service (systemd then shows it failing, and a deploy's health check rolls it back)
rather than serving with a dev setting on.
"""

import os
import sys

DEFAULT_ARI_PASSWORDS = {"", "treeline-dev", "change-me"}

# What production cannot work without. A missing value is a failed start, not a silent default.
REQUIRED = (
    "TREELINE_DB", "ARI_PASS", "TREELINE_PUBLIC_HOST", "TREELINE_PUBLIC_ORIGIN", "TREELINE_PUBLIC_WS_URL",
    "TREELINE_SMTP_HOST", "TREELINE_SMTP_USER", "TREELINE_SMTP_PASS", "TREELINE_MAIL_FROM",
    "TREELINE_VAPID_PUBLIC", "TREELINE_VAPID_PRIVATE", "TREELINE_VAPID_SUBJECT",
    "TREELINE_GOOGLE_CLIENT_ID", "TREELINE_GOOGLE_CLIENT_SECRET", "TREELINE_BETA_CODE_HASH", "TREELINE_BETA_CODE_EXPIRES",
)

# Development-only settings: their presence at all (even set to 0) is refused.
DEV_ONLY = ("TREELINE_DEV_CODES", "TREELINE_OUTBOX", "TREELINE_FACTORY_KEY_DEV",
            "TREELINE_GOOGLE_AUTH_URL", "TREELINE_GOOGLE_TOKEN_URL")      # the last two would point sign-in at another server


# Deployed code is production, whatever the environment says. A release always carries release.json at its root (scripts/
# build_release.sh); a development checkout never does. So even a server whose TREELINE_ENV was lost or mistyped cannot
# fall back to the development sign-in or the default ARI login (SECURITY.md R6-3).
RELEASE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "release.json")


def is_release(path=None):
    return os.path.isfile(path or RELEASE_FILE)


def is_production(env=None):
    return (env if env is not None else os.environ).get("TREELINE_ENV") == "production" or is_release()


def problems(env=None):
    """What is wrong with this environment for a production start (empty list: fine)."""
    env = os.environ if env is None else env
    out = []
    if is_release() and env.get("TREELINE_ENV") != "production":
        out.append(f"this is a deployed release, which only runs in production, but TREELINE_ENV is {env.get('TREELINE_ENV')!r}")
    for name in DEV_ONLY:
        if name in env:
            out.append(f"{name} is a development setting and must not be set in production")
    if env.get("ARI_USER", "treeline") == "treeline" and env.get("ARI_PASS", "") in DEFAULT_ARI_PASSWORDS:
        out.append("ARI_PASS is missing or is the development password")
    elif len(env.get("ARI_PASS", "")) < 20:
        out.append("ARI_PASS is too short (the installer generates a long random one)")
    for name in REQUIRED:
        if not env.get(name):
            out.append(f"{name} is not set (the secrets fetch from SSM or the installer should have provided it)")
    if env.get("TREELINE_PUBLIC_WS_URL") and not env["TREELINE_PUBLIC_WS_URL"].startswith("wss://"):
        out.append("TREELINE_PUBLIC_WS_URL must start with wss:// (a plain ws:// URL is refused by browsers on an https page)")
    if env.get("TREELINE_PUBLIC_ORIGIN") and not env["TREELINE_PUBLIC_ORIGIN"].startswith("https://"):
        out.append("TREELINE_PUBLIC_ORIGIN must start with https://")
    if env.get("TREELINE_TRUST_PROXY") != "1":
        out.append("TREELINE_TRUST_PROXY must be 1 (the app runs behind Caddy; without it every client has Caddy's address)")
    if env.get("TREELINE_SMTP_TLS", "1") != "1":
        out.append("TREELINE_SMTP_TLS must not be turned off")
    if env.get("ARI_URL", "http://127.0.0.1:8088/ari").split("://", 1)[-1].split("/")[0].split(":")[0] not in ("127.0.0.1", "localhost", "[::1]"):
        out.append("ARI_URL must point at this machine (ARI is never reached over the network)")
    return out


def enforce(env=None):
    """Exit with the list of problems if this is a production start with a bad environment."""
    env = os.environ if env is None else env
    if not is_production(env):
        return
    bad = problems(env)
    if bad:
        sys.stderr.write("Treeline refuses to start in production:\n" + "".join(f"  - {p}\n" for p in bad))
        raise SystemExit(78)      # EX_CONFIG
