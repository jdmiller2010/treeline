"""gunicorn's access log without anything a reader of the log could use: no query string, and no token in the
paths that carry one (adapter provisioning). Pairing codes travel in request bodies, never the log.
(SECURITY.md R1-5.) Used from deploy/native/gunicorn.conf.py as `logger_class`."""

import re

from gunicorn.glogging import Logger as _Logger

FORMAT = '%(h)s "%(m)s %(U)s" %(s)s %(b)s %(L)s'          # %(U)s is the path only, never the query

_SECRET_PATHS = (
    (re.compile(r"^(/api/provision/)[^/]+(\.xml)$"), r"\1<token>\2"),
    (re.compile(r"^(/api/ladder-codes/)[^/]+$"), r"\1<code>"),
)


def redact_path(path):
    path = (path or "-").split("?", 1)[0]
    for pattern, repl in _SECRET_PATHS:
        path = pattern.sub(repl, path)
    return path


class Logger(_Logger):
    def atoms(self, resp, req, environ, request_time):
        atoms = super().atoms(resp, req, environ, request_time)
        atoms["U"] = redact_path(atoms["U"])
        return atoms
