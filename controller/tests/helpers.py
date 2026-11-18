"""Shared test setup: a throwaway database and a fake Asterisk."""

import os
import tempfile

_dir = tempfile.mkdtemp(prefix="treeline-test-")
# Always override: a test must never touch the real database or Asterisk config.
os.environ["TREELINE_DB"] = os.path.join(_dir, "test.db")
os.environ["TREELINE_PJSIP_FILE"] = os.path.join(_dir, "pjsip.conf")
os.environ["TREELINE_OUTBOX"] = os.path.join(_dir, "outbox")
os.environ["TREELINE_DEV_CODES"] = "1"
os.environ["TREELINE_WEB"] = os.path.join(_dir, "web")

from treeline import ari, db  # noqa: E402

CALLS_TO_ARI = []


def fake_request(self, method, path, **params):
    CALLS_TO_ARI.append((method, path, params))
    if path == "/endpoints/PJSIP":
        return []
    return None


ari.Ari.request = fake_request


def fresh_conn():
    """A new empty in-memory database."""
    return db.connect(":memory:")
