"""treeline-admin: the way the first admin is made, over ssh (docs/ADMIN.md)."""
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

import helpers

tool = helpers.load("treeline-admin")
ROOT = helpers.ROOT


class Fake:
    def __init__(self, stdout="", returncode=0, stderr=""):
        self.calls = []
        self.result = subprocess.CompletedProcess([], returncode, stdout, stderr)

    def __call__(self, cmd, **kw):
        self.calls.append((cmd, kw))
        return self.result


class Held:
    def close(self):
        pass


def run(argv, fake, **kw):
    return tool.main(argv, run=fake, lock=lambda: Held(), release=lambda: "/opt/treeline/releases/v1.0.0", env=lambda: {"A": "b"}, **kw)


class Cli(unittest.TestCase):
    def test_bad_usage_is_refused(self):
        for argv in ([], ["bogus"], ["add"], ["add", "a", "b"], ["list", "x"], ["remove"]):
            self.assertEqual(run(argv, Fake()), 2, argv)

    def test_add_runs_the_apps_own_code_as_the_app_user_and_says_what_happened(self):
        fake = Fake(json.dumps({"email": "me@example.com", "is_grown_up": True}))
        self.assertEqual(run(["add", "Me@Example.com"], fake), 0)
        cmd, kw = fake.calls[0]
        self.assertEqual(cmd[:4], ["runuser", "-u", "treeline", "--"])
        self.assertEqual(cmd[4], "/opt/treeline/releases/v1.0.0/venv/bin/python")
        self.assertEqual(cmd[5:7], ["-I", "-c"])
        self.assertEqual(cmd[8:10], ["add", "Me@Example.com"], "the address is an argument, never part of the code or a shell line")
        self.assertEqual(kw["cwd"], "/opt/treeline/releases/v1.0.0")

    def test_an_address_that_is_not_a_grown_up_gets_a_plain_warning(self):
        import io, contextlib
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            run(["add", "x@example.com"], Fake(json.dumps({"email": "x@example.com", "is_grown_up": False})))
        self.assertIn("cannot sign in yet", out.getvalue())

    def test_an_error_from_the_app_code_is_shown_and_fails(self):
        self.assertEqual(run(["remove", "a@example.com"], Fake(json.dumps({"error": "that is the last admin: add another first"}))), 1)

    def test_a_crash_or_garbage_fails_without_a_traceback(self):
        self.assertEqual(run(["list"], Fake("", 1, "boom")), 1)
        self.assertEqual(run(["list"], Fake("not json")), 1)

    def test_who_ran_it_is_recorded_and_cleaned(self):
        self.assertEqual(tool.who_ran_it({"SUDO_USER": "owner"}), "ssh:owner")
        self.assertEqual(tool.who_ran_it({"LOGNAME": "x y;rm"}), "ssh:xyrm")
        self.assertEqual(tool.who_ran_it({}), "ssh:root")

    def test_it_will_not_run_under_a_deploy(self):
        path = tempfile.mkdtemp() + "/deploy.lock"
        import fcntl
        deploy = open(path, "a")
        fcntl.flock(deploy, fcntl.LOCK_EX | fcntl.LOCK_NB)            # what a running deploy holds
        try:
            with self.assertRaises(SystemExit) as cm:
                tool.hold_deploy_lock(path)
            self.assertIn("deploy is running", str(cm.exception))
        finally:
            deploy.close()
        tool.hold_deploy_lock(path).close()                            # free again


class TheRealCode(unittest.TestCase):
    """The code the tool hands to the app's python, run against a real (temporary) database: no fake of the part that matters."""

    def go(self, db_path, op, email="-", who="ssh:test"):
        env = {"PATH": os.environ.get("PATH", ""), "TREELINE_DB": db_path}
        done = subprocess.run([sys.executable, "-I", "-c", tool.CODE, op, email, who], cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr)
        return json.loads(done.stdout.strip().splitlines()[-1])

    def test_add_list_remove_and_the_last_admin_rule_and_the_audit_row(self):
        db_path = os.path.join(tempfile.mkdtemp(), "t.db")
        self.assertEqual(self.go(db_path, "list")["admins"], [])
        self.assertEqual(self.go(db_path, "add", "First@Example.com")["email"], "first@example.com")
        self.assertEqual([a["added_by"] for a in self.go(db_path, "list")["admins"]], ["ssh:test"])
        self.assertIn("last admin", self.go(db_path, "remove", "first@example.com")["error"])
        self.assertTrue(self.go(db_path, "add", "second@example.com")["email"])
        self.assertEqual(self.go(db_path, "remove", "first@example.com")["email"], "first@example.com")
        self.assertEqual(self.go(db_path, "add", "first@example.com")["email"], "first@example.com", "a removed admin can be brought back")
        self.assertIn("not an email", self.go(db_path, "add", "nonsense")["error"])
        import sqlite3
        rows = sqlite3.connect(db_path).execute("SELECT email, action, target_id FROM admin_audit ORDER BY id").fetchall()
        self.assertEqual([r[1] for r in rows], ["admin_add", "admin_add", "admin_remove", "admin_add"])
        self.assertTrue(all(r[0] == "ssh:test" for r in rows))


class Installed(unittest.TestCase):
    def test_install_sh_links_it_next_to_the_other_tools(self):
        text = (ROOT / "deploy" / "native" / "install.sh").read_text()
        self.assertRegex(text, r"for t in [^;]*\btreeline-admin\b[^;]*; do ln -sf")
        self.assertTrue(os.access(ROOT / "deploy" / "native" / "bin" / "treeline-admin", os.X_OK))


if __name__ == "__main__":
    unittest.main()
