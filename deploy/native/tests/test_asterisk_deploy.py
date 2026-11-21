"""The deploy agent and Asterisk: which build runs, when Asterisk restarts, what a rollback restores, and what is refused. The things
that need systemd, root and a real Asterisk are replaced by recorders; vm_test.py (./dev vm) runs the real ones."""

import contextlib
import gzip
import json
import os
import pathlib
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from unittest import mock

import helpers
from helpers import ID
import treeline_common as common  # noqa: E402
import treeline_release as rel  # noqa: E402
from test_asterisk_release import make_release  # noqa: E402

deploy = helpers.load("treeline-deploy")
OLD, NEW = "24.0.0-t1", "24.0.0-t2"


def release_json(folder, version, ast_id, fmt=2):
    folder.mkdir(parents=True, exist_ok=True)
    info = {"version": version, "schema": {"central": 1, "household": 1}, "format": fmt}
    if ast_id:
        info["asterisk"] = {"id": ast_id, "sha256": "a" * 64}
    (folder / "release.json").write_text(json.dumps(info))


class Agent(unittest.TestCase):
    """A machine of temporary directories, with the effects (systemctl, apply, health) recorded in order in self.calls."""

    def setUp(self):
        self.d = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.d, True)
        self.calls = []
        self.p = {"state": str(self.d / "state"), "releases": str(self.d / "releases"), "current": str(self.d / "current"),
                  "run": str(self.d / "run" / "deploy.lock")}
        release_json(self.d / "releases" / "v1.0.0", "v1.0.0", OLD)
        release_json(self.d / "releases" / "v1.1.0", "v1.1.0", NEW)
        os.symlink(self.d / "releases" / "v1.0.0", self.p["current"])
        deploy.record(self.p, current="v1.0.0", previous=None)
        self.running = OLD                                  # what the process is running: changed by a restart
        self.config_changes = {"app"}                       # what `treeline-config apply` reports for the next release
        self.healthy = {"v1.1.0": True, "v1.0.0": True}
        self.ast_healthy = {NEW: True, OLD: True}
        self.apply_fails_for = set()

    def fake_run(self, cmd, **kw):
        self.calls.append(list(cmd))
        out = ""
        if "treeline-config" in cmd[0] and cmd[1] == "apply":
            target = os.path.basename(cmd[3])
            if target in self.apply_fails_for:
                return subprocess.CompletedProcess(cmd, 1, "", "template error")
            out = "changed: " + ", ".join(sorted(self.config_changes))
        if cmd[:2] == ["systemctl", "restart"] and "asterisk" in cmd:
            self.running = self.link_target()
        return subprocess.CompletedProcess(cmd, 0, out, "")

    def link_target(self):
        """The build the Asterisk link names (what a restart would now start)."""
        for c in reversed([c for c in self.calls if c and c[0] == "switch_asterisk"]):
            return c[1]
        return OLD

    @contextlib.contextmanager
    def machine(self, **extra):
        def switch_asterisk(i):
            self.calls.append(["switch_asterisk", i])
        patches = dict(
            data_versions=lambda: {"treeline.db": 1},
            wait_for_quiet=lambda *a, **k: None,
            snapshot_config=lambda dest: self.calls.append(["snapshot_config"]),
            restore_config=lambda src: self.calls.append(["restore_config"]),
            build_sounds=lambda rd: self.calls.append(["build_sounds", os.path.basename(rd)]),
            health=lambda v, seconds=0: self.healthy.get(v, False),
            asterisk_health=lambda i, seconds=0: self.ast_healthy.get(i, False),
            previous_asterisk=lambda d: rel.release_asterisk_id(d),
            running_asterisk_id=lambda *a: self.running,
            switch_asterisk=switch_asterisk,
            config_tool=lambda: "/x/treeline-config",
        )
        patches.update(extra)
        with contextlib.ExitStack() as stack:
            for name, value in patches.items():
                stack.enter_context(mock.patch.object(deploy, name, value))
            stack.enter_context(mock.patch.object(deploy.subprocess, "run", self.fake_run))
            stack.enter_context(mock.patch.object(common, "ASTERISK_OPT", str(self.d / "opt-asterisk")))
            yield

    def names(self):
        return [" ".join(c[:3]) for c in self.calls]

    def deploy_new(self, **kw):
        with self.machine(**kw):
            return deploy.deploy(str(self.d / "releases" / "v1.1.0"), self.p, {}, "v1.0.0", window=False)


class PickLatest(unittest.TestCase):
    def rel(self, tag, draft=False, prerelease=False):
        return {"tag_name": tag, "draft": draft, "prerelease": prerelease}

    def test_the_highest_published_version_wins_and_asterisk_releases_are_never_chosen(self):
        got = deploy.pick_latest([self.rel("asterisk-24.0.0-t2", prerelease=True), self.rel("v1.2.0"), self.rel("v1.10.0"), self.rel("v1.9.9")])
        self.assertEqual(got, "v1.10.0")

    def test_even_a_non_prerelease_with_the_wrong_name_is_ignored(self):
        self.assertEqual(deploy.pick_latest([self.rel("asterisk-24.0.0-t2"), self.rel("v1.0.0")]), "v1.0.0")

    def test_drafts_prereleases_and_odd_tags_are_ignored(self):
        got = deploy.pick_latest([self.rel("v9.0.0", draft=True), self.rel("v8.0.0", prerelease=True), self.rel("v7.0.0-rc1"),
                                  self.rel("v6.0.0\n"), self.rel(" v5.0.0"), self.rel("V4.0.0"), self.rel("v1.0.0")])
        self.assertEqual(got, "v1.0.0")

    def test_a_flag_that_is_not_literally_false_is_not_trusted(self):
        for bad in ("false", 0, None):
            with self.subTest(bad):
                with self.assertRaises(deploy.Failed):
                    deploy.pick_latest([{"tag_name": "v1.0.0", "draft": bad, "prerelease": False}])
                with self.assertRaises(deploy.Failed):
                    deploy.pick_latest([{"tag_name": "v1.0.0", "draft": False, "prerelease": bad}])

    def test_nothing_published_or_a_wrong_shape_is_a_failure_not_a_guess(self):
        for bad in ([], {"message": "rate limited"}, "x", None, [None, 5, "v1.0.0"]):
            with self.subTest(repr(bad)), self.assertRaises(deploy.Failed):
                deploy.pick_latest(bad)


class RunningId(unittest.TestCase):
    def setUp(self):
        self.d = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.d, True)
        self.proc = self.d / "proc"
        (self.proc / "4242").mkdir(parents=True)
        self.pid = "4242"

    def id_of(self, exe, pid="4242", rc=0):
        link = self.proc / "4242" / "exe"
        if os.path.lexists(link):
            os.remove(link)
        if exe:
            os.symlink(exe, link)
        with mock.patch.object(common, "ASTERISK_OPT", "/opt/asterisk"), \
                mock.patch.object(deploy.subprocess, "run", lambda cmd, **kw: subprocess.CompletedProcess(cmd, rc, pid + "\n", "")):
            return deploy.running_asterisk_id(str(self.proc))

    def test_the_build_comes_from_the_process_not_from_a_file(self):
        self.assertEqual(self.id_of("/opt/asterisk/24.0.0-t2/sbin/asterisk"), "24.0.0-t2")

    def test_not_running_or_not_ours_is_none(self):
        self.assertIsNone(self.id_of("/opt/asterisk/24.0.0-t2/sbin/asterisk", pid="0"))
        self.assertIsNone(self.id_of("/opt/asterisk/24.0.0-t2/sbin/asterisk", pid=""))
        self.assertIsNone(self.id_of("/opt/asterisk/24.0.0-t2/sbin/asterisk", rc=1))
        self.assertIsNone(self.id_of("/usr/sbin/asterisk"))
        self.assertIsNone(self.id_of("/opt/asterisk/../etc/sbin/asterisk"))
        self.assertIsNone(self.id_of("/opt/asterisk/24.0.0-t2/sbin/asterisk (deleted)"))
        self.assertIsNone(self.id_of(None))


class DeployRules(Agent):
    def test_asterisk_is_left_alone_when_it_runs_the_right_build_and_nothing_about_it_changed(self):
        self.running = NEW
        self.assertEqual(self.deploy_new(), 0)
        restarts = [c for c in self.calls if c[:2] == ["systemctl", "restart"]]
        self.assertFalse(any("asterisk" in c for c in restarts), restarts)
        self.assertTrue(any("treeline-api" in c for c in restarts))

    def test_a_different_running_build_restarts_asterisk_after_the_links_and_the_reload(self):
        self.assertEqual(self.deploy_new(), 0)
        n = self.names()
        restart = next(i for i, c in enumerate(self.calls) if c[:2] == ["systemctl", "restart"] and "asterisk" in c)
        self.assertLess(n.index("systemctl daemon-reload"), restart)
        self.assertLess(self.calls.index(["switch_asterisk", NEW]), restart)
        self.assertLess(next(i for i, c in enumerate(self.calls) if c[0] == "/x/treeline-config"), restart)
        self.assertEqual(self.running, NEW)

    def test_a_changed_configuration_restarts_asterisk_even_on_the_same_build(self):
        self.running = NEW
        self.config_changes = {"asterisk"}
        self.deploy_new()
        self.assertTrue(any(c[:2] == ["systemctl", "restart"] and "asterisk" in c for c in self.calls))

    def test_a_state_file_that_lies_does_not_decide_the_restart(self):
        deploy.record(self.p, asterisk=NEW)          # state says the new build is running; the process says otherwise
        self.running = OLD
        self.deploy_new()
        self.assertTrue(any(c[:2] == ["systemctl", "restart"] and "asterisk" in c for c in self.calls))

    def test_success_records_both_builds_and_clears_the_journal(self):
        self.assertEqual(self.deploy_new(), 0)
        state = deploy.read_state(self.p)
        self.assertEqual((state["asterisk"], state["asterisk_previous"], state["current"]), (NEW, OLD, "v1.1.0"))
        self.assertFalse(os.path.exists(deploy.inflight_path(self.p)))
        self.assertEqual(os.path.realpath(self.p["current"]), str(self.d / "releases" / "v1.1.0"))

    def test_asterisk_that_runs_the_wrong_build_fails_the_deploy_and_rolls_everything_back(self):
        self.ast_healthy[NEW] = False
        self.assertEqual(self.deploy_new(), 1)
        self.assertEqual(os.path.realpath(self.p["current"]), str(self.d / "releases" / "v1.0.0"))
        n = self.calls
        self.assertIn(["switch_asterisk", OLD], n[n.index(["switch_asterisk", NEW]):])
        applies = [c for c in n if c[0] == "/x/treeline-config"]
        self.assertEqual([os.path.basename(c[3]) for c in applies], ["v1.1.0", "v1.0.0"], "the old release's files are rendered again")
        self.assertTrue(any(c[:2] == ["systemctl", "restart"] and "asterisk" in c for c in n[n.index(["switch_asterisk", OLD]):]),
                        "and Asterisk is restarted onto the old build")
        self.assertIn("v1.1.0", deploy.read_state(self.p)["failed"])
        self.assertFalse(os.path.exists(deploy.inflight_path(self.p)))

    def test_a_failure_to_render_the_new_configuration_never_reaches_the_restart(self):
        self.apply_fails_for = {"v1.1.0"}
        self.assertEqual(self.deploy_new(), 1)
        first_restart = next((i for i, c in enumerate(self.calls) if c[:2] == ["systemctl", "restart"]), None)
        self.assertNotIn(["switch_asterisk", NEW], self.calls[:first_restart] if first_restart else self.calls)

    def test_a_pruning_error_never_turns_a_healthy_deploy_into_a_failed_one(self):
        def boom(p, keep):
            raise OSError("disk says no")
        self.assertEqual(self.deploy_new(prune=boom), 0)
        self.assertEqual(deploy.read_state(self.p)["current"], "v1.1.0")
        self.assertEqual(os.path.realpath(self.p["current"]), str(self.d / "releases" / "v1.1.0"))

    def test_a_previous_release_with_no_asterisk_is_refused_before_anything_is_touched(self):
        def refuse(d):
            raise deploy.Refused("the running release names no Asterisk build")
        with self.assertRaises(deploy.Refused):
            self.deploy_new(previous_asterisk=refuse)
        self.assertEqual([c for c in self.calls if c[0] in ("systemctl", "/x/treeline-config", "switch_asterisk")], [])
        self.assertEqual(os.path.realpath(self.p["current"]), str(self.d / "releases" / "v1.0.0"))

    def test_an_interrupted_deploy_is_repaired_at_the_next_run(self):
        # killed between writing the configuration and finishing the restart: the journal is left behind
        deploy.set_inflight(self.p, **{"from": "v1.0.0", "to": "v1.1.0"})
        self.running = NEW                                    # the process is already on the new build, the link says old
        with self.machine():
            deploy.recover(self.p)
        applies = [c for c in self.calls if c[0] == "/x/treeline-config"]
        self.assertEqual([os.path.basename(c[3]) for c in applies], ["v1.0.0"], "re-rendered for the release `current` names")
        self.assertIn(["switch_asterisk", OLD], self.calls)
        self.assertTrue(any(c[:2] == ["systemctl", "restart"] and "asterisk" in c for c in self.calls))
        self.assertFalse(os.path.exists(deploy.inflight_path(self.p)))

    def test_with_no_journal_recovery_does_nothing(self):
        with self.machine():
            deploy.recover(self.p)
        self.assertEqual(self.calls, [])


class ManualRollback(Agent):
    def setUp(self):
        super().setUp()
        os.remove(self.p["current"])
        os.symlink(self.d / "releases" / "v1.1.0", self.p["current"])
        deploy.record(self.p, current="v1.1.0", previous="v1.0.0", asterisk=NEW)
        self.running = NEW

    def rollback(self, **kw):
        with self.machine(schema_of=lambda d: {"central": 1, "household": 1}, **kw), \
                mock.patch.object(deploy.common, "host_settings", lambda *a: {}):
            return deploy.manual_rollback(self.p)

    def test_a_previous_build_that_is_not_intact_is_refused_before_a_single_service_is_stopped(self):
        def broken(d):
            raise deploy.Refused("the running release's Asterisk build is not intact")
        with self.assertRaises(deploy.Refused):
            self.rollback(previous_asterisk=broken)
        self.assertEqual([c for c in self.calls if c[:2] == ["systemctl", "stop"]], [])
        self.assertEqual(os.path.realpath(self.p["current"]), str(self.d / "releases" / "v1.1.0"))

    def test_it_goes_back_to_the_previous_build_and_says_so(self):
        self.assertEqual(self.rollback(), 0)
        state = deploy.read_state(self.p)
        self.assertEqual((state["current"], state["previous"], state["asterisk"], state["asterisk_previous"]), ("v1.0.0", "v1.1.0", OLD, NEW))
        self.assertEqual(self.running, OLD)
        self.assertFalse(os.path.exists(deploy.inflight_path(self.p)))
        self.assertIn(["switch_asterisk", OLD], self.calls)

    def test_a_previous_release_that_never_becomes_healthy_puts_back_what_was_running(self):
        self.healthy["v1.0.0"] = False
        self.assertEqual(self.rollback(), 1, "the failure is reported (1), and the machine is on what it was running (not 5)")
        self.assertEqual(os.path.realpath(self.p["current"]), str(self.d / "releases" / "v1.1.0"))
        went_back = self.calls[self.calls.index(["switch_asterisk", OLD]):]
        self.assertIn(["switch_asterisk", NEW], went_back)
        self.assertFalse(os.path.exists(deploy.inflight_path(self.p)))


class Pruning(unittest.TestCase):
    def setUp(self):
        self.d = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.d, True)
        self.p = {"releases": str(self.d / "releases")}
        self.opt = self.d / "opt"
        for build in ("24.0.0-t1", "24.0.0-t2", "24.0.0-t3", "24.0.0-t4"):
            (self.opt / build).mkdir(parents=True)
        release_json(self.d / "releases" / "v1.0.0", "v1.0.0", "24.0.0-t1")
        release_json(self.d / "releases" / "v1.1.0", "v1.1.0", "24.0.0-t2")

    def prune(self, running=None):
        with mock.patch.object(common, "ASTERISK_OPT", str(self.opt)), mock.patch.object(deploy, "running_asterisk_id", lambda *a: running):
            return deploy.prune_asterisk(self.p)

    def test_builds_no_release_carries_go_and_the_others_and_the_running_one_stay(self):
        self.prune(running="24.0.0-t3")
        self.assertEqual(sorted(os.listdir(self.opt)), ["24.0.0-t1", "24.0.0-t2", "24.0.0-t3"])

    def test_an_unreadable_release_means_nothing_is_removed(self):
        release_json(self.d / "releases" / "v1.2.0", "v1.2.0", None, fmt=1)        # an old format: what it needs is unknown
        self.assertEqual(self.prune(), [])
        self.assertEqual(len(os.listdir(self.opt)), 4)


class SigningAndStaging(unittest.TestCase):
    """The real signing path: a release that verifies, with the nested Asterisk changed by someone with the signing key's output
    but not the key (a valid outer signature cannot be made), and by someone with a valid re-signed outer tarball but a lying inner file."""

    @classmethod
    def setUpClass(cls):
        cls.d = pathlib.Path(tempfile.mkdtemp())
        cls.key, cls.signers = helpers.keygen(cls.d)
        cls.tar = helpers.build("v0.0.7", cls.d / "out", cls.key)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.d, ignore_errors=True)

    def setUp(self):
        self.w = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.w, True)
        self.p = {"releases": str(self.w / "releases"), "state": str(self.w / "state")}
        self.opt = self.w / "opt-asterisk"

    def stage(self, tarball, sig, version="v0.0.7"):
        with mock.patch.object(deploy.rel, "build_venv", lambda d: None), mock.patch.object(deploy.rel, "seal", lambda d: None), \
                mock.patch.object(deploy, "preflight", lambda d, ci=False: None), \
                mock.patch.object(common, "ASTERISK_OPT", str(self.opt)):
            return deploy.stage(str(tarball), str(sig), version, self.p, {"TREELINE_CI": "1"}, signers=str(self.signers))

    def resign(self, mutate, name="mutant"):
        """Unpack the good release, let `mutate(folder)` change it, repack it in the same layout and sign it with the real key."""
        folder = self.w / name
        rel.extract(str(self.tar), str(folder))
        mutate(folder)
        out = self.w / f"{name}.tar.gz"
        raw = out.with_suffix(".tar")
        with tarfile.open(raw, "w") as tf:
            tf.add(folder, arcname=".", filter=lambda ti: (setattr(ti, "uid", 0), setattr(ti, "gid", 0), ti)[2])
        with open(raw, "rb") as f, open(out, "wb") as o, gzip.GzipFile(fileobj=o, mode="wb", mtime=0) as g:
            g.write(f.read())
        return out, helpers.sign(out, self.key)

    def test_the_genuine_release_stages_and_installs_its_build(self):
        dest = self.stage(self.tar, str(self.tar) + ".sig")
        self.assertEqual(os.path.basename(dest), "v0.0.7")
        self.assertTrue((self.opt / ID / "sbin" / "asterisk").is_file())

    def test_a_release_with_a_different_nested_file_is_refused_even_though_its_signature_is_valid(self):
        def swap(folder):
            f = folder / "asterisk" / "runtime" / f"asterisk-{ID}.tar.gz"
            f.write_bytes(helpers.tar_bytes(helpers.good_members(binary=b"#!an attacker's asterisk\n")))
        tarball, sig = self.resign(swap)
        rel.verify(str(tarball), str(sig), str(self.signers))                      # the outer signature really is valid
        with self.assertRaises(deploy.Refused) as cm:
            self.stage(tarball, sig)
        self.assertIn("does not match the sha256", str(cm.exception))
        self.assertFalse((self.opt / ID).exists())
        self.assertEqual(os.listdir(self.p["releases"]), [])                       # nothing left staged

    def test_a_release_whose_json_names_another_build_than_the_one_inside_is_refused(self):
        def rename(folder):
            info = json.loads((folder / "release.json").read_text())
            info["asterisk"]["id"] = "24.0.0-t7"
            (folder / "release.json").write_text(json.dumps(info))
        tarball, sig = self.resign(rename)
        with self.assertRaises(deploy.Refused):
            self.stage(tarball, sig)
        self.assertFalse(self.opt.exists() and any(self.opt.iterdir()))

    def test_an_old_format_release_is_refused_with_nothing_changed(self):
        def old(folder):
            info = json.loads((folder / "release.json").read_text())
            info["format"] = 1
            del info["asterisk"]
            (folder / "release.json").write_text(json.dumps(info))
        tarball, sig = self.resign(old)
        with self.assertRaises(deploy.Refused) as cm:
            self.stage(tarball, sig)
        self.assertIn("format 1", str(cm.exception))
        self.assertEqual(os.listdir(self.p["releases"]), [])

    def test_a_flipped_byte_in_the_outer_tarball_is_refused_by_the_signature_before_anything_is_read(self):
        bad = self.w / "bad.tar.gz"
        data = bytearray(self.tar.read_bytes())
        data[len(data) // 2] ^= 1
        bad.write_bytes(bytes(data))
        shutil.copy(str(self.tar) + ".sig", str(bad) + ".sig")
        with self.assertRaises(deploy.Refused) as cm:
            self.stage(bad, str(bad) + ".sig")
        self.assertIn("signature", str(cm.exception).lower())
        self.assertFalse(self.opt.exists())

    def test_a_test_build_id_is_refused_on_a_real_install(self):
        art = helpers.artifact(self.w / "t9", ast_id="24.0.0-t9")
        tarball = helpers.build("v0.0.8", self.w / "out9", self.key, asterisk=art)
        with mock.patch.object(deploy.rel, "build_venv", lambda d: None), mock.patch.object(deploy.rel, "seal", lambda d: None), \
                mock.patch.object(common, "ASTERISK_OPT", str(self.opt)):
            with self.assertRaises(deploy.Refused) as cm:
                deploy.stage(str(tarball), str(tarball) + ".sig", "v0.0.8", self.p, {}, signers=str(self.signers))      # not CI
        self.assertIn("test id", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
