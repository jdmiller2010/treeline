"""Tests for check_repo_rules.py:  python3 -m unittest scripts/test_check_repo_rules.py

Each test builds a throwaway git repo, so nothing here touches the real one. The "secrets" are made
up at run time (split strings), so this file itself passes the scanner.
"""

import os
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "check_repo_rules.py")

AWS_KEY = "AK" + "IA" + "ABCDEFGH12345678"
AGE_KEY = "AGE-SECRET-" + "KEY-1" + "Q" * 40
PEM = "-----BEGIN " + "RSA PRIVATE KEY-----"
HIGH_ENTROPY = "q8Zr3KfV9xLm2PtB7wYc4NdH6sJg5aEu"
PUBLIC_IP = "8.8." + "4.4"
OTHER_PUBLIC_IP = "8.8." + "8.8"
REAL_EMAIL = "parent.real" + "@gmail.com"
REAL_ACCOUNT_ARN = "arn:aws:iam::" + "210987654321" + ":user/x"


class Repo:
    def __init__(self):
        self.dir = tempfile.mkdtemp()
        self.git("init", "-q")
        self.git("config", "user.email", "t@example.com")
        self.git("config", "user.name", "t")

    def git(self, *a):
        return subprocess.run(["git", "-C", self.dir, *a], capture_output=True, text=True, check=True).stdout

    def write(self, path, text, add=True):
        full = os.path.join(self.dir, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write(text)
        if add:
            self.git("add", path)

    def commit(self, msg="c"):
        self.git("commit", "-q", "-m", msg)

    def scan(self, *args, env=None):
        e = {k: v for k, v in os.environ.items() if k != "REPO_RULES_EXTRA"}
        e.update(env or {})
        p = subprocess.run([sys.executable, SCRIPT, *args], cwd=self.dir, capture_output=True, text=True, env=e)
        return p.returncode, p.stdout + p.stderr


class Rules(unittest.TestCase):
    def setUp(self):
        self.r = Repo()

    def assertFinds(self, rule, **kw):
        code, out = self.r.scan(**kw)
        self.assertEqual(code, 1, out)
        self.assertIn(rule, out)
        return out

    def test_clean_repo_passes(self):
        self.r.write("README.md", "Contact jdmiller2010@gmail.com or a@example.com. Listen on 127.0.0.1 and 192.168.1.5.\n")
        self.r.write("deploy/env.example", "ARI_PASS=change-me\nTREELINE_SMTP_PASS=\n")
        code, out = self.r.scan()
        self.assertEqual(code, 0, out)

    def test_aws_key_is_found_and_not_printed_in_full(self):
        self.r.write("a.py", f'KEY = "{AWS_KEY}"\n')
        out = self.assertFinds("aws-access-key")
        self.assertNotIn(AWS_KEY, out)

    def test_private_keys(self):
        self.r.write("k.txt", PEM + "\nabc\n")
        self.assertFinds("private-key")
        self.r.write("k.txt", AGE_KEY + "\n")
        self.r.git("add", "k.txt")
        self.assertFinds("age-secret-key")

    def test_secret_looking_assignment_but_not_placeholders(self):
        self.r.write("c.py", f'api_token = "{HIGH_ENTROPY}"\n')
        self.assertFinds("secret-looking-value")
        self.r.write("c.py", 'api_token = "change-me-to-a-long-random-string-123"\nsecret = os.environ["TREELINE_X"]\n')
        code, out = self.r.scan()
        self.assertEqual(code, 0, out)

    def test_public_ip_found_private_and_docs_ranges_allowed_tests_exempt(self):
        self.r.write("n.md", f"family ip {PUBLIC_IP}\n")
        self.assertFinds("public-ip-address")
        self.r.write("n.md", "10.0.0.1 172.20.1.1 192.168.0.1 127.0.0.1 203.0.113.9 198.51.100.7 192.0.2.4 0.0.0.0\n")
        self.r.write("controller/tests/t.py", f'x = "{OTHER_PUBLIC_IP}"\n')
        code, out = self.r.scan()
        self.assertEqual(code, 0, out)

    def test_email_rules(self):
        self.r.write("a.md", REAL_EMAIL + "\n")
        self.assertFinds("email-address")
        self.r.write("a.md", "no-reply@treeline.invalid logo@2x.png someone@example.org ubuntu@app.treelinephone.com\n")
        code, out = self.r.scan()
        self.assertEqual(code, 0, out)

    def test_upstream_license_texts_are_not_scanned_but_the_same_line_anywhere_else_is(self):
        line = "licensing contact: " + REAL_EMAIL + " (via email)\n"
        self.r.write("asterisk/licenses/ASTERISK-LICENSE.txt", line)
        code, out = self.r.scan()
        self.assertEqual(code, 0, out)
        self.r.write("asterisk/other/LICENSE.txt", line)
        self.assertFinds("email-address")
        self.r.write("asterisk/other/LICENSE.txt", "nothing\n")
        self.r.write("asterisk/licenses-notes.md", line)          # a look-alike name is not the directory
        self.assertFinds("email-address")

    def test_aws_arn_with_a_real_looking_account_id(self):
        self.r.write("p.json", '"arn:aws:s3:::bucket" "' + REAL_ACCOUNT_ARN + '"\n')
        self.assertFinds("aws-arn-with-account-id")
        self.r.write("p.json", '"arn:aws:iam::123456789012:user/fake"\n')
        code, out = self.r.scan()
        self.assertEqual(code, 0, out)

    def test_forbidden_files(self):
        for path in (".env", "deploy/.env", "x/server.pem", "data/treeline.db", "infra/.local/vm-credentials",
                     "cdk.context.json", "id_ed25519", "backup.agekey", "data/households/4.db-wal", "x/1.db-journal",
                     "central/20261119T030000Z.db.age", "pre-migrate/1-v1-20261119T000000-abc123.db", "backups/central/x.txt"):
            r = Repo()
            r.write(path, "x\n")
            code, out = r.scan()
            self.assertEqual(code, 1, f"{path}: {out}")
            self.assertIn("forbidden-file", out, path)
        r = Repo()
        r.write("deploy/env.example", "A=b\n")
        r.write("data/.gitkeep", "")
        code, out = r.scan()
        self.assertEqual(code, 0, out)

    def test_allow_marker(self):
        self.r.write("n.md", "stun at 8.8.4.4  <!-- repo-rules: allow -->\n")
        code, out = self.r.scan()
        self.assertEqual(code, 0, out)

    def test_local_deny_list_from_file_and_env_never_printed_in_full(self):
        self.r.write("plan.md", "meet at Maple Hollow Park\n")
        code, out = self.r.scan(env={"REPO_RULES_EXTRA": "# places\nmaple hollow\n"})
        self.assertEqual(code, 1, out)
        self.assertIn("local-deny-list", out)
        self.assertNotIn("Maple Hollow", out)
        self.r.write(".repo-rules.local", "maple hollow\n", add=False)
        code, out = self.r.scan()
        self.assertEqual(code, 1, out)

    def test_local_deny_list_file_itself_cannot_be_committed(self):
        self.r.write(".repo-rules.local", "maple hollow\n")
        self.assertFinds("forbidden-file")

    def test_staged_scan_reads_the_index_not_the_working_copy(self):
        self.r.write("a.py", "x = 1\n")
        self.r.commit()
        self.r.write("a.py", f'KEY = "{AWS_KEY}"\n')                 # staged
        self.r.write("a.py", "x = 2\n", add=False)                     # working copy is clean again
        code, out = self.r.scan("--staged")
        self.assertEqual(code, 1, out)
        self.assertIn("aws-access-key", out)

    def test_range_finds_a_secret_that_was_committed_then_deleted(self):
        self.r.write("a.py", "x = 1\n")
        self.r.commit("base")
        base = self.r.git("rev-parse", "HEAD").strip()
        self.r.write("a.py", f'KEY = "{AWS_KEY}"\n')
        self.r.commit("oops")
        self.r.write("a.py", "x = 1\n")
        self.r.commit("remove it")
        code, out = self.r.scan()                                      # the tree is clean...
        self.assertEqual(code, 0, out)
        code, out = self.r.scan("--range", f"{base}..HEAD")            # ...the history is not
        self.assertEqual(code, 1, out)
        self.assertIn("aws-access-key", out)


if __name__ == "__main__":
    unittest.main()
