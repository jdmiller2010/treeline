"""A small Asterisk REST Interface client. Standard library only."""

import base64
import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request

APP = "treeline"
log = logging.getLogger("treeline")


class Ari:
    def __init__(self, url=None, user=None, password=None):
        self.url = (url or os.environ.get("ARI_URL", "http://127.0.0.1:8088/ari")).rstrip("/")
        self.user = user or os.environ.get("ARI_USER", "treeline")
        self.password = password or os.environ.get("ARI_PASS", "treeline-dev")
        token = base64.b64encode(f"{self.user}:{self.password}".encode()).decode()
        self._auth = f"Basic {token}"

    def request(self, method, path, _timeout=10, **params):
        query = urllib.parse.urlencode(
            {k: v for k, v in params.items() if v is not None}, doseq=True)
        req = urllib.request.Request(f"{self.url}{path}?{query}", method=method)
        req.add_header("Authorization", self._auth)
        try:
            with urllib.request.urlopen(req, timeout=_timeout) as resp:
                body = resp.read()
        except urllib.error.HTTPError as err:
            body = err.read()
            if err.code not in (404, 409):
                log.warning(
                    "ARI %s %s -> %s %s", method, path, err.code, body[:200])
        except (urllib.error.URLError, TimeoutError, OSError):
            return None
        try:
            return json.loads(body) if body else None
        except ValueError:
            return None

    def reload_module(self, module):
        return self.request("PUT", f"/asterisk/modules/{module}")

    def online_users(self, timeout=10):
        """Names of PJSIP endpoints that are registered right now.
        Returns None if Asterisk can't be reached."""
        data = self.request("GET", "/endpoints/PJSIP", _timeout=timeout)
        if data is None:
            return None
        if not isinstance(data, list):
            return set()
        return {e["resource"] for e in data if e.get("state") == "online"}
