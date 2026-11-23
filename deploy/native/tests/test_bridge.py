"""treeline_bridge: the root side of the admin page (docs/ADMIN.md). The app that writes the requests is treated as hostile here."""
import json
import os
import pathlib
import shutil
import stat
import subprocess
import tempfile
import time
import unittest

import helpers  # noqa: F401  (puts deploy/native/bin on the path)
import treeline_bridge as b

ME = os.getuid()
RID = "0123456789abcdef0123456789abcdef"


def request(**over):
    req = {"v": 1, "id": RID, "op": "logs", "source": "deploy", "lines": 50, "since": "1h", "by": "owner@example.com",
           "t": int(time.time())}
    req.update(over)
    return req


class Folders(unittest.TestCase):
    def setUp(self):
        self.d = pathlib.Path(tempfile.mkdtemp(prefix="bridge-"))
        self.addCleanup(shutil.rmtree, self.d, True)
        self.req, self.out, self.victim = self.d / "req", self.d / "out", self.d / "victim"
        for p in (self.req, self.out, self.victim):
            p.mkdir()
        (self.victim / "secret").write_text("root only")
        self.audit = self.d / "audit.log"
        self.journal_calls = []

    def journal(self, req):
        self.journal_calls.append(b.journal_command(req))
        return "line one\nline two from 203.0.113.9 \x1b[2J", False

    def put(self, name, data):
        p = self.req / name
        p.write_bytes(data if isinstance(data, bytes) else json.dumps(data).encode())
        return p

    def run_bridge(self, **kw):
        return b.run_once(ME, req_dir=str(self.req), out_dir=str(self.out), journal=self.journal, audit_path=str(self.audit), **kw)

    def result(self, rid=RID):
        return json.loads((self.out / f"{rid}.json").read_text())


class ValidRequests(Folders):
    def test_a_good_request_is_answered_with_the_journal_and_audited_without_the_text(self):
        self.put(RID + ".json", request())
        self.assertEqual(self.run_bridge(), [(RID, "ok")])
        r = self.result()
        self.assertEqual((r["status"], r["source"], r["text"]), ("ok", "deploy", "line one\nline two from [ip] "), "cleaned on the way out")
        self.assertEqual(stat.S_IMODE(os.stat(self.out / f"{RID}.json").st_mode), 0o640)
        self.assertEqual(os.listdir(self.req), [], "the request is gone")
        line = json.loads(self.audit.read_text().splitlines()[-1])
        self.assertEqual((line["op"], line["source"], line["by"], line["outcome"]), ("logs", "deploy", "owner@example.com", "ok"))
        self.assertNotIn("line one", self.audit.read_text(), "no log text in the audit")
        self.assertEqual(stat.S_IMODE(os.stat(self.audit).st_mode), 0o600)

    def test_the_command_is_built_only_from_the_fixed_tables(self):
        self.put(RID + ".json", request(source="caddy", lines=7, since="boot"))
        self.run_bridge()
        self.assertEqual(self.journal_calls, [["/usr/bin/journalctl", "--no-pager", "-q", "--no-hostname", "-o", "short-iso", "-n", "7", "-b",
                                               "-u", "caddy.service"]])

    def test_the_api_and_the_controller_are_not_sources(self):
        """They log calls and emails (docs/ADMIN.md): only after their logging is cleaned up."""
        for name in ("api", "controller", "treeline-api", "asterisk", "../etc/shadow", "-u ssh"):
            self.assertNotIn(name, b.SOURCES)
        flat = " ".join(" ".join(v) for v in b.SOURCES.values())
        self.assertNotIn("treeline-api", flat)
        self.assertNotIn("treeline-controller", flat)
        self.assertNotIn("asterisk", flat)


class WhatIsRefused(Folders):
    def refused(self, req_or_bytes, name=RID + ".json"):
        self.put(name, req_or_bytes)
        out = self.run_bridge()
        self.assertEqual(self.journal_calls, [], "nothing was run")
        self.assertEqual(os.listdir(self.req), [])
        return out

    def test_bad_values(self):
        now = int(time.time())
        for bad in (request(v=2), request(op="deploy"), request(op="shell"), request(source="api"), request(source=["deploy"]),
                    request(lines=0), request(lines=1001), request(lines=True), request(lines=5.0), request(lines="5"),
                    request(since="1y"), request(since="--since=yesterday"), request(by="a b"), request(by="x" * 201), request(by=""),
                    request(t=now - 3600), request(t=now + 3600), request(t=float(now)), request(id="0" * 32)):
            with self.subTest(bad=bad):
                self.journal_calls.clear()
                out = self.refused(bad)
                self.assertTrue(out[0][1].startswith("refused"), out)

    def test_wrong_shapes(self):
        for data in (b"not json", b"[1,2]", b'{"v":1}', json.dumps(dict(request(), extra=1)).encode(),
                     b'{"v":1,"v":1,"id":"' + RID.encode() + b'","op":"logs","source":"deploy","lines":5,"since":"1h","by":"a","t":1}',
                     json.dumps(request()).replace('"lines": 50', '"lines": NaN').encode(), b"\xff\xfe"):
            with self.subTest(data=data[:40]):
                self.journal_calls.clear()
                out = self.refused(data)
                self.assertIn("refused", out[0][1])

    def test_the_answer_to_a_refused_request_says_why(self):
        self.refused(request(source="api"))
        self.assertEqual(self.result()["status"], "refused")
        self.assertIn("unknown log source", self.result()["reason"])


class HostileFolderContents(Folders):
    """What a compromised app (uid treeline) can put in the one folder it may write."""

    def test_a_directory_a_nest_and_odd_names_are_removed_and_nothing_is_followed(self):
        (self.req / (RID + ".json")).mkdir()                               # a directory with a request's name
        deep = self.req / "x.json" / "y" / "z"
        deep.mkdir(parents=True)
        (deep / "f").write_text("x")
        os.symlink(self.victim, self.req / "link-to-victim")
        os.symlink(self.victim / "secret", self.req / ("a" * 32 + ".json"))  # a link with a request's name
        os.link(self.victim / "secret", self.req / ("b" * 32 + ".json"))     # a hard link to a file root cares about
        os.mkfifo(self.req / ("c" * 32 + ".json"))                           # would block a plain open()
        (self.req / "README").write_text("hello")
        out = dict(self.run_bridge())
        self.assertEqual(os.listdir(self.req), [], "everything is gone, whatever it was")
        self.assertEqual((self.victim / "secret").read_text(), "root only", "nothing was followed or truncated")
        self.assertEqual(os.listdir(self.victim), ["secret"])
        self.assertEqual(self.journal_calls, [])
        self.assertIn("refused", out["a" * 32 + ".json"])
        self.assertIn("other links", out["b" * 32 + ".json"])
        self.assertIn("not a plain file", out["c" * 32 + ".json"])

    def test_a_file_owned_by_someone_else_or_too_large_is_refused(self):
        self.put(RID + ".json", request())
        out = b.run_once(ME + 1, req_dir=str(self.req), out_dir=str(self.out), journal=self.journal, audit_path=str(self.audit))
        self.assertIn("not written by the app", out[0][1])
        self.put("d" * 32 + ".json", b"{" + b" " * 600 + b"}")
        self.assertIn("too large", self.run_bridge()[0][1])

    def test_a_flood_is_answered_up_to_the_cap_and_the_rest_is_removed(self):
        for i in range(b.MAX_PER_RUN + 15):
            rid = f"{i:032x}"
            self.put(rid + ".json", request(id=rid))
        out = self.run_bridge()
        self.assertEqual(sum(1 for _, o in out if o == "ok"), b.MAX_PER_RUN)
        self.assertEqual(sum(1 for _, o in out if o.startswith("dropped")), 15)
        self.assertEqual(os.listdir(self.req), [])

    def test_the_results_folder_cannot_be_used_against_us(self):
        """A planted link where our temporary file goes is replaced, not written through."""
        os.symlink(self.victim / "secret", self.out / f".{RID}.tmp")
        self.put(RID + ".json", request())
        self.run_bridge()
        self.assertEqual((self.victim / "secret").read_text(), "root only")
        self.assertEqual(self.result()["status"], "ok")

    def test_the_request_folder_itself_being_a_link_is_refused(self):
        shutil.rmtree(self.req)
        os.symlink(self.victim, self.req)
        with self.assertRaises(OSError):
            self.run_bridge()
        self.assertEqual(os.listdir(self.victim), ["secret"])


class Sweep(Folders):
    def test_old_answers_and_anything_odd_go(self):
        (self.out / "new.json").write_text("{}")
        (self.out / "old.json").write_text("{}")
        os.utime(self.out / "old.json", (time.time() - 1000, time.time() - 1000))
        (self.out / "planted").mkdir()
        os.symlink(self.victim, self.out / "link")
        removed = b.sweep(str(self.out))
        self.assertEqual(sorted(os.listdir(self.out)), ["new.json"])
        self.assertEqual(sorted(removed), ["link", "old.json", "planted"])
        self.assertEqual(os.listdir(self.victim), ["secret"])


class Cleaning(unittest.TestCase):
    def test_addresses_accounts_and_control_characters(self):
        cases = {
            "tls handshake error from 203.0.113.7:4433": "tls handshake error from [ip]:4433",
            "from [2001:db8::1]:443 and fe80::1": "from [[ip]]:443 and [ip]",
            "mailed parent@example.com ok": "mailed [email] ok",
            "s3://treeline-backups-123456789012-us-west-2/x": "s3://treeline-backups-[account]-us-west-2/x",
            "\x1b[31mred\x1b[0m\x07": "red",
            "2026-11-23T18:58:35+00:00 started at 18:58:35": "2026-11-23T18:58:35+00:00 started at 18:58:35",
            "release v0.2.0 build 24.0.0-t1": "release v0.2.0 build 24.0.0-t1",
        }
        for raw, want in cases.items():
            self.assertEqual(b.clean(raw), want, raw)

    def test_long_output_keeps_the_newest_lines_and_says_so(self):
        lines = b"".join(b"line %06d\n" % i for i in range(60000))
        text, truncated = b.read_logs(request(), run=lambda *a, **k: subprocess.CompletedProcess(a, 0, lines, b""))
        self.assertTrue(truncated)
        self.assertLessEqual(len(text), b.MAX_OUTPUT)
        self.assertTrue(text.rstrip().endswith("line 059999"))
        self.assertTrue(text.startswith("line "), "no half line at the top")

    def test_the_journal_runs_with_an_empty_environment_and_no_input(self):
        seen = {}
        def run(cmd, **kw):
            seen.update(kw)
            return subprocess.CompletedProcess(cmd, 0, b"x", b"")
        b.read_logs(request(), run=run)
        self.assertEqual(seen["env"], {})
        self.assertIs(seen["stdin"], subprocess.DEVNULL)
        self.assertNotIn("shell", seen)

    def test_a_journal_that_hangs_or_fails_becomes_a_message(self):
        def hang(*a, **k):
            raise subprocess.TimeoutExpired("journalctl", 10)
        self.assertIn("too long", b.read_logs(request(), run=hang)[0])
        self.assertIn("failed", b.read_logs(request(), run=lambda *a, **k: subprocess.CompletedProcess(a, 1, b"", b"no journal"))[0])


class MatchesTheApp(unittest.TestCase):
    def test_the_app_offers_exactly_the_sources_and_ranges_the_bridge_accepts(self):
        import ast
        src = (helpers.ROOT / "controller" / "treeline" / "admin.py").read_text()
        values = {}
        for node in ast.parse(src).body:
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id in ("LOG_SOURCES", "LOG_SINCE"):
                values[node.targets[0].id] = ast.literal_eval(node.value)
        self.assertEqual(tuple(values["LOG_SOURCES"]), tuple(b.SOURCES))
        self.assertEqual(tuple(values["LOG_SINCE"]), tuple(b.SINCE))


if __name__ == "__main__":
    unittest.main()
