"""treeline_bridge: the root side of the admin page (docs/ADMIN.md). The app that writes the requests is treated as hostile here."""
import json
import re
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
            '"uri":"/api/pair/status?token=Zx9_secret-Token"': '"uri":"/api/pair/status?[query]"',
            "GET /api/provision/abc?x=1&token=s3cr3t HTTP/1.1": "GET /api/provision/abc?[query] HTTP/1.1",
            "failed: token=abc123 and password=hunter2": "failed: token=[hidden] and password=[hidden]",
            "what? nothing to hide here": "what? nothing to hide here",
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


class Installed(unittest.TestCase):
    def test_install_sh_installs_enables_and_starts_the_units(self):
        text = (helpers.ROOT / "deploy" / "native" / "install.sh").read_text()
        self.assertIn('"$S"/*.path', text)
        enable = re.search(r"systemctl enable asterisk[^\n]*", text).group(0)
        start = re.search(r"systemctl start treeline-certsync[^\n]*", text).group(0)
        for unit in ("treeline-bridge.path", "treeline-bridge-sweep.timer", "treeline-bridge-releases.timer", "treeline-bridge-deploy.path"):
            self.assertIn(unit, enable)
            self.assertIn(unit, start)
        self.assertNotIn("treeline-bridge.service", enable, "the service is started by its path unit, never on its own")
        for name in ("treeline-bridge.path", "treeline-bridge.service", "treeline-bridge-sweep.service", "treeline-bridge-sweep.timer"):
            self.assertTrue((helpers.ROOT / "deploy" / "native" / "systemd" / name).is_file(), name)

    def test_the_api_may_write_the_request_folder_and_nothing_else_of_the_bridge(self):
        unit = (helpers.ROOT / "deploy" / "native" / "systemd" / "treeline-api.service").read_text()
        rw = re.search(r"^ReadWritePaths=(.*)$", unit, re.M).group(1).split()
        self.assertIn("-/var/lib/treeline/bridge/req", rw)
        self.assertIn("-/var/lib/treeline/bridge/deploy-req", rw)
        self.assertFalse([p for p in rw if "bridge" in p and p not in ("-/var/lib/treeline/bridge/req", "-/var/lib/treeline/bridge/deploy-req")])


class CleaningIsFast(unittest.TestCase):
    def test_a_whole_answer_of_hostile_shapes_is_cleaned_quickly(self):
        """An unbounded email pattern was quadratic on a long line with no spaces (it took minutes)."""
        for text in ("é\u2603" * 130000, ("a" * 5000 + "@" + "b" * 5000) * 25, ":" * 260000, "1." * 130000, "?=" * 130000):
            start = time.time()
            b.clean(text[:b.MAX_OUTPUT])
            self.assertLess(time.time() - start, 2.0, text[:20])


class Releases(Folders):
    def test_the_report_from_the_agent_is_rechecked_and_written_for_the_app(self):
        report = {"current": "v0.2.0", "previous": None, "failed": [], "asterisk": "24.0.0-t1", "error": None,
                  "published": [{"version": "v0.3.0", "published_at": "2026-11-24T10:00:00Z", "newer": True, "failed": False}]}
        seen = []
        def run(cmd, **kw):
            seen.append((cmd, kw))
            return subprocess.CompletedProcess(cmd, 0, json.dumps(report) + "\n", "")
        out = b.refresh_releases(out_dir=str(self.out), run=run)
        self.assertEqual(seen[0][0], ["/usr/local/sbin/treeline-deploy", "releases"])
        self.assertIs(seen[0][1]["stdin"], subprocess.DEVNULL)
        written = json.loads((self.out / "releases.json").read_text())
        self.assertEqual(written["current"], "v0.2.0")
        self.assertEqual(written, out)
        self.assertEqual(stat.S_IMODE(os.stat(self.out / "releases.json").st_mode), 0o640)

    def test_an_agent_that_says_something_else_becomes_an_error_not_a_crash(self):
        for stdout in ("", "not json", json.dumps({"current": "v1"}), json.dumps([1])):
            out = b.refresh_releases(out_dir=str(self.out), run=lambda *a, **k: subprocess.CompletedProcess(a, 1, stdout, "boom 203.0.113.5"))
            self.assertEqual(out["published"], [])
            self.assertIn("did not answer", out["error"])
            self.assertNotIn("203.0.113.5", out["error"], "cleaned like a log")

    def test_the_sweep_keeps_the_releases_report(self):
        (self.out / "releases.json").write_text("{}")
        os.utime(self.out / "releases.json", (time.time() - 5000, time.time() - 5000))
        b.sweep(str(self.out))
        self.assertTrue((self.out / "releases.json").exists())


class AgentReleases(unittest.TestCase):
    """treeline-deploy's read-only `releases` report."""

    deploy = helpers.load("treeline-deploy")

    def test_only_published_plain_versions_newest_first(self):
        gh = [{"tag_name": "v0.2.0", "draft": False, "prerelease": False, "published_at": "2026-11-22T02:58:38Z"},
              {"tag_name": "asterisk-24.0.0-t1", "draft": False, "prerelease": True},
              {"tag_name": "v0.10.0", "draft": False, "prerelease": False, "published_at": "2026-12-01T00:00:00Z"},
              {"tag_name": "v0.3.0", "draft": True, "prerelease": False},
              {"tag_name": "v0.1.1", "draft": False, "prerelease": False, "published_at": "<script>"},
              "junk", {"tag_name": 5}]
        self.assertEqual(self.deploy.published(gh), [("v0.10.0", "2026-12-01T00:00:00Z"), ("v0.2.0", "2026-11-22T02:58:38Z"), ("v0.1.1", None)])
        with self.assertRaises(self.deploy.Failed):
            self.deploy.published({"message": "rate limited"})

    def test_the_report_marks_newer_and_failed_and_survives_github_being_down(self):
        d = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        (d / "releases" / "v0.2.0").mkdir(parents=True)
        os.symlink(d / "releases" / "v0.2.0", d / "current")
        p = {"state": str(d / "state"), "releases": str(d / "releases"), "current": str(d / "current"), "run": str(d / "lock")}
        self.deploy.record(p, current="v0.2.0", previous="v0.1.1", failed=["v0.3.0"])
        from unittest import mock
        gh = json.dumps([{"tag_name": t, "draft": False, "prerelease": False, "published_at": None} for t in ("v0.3.0", "v0.4.0", "v0.2.0")]).encode()
        env = {"TREELINE_RELEASE_REPO": "owner/repo"}
        with mock.patch.object(self.deploy, "https_get", lambda *a, **k: gh), mock.patch.object(self.deploy, "running_asterisk_id", lambda *a: "24.0.0-t1"):
            r = self.deploy.releases_report(p, env)
        self.assertEqual((r["current"], r["previous"], r["failed"], r["asterisk"], r["error"]), ("v0.2.0", "v0.1.1", ["v0.3.0"], "24.0.0-t1", None))
        self.assertEqual([(x["version"], x["newer"], x["failed"]) for x in r["published"]],
                         [("v0.4.0", True, False), ("v0.3.0", True, True), ("v0.2.0", False, False)])
        def down(*a, **k):
            raise OSError("network is unreachable")
        with mock.patch.object(self.deploy, "https_get", down), mock.patch.object(self.deploy, "running_asterisk_id", lambda *a: None):
            r = self.deploy.releases_report(p, env)
        self.assertEqual(r["published"], [])
        self.assertIn("could not read", r["error"])
        self.assertEqual(r["current"], "v0.2.0", "what runs is still reported")


def deploy_request(**over):
    req = {"v": 1, "id": RID, "op": "deploy", "version": "v0.4.0", "retry": False, "by": "owner@example.com", "t": int(time.time())}
    req.update(over)
    return req


class DeployOp(Folders):
    """The Install button's root half. The agent itself is replaced by a recorder; the VM job runs the real one."""

    def setUp(self):
        super().setUp()
        self.state = self.d / "deploy-state.json"
        self.report = {"current": "v0.3.0", "previous": "v0.2.0", "failed": ["v0.3.5"], "asterisk": "24.0.0-t1", "error": None,
                       "published": [{"version": v, "published_at": None, "newer": True, "failed": False} for v in ("v0.4.0", "v0.3.5", "v0.3.0", "v0.2.0")]}
        self.agent_calls, self.agent_exit = [], 0

    def fake_agent(self, cmd, **kw):
        self.agent_calls.append((cmd, kw))
        if cmd[1:] == ["releases"]:
            return subprocess.CompletedProcess(cmd, 0, json.dumps(self.report) + "\n", "")
        return subprocess.CompletedProcess(cmd, self.agent_exit, "v0.4.0 is healthy from 203.0.113.9", "")

    def deploy(self, **kw):
        return b.deploy_once(ME, req_dir=str(self.req), out_dir=str(self.out), run=self.fake_agent, audit_path=str(self.audit), state_path=str(self.state), **kw)

    def status(self):
        return json.loads((self.out / "deploy-status.json").read_text())

    def test_a_good_request_runs_exactly_the_agent_with_the_version_and_reports_healthy(self):
        self.put(RID + ".json", deploy_request())
        self.assertEqual(self.deploy(), "healthy")
        cmd, kw = self.agent_calls[-1]
        self.assertEqual(cmd, ["/usr/local/sbin/treeline-deploy", "--version", "v0.4.0", "--wait", "600"])
        self.assertEqual(kw["env"], {"PATH": "/usr/sbin:/usr/bin:/sbin:/bin"})
        self.assertIs(kw["stdin"], subprocess.DEVNULL)
        st = self.status()
        self.assertEqual((st["state"], st["version"], st["from"], st["exit"]), ("healthy", "v0.4.0", "v0.3.0", 0))
        self.assertNotIn("203.0.113.9", st["output"], "the agent's output is cleaned like a log")
        self.assertEqual(os.listdir(self.req), [])
        self.assertIn('"outcome": "healthy"', self.audit.read_text())

    def test_each_exit_code_has_its_own_state(self):
        for code, state in ((1, "rolled_back"), (3, "refused"), (4, "busy"), (5, "needs_operator"), (9, "needs_operator")):
            self.state.unlink(missing_ok=True)
            self.agent_exit = code
            self.put(RID + ".json", deploy_request())
            self.assertEqual(self.deploy(), state, code)
            self.assertEqual(self.status()["state"], state)

    def test_what_the_agent_does_not_list_or_that_is_not_newer_is_never_asked_for(self):
        for over, why in (({"version": "v9.9.9"}, "not a published release"), ({"version": "v0.3.0"}, "not newer"),
                          ({"version": "v0.2.0"}, "not newer"), ({"version": "v0.3.5"}, "failed before")):
            with self.subTest(over=over):
                self.state.unlink(missing_ok=True)
                self.agent_calls.clear()
                self.put(RID + ".json", deploy_request(**over))
                self.assertEqual(self.deploy(), "refused")
                self.assertIn(why, self.status()["reason"])
                self.assertEqual([c for c, _ in self.agent_calls if "--version" in c], [], "the agent was not asked to install")

    def test_a_release_that_failed_before_needs_an_explicit_retry(self):
        self.put(RID + ".json", deploy_request(version="v0.3.5", retry=True))
        self.report["current"] = "v0.3.0"
        self.assertEqual(self.deploy(), "healthy")

    def test_bad_requests_are_refused_before_the_agent_is_even_asked(self):
        for bad in (deploy_request(version="v0.4.0-rc1"), deploy_request(version="v04.0.0"), deploy_request(version="asterisk-24.0.0-t1"),
                    deploy_request(version="v0.4.0 --force"), deploy_request(version="--tarball=/tmp/x"), deploy_request(retry="yes"),
                    deploy_request(op="logs"), dict(deploy_request(), extra=1), deploy_request(t=0)):
            with self.subTest(bad=bad):
                self.agent_calls.clear()
                self.put(RID + ".json", bad)
                self.assertEqual(self.deploy(), "refused")
                self.assertEqual(self.agent_calls, [], "not even the read-only report")

    def test_one_install_at_a_time_and_a_cooldown_between_them(self):
        for i in range(3):
            rid = f"{i:032x}"
            self.put(rid + ".json", deploy_request(id=rid))
        self.assertEqual(self.deploy(), "healthy")
        self.assertEqual(sum(1 for c, _ in self.agent_calls if "--version" in c), 1)
        self.assertEqual(os.listdir(self.req), [], "the others were dropped, not queued")
        self.put(RID + ".json", deploy_request(version="v0.4.0"))
        self.report["current"] = "v0.3.0"
        self.assertEqual(self.deploy(), "refused")
        self.assertIn("a few minutes ago", self.status()["reason"])

    def test_hostile_folder_contents_are_removed_and_never_followed(self):
        (self.req / (RID + ".json")).mkdir()
        os.symlink(self.victim / "secret", self.req / ("a" * 32 + ".json"))
        os.mkfifo(self.req / ("c" * 32 + ".json"))
        self.assertIsNone(self.deploy())
        self.assertEqual(os.listdir(self.req), [])
        self.assertEqual((self.victim / "secret").read_text(), "root only")
        self.assertEqual(self.agent_calls, [])

    def test_the_sweep_keeps_the_install_status(self):
        (self.out / "deploy-status.json").write_text("{}")
        os.utime(self.out / "deploy-status.json", (time.time() - 9000, time.time() - 9000))
        b.sweep(str(self.out))
        self.assertTrue((self.out / "deploy-status.json").exists())


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
