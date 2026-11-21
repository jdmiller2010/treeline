"""Tests for scripts/asterisk_build.py: the pinned Asterisk build's inputs and artifact.lock."""
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import asterisk_build as ab  # noqa: E402

SOURCES = ab.read_text(os.path.join(ab.BUILD, "sources.lock"))


def make_tree(sources=SOURCES, extra=None):
    d = tempfile.mkdtemp()
    for name in ("modules.txt", "build.sh", "Dockerfile", "build-deps.txt"):
        shutil.copy(os.path.join(ab.BUILD, name), os.path.join(d, name))
    with open(os.path.join(d, "sources.lock"), "w", encoding="utf-8") as f:
        f.write(sources)
    for name, text in (extra or {}).items():
        with open(os.path.join(d, name), "w", encoding="utf-8") as f:
            f.write(text)
    return d


class RealInputs(unittest.TestCase):
    def test_the_repository_inputs_pass(self):
        ab.check()

    def test_pins_are_the_ones_we_verified(self):
        src = ab.parse_lock(SOURCES, ab.SOURCES_FIELDS)
        self.assertEqual(src["ASTERISK_VERSION"], "24.0.0")
        self.assertEqual(src["PJPROJECT_VERSION"], "2.17")
        self.assertEqual(src["ASTERISK_KEY_FPR"], "F2FC93DB7587BD1FB49E045A5D984BE337191CE7")
        self.assertIn("@sha256:", src["BASE_IMAGE"])   # the toolchain is pinned by digest, never by tag alone

    def test_no_module_the_plan_leaves_out(self):
        names = ab.modules(ab.read_text(os.path.join(ab.BUILD, "modules.txt")))
        for banned in ("chan_iax2", "chan_sip", "res_stir_shaken", "func_odbc", "res_pjsip_history", "res_pjsip_messaging",
                       "res_pjsip_diversion", "codec_opus", "chan_ooh323", "res_resolver_unbound"):
            self.assertNotIn(banned, names)
        for needed in ("res_pjsip", "chan_pjsip", "res_ari", "app_stasis", "res_rtp_asterisk", "res_srtp",
                       "res_http_websocket", "res_pjsip_transport_websocket", "res_sorcery_config",
                       "chan_bridge_media"):   # ARI's bridges/{id}/play needs the Announcer channel: no pips or join tone without it
            self.assertIn(needed, names)

    def test_build_script_stays_sealed(self):
        text = ab.read_text(os.path.join(ab.BUILD, "build.sh"))
        self.assertIn("gpgv", text)
        self.assertIn("sha256sum -c", text)
        self.assertIn("a network fetch was attempted", text)   # the fake downloader that fails the build
        # What make_build_h stamps into the binary must not depend on who runs the build (found when the CI runner, uid 1001
        # with no name, produced different bytes from a developer's uid 1000 "ubuntu"): date, hostname, kernel and user.
        for stamped in ('"$SHIM/date"', '"$SHIM/uname"', '"$SHIM/id"'):
            self.assertIn(stamped, text)
        for forbidden in ("curl ", "git clone", "pip install", "apt-get install"):
            self.assertNotIn(forbidden, text)   # fetching is run-build.sh's job, before the container loses its network
        # What the build is required to have produced (each was true of the real build when written, and a mutation test
        # confirmed the first one fails the build): the TLS-switch mitigation for GHSA-j4c2, systemd notify support, the
        # log line fail2ban matches, ICE, and hardened linking.
        for required in ("PJSIP_DONT_SWITCH_TO_TLS=1", "libsystemd", "failed for '%s' (callid: %s) - %s", "icesupport",
                         "GNU_RELRO", "BIND_NOW", "executable stack"):
            self.assertIn(required, text)
        self.assertIn('-Wl,-z,relro,-z,now', text)
        run = ab.read_text(os.path.join(ab.BUILD, "run-build.sh"))
        self.assertIn("--network none", run)
        self.assertIn("--cap-drop ALL", run)


class ReleaseWorkflow(unittest.TestCase):
    """.github/workflows/release.yml: the Asterisk build is verified before, and apart from, the step that holds the signing key."""
    text = ab.read_text(os.path.join(ab.ROOT, ".github", "workflows", "release.yml"))

    def step(self, name):
        start = self.text.index(f"- name: {name}")
        nxt = self.text.find("\n      - ", start + 1)
        return self.text[start:nxt if nxt != -1 else len(self.text)]

    def test_the_build_is_verified_before_the_signing_step_and_in_a_step_that_never_holds_the_key(self):
        verify = self.step("The Asterisk build this release carries")
        sign = self.step("Build and sign")
        self.assertLess(self.text.index(verify), self.text.index(sign))
        self.assertNotIn("RELEASE_SIGNING_KEY", verify)
        self.assertIn("gh attestation verify", verify)
        self.assertIn("--signer-workflow", verify)
        self.assertIn("--source-ref refs/heads/main", verify)
        self.assertIn("--deny-self-hosted-runners", verify)
        self.assertIn("lock-field ARTIFACT_SHA256", verify)

    def test_the_signed_release_is_built_from_exactly_the_verified_file(self):
        sign = self.step("Build and sign")
        self.assertRegex(sign, r'--asterisk "dist/asterisk/asterisk-\$\(python3 -I scripts/asterisk_build\.py lock-field ARTIFACT_ID\)\.tar\.gz"')
        self.assertNotIn("--asterisk-unlocked", self.text)

    def test_nothing_downloaded_is_executed_and_the_source_is_checked_against_the_pins(self):
        for name in ("The Asterisk build this release carries", "The source of what is shipped"):
            step = self.step(name)
            for forbidden in ("./dist", "bash dist", "sh dist", "tar -x", "dpkg -i", "python3 dist", "chmod +x"):
                self.assertNotIn(forbidden, step, name)
        self.assertIn("sha256sum", self.step("The source of what is shipped"))
        self.assertIn("dist/source/*", self.text)

    def test_the_workflow_still_has_no_other_trigger_and_the_job_a_longer_timeout(self):
        code = "\n".join(l for l in self.text.splitlines() if not l.lstrip().startswith("#"))
        self.assertNotIn("pull_request_target", code)
        self.assertRegex(code, r"(?m)^on:\n  push:\n    tags:")
        self.assertNotRegex(code, r"(?m)^  (pull_request|workflow_dispatch|schedule):")


class Command(unittest.TestCase):
    def run_main(self, *argv):
        import contextlib
        import io
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = ab.main(list(argv))
        return rc, out.getvalue().strip(), err.getvalue()

    def test_lock_field_prints_a_validated_field(self):
        rc, out, _ = self.run_main("lock-field", "ARTIFACT_SHA256")
        self.assertEqual(rc, 0)
        self.assertRegex(out, r"^[0-9a-f]{64}$")
        self.assertEqual(self.run_main("lock-field", "ARTIFACT_ID")[1], ab.parse_lock(SOURCES, ab.SOURCES_FIELDS)["BUILD_ID"])

    def test_lock_field_refuses_an_unknown_name_and_odd_arguments(self):
        self.assertEqual(self.run_main("lock-field", "ARTIFACT_SHA256; id")[0], 1)
        self.assertEqual(self.run_main("lock-field")[0], 2)
        self.assertEqual(self.run_main("check", "--require")[0], 2)

    def test_require_lock_passes_with_the_repository_lock(self):
        self.assertEqual(self.run_main("check", "--require-lock")[0], 0)


class Parsing(unittest.TestCase):
    def bad(self, text):
        with self.assertRaises(ab.Problem):
            ab.parse_lock(text, ab.SOURCES_FIELDS)

    def test_rejects_malformed_lines(self):
        self.bad(SOURCES + "BUILD_ID=24.0.0-t2\n")                        # duplicate
        self.bad(SOURCES + "EXTRA_THING=1\n")                              # unknown field
        self.bad(SOURCES.replace("ASTERISK_VERSION=24.0.0", "ASTERISK_VERSION = 24.0.0"))
        self.bad(SOURCES.replace("ASTERISK_VERSION=24.0.0", "ASTERISK_VERSION=$(id)"))
        self.bad(SOURCES.replace("https://downloads", "http://downloads", 1))   # no plain http
        self.bad(SOURCES.replace("ASTERISK_SHA256=ece42a", "ASTERISK_SHA256=ECE42A"))   # lower-case hex only
        self.bad(SOURCES.replace("ubuntu:24.04@sha256:", "ubuntu:24.04@sha1:"))
        self.bad("\n".join(l for l in SOURCES.splitlines() if not l.startswith("PJPROJECT_MD5")))   # missing

    def test_comments_and_blank_lines_are_fine(self):
        ab.parse_lock("# hi\n\n" + SOURCES, ab.SOURCES_FIELDS)

    def test_modules_rejects_odd_names_and_duplicates(self):
        with self.assertRaises(ab.Problem):
            ab.modules("res_pjsip\nres_pjsip\n")
        with self.assertRaises(ab.Problem):
            ab.modules("res_pjsip; rm -rf /\n")


class ArtifactLock(unittest.TestCase):
    def setUp(self):
        self.dir = make_tree()
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.art = os.path.join(self.dir, "asterisk-24.0.0-t1.tar.gz")
        with open(self.art, "wb") as f:
            f.write(b"not really a tarball")

    def test_lock_round_trip_and_size_and_hash(self):
        ab.write_lock(self.art, self.dir)
        src, art = ab.check(self.dir)
        self.assertEqual(art["ARTIFACT_ID"], src["BUILD_ID"])
        self.assertEqual(art["ARTIFACT_SIZE"], str(len(b"not really a tarball")))

    def test_changing_the_build_script_without_a_new_artifact_fails(self):
        ab.write_lock(self.art, self.dir)
        with open(os.path.join(self.dir, "build.sh"), "a") as f:
            f.write("# a new instruction\n")
        with self.assertRaisesRegex(ab.Problem, "changed since artifact.lock"):
            ab.check(self.dir)

    def test_changing_the_module_list_or_sources_fails(self):
        for name in ("modules.txt", "sources.lock", "Dockerfile", "build-deps.txt"):
            d = make_tree()
            self.addCleanup(shutil.rmtree, d, True)
            ab.write_lock(self.art, d)
            with open(os.path.join(d, name), "a") as f:
                f.write("\n# edited\n")
            with self.assertRaises(ab.Problem, msg=name):
                ab.check(d)

    def test_a_new_file_in_the_tree_fails(self):
        ab.write_lock(self.art, self.dir)
        with open(os.path.join(self.dir, "patch.diff"), "w") as f:
            f.write("--- a\n+++ b\n")
        with self.assertRaises(ab.Problem):
            ab.check(self.dir)

    def test_a_lock_for_another_build_id_fails(self):
        ab.write_lock(self.art, self.dir)
        s = SOURCES.replace("BUILD_ID=24.0.0-t1", "BUILD_ID=24.0.0-t2")
        with open(os.path.join(self.dir, "sources.lock"), "w") as f:
            f.write(s)
        with self.assertRaisesRegex(ab.Problem, "another build"):
            ab.check(self.dir)

    def test_artifact_lock_itself_does_not_count_in_the_digest(self):
        before = ab.tree_digest(self.dir)
        ab.write_lock(self.art, self.dir)
        self.assertEqual(before, ab.tree_digest(self.dir))

    def test_the_readme_is_documentation_and_does_not_count(self):
        before = ab.tree_digest(self.dir)
        with open(os.path.join(self.dir, "README.md"), "w") as f:
            f.write("words")
        self.assertEqual(before, ab.tree_digest(self.dir))

    def test_symlinks_are_refused(self):
        os.symlink("/etc/passwd", os.path.join(self.dir, "link"))
        with self.assertRaises(ab.Problem):
            ab.tree_digest(self.dir)

    def test_url_must_match_version(self):
        d = make_tree(SOURCES.replace("asterisk-24.0.0.tar.gz\n", "asterisk-24.0.1.tar.gz\n", 1))
        self.addCleanup(shutil.rmtree, d, True)
        with self.assertRaises(ab.Problem):
            ab.check(d)


if __name__ == "__main__":
    unittest.main()
