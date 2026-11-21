"""What is written for Asterisk: its modules, directories, unit and files, for production and for the dev image."""

import os
import pathlib
import re
import shutil
import tempfile
import unittest
from unittest import mock

import helpers
from helpers import ID, ROOT
import treeline_common as common  # noqa: E402

config = helpers.load("treeline-config")
BUILD = ROOT / "asterisk" / "build"
DIRECTORIES = ("astetcdir", "astmoddir", "astsbindir", "astdatadir", "astagidir", "astvarlibdir", "astdbdir", "astkeydir",
               "astcachedir", "astspooldir", "astlogdir", "astrundir")           # the twelve main/options.c reads


def modules_txt():
    return [l.strip() for l in (BUILD / "modules.txt").read_text().splitlines() if l.strip() and not l.lstrip().startswith("#")]


def requires(path):
    return re.findall(r"^require\s*=>\s*(\w+)\.so\s*$", pathlib.Path(path).read_text(), re.M)


class Modules(unittest.TestCase):
    def test_modules_conf_loads_exactly_the_modules_the_build_contains_and_nothing_else(self):
        conf = (ROOT / "asterisk" / "config" / "modules.conf").read_text()
        self.assertIn("autoload=no", conf)
        self.assertEqual(sorted(requires(ROOT / "asterisk" / "config" / "modules.conf")), sorted(modules_txt()))
        self.assertNotRegex(conf, r"^(load|preload|noload)\s*=>", "every module is required: a failed load must stop Asterisk")

    def test_the_sorcery_configuration_is_loaded_before_ari_and_pjsip(self):
        order = requires(ROOT / "asterisk" / "config" / "modules.conf")
        for later in ("res_ari", "res_pjsip", "res_pjproject"):
            self.assertLess(order.index("res_sorcery_config"), order.index(later), later)
        self.assertLess(order.index("res_pjproject"), order.index("res_pjsip"))

    def test_the_modules_the_controller_depends_on_are_in_the_build(self):
        # chan_bridge_media: ARI's bridges/{id}/play (the pips and the join tone) creates an Announcer channel through it
        for needed in ("chan_bridge_media", "res_ari_bridges", "res_ari_channels", "res_ari_playbacks", "res_stasis_playback",
                       "app_stasis", "res_pjsip_transport_websocket", "res_srtp", "res_rtp_asterisk", "format_wav", "codec_g722"):
            self.assertIn(needed, modules_txt())

    def test_nothing_is_left_that_the_old_package_had(self):
        for gone in ("chan_sip", "chan_iax2", "res_stir_shaken", "res_pjsip_history", "res_pjsip_messaging", "codec_opus", "res_format_attr_opus"):
            self.assertNotIn(gone, modules_txt())

    def test_no_opus_anywhere_a_phone_could_ask_for_it(self):
        for path in (ROOT / "asterisk" / "config" / "pjsip.conf", ROOT / "deploy" / "native" / "templates" / "asterisk" / "pjsip.conf"):
            text = path.read_text()
            self.assertNotRegex(text, r"(?m)^allow=.*opus", str(path))
            self.assertRegex(text, r"(?m)^allow=ulaw,alaw$")

    def test_the_task_pool_cannot_shrink_in_dev_or_production(self):
        for path in (ROOT / "asterisk" / "config" / "pjsip.conf", ROOT / "deploy" / "native" / "templates" / "asterisk" / "pjsip.conf"):
            text = path.read_text()
            self.assertRegex(text, r"(?m)^\[system\]\ntype=system\ntaskpool_idle_timeout=0$", str(path))
            self.assertIn("2314", text)                                       # the reason is written next to the setting

    def test_ari_answers_to_this_machine_only_in_dev_and_production(self):
        for path in (ROOT / "asterisk" / "config" / "ari.conf", ROOT / "deploy" / "native" / "templates" / "asterisk" / "ari.conf"):
            text = path.read_text()
            self.assertRegex(text, r"(?m)^deny=0\.0\.0\.0/0$")
            self.assertRegex(text, r"(?m)^permit=127\.0\.0\.1$")
            self.assertIn("allowed_origins=http://127.0.0.1:8088", text)

    def test_the_optional_files_asterisk_would_log_errors_for_are_present_and_ami_stays_off(self):
        cfg = ROOT / "asterisk" / "config"
        for name in ("stasis", "pjproject", "websocket_client", "udptl", "features", "acl", "ccss", "cdr", "cel"):
            self.assertTrue((cfg / f"{name}.conf").is_file(), name)
        self.assertFalse((cfg / "manager.conf").exists(), "AMI is off because it has no configuration")


class Rendered(unittest.TestCase):
    def setUp(self):
        self.d = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.d, True)
        (self.d / "ari-password").write_text("Abc123" * 6 + "\n")
        (self.d / "host.env").write_text("".join(f"{k}={v}\n" for k, v in {
            "TREELINE_DOMAIN": "app.example.invalid", "TREELINE_MAIL_DOMAIN": "example.invalid", "TREELINE_AWS_REGION": "us-west-2",
            "TREELINE_PRIVATE_IP": "172.26.3.4", "TREELINE_PUBLIC_IP": "203.0.113.9", "TREELINE_LOCAL_NET": "172.26.0.0/20"}.items()))
        patch = mock.patch.object(config, "asterisk_id", lambda release: ID)
        patch.start()
        self.addCleanup(patch.stop)
        self.s = config.settings(str(self.d))

    def files(self):
        return config.asterisk_files(str(ROOT), self.s)

    def test_the_build_gets_its_own_asterisk_conf_with_every_directory_set(self):
        files = self.files()
        text = files[f"asterisk-{ID}.conf"]
        for name in DIRECTORIES:
            self.assertRegex(text, rf"(?m)^{name}\s*=>\s*/", name)
        self.assertIn(f"astmoddir => /opt/asterisk/{ID}/lib/asterisk/modules", text)
        self.assertIn(f"astdatadir => /opt/asterisk/{ID}/share/asterisk", text)
        for state in ("astdbdir", "astspooldir", "astcachedir", "astlogdir", "astkeydir", "astvarlibdir"):
            self.assertRegex(text, rf"(?m)^{state}\s*=>\s*/var/lib/treeline/", f"{state} is on the state disk")
        directives = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith(";"))
        self.assertNotIn("/var/lib/asterisk", directives, "nothing points at the compiled-in default")
        self.assertNotIn("@", directives)

    def test_the_stable_asterisk_conf_names_only_what_does_not_depend_on_the_build(self):
        text = self.files()["asterisk.conf"]
        for name in ("astmoddir", "astsbindir", "astdatadir", "astagidir"):
            self.assertNotRegex(text, rf"(?m)^{name}\b", name)
        self.assertRegex(text, r"(?m)^astrundir\s*=>\s*/run/asterisk")

    def test_no_file_of_a_previous_build_is_rendered_and_the_template_name_never_leaks(self):
        names = set(self.files())
        self.assertIn(f"asterisk-{ID}.conf", names)
        self.assertNotIn("asterisk-ID.conf", names)
        self.assertEqual([n for n in names if n.startswith("asterisk-")], [f"asterisk-{ID}.conf"], "one build's file, not a stale one")

    def test_the_unit_runs_as_the_asterisk_user_with_no_capabilities_and_a_strict_filesystem(self):
        unit = (ROOT / "deploy" / "native" / "systemd" / "asterisk.service").read_text()
        for line in ("Type=notify", "User=asterisk", "Group=asterisk", "NoNewPrivileges=yes", "CapabilityBoundingSet=", "ProtectSystem=strict",
                     "PrivateDevices=yes", "PrivateTmp=yes", "RestrictSUIDSGID=yes", "LockPersonality=yes", "RuntimeDirectory=asterisk",
                     "RequiresMountsFor=/var/lib/treeline", "StartLimitIntervalSec=0"):
            self.assertRegex(unit, rf"(?m)^{re.escape(line)}\s*$", line)
        self.assertRegex(unit, r"(?m)^RestrictAddressFamilies=.*AF_NETLINK")
        self.assertNotRegex(unit, r"(?m)^ExecStart=.* -[a-zA-Z]*p", "no real-time priority (-p): it would need a capability")
        self.assertNotRegex(unit, r"(?m)^User=root")
        self.assertIn("ReadWritePaths=/var/lib/treeline/asterisk /var/lib/treeline/logs/asterisk", unit)

    def test_the_drop_in_names_this_builds_binary_and_config(self):
        files = config.systemd_files(str(ROOT))
        drop = next(t for path, t in files.items() if path.endswith("asterisk.service.d/treeline.conf"))
        self.assertIn(f"ExecStart=/opt/asterisk/{ID}/sbin/asterisk -mqf -C /etc/asterisk/asterisk-{ID}.conf", drop)
        self.assertRegex(drop, r"(?m)^ExecStart=\s*$")                         # resets the unit's own line first
        self.assertNotIn("@", drop.replace("# ", ""))

    def test_a_new_build_is_a_changed_file_and_so_a_restart(self):
        first = config.systemd_files(str(ROOT))
        with mock.patch.object(config, "asterisk_id", lambda release: "24.0.0-t2"):
            second = config.systemd_files(str(ROOT))
        self.assertNotEqual(first, second)

    def test_apply_writes_everything_removes_what_a_release_does_not_say_and_leaves_the_keys_alone(self):
        etc_ast, systemd = self.d / "etc-asterisk", self.d / "systemd"
        (etc_ast / "keys").mkdir(parents=True)
        (etc_ast / "keys" / "treeline.key").write_text("secret")
        (etc_ast / "extconfig.conf").write_text("; left over by the old package")
        (etc_ast / "asterisk-24.0.0-t0.conf").write_text("; an old build's")
        (etc_ast / "notes.txt").write_text("not a .conf file")
        with mock.patch.object(config, "ASTERISK_DIR", str(etc_ast)), mock.patch.object(config, "SYSTEMD_DIR", str(systemd)), \
                mock.patch.object(config, "CADDYFILE", str(self.d / "Caddyfile")):
            changed = config.apply(str(ROOT), etc=str(self.d))
            again = config.apply(str(ROOT), etc=str(self.d))
        self.assertIn("asterisk", changed)
        self.assertEqual(again, set(), "a second apply changes nothing")
        self.assertFalse((etc_ast / "extconfig.conf").exists())
        self.assertFalse((etc_ast / "asterisk-24.0.0-t0.conf").exists())
        self.assertTrue((etc_ast / f"asterisk-{ID}.conf").is_file())
        self.assertEqual((etc_ast / "keys" / "treeline.key").read_text(), "secret")
        self.assertEqual((etc_ast / "notes.txt").read_text(), "not a .conf file", "only .conf files are managed")
        self.assertTrue((systemd / "asterisk.service").is_file())
        self.assertTrue((systemd / "asterisk.service.d" / "treeline.conf").is_file())
        self.assertEqual(oct((etc_ast / "modules.conf").stat().st_mode & 0o777), "0o640")

    def test_a_changed_unit_is_reloaded_before_any_restart(self):
        etc_ast, systemd = self.d / "etc-asterisk", self.d / "systemd"
        calls = []
        with mock.patch.object(config, "ASTERISK_DIR", str(etc_ast)), mock.patch.object(config, "SYSTEMD_DIR", str(systemd)), \
                mock.patch.object(config, "CADDYFILE", str(self.d / "Caddyfile")), \
                mock.patch.object(config.subprocess, "run", lambda cmd, **kw: calls.append(cmd)):
            config.apply(str(ROOT), etc=str(self.d), restart=True)
        self.assertEqual(calls[0], ["systemctl", "daemon-reload"])
        self.assertIn(["systemctl", "restart", "asterisk"], calls)
        self.assertLess(calls.index(["systemctl", "daemon-reload"]), calls.index(["systemctl", "restart", "asterisk"]))


class InstallAndImage(unittest.TestCase):
    def test_the_vm_installs_the_libraries_the_dev_image_does_and_no_asterisk_package(self):
        deps = [l.strip() for l in (ROOT / "asterisk" / "runtime-deps.txt").read_text().splitlines() if l.strip() and not l.startswith("#")]
        install = (ROOT / "deploy" / "native" / "install.sh").read_text()
        block = install[install.index("apt-get install -y -qq"):install.index(">/dev/null", install.index("apt-get install -y -qq"))]
        for dep in deps:
            self.assertRegex(block, rf"\b{re.escape(dep)}\b", dep)
        self.assertNotRegex(block, r"\basterisk\b")
        self.assertNotIn("asterisk-core-sounds", block)

    def test_the_dev_image_takes_only_the_artifact_the_lock_names_and_no_ubuntu_asterisk(self):
        dockerfile = (ROOT / "asterisk" / "Dockerfile").read_text()
        self.assertIn("sha256sum -c", dockerfile)
        self.assertIn("ASTERISK_SHA256", dockerfile)
        self.assertNotRegex(dockerfile, r"apt-get install[^\n]*\basterisk\b")
        self.assertNotIn("asterisk-core-sounds", dockerfile)

    def test_the_old_package_is_purged_pinned_out_and_replaced_before_it_is_removed(self):
        install = (ROOT / "deploy" / "native" / "install.sh").read_text()
        self.assertLess(install.index("install-asterisk"), install.index("apt-get purge"), "the replacement is in place before the old one goes")
        self.assertIn("Pin-Priority: -1", install)
        self.assertIn("/etc/apt/preferences.d/treeline-asterisk", install)
        self.assertLess(install.index("apt-get purge"), install.index('"$LIB/treeline-config" apply'))
        self.assertIn("ensure_asterisk_user", install[install.index("apt-get purge"):])

    def test_logrotate_works_inside_a_directory_only_asterisk_can_write_as_that_user(self):
        text = (ROOT / "deploy" / "native" / "logrotate" / "treeline-asterisk").read_text()
        self.assertIn("su asterisk asterisk", text)
        self.assertIn("/var/lib/treeline/logs/asterisk/messages", text)
        self.assertIn('-rx "logger reload"', text)
        self.assertNotIn("HUP", text)

    def test_the_build_inputs_ship_in_a_release_for_the_gpl_and_the_dev_only_files_do_not(self):
        # asterisk/Dockerfile, entrypoint.sh, runtime-deps.txt and dev/ are the dev image's; the release script leaves them out
        script = (ROOT / "scripts" / "build_release.sh").read_text()
        self.assertIn(r"^Dockerfile$|^entrypoint\.sh$|^runtime-deps\.txt$|^(dev|runtime)/", script)


if __name__ == "__main__":
    unittest.main()
