"""Tests for scripts/ci_gate.py: which changes may skip the VM-imitation job."""
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import ci_gate  # noqa: E402


class Gate(unittest.TestCase):
    def test_a_small_ui_change_does_not_need_the_vm(self):
        for paths in (["web/parent/js/home.js"], ["web/phone/js/phone.js", "web/tests/phone_calls.py"], ["design/ui/css/treeline.css"],
                      ["docs/PLAN.md", "README.md"], ["web/shared/ui.js", "THIRD_PARTY_NOTICES.md"], ["testphones/run_scenarios.py"],
                      ["controller/tests/test_calls.py"], ["infra/treeline_infra/config.py"]):
            self.assertFalse(ci_gate.needs_vm(paths), paths)

    def test_anything_that_could_touch_the_install_or_the_machine_does(self):
        for path in ("deploy/native/install.sh", "deploy/native/bin/treeline-deploy", "deploy/native/systemd/asterisk.service",
                     "deploy/native/templates/asterisk/pjsip.conf", "deploy/fail2ban/filter.d/treeline-asterisk.conf", "deploy/native/ci/vm_test.py",
                     "scripts/build_release.sh", "scripts/asterisk_build.py", "asterisk/build/build.sh", "asterisk/config/modules.conf",
                     "asterisk/Dockerfile", "controller/treeline/api.py", "controller/treeline/calls.py", "controller/requirements-prod.lock",
                     ".github/workflows/vm-imitation.yml", ".github/workflows/release.yml", ".github/workflows/asterisk.yml"):
            self.assertTrue(ci_gate.needs_vm([path]), path)

    def test_one_path_of_the_other_kind_is_enough(self):
        self.assertTrue(ci_gate.needs_vm(["web/parent/js/home.js", "deploy/native/install.sh"]))
        self.assertTrue(ci_gate.needs_vm(["README.md", "controller/treeline/db.py"]))

    def test_what_the_list_has_never_heard_of_runs_the_job(self):
        for path in ("brand-new-directory/file.py", "Makefile", "docker-compose.yml", "dev", ".github/workflows/new.yml", "webextras/x.js",
                     "docs.sh", "scripts/something_new.py", "web", ""):
            self.assertTrue(ci_gate.needs_vm([path]), path)

    def test_nothing_to_compare_runs_the_job(self):
        self.assertTrue(ci_gate.needs_vm([]))
        self.assertTrue(ci_gate.needs_vm(["", "  "]))

    def test_look_alike_names_are_not_the_safe_directories(self):
        for path in ("webhook/x.py", "design-notes/x", "docs-build/x", "infrastructure/x", "READMEx", "controller/tests-helper/x.py"):
            self.assertTrue(ci_gate.needs_vm([path]), path)

    def test_every_workflow_and_every_top_level_directory_is_a_decision_somebody_made(self):
        # A new top-level directory defaults to "run the job"; this makes the owner of that change look at the list.
        known_runs = {"asterisk", "controller", "deploy", ".github", "scripts"}
        known_skips = {"web", "design", "docs", "testphones", "infra"}
        top = {n for n in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, n)) and n not in {".git", ".cache", "dist", "data", ".venv-dev", "node_modules", "__pycache__"}}
        for d in sorted(top):
            if d in known_runs or d in known_skips:
                continue
            self.assertTrue(ci_gate.needs_vm([d + "/x"]), f"{d}/ is not on the safe list, so it runs the job: say so here if that is on purpose")

    def test_the_command_line_form_github_reads(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            f.write("web/parent/js/home.js\nREADME.md\n")
        self.addCleanup(os.remove, f.name)
        out = subprocess.run([sys.executable, os.path.join(HERE, "ci_gate.py"), f.name], capture_output=True, text=True)
        self.assertEqual(out.stdout.strip(), "run=false")
        out = subprocess.run([sys.executable, os.path.join(HERE, "ci_gate.py"), "--event", "push"], capture_output=True, text=True)
        self.assertEqual(out.stdout.strip(), "run=true")
        self.assertEqual(subprocess.run([sys.executable, os.path.join(HERE, "ci_gate.py")], capture_output=True).returncode, 2)


class Renames(unittest.TestCase):
    """R10-1: a rename out of a root-run path must not look like a change to the place it moved to."""

    def git(self, d, *a):
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid")
        return subprocess.run(["git", "-C", d, *a], check=True, capture_output=True, text=True, env=env).stdout

    def test_moving_the_deploy_agent_into_docs_runs_the_job(self):
        with tempfile.TemporaryDirectory() as d:
            self.git(d, "init", "-q")
            os.makedirs(os.path.join(d, "deploy/native/bin")); os.makedirs(os.path.join(d, "docs"))
            with open(os.path.join(d, "deploy/native/bin/treeline-deploy"), "w") as f:
                f.write("#!/bin/sh\n" + "echo root work\n" * 20)
            self.git(d, "add", "-A"); self.git(d, "commit", "-qm", "one")
            self.git(d, "mv", "deploy/native/bin/treeline-deploy", "docs/treeline-deploy.txt"); self.git(d, "commit", "-qm", "two")
            plain = self.git(d, "-c", "diff.renames=true", "diff", "--name-only", "HEAD^1", "HEAD").splitlines()
            self.assertEqual(plain, ["docs/treeline-deploy.txt"], "the premise: with rename detection the old path is not listed")
            self.assertFalse(ci_gate.needs_vm(plain))
            safe = self.git(d, "diff", "--name-only", "--no-renames", "HEAD^1", "HEAD").splitlines()
            self.assertIn("deploy/native/bin/treeline-deploy", safe)
            self.assertTrue(ci_gate.needs_vm(safe))

    def test_the_workflow_asks_git_for_both_sides_of_a_rename(self):
        self.assertIn("git diff --name-only --no-renames HEAD^1 HEAD", Workflow.text)

    def test_a_longer_name_that_starts_like_a_safe_one_is_not_safe(self):
        for path in ("README.md.sh", "LICENSE.exe", ".gitignore.d/x", "scripts/sbom.py.bak", "scripts/sbom.pyc", "THIRD_PARTY_NOTICES.md.sh", "web/", "docs/"):
            self.assertTrue(ci_gate.needs_vm([path]), path)


class Workflow(unittest.TestCase):
    with open(os.path.join(ROOT, ".github", "workflows", "vm-imitation.yml"), encoding="utf-8") as _f:
        text = _f.read()

    def vm_job(self):
        return self.text[self.text.index("  vm:\n"):]

    def test_the_job_always_starts_so_the_required_check_always_reports(self):
        code = "\n".join(l for l in self.text.splitlines() if not l.lstrip().startswith("#"))
        self.assertNotRegex(code, r"(?m)^on:\n(?:.*\n)*?\s+paths(-ignore)?:", "a workflow-level path filter leaves a required check pending forever")
        header = self.vm_job().split("    steps:")[0]
        self.assertNotRegex(header, r"(?m)^    if:", "the job itself must not be conditional")

    def test_the_steps_that_cost_the_ten_minutes_are_the_ones_that_skip(self):
        job = self.vm_job()
        self.assertIn("scripts/ci_gate.py", job)
        self.assertRegex(job, r"(?s)id: gate.*?name: install\.sh.*?if: steps\.gate\.outputs\.run == 'true'")
        self.assertIn("github.event_name", job)


if __name__ == "__main__":
    unittest.main()
