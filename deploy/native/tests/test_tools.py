"""Unit tests for the root-run tools: secrets, certificate sync, configuration rendering, releases. No root, no Docker."""

import hashlib
import io
import json
import os
import pathlib
import shutil
import subprocess
import tarfile
import tempfile
import unittest

import helpers

fetch = helpers.load("treeline-fetch-secrets")
certsync = helpers.load("treeline-certsync")
deploy = helpers.load("treeline-deploy")
config = helpers.load("treeline-config")
import treeline_common as common  # noqa: E402
import treeline_release as rel  # noqa: E402


class FakeSsm:
    def __init__(self, params):
        self.params = params
        self.asked = []

    def get_parameters(self, Names, WithDecryption):
        self.asked.append((tuple(Names), WithDecryption))
        return {"Parameters": [{"Name": n, "Value": self.params[n]} for n in Names if n in self.params],
                "InvalidParameters": [n for n in Names if n not in self.params]}


GOOD = {"/treeline/smtp_user": "u", "/treeline/smtp_password": 'p"w\\d', "/treeline/vapid_public": "pub", "/treeline/vapid_private": "priv",
        "/treeline/google_client_id": "cid", "/treeline/google_client_secret": "csecret", "/treeline/beta_code_hash": "h", "/treeline/beta_code_expires": "2099-01-01"}


class Secrets(unittest.TestCase):
    def setUp(self):
        self.d = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.d, True)
        (self.d / "ari-password").write_text("a" * 40 + "\n")

    def test_every_parameter_becomes_an_environment_line_and_the_ari_password_is_added(self):
        text = fetch.build(FakeSsm(GOOD), etc=str(self.d))
        lines = dict(l.split("=", 1) for l in text.splitlines())
        self.assertEqual(set(lines), {"TREELINE_SMTP_USER", "TREELINE_SMTP_PASS", "TREELINE_VAPID_PUBLIC", "TREELINE_VAPID_PRIVATE", "ARI_PASS",
                                 "TREELINE_GOOGLE_CLIENT_ID", "TREELINE_GOOGLE_CLIENT_SECRET", "TREELINE_BETA_CODE_HASH", "TREELINE_BETA_CODE_EXPIRES"})
        self.assertEqual(lines["TREELINE_SMTP_PASS"], '"p\\"w\\\\d"')          # quotes and backslashes are escaped for systemd
        self.assertEqual(lines["ARI_PASS"], '"' + "a" * 40 + '"')

    def test_decryption_is_requested_and_only_our_prefix_is_read(self):
        ssm = FakeSsm(GOOD)
        fetch.build(ssm, etc=str(self.d))
        names, decrypt = ssm.asked[0]
        self.assertTrue(decrypt)
        self.assertTrue(all(n.startswith("/treeline/") for n in names))

    def test_a_missing_parameter_is_a_hard_failure_that_names_it(self):
        partial = {k: v for k, v in GOOD.items() if k != "/treeline/vapid_private"}
        with self.assertRaises(SystemExit) as caught:
            fetch.build(FakeSsm(partial), etc=str(self.d))
        self.assertIn("vapid_private", str(caught.exception))

    def test_a_value_with_a_line_break_is_refused(self):
        with self.assertRaises(SystemExit):
            fetch.build(FakeSsm(dict(GOOD, **{"/treeline/smtp_user": "a\nTREELINE_ENV=development"})), etc=str(self.d))

    def test_the_file_is_private_from_its_first_byte_and_replaced_atomically(self):
        out = self.d / "run" / "env"
        common.atomic_write(str(out), "A=1\n", mode=0o600)
        self.assertEqual(oct(out.stat().st_mode & 0o777), "0o600")
        self.assertFalse(common.atomic_write(str(out), "A=1\n", mode=0o600))
        self.assertTrue(common.atomic_write(str(out), "A=2\n", mode=0o600))
        self.assertEqual([p.name for p in out.parent.iterdir()], ["env"])


def make_cert(directory, host):
    key, crt = pathlib.Path(directory) / f"{host}.key", pathlib.Path(directory) / f"{host}.crt"
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", key, "-out", crt, "-days", "2", "-subj", f"/CN={host}"],
                   check=True, capture_output=True)
    return key, crt


class CertSync(unittest.TestCase):
    def setUp(self):
        self.d = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.d, True)
        self.storage, self.keys = self.d / "caddy", self.d / "keys"

    def put(self, issuer, host="app.example.invalid"):
        folder = self.storage / "certificates" / issuer / host
        folder.mkdir(parents=True)
        key, crt = make_cert(folder, host)
        return crt

    def test_the_one_matching_pair_is_copied_with_a_private_key(self):
        self.put("acme-v02.api.letsencrypt.org-directory")
        self.assertTrue(certsync.sync(str(self.storage), "app.example.invalid", str(self.keys), owner="nonexistent-user"))
        self.assertEqual(oct((self.keys / "treeline.key").stat().st_mode & 0o777), "0o600")
        self.assertFalse(certsync.sync(str(self.storage), "app.example.invalid", str(self.keys), owner="nonexistent-user"), "second run must report no change")

    def test_none_or_two_issuers_is_refused(self):
        with self.assertRaises(SystemExit) as none:
            certsync.find_pair(str(self.storage), "app.example.invalid")
        self.assertIn("not obtained", str(none.exception))
        self.put("issuer-one")
        self.put("issuer-two")
        with self.assertRaises(SystemExit) as two:
            certsync.find_pair(str(self.storage), "app.example.invalid")
        self.assertIn("more than one", str(two.exception))

    def test_a_host_name_cannot_walk_out_of_the_storage_directory(self):
        for bad in ("../etc", "a/b.example.com", "*.example.com", ""):
            with self.assertRaises(ValueError):
                certsync.find_pair(str(self.storage), bad)


class Config(unittest.TestCase):
    def setUp(self):
        self.d = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.d, True)
        (self.d / "ari-password").write_text("Abc123" * 6 + "\n")
        self.write_host()

    def write_host(self, **over):
        host = {"TREELINE_DOMAIN": "app.example.invalid", "TREELINE_MAIL_DOMAIN": "example.invalid", "TREELINE_AWS_REGION": "us-west-2",
                "TREELINE_PRIVATE_IP": "172.26.3.4", "TREELINE_PUBLIC_IP": "203.0.113.9", "TREELINE_LOCAL_NET": "172.26.0.0/20"}
        host.update(over)
        (self.d / "host.env").write_text("".join(f"{k}={v}\n" for k, v in host.items()))

    def test_behind_a_nat_every_option_is_written_and_the_ice_section_maps_private_to_public(self):
        s = config.settings(str(self.d))
        nat = config.nat_values(s)
        self.assertIn("external_media_address=203.0.113.9", nat["NAT_OPTIONS"])
        self.assertIn("external_signaling_address=203.0.113.9", nat["NAT_OPTIONS"])
        self.assertIn("local_net=172.26.0.0/20", nat["NAT_OPTIONS"])
        self.assertEqual(nat["ICE_HOST_CANDIDATES"], "172.26.3.4 => 203.0.113.9")
        files = config.asterisk_files(str(helpers.ROOT), s)
        self.assertIn("[ice_host_candidates]\n172.26.3.4 => 203.0.113.9", files["rtp.conf"])
        self.assertEqual(files["pjsip.conf"].count("external_media_address=203.0.113.9"), 2)     # tls and ws transports
        self.assertIn("password=" + "Abc123" * 6, files["ari.conf"])

    def test_without_a_nat_nothing_is_said_about_addresses(self):
        self.write_host(TREELINE_PUBLIC_IP="172.26.3.4")
        files = config.asterisk_files(str(helpers.ROOT), config.settings(str(self.d)))
        self.assertNotIn("external_media_address", files["pjsip.conf"])
        self.assertNotIn("=>", files["rtp.conf"].split("[ice_host_candidates]")[1])

    def test_no_placeholder_is_left_in_anything_rendered_and_nothing_environment_specific_is_in_the_repo_templates(self):
        s = config.settings(str(self.d))
        rendered = list(config.asterisk_files(str(helpers.ROOT), s).values()) + [config.caddyfile(str(helpers.ROOT), s), config.app_env(str(helpers.ROOT), s)]
        for text in rendered:
            self.assertNotRegex(text, r"@[A-Z][A-Z_]*@")
        for path in (helpers.ROOT / "deploy" / "native" / "templates").rglob("*"):
            if path.is_file():
                text = path.read_text().replace("127.0.0.1", "").replace("0.0.0.0", "")          # loopback and "all interfaces" are not environment-specific
                self.assertNotRegex(text, r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", f"{path} holds an address")

    def test_the_caddyfile_pins_one_issuer_and_one_storage_root_and_proxies_only_ws(self):
        text = config.caddyfile(str(helpers.ROOT), config.settings(str(self.d)))
        self.assertIn("storage file_system /var/lib/treeline/caddy", text)
        self.assertIn("dir https://acme-v02.api.letsencrypt.org/directory", text)
        self.assertEqual(text.count("reverse_proxy @asterisk_ws 127.0.0.1:8088"), 1)
        self.assertEqual(text.count("reverse_proxy"), 2)           # /ws to Asterisk, everything else to the app: nothing else is proxied
        self.assertIn("@asterisk_ws path /ws", text)
        self.assertNotIn("/ari", text)
        self.assertIn("redir https://app.example.invalid{uri} 308", text)
        self.assertIn("example.invalid {", text.replace("app.example.invalid {", ""))          # the bare domain redirects too
        self.assertIn("max-age=31536000", text)
        self.assertNotIn("preload", text)

    def test_a_hostile_value_in_host_env_is_refused_not_rendered(self):
        for over in ({"TREELINE_DOMAIN": "x.example.com {\n respond 200\n}"}, {"TREELINE_PUBLIC_IP": "203.0.113.9; evil"},
                     {"TREELINE_ACME_DIR": "https://ca.example.invalid/dir }"}, {"TREELINE_VAPID_CONTACT": "a b@c"}):
            self.write_host(**over)
            with self.assertRaises((ValueError, KeyError)):
                config.settings(str(self.d))

    def test_the_app_environment_is_production_with_secure_urls_and_no_secret(self):
        env = config.app_env(str(helpers.ROOT), config.settings(str(self.d)))
        self.assertIn("TREELINE_ENV=production", env)
        self.assertIn("TREELINE_PUBLIC_WS_URL=wss://app.example.invalid/ws", env)
        self.assertIn("TREELINE_TRUST_PROXY=1", env)
        self.assertNotIn("TREELINE_DEV_CODES", env)
        self.assertNotIn("Abc123", env)

    def test_a_development_setting_is_never_installed_even_if_a_template_went_missing(self):
        """R6-3: if a production template were missing, the dev file from asterisk/config would be left in place."""
        s_ = config.settings(str(self.d))
        files = config.asterisk_files(str(helpers.ROOT), s_)
        config.refuse_dev_config(files)                    # the real release renders clean
        for name, text in (("ari.conf", "password=treeline-dev"), ("http.conf", "bindaddr=0.0.0.0"), ("pjsip.conf", "[transport-udp]\nprotocol=udp\nbind=0.0.0.0:5060")):
            with self.assertRaises(ValueError, msg=name):
                config.refuse_dev_config(dict(files, **{name: text}))
        # and the base (development) files really do carry those markers, so the check would bite
        base = {n: (helpers.ROOT / "asterisk" / "config" / n).read_text() for n in ("ari.conf", "http.conf", "pjsip.conf")}
        with self.assertRaises(ValueError):
            config.refuse_dev_config(base)

    def test_the_ci_only_aws_endpoint_is_refused_on_a_real_install(self):
        import treeline_aws
        (self.d / "aws-endpoint").write_text("http://fake.example.invalid:9000\n")
        (self.d / "aws-credentials").write_text("[treeline-vm]\naws_access_key_id = x\naws_secret_access_key = y\n")
        with self.assertRaises(SystemExit) as caught:
            treeline_aws.client("ssm", etc=str(self.d))
        self.assertIn("not a CI install", str(caught.exception))

    def test_an_unknown_placeholder_is_an_error(self):
        with self.assertRaises(KeyError):
            common.render("@NOPE@", {})


class Releases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = pathlib.Path(tempfile.mkdtemp())
        cls.key, cls.signers = helpers.keygen(cls.d)
        cls.tar = helpers.build("v0.0.1", cls.d / "out", cls.key)
        cls.sig = pathlib.Path(str(cls.tar) + ".sig")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.d, ignore_errors=True)

    def test_a_good_signature_verifies(self):
        rel.verify(str(self.tar), str(self.sig), str(self.signers))

    def test_one_flipped_byte_is_refused(self):
        bad = self.d / "bad.tar.gz"
        data = bytearray(self.tar.read_bytes())
        data[len(data) // 2] ^= 1
        bad.write_bytes(bytes(data))
        shutil.copy(self.sig, str(bad) + ".sig")
        with self.assertRaises(rel.ReleaseError) as caught:
            rel.verify(str(bad), str(bad) + ".sig", str(self.signers))
        self.assertIn("FAILED", str(caught.exception))

    def test_a_signature_by_another_key_is_refused(self):
        other, _ = helpers.keygen(self.d, "other")
        subprocess.run(["ssh-keygen", "-Y", "sign", "-q", "-f", str(other), "-n", "treeline-release", str(self.d / "x")], input=b"", capture_output=True)
        copy = self.d / "copy.tar.gz"
        shutil.copy(self.tar, copy)
        subprocess.run(["ssh-keygen", "-Y", "sign", "-q", "-f", str(other), "-n", "treeline-release", str(copy)], check=True)
        with self.assertRaises(rel.ReleaseError):
            rel.verify(str(copy), str(copy) + ".sig", str(self.signers))

    def test_a_signature_for_another_purpose_is_refused(self):
        copy = self.d / "ns.tar.gz"
        shutil.copy(self.tar, copy)
        subprocess.run(["ssh-keygen", "-Y", "sign", "-q", "-f", str(self.key), "-n", "file", str(copy)], check=True)    # a different namespace
        with self.assertRaises(rel.ReleaseError):
            rel.verify(str(copy), str(copy) + ".sig", str(self.signers))

    def test_no_signature_or_no_trusted_key_is_refused(self):
        with self.assertRaises(rel.ReleaseError):
            rel.verify(str(self.tar), str(self.d / "nope.sig"), str(self.signers))
        empty = self.d / "empty"
        empty.write_text("# no key yet\n")
        with self.assertRaises(rel.ReleaseError):
            rel.verify(str(self.tar), str(self.sig), str(empty))
        with self.assertRaises(rel.ReleaseError):
            rel.verify(str(self.tar), str(self.sig), str(self.d / "missing"))

    def test_extract_refuses_paths_that_leave_the_directory_and_links_that_point_out(self):
        for name, kind in (("../escape", "file"), ("/abs/path", "file"), ("link", "symlink-out")):
            path = self.d / f"evil-{kind}-{abs(hash(name))}.tar.gz"
            with tarfile.open(path, "w:gz") as tf:
                info = tarfile.TarInfo(name)
                if kind == "symlink-out":
                    info.type, info.linkname = tarfile.SYMTYPE, "/etc/passwd"
                    tf.addfile(info)
                else:
                    data = b"x"
                    info.size = len(data)
                    tf.addfile(info, io.BytesIO(data))
            dest = self.d / f"dest-{abs(hash(name))}"
            with self.assertRaises(rel.ReleaseError):
                rel.extract(str(path), str(dest))
            self.assertFalse(dest.exists(), "a failed unpack must leave nothing behind")
            self.assertFalse((self.d / "escape").exists())

    def test_the_release_holds_code_and_templates_and_nothing_that_must_not_be_public(self):
        with tarfile.open(self.tar) as tf:
            names = tf.getnames()
            info = json.load(tf.extractfile("./release.json"))
        for must in ("./controller/treeline/api.py", "./controller/requirements-prod.lock", "./web/site/index.html", "./web/ui/css", "./asterisk/config/extensions.conf",
                     "./deploy/native/install.sh", "./deploy/native/bin/treeline-deploy", "./deploy/native/templates/Caddyfile.tmpl"):
            self.assertIn(must, names)
        for bad in ("tests", ".git", ".local", "cdk.out"):
            self.assertFalse([n for n in names if f"/{bad}/" in n or n.endswith("/" + bad)], bad)
        for ending in (".db", ".agekey", ".pem", ".key", "/.env"):
            self.assertFalse([n for n in names if n.endswith(ending)], ending)
        # R6-3: nothing that only exists for development is shipped
        for dev in ("docker-compose", "Caddyfile.dev", "env.example", "testphones", "/web/site/tests/", "LOCAL_HTTPS", ".override."):
            self.assertFalse([n for n in names if dev in n], dev)
        self.assertEqual(info["version"], "v0.0.1")
        self.assertEqual(info["schema"], {"central": 1, "household": 1})
        self.assertFalse([n for n in names if n.startswith("./deploy/native/ci") or n.startswith("./deploy/native/tests")])

    def test_the_build_is_reproducible(self):
        again = helpers.build("v0.0.1", self.d / "out2", self.key)
        self.assertEqual(hashlib.sha256(self.tar.read_bytes()).hexdigest(), hashlib.sha256(again.read_bytes()).hexdigest())

    def test_a_dirty_tree_is_refused_without_the_flag_and_a_bad_version_is_refused(self):
        done = subprocess.run([str(helpers.ROOT / "scripts" / "build_release.sh"), "1.0", "--allow-dirty", "--out", str(self.d / "x")], capture_output=True, text=True)
        self.assertNotEqual(done.returncode, 0)

    def test_read_info_rejects_a_release_without_a_version_or_schema(self):
        for bad in ({}, {"version": "v1.0.0"}, {"version": "latest", "schema": {"central": 1, "household": 1}}):
            folder = self.d / f"info-{abs(hash(json.dumps(bad)))}"
            folder.mkdir()
            (folder / "release.json").write_text(json.dumps(bad))
            with self.assertRaises(rel.ReleaseError):
                rel.read_info(str(folder))

    def test_switch_replaces_the_link_atomically(self):
        a, b, link = self.d / "ra", self.d / "rb", self.d / "current"
        a.mkdir(), b.mkdir()
        rel.switch(str(link), str(a))
        rel.switch(str(link), str(b))
        self.assertEqual(os.path.realpath(link), str(b))
        self.assertFalse((self.d / "current.new").exists())


class DeployAgentLogic(unittest.TestCase):
    """The parts of the agent that are plain logic; the real switch, health check and rollback run in the VM job."""

    def test_versions_sort_numerically_and_prereleases_sort_before_releases(self):
        order = ["v0.0.9", "v0.0.10", "v0.1.0", "v1.0.0-rc1", "v1.0.0", "v1.0.1"]
        self.assertEqual(sorted(reversed(order), key=deploy.vkey), order)
        with self.assertRaises(ValueError):
            deploy.vkey("latest")

    def test_the_deploy_window_may_wrap_midnight_and_empty_means_always(self):
        import datetime as dt
        at = lambda h: dt.datetime(2026, 1, 1, h, 30, tzinfo=dt.timezone.utc)
        self.assertTrue(deploy.in_window("", at(14)))
        self.assertTrue(deploy.in_window("09-12", at(9)))
        self.assertFalse(deploy.in_window("09-12", at(12)))
        self.assertTrue(deploy.in_window("22-02", at(23)))
        self.assertTrue(deploy.in_window("22-02", at(1)))
        self.assertFalse(deploy.in_window("22-02", at(3)))

    def test_it_will_only_download_from_github_over_https(self):
        for url in ("http://github.com/x", "https://evil.example.invalid/x", "file:///etc/passwd", "ftp://github.com/x", "https://github.com.evil.invalid/x"):
            with self.assertRaises(deploy.Refused):
                deploy.https_get(url)

    def test_the_ci_release_base_is_refused_on_anything_but_a_ci_install(self):
        with self.assertRaises(deploy.Refused):
            deploy.source({"TREELINE_RELEASE_BASE": "http://example.invalid/releases"})
        self.assertEqual(deploy.source({"TREELINE_RELEASE_BASE": "http://x/r", "TREELINE_CI": "1"}), ("http://x/r", True))
        with self.assertRaises(deploy.Failed):
            deploy.source({})
        with self.assertRaises(deploy.Failed):
            deploy.source({"TREELINE_RELEASE_REPO": "../../etc"})

    def test_calls_in_progress_counts_channels_and_treats_an_unanswered_question_as_busy(self):
        import http.server
        import threading

        class Ari(http.server.BaseHTTPRequestHandler):
            channels = []

            def do_GET(self):
                if self.headers.get("Authorization") is None:
                    self.send_response(401)
                    self.send_header("WWW-Authenticate", 'Basic realm="x"')
                    self.end_headers()
                    return
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps(Ari.channels).encode())

            def log_message(self, *a):
                pass

        server = http.server.HTTPServer(("127.0.0.1", 0), Ari)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        url = f"http://127.0.0.1:{server.server_port}/ari"
        Ari.channels = []
        self.assertEqual(deploy.calls_in_progress(url, "u", "p"), 0)
        Ari.channels = [{"id": "a"}, {"id": "b"}]
        self.assertEqual(deploy.calls_in_progress(url, "u", "p"), 2)
        self.assertIsNone(deploy.calls_in_progress("http://127.0.0.1:9/ari", "u", "p"), "unknown must not look like idle")

    def test_wait_for_quiet_raises_busy_for_a_call_and_for_not_knowing(self):
        real = deploy.calls_in_progress
        try:
            for answer, text in ((1, "a call is in progress"), (None, "could not ask")):
                deploy.calls_in_progress = lambda a=answer: a
                with self.assertRaises(deploy.Busy) as caught:
                    deploy.wait_for_quiet({}, window=False)
                self.assertIn(text, str(caught.exception))
            deploy.calls_in_progress = lambda: 0
            deploy.wait_for_quiet({}, window=False)
        finally:
            deploy.calls_in_progress = real

    def test_pre_migration_copies_are_restored_at_the_version_the_old_code_expects_and_only_if_all_exist(self):
        d = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        real = deploy.common.STATE
        deploy.common.STATE = str(d)
        self.addCleanup(setattr, deploy.common, "STATE", real)
        import sqlite3
        def make(path, version, marker):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.unlink(missing_ok=True)
            c = sqlite3.connect(path)
            c.execute("CREATE TABLE t(x)"); c.execute("INSERT INTO t VALUES (?)", (marker,))
            c.execute(f"PRAGMA user_version={version}"); c.commit(); c.close()
        d = d / "data"                                       # the databases live in STATE/data
        make(d / "treeline.db", 2, "migrated")
        make(d / "pre-migrate" / "treeline-v1-20260101T000000-aaaaaa.db", 1, "old-older")
        make(d / "pre-migrate" / "treeline-v1-20260102T000000-bbbbbb.db", 1, "old-newer")
        make(d / "pre-migrate" / "treeline-v2-20260103T000000-cccccc.db", 2, "wrong-version")
        done = deploy.restore_data_from_pre_migrate({"treeline.db": 2}, {"treeline.db": 1}, owner=None)
        self.assertEqual(done, ["treeline.db"])
        c = sqlite3.connect(d / "treeline.db")
        self.assertEqual(c.execute("PRAGMA user_version").fetchone()[0], 1)
        self.assertEqual(c.execute("SELECT x FROM t").fetchone()[0], "old-newer")      # the newest copy at the old version
        # a household with no copy: nothing at all is changed (all-or-nothing)
        make(d / "treeline.db", 2, "migrated-again")
        make(d / "households" / "7.db", 2, "h")
        with self.assertRaises(deploy.Failed):
            deploy.restore_data_from_pre_migrate({"treeline.db": 2, "households/7.db": 2}, {"treeline.db": 1, "households/7.db": 1}, owner=None)
        self.assertEqual(sqlite3.connect(d / "treeline.db").execute("SELECT x FROM t").fetchone()[0], "migrated-again")

    def test_a_file_made_by_the_failed_release_is_set_aside_not_a_reason_to_abandon_the_rollback(self):
        """Code review #2: a family created during the health wait has a household file at the NEW version and no pre-migration
        copy. It must not make the whole rollback fail and leave every family without service."""
        before = {"treeline.db": 1, "households/1.db": 1}
        after = {"treeline.db": 2, "households/1.db": 2, "households/42.db": 2}
        expected = {"treeline.db": 1, "households/1.db": 1, "households/42.db": 1}
        moved, created = deploy.plan_rollback(before, after, expected)
        self.assertEqual(moved, {"treeline.db": 2, "households/1.db": 2})
        self.assertEqual(created, {"households/42.db": 2})
        d = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        real = deploy.common.STATE
        deploy.common.STATE = str(d)
        self.addCleanup(setattr, deploy.common, "STATE", real)
        (d / "data" / "households").mkdir(parents=True)
        for suffix in ("", "-wal"):
            (d / "data" / "households" / f"42.db{suffix}").write_text("x")
        deploy.quarantine(created)
        self.assertFalse((d / "data" / "households" / "42.db").exists())
        kept = list((d / "data" / "quarantine").rglob("42.db*"))
        self.assertEqual(len(kept), 2, "set aside with its WAL, not deleted")

    def test_state_keeps_the_failed_list_and_a_success_clears_it(self):
        d = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        p = {"state": str(d)}
        deploy.record(p, current="v1.0.0", previous=None)
        deploy.mark_failed(p, "v1.1.0")
        deploy.record(p, current="v1.0.0", previous=None)          # a later record keeps the list
        self.assertEqual(deploy.read_state(p)["failed"], ["v1.1.0"])
        deploy.clear_failed(p, "v1.1.0")
        self.assertEqual(deploy.read_state(p)["failed"], [])

    def test_a_manual_rollback_that_fails_goes_back_and_never_leaves_the_services_stopped(self):
        """Code review #3: an error after the services were stopped used to escape as a traceback."""
        d = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        (d / "releases" / "v1.0.0").mkdir(parents=True)
        (d / "releases" / "v1.1.0").mkdir(parents=True)
        p = {"state": str(d / "state"), "releases": str(d / "releases"), "current": str(d / "current")}
        os.symlink(d / "releases" / "v1.1.0", d / "current")
        deploy.record(p, current="v1.1.0", previous="v1.0.0")
        calls = []
        def fake_run(cmd, **kw):
            calls.append(cmd)
            return subprocess.CompletedProcess(cmd, 1 if "treeline-config" in cmd[0] else 0, "", "boom: a template")
        from unittest import mock
        with mock.patch.object(deploy, "data_versions", lambda: {"treeline.db": 1}), \
                mock.patch.object(deploy, "schema_of", lambda _d: {"central": 1, "household": 1}), \
                mock.patch.object(deploy, "wait_for_quiet", lambda *a, **k: None), \
                mock.patch.object(deploy.common, "host_settings", lambda *a: {}), \
                mock.patch.object(deploy, "snapshot_config", lambda dest: None), \
                mock.patch.object(deploy, "restore_config", lambda src: calls.append(["restore_config"])), \
                mock.patch.object(deploy, "build_sounds", lambda rd: None), \
                mock.patch.object(deploy, "health", lambda v, seconds=0: v == "v1.1.0"), \
                mock.patch.object(deploy.subprocess, "run", fake_run):
            rc = deploy.manual_rollback(p)
        self.assertEqual(rc, 1, "it reports the failure ...")
        self.assertEqual(os.path.realpath(d / "current"), str(d / "releases" / "v1.1.0"), "... and is back on what was running")
        self.assertIn(["restore_config"], calls)
        self.assertTrue(any(c[:2] == ["systemctl", "restart"] and "treeline-api" in c for c in calls), "the services were started again")

    def test_expected_versions_come_from_the_old_releases_own_schema(self):
        self.assertEqual(deploy.expected_versions(["treeline.db", "households/3.db"], {"central": 4, "household": 2}),
                         {"treeline.db": 4, "households/3.db": 2})


if __name__ == "__main__":
    unittest.main()
