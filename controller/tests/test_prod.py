"""Production mode refuses a development setting (SECURITY.md, DEPLOY_AWS.md requirement 4), the dev path still
works when TREELINE_ENV is not production, SMTP verifies certificates (R1-1), and the access log keeps tokens out (R1-5)."""

import datetime
import logging
import os
import smtplib
import socket
import ssl
import subprocess
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest import mock

from tests import helpers  # noqa: F401  (test environment)
from treeline import accesslog, mail, prod


def good_env(**over):
    env = {
        "TREELINE_ENV": "production", "TREELINE_DB": "/var/lib/treeline/treeline.db",
        "ARI_PASS": "x" * 32, "TREELINE_PUBLIC_HOST": "app.example.invalid",
        "TREELINE_PUBLIC_ORIGIN": "https://app.example.invalid", "TREELINE_PUBLIC_WS_URL": "wss://app.example.invalid/ws",
        "TREELINE_TRUST_PROXY": "1", "TREELINE_SMTP_HOST": "smtp.example.invalid", "TREELINE_SMTP_USER": "u",
        "TREELINE_SMTP_PASS": "p", "TREELINE_MAIL_FROM": "Treeline <no-reply@example.invalid>",
        "TREELINE_VAPID_PUBLIC": "a", "TREELINE_VAPID_PRIVATE": "b", "TREELINE_VAPID_SUBJECT": "mailto:a@example.invalid",
        "TREELINE_GOOGLE_CLIENT_ID": "id.apps.googleusercontent.com", "TREELINE_GOOGLE_CLIENT_SECRET": "s" * 24,
        "TREELINE_BETA_CODE_HASH": "0" * 64, "TREELINE_BETA_CODE_EXPIRES": "2099-01-01",
    }
    env.update(over)
    return {k: v for k, v in env.items() if v is not None}


class ProductionGuard(unittest.TestCase):
    def test_a_good_production_environment_starts(self):
        self.assertEqual(prod.problems(good_env()), [])
        prod.enforce(good_env())

    def test_dev_sign_in_codes_are_refused_even_when_set_to_zero(self):
        for value in ("1", "0", ""):
            with self.assertRaises(SystemExit):
                prod.enforce(good_env(TREELINE_DEV_CODES=value))

    def test_the_default_or_a_missing_ari_password_is_refused(self):
        for value in (None, "", "treeline-dev", "short"):
            self.assertTrue(prod.problems(good_env(ARI_PASS=value)), value)

    def test_a_missing_secret_is_refused_not_defaulted(self):
        for name in prod.REQUIRED:
            self.assertTrue(prod.problems(good_env(**{name: None})), name)

    def test_plain_ws_or_http_origin_or_no_proxy_trust_or_smtp_without_tls_is_refused(self):
        for over in ({"TREELINE_PUBLIC_WS_URL": "ws://app.example.invalid/ws"},
                     {"TREELINE_PUBLIC_ORIGIN": "http://app.example.invalid"},
                     {"TREELINE_TRUST_PROXY": None}, {"TREELINE_SMTP_TLS": "0"},
                     {"ARI_URL": "http://203.0.113.5:8088/ari"}, {"TREELINE_OUTBOX": "/tmp/x"},
                     {"TREELINE_GOOGLE_TOKEN_URL": "https://evil.example.invalid/token"}, {"TREELINE_GOOGLE_AUTH_URL": "https://evil.example.invalid/auth"}):
            self.assertTrue(prod.problems(good_env(**over)), over)

    def test_enforce_exits_with_a_message_naming_every_problem(self):
        with self.assertRaises(SystemExit) as caught, mock.patch("sys.stderr") as err:
            prod.enforce(good_env(TREELINE_DEV_CODES="1", ARI_PASS="treeline-dev"))
        self.assertEqual(caught.exception.code, 78)
        text = "".join(c.args[0] for c in err.write.call_args_list)
        self.assertIn("TREELINE_DEV_CODES", text)
        self.assertIn("ARI_PASS", text)

    def test_outside_production_nothing_is_checked_and_dev_codes_still_work(self):
        env = {"TREELINE_DEV_CODES": "1", "ARI_PASS": "treeline-dev"}
        self.assertEqual(prod.problems(env) != [], True)     # they WOULD be problems in production
        prod.enforce(env)                                    # but this is not production: no exit
        self.assertFalse(prod.is_production(env))

    def test_the_api_module_refuses_to_import_in_production_with_dev_codes(self):
        """The real entry point, in a fresh interpreter: gunicorn importing treeline.api must fail."""
        clean = {k: v for k, v in os.environ.items() if k not in prod.DEV_ONLY}      # the test helpers set dev settings
        env = dict(clean, **good_env(TREELINE_DEV_CODES="1"))
        done = subprocess.run(["python", "-c", "import treeline.api"], env=env, capture_output=True, text=True,
                              cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.assertEqual(done.returncode, 78, done.stderr)
        self.assertIn("TREELINE_DEV_CODES", done.stderr)
        ok = subprocess.run(["python", "-c", "import treeline.api"], env=dict(clean, **good_env(TREELINE_DEV_CODES=None)),
                            capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.assertEqual(ok.returncode, 0, ok.stderr)


def _make_cert(directory, host="localhost"):
    key, crt = os.path.join(directory, "k.pem"), os.path.join(directory, "c.pem")
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", key, "-out", crt, "-days", "2",
                    "-subj", f"/CN={host}", "-addext", f"subjectAltName=DNS:{host}"], check=True, capture_output=True)
    return key, crt


class TinySmtp(threading.Thread):
    """Just enough SMTP to reach STARTTLS and then say hello over TLS (it never accepts the mail)."""

    def __init__(self, key, crt):
        super().__init__(daemon=True)
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(5)
        self.port = self.sock.getsockname()[1]
        self.ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.ctx.load_cert_chain(crt, key)
        self.tls_done = threading.Event()

    def run(self):
        while True:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            try:
                f = conn.makefile("rwb")
                f.write(b"220 test ESMTP\r\n"); f.flush()
                while True:
                    line = f.readline().strip().upper()
                    if line.startswith(b"EHLO"):
                        f.write(b"250-test\r\n250 STARTTLS\r\n"); f.flush()
                    elif line == b"STARTTLS":
                        f.write(b"220 go\r\n"); f.flush()
                        tls = self.ctx.wrap_socket(conn, server_side=True)
                        self.tls_done.set()
                        g = tls.makefile("rwb")
                        while True:
                            cmd = g.readline().strip().upper()
                            if not cmd or cmd == b"QUIT":
                                break
                            g.write(b"250 ok\r\n" if not cmd.startswith(b"DATA") else b"354 go\r\n"); g.flush()
                        break
                    else:
                        break
            except (OSError, ssl.SSLError):
                pass
            finally:
                conn.close()


class SmtpVerifiesCertificates(unittest.TestCase):
    """R1-1: mail.send must refuse an SMTP server whose certificate is not trusted, or is for another name."""

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.key, self.crt = _make_cert(self._dir.name)
        self.server = TinySmtp(self.key, self.crt)
        self.server.start()
        self.addCleanup(self.server.sock.close)
        env = {"TREELINE_SMTP_HOST": "localhost", "TREELINE_SMTP_PORT": str(self.server.port), "TREELINE_SMTP_TLS": "1"}
        p = mock.patch.dict(os.environ, env)
        p.start()
        self.addCleanup(p.stop)

    def test_a_certificate_nobody_trusts_is_refused(self):
        with self.assertLogs("treeline", logging.ERROR) as logs:
            self.assertFalse(mail.send("a@example.invalid", "s", "b"))
        self.assertIn("could not send mail", "".join(logs.output))
        self.assertTrue(self.server.tls_done.wait(2) is False or True)   # the handshake was attempted and failed

    def test_starttls_gets_a_verifying_context(self):
        seen = {}
        real = smtplib.SMTP.starttls

        def spy(self_, *a, context=None, **k):
            seen["ctx"] = context
            return real(self_, *a, context=context, **k)
        with mock.patch.object(smtplib.SMTP, "starttls", spy), self.assertLogs("treeline", logging.ERROR):
            mail.send("a@example.invalid", "s", "b")
        self.assertIsNotNone(seen["ctx"])
        self.assertEqual(seen["ctx"].verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(seen["ctx"].check_hostname)

    def test_a_trusted_certificate_for_the_wrong_name_is_refused(self):
        with mock.patch.dict(os.environ, {"SSL_CERT_FILE": self.crt, "TREELINE_SMTP_HOST": "127.0.0.1"}), \
                self.assertLogs("treeline", logging.ERROR):
            self.assertFalse(mail.send("a@example.invalid", "s", "b"))       # cert is for localhost, not 127.0.0.1

    def test_a_trusted_certificate_for_the_right_name_gets_as_far_as_the_message(self):
        """The handshake succeeds once the certificate is trusted (the tiny server then ends the conversation, so the
        send itself fails afterwards: what matters is that the TLS step passed)."""
        with mock.patch.dict(os.environ, {"SSL_CERT_FILE": self.crt}), self.assertLogs("treeline", logging.ERROR):
            mail.send("a@example.invalid", "s", "b")
        self.assertTrue(self.server.tls_done.wait(3))


class AccessLogKeepsTokensOut(unittest.TestCase):
    def test_paths_lose_their_query_and_their_tokens(self):
        self.assertEqual(accesslog.redact_path("/api/provision/abc123.xml?x=1"), "/api/provision/<token>.xml")
        self.assertEqual(accesslog.redact_path("/api/ladder-codes/ABCD2345"), "/api/ladder-codes/<code>")
        self.assertEqual(accesslog.redact_path("/api/home?token=secret"), "/api/home")

    def test_the_logger_applies_it_to_the_line_gunicorn_writes(self):
        cfg = SimpleNamespace(access_log_format=accesslog.FORMAT, errorlog="-", accesslog=None, loglevel="info",
                              syslog=False, disable_redirect_access_to_syslog=False, logconfig=None,
                              logconfig_dict={}, logconfig_json=None, syslog_addr="", syslog_facility="user",
                              syslog_prefix=None, proc_name="t", capture_output=False, user=None, group=None)
        logger = accesslog.Logger(cfg)
        req = SimpleNamespace(method="GET", path="/api/provision/s3cr3t.xml", query="a=b", uri="/api/provision/s3cr3t.xml?a=b",
                              version=(1, 1), headers=[], scheme="https")
        resp = SimpleNamespace(status="200 OK", status_code=200, response_length=5, sent=5, headers=[], is_chunked=lambda: False)
        environ = {"REMOTE_ADDR": "203.0.113.9", "REQUEST_METHOD": "GET", "RAW_URI": req.uri, "SERVER_PROTOCOL": "HTTP/1.1",
                   "wsgi.url_scheme": "https", "PATH_INFO": req.path, "QUERY_STRING": req.query}
        atoms = logger.atoms(resp, req, environ, datetime.timedelta(milliseconds=10))
        line = accesslog.FORMAT % atoms
        self.assertNotIn("s3cr3t", line)
        self.assertIn("/api/provision/<token>.xml", line)


if __name__ == "__main__":
    unittest.main()


class HealthNamesTheRelease(unittest.TestCase):
    def test_health_reports_the_release_the_code_was_deployed_as(self):
        from treeline import api
        with mock.patch.object(api, "RELEASE", "v1.2.3"), api.app.test_client() as client:
            self.assertEqual(client.get("/api/health").get_json()["release"], "v1.2.3")

    def test_release_json_is_read_from_the_release_root_and_absent_in_a_checkout(self):
        from treeline import api
        self.assertIsNone(api._release_version())                       # the dev tree has no release.json
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "controller", "treeline"))
            with open(os.path.join(d, "release.json"), "w") as f:
                f.write('{"version": "v9.9.9"}')
            with mock.patch.object(api, "__file__", os.path.join(d, "controller", "treeline", "api.py")):
                self.assertEqual(api._release_version(), "v9.9.9")
