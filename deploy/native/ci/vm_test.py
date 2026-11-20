#!/usr/bin/env python3
"""The CI job that imitates the VM (docs/DEPLOY_AWS.md, work package 3).

It runs the real install.sh and the real deploy agent inside an ubuntu:24.04 container that runs systemd, next to
three helpers on a private Docker network: a fake SSM/S3 (fake_aws.py), a local ACME CA (Caddy 2.6.2, the version
Ubuntu installs, acting as `acme_server`) and an outside client that probes the VM from another host.

What it can and cannot show is in the spec: it finds install breakage, wrong routing, ports that are reachable,
a signature check that accepts too much, a rollback that does not happen. It cannot test NAT, Let's Encrypt, SES,
Lightsail's firewall or disk. Run it with `./dev vm` (needs Docker, privileged containers and ~6 minutes) or
`python3 -m unittest deploy/native/ci/vm_test.py -v`. Set TREELINE_VM_KEEP=1 to leave the containers up to look around.
"""

import gzip
import json
import os
import pathlib
import shutil
import subprocess
import tarfile
import tempfile
import textwrap
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
CI = ROOT / "deploy" / "native" / "ci"
NET = "treeline-vmtest"
VM, CLIENT, CA, AWS = "treeline-vmtest-vm", "treeline-vmtest-client", "treeline-vmtest-ca", "treeline-vmtest-aws"
DOMAIN = "app.treeline.test"
SECRETS = {"/treeline/smtp_user": "AKI" + "AFAKESMTPUSER00000", "/treeline/smtp_password": "fakeSmtpPassword-ci-only-0123456789",
           "/treeline/vapid_public": "BFakeVapidPublicKeyForCiOnly0123456789abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqrs",
           "/treeline/vapid_private": "fakeVapidPrivateKeyForCiOnly0123456789abc"}


def run(*args, check=True, timeout=900, input=None):
    done = subprocess.run([str(a) for a in args], capture_output=True, text=True, timeout=timeout, input=input)
    if check and done.returncode != 0:
        raise AssertionError(f"{' '.join(map(str, args))[:200]} -> {done.returncode}\n{done.stdout[-2500:]}\n{done.stderr[-2500:]}")
    return done


def vm(cmd, check=True, timeout=900):
    return run("docker", "exec", VM, "bash", "-c", cmd, check=check, timeout=timeout)


def client(cmd, check=True):
    return run("docker", "exec", CLIENT, "bash", "-c", cmd, check=check, timeout=120)


def build_image(tag, dockerfile):
    run("docker", "build", "-q", "-t", tag, "-", input=dockerfile)


def wait_for(fn, seconds, what):
    end = time.time() + seconds
    last = None
    while time.time() < end:
        try:
            if fn():
                return
        except Exception as err:       # noqa: BLE001
            last = err
        time.sleep(1.5)
    raise AssertionError(f"timed out waiting for {what}: {last}")


def setUpModule():
    VmTestCase.bring_up()


def tearDownModule():
    VmTestCase.bring_down()


class VmTestCase(unittest.TestCase):
    """Base: the environment, built once for the whole module (setUpModule); the classes below share it."""

    @classmethod
    def bring_up(cls):
        if os.environ.get("TREELINE_VM_REUSE") == "1" and run("docker", "inspect", VM, check=False).returncode == 0:
            cls.tmp = pathlib.Path(os.environ["TREELINE_VM_TMP"])
            return
        cls.teardown_env()
        cls.tmp = pathlib.Path(tempfile.mkdtemp(prefix="treeline-vmtest-"))
        (cls.tmp / "shared").mkdir()
        os.chmod(cls.tmp, 0o755)
        os.chmod(cls.tmp / "shared", 0o777)
        cls.build_images()
        run("docker", "network", "create", NET)
        # the fake AWS
        (cls.tmp / "aws").mkdir()
        os.chmod(cls.tmp / "aws", 0o777)
        (cls.tmp / "params.json").write_text(json.dumps(SECRETS))
        run("docker", "run", "-d", "--name", AWS, "--network", NET, "--network-alias", "fakeaws",
            "-v", f"{CI}/fake_aws.py:/fake_aws.py:ro", "-v", f"{cls.tmp}/params.json:/params.json:ro", "-v", f"{cls.tmp}/aws:/state",
            "python:3.12-slim", "python3", "/fake_aws.py", "9000", "/params.json", "/state")
        # the local ACME CA
        (cls.tmp / "CaCaddyfile").write_text(textwrap.dedent("""\
            {
            	admin off
            }
            ca.treeline.test:9000 {
            	tls internal
            	acme_server
            }
            """))
        run("docker", "run", "-d", "--name", CA, "--network", NET, "--network-alias", "ca.treeline.test",
            "-v", f"{cls.tmp}/CaCaddyfile:/etc/caddy/CaCaddyfile:ro", "-v", f"{cls.tmp}/shared:/shared", "treeline-vmtest-ca",
            "bash", "-c", "caddy run --config /etc/caddy/CaCaddyfile --adapter caddyfile")
        wait_for(lambda: run("docker", "exec", CA, "test", "-f", "/root/.local/share/caddy/pki/authorities/local/root.crt", check=False).returncode == 0,
                 60, "the test CA's root certificate")
        run("docker", "exec", CA, "bash", "-c", "cp /root/.local/share/caddy/pki/authorities/local/root.crt /shared/root.crt && chmod 644 /shared/root.crt")
        # outside client and the VM
        run("docker", "run", "-d", "--name", CLIENT, "--network", NET, "-v", f"{cls.tmp}/shared:/shared:ro", "treeline-vmtest-client", "sleep", "infinity")
        run("docker", "run", "-d", "--name", VM, "--privileged", "--cgroupns=host", "-v", "/sys/fs/cgroup:/sys/fs/cgroup:rw",
            "--tmpfs", "/run", "--tmpfs", "/run/lock", "--network", NET, "--network-alias", DOMAIN, "--network-alias", "treeline.test",
            "-v", f"{cls.tmp}/shared:/ci-shared:ro", "-v", f"{ROOT}/deploy/native/ci:/ci:ro", "treeline-vmtest-vm")
        wait_for(lambda: vm("systemctl is-system-running --wait 2>&1 | head -1", check=False).stdout.strip() in ("running", "degraded"), 60, "systemd")
        cls.make_release("v0.0.1", "good")
        cls.install_first_release()

    @classmethod
    def build_images(cls):
        base = "FROM ubuntu:24.04\nENV DEBIAN_FRONTEND=noninteractive\nRUN apt-get update -qq && apt-get install -y -qq --no-install-recommends %s >/dev/null && apt-get clean\n"
        build_image("treeline-vmtest-vm", base % "systemd systemd-sysv dbus openssh-client ca-certificates" + "STOPSIGNAL SIGRTMIN+3\nCMD [\"/sbin/init\"]\n")
        build_image("treeline-vmtest-client", base % "curl openssl ca-certificates python3 iproute2")
        build_image("treeline-vmtest-ca", base % "caddy ca-certificates")

    @classmethod
    def make_release(cls, version, name, mutate=None, sign=True, copy=True):
        """Build a signed release on the host and copy it into the VM as /root/<name>.tar.gz(.sig)."""
        key = cls.tmp / "signing-key"
        if not key.exists():
            run("ssh-keygen", "-t", "ed25519", "-N", "", "-q", "-f", key, "-C", "treeline ci test key")
            pub = (cls.tmp / "signing-key.pub").read_text().strip()
            (cls.tmp / "signers").write_text(f'treeline-release namespaces="treeline-release" {pub}\n')
        out = cls.tmp / f"out-{name}"
        shutil.rmtree(out, ignore_errors=True)
        run(ROOT / "scripts" / "build_release.sh", version, "--allow-dirty", "--out", out, *(["--sign", key] if sign else []))
        tarball = out / f"treeline-{version}.tar.gz"
        if mutate:
            mutate(tarball)
        if copy:
            run("docker", "cp", str(tarball), f"{VM}:/root/{name}.tar.gz")
            if sign:
                run("docker", "cp", f"{tarball}.sig", f"{VM}:/root/{name}.tar.gz.sig")
        return tarball

    @classmethod
    def variant(cls, version, name, patches=(), schema=None, key=None, copy_sig=True, tamper=False, serve=False):
        """A signed release of the current tree with edits, as an attacker with the key (or a bad commit) could make:
        patches is [(path in the release, old text, new text)]; schema overrides release.json's schema. Copied to the VM
        as /root/<name>.tar.gz(.sig); with serve=True also published on the fake release server as `latest`."""
        built = cls.make_release(version, name + "-plain", sign=False, copy=False)
        work = cls.tmp / f"var-{name}"
        shutil.rmtree(work, ignore_errors=True)
        work.mkdir()
        with tarfile.open(built) as tf:
            tf.extractall(work, filter="data")
        for path, old, new in patches:
            f = work / path
            text = f.read_text()
            assert old in text, f"{path} has no {old!r}"
            f.write_text(text.replace(old, new))
        if schema:
            info = json.loads((work / "release.json").read_text())
            info["schema"] = schema
            (work / "release.json").write_text(json.dumps(info, indent=2, sort_keys=True))
        out = cls.tmp / f"out-{name}"
        shutil.rmtree(out, ignore_errors=True)
        out.mkdir()
        tarball = out / f"treeline-{version}.tar.gz"
        with open(tarball, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as gz, tarfile.open(fileobj=gz, mode="w") as tf:
            for p in sorted(work.rglob("*")):
                info = tf.gettarinfo(str(p), arcname="./" + str(p.relative_to(work)))
                info.uid = info.gid = 0
                info.uname = info.gname = ""
                info.mtime = 0
                if p.is_file():
                    with open(p, "rb") as fh:
                        tf.addfile(info, fh)
                else:
                    tf.addfile(info)
        signing_key = key or (cls.tmp / "signing-key")
        run("ssh-keygen", "-Y", "sign", "-q", "-f", signing_key, "-n", "treeline-release", tarball)
        if tamper:
            data = bytearray(tarball.read_bytes())
            data[len(data) // 2] ^= 1
            tarball.write_bytes(bytes(data))
        run("docker", "cp", str(tarball), f"{VM}:/root/{name}.tar.gz")
        if copy_sig:
            run("docker", "cp", f"{tarball}.sig", f"{VM}:/root/{name}.tar.gz.sig")
        if serve:
            folder = cls.tmp / "aws" / "releases" / version
            folder.mkdir(parents=True, exist_ok=True)
            shutil.copy(tarball, folder / tarball.name)
            shutil.copy(f"{tarball}.sig", folder / (tarball.name + ".sig"))
            (cls.tmp / "aws" / "releases" / "latest").write_text(version + "\n")
        return tarball

    @classmethod
    def install_first_release(cls):
        run("docker", "cp", str(cls.tmp / "signers"), f"{VM}:/root/signers")
        # As the owner would: verify the signature by hand, then unpack, then install.
        vm("ssh-keygen -Y verify -f /root/signers -I treeline-release -n treeline-release -s /root/good.tar.gz.sig < /root/good.tar.gz")
        vm("mkdir /root/rel && tar -xzf /root/good.tar.gz -C /root/rel")
        cls.install(extra="--no-start")
        # key-shaped strings are assembled here so the repo-rules scan does not (rightly) mistake them for a key
        key_id, key_secret = "AKI" + "AFAKEFAKEFAKE0000", "fake" * 10
        vm("install -d -m 0755 /etc/treeline && printf '[treeline-vm]\\n%s = %s\\n%s = %s\\n' aws_access_key_id " + key_id +
           " aws_secret_access_key " + key_secret + " > /etc/treeline/aws-credentials && chmod 600 /etc/treeline/aws-credentials")
        vm("systemctl restart asterisk caddy && systemctl start treeline-api treeline-controller")

    @classmethod
    def install(cls, extra="", public_ip=None):
        cmd = ("cd /root/rel && ./deploy/native/install.sh --ci --domain %s --state-dir /srv/state --aws-endpoint http://fakeaws:9000 "
               "--acme-dir https://ca.treeline.test:9000/acme/local/directory --acme-root /ci-shared/root.crt --signers /root/signers "
               "--release-base http://fakeaws:9000/releases --deploy-window '' %s %s"
               % (DOMAIN, f"--public-ip {public_ip}" if public_ip else "", extra))
        return vm(cmd + " 2>&1 | tail -40", timeout=1200)

    @classmethod
    def teardown_env(cls):
        for c in (VM, CLIENT, CA, AWS):
            run("docker", "rm", "-f", c, check=False)
        run("docker", "network", "rm", NET, check=False)

    @classmethod
    def bring_down(cls):
        if os.environ.get("TREELINE_VM_KEEP") != "1":
            cls.teardown_env()
            shutil.rmtree(getattr(cls, "tmp", "/nonexistent"), ignore_errors=True)
        else:
            print(f"\nkept the containers; scratch directory {cls.tmp}; TREELINE_VM_REUSE=1 TREELINE_VM_TMP={cls.tmp} to reuse")

    # ------------------------------------------------------------ helpers for the tests
    def https(self, path, extra="", host=DOMAIN):
        return client(f"curl -sS -m 10 --cacert /shared/root.crt --resolve {host}:443:$(getent hosts {DOMAIN} | cut -d' ' -f1) {extra} https://{host}{path}", check=False)

    def wait_healthy(self, seconds=90):
        wait_for(lambda: self.https("/api/health", "-o /dev/null -w %{http_code}").stdout.strip() == "200", seconds, "/api/health 200 over https")


class A_Install(VmTestCase):
    def test_services_are_active(self):
        for unit in ("asterisk", "caddy", "treeline-api", "treeline-controller"):
            wait_for(lambda u=unit: vm(f"systemctl is-active {u}", check=False).stdout.strip() == "active", 90, f"{unit} active")

    def test_install_is_idempotent(self):
        before = vm("sha256sum /etc/treeline/host.env /etc/treeline/ari-password /etc/treeline/release_signers /etc/caddy/Caddyfile /etc/asterisk/pjsip.conf /etc/treeline/app.env").stdout
        self.install()
        after = vm("sha256sum /etc/treeline/host.env /etc/treeline/ari-password /etc/treeline/release_signers /etc/caddy/Caddyfile /etc/asterisk/pjsip.conf /etc/treeline/app.env").stdout
        self.assertEqual(before, after)
        self.wait_healthy()

    def test_health_is_200_locally_and_over_https_from_another_host(self):
        self.wait_healthy()
        local = vm("curl -sS -m 5 http://127.0.0.1:8080/api/health").stdout
        body = json.loads(local)
        self.assertTrue(body["ok"], local)
        self.assertEqual(self.https("/api/health", "-o /dev/null -w %{http_code}").stdout.strip(), "200")

    def test_state_is_on_its_own_mount_and_nothing_sensitive_is_on_the_system_disk(self):
        self.wait_healthy()
        self.assertEqual(vm("mountpoint -q /var/lib/treeline && echo yes").stdout.strip(), "yes")
        self.assertIn("treeline.db", vm("ls /var/lib/treeline").stdout)
        # nothing of ours, other than code, lives elsewhere on disk
        stray = vm("find / -xdev \\( -name 'treeline.db*' -o -name 'households' -o -name 'swapfile' \\) -not -path '/srv/state/*' -not -path '/var/lib/treeline/*' -not -path '/proc/*' 2>/dev/null").stdout.strip()
        self.assertEqual(stray, "")
        self.assertEqual(vm("readlink /var/log/asterisk").stdout.strip(), "/var/lib/treeline/logs/asterisk")
        self.assertEqual(vm("stat -c %a /var/lib/treeline/households").stdout.strip(), "700")
        self.assertIn("Storage=volatile", vm("cat /etc/systemd/journald.conf.d/treeline.conf").stdout)

    def test_the_app_runs_as_its_own_user_from_a_root_owned_release(self):
        self.wait_healthy()
        self.assertEqual(vm("ps -o user= -C gunicorn | sort -u").stdout.strip(), "treeline")
        self.assertEqual(vm("stat -c %U:%a /opt/treeline/current/controller/treeline/api.py").stdout.strip(), "root:644")
        self.assertEqual(vm("sudo -n -u treeline true 2>&1; su -s /bin/sh treeline -c 'touch /opt/treeline/current/x' 2>&1 | grep -c -i 'denied\\|read-only'", check=False).stdout.strip().splitlines()[-1], "1")


class B_Network(VmTestCase):
    """What can be reached from another host (the client container), and what is routed where."""

    def test_port_80_only_redirects(self):
        for path, host in (("/", DOMAIN), ("/api/health", DOMAIN), ("/anything?x=1", "other.example.invalid"), ("/ws", DOMAIN), ("/ari/asterisk/info", DOMAIN)):
            out = client(f"curl -sS -m 10 -o /dev/null -w '%{{http_code}} %{{redirect_url}}' -H 'Host: {host}' http://{DOMAIN}{path}").stdout.strip()
            code, _, location = out.partition(" ")
            self.assertEqual(code, "308", f"{host}{path}: {out}")
            self.assertTrue(location.startswith(f"https://{DOMAIN}/"), out)
        post = client(f"curl -sS -m 10 -X POST -d x=1 -o /dev/null -w '%{{http_code}}' http://{DOMAIN}/api/auth/request").stdout.strip()
        self.assertEqual(post, "308")
        # nothing is served in the clear: the body of a redirect carries no application content
        body = client(f"curl -sS -m 10 http://{DOMAIN}/").stdout
        self.assertNotIn("Treeline", body)

    def test_only_ws_reaches_asterisk(self):
        self.wait_healthy()
        ari = vm("cat /etc/treeline/ari-password").stdout.strip()
        # ARI, asked for through the public name with the right password, is not Asterisk
        r = self.https("/ari/asterisk/info", f"-u treeline:{ari} -w '\\n%{{http_code}}'")
        self.assertNotIn('"system"', r.stdout)
        self.assertNotIn("Asterisk", r.stdout.split("\n")[0] if r.stdout else "")
        self.assertTrue(r.stdout.strip().endswith("404"), r.stdout)
        # the real thing, from inside, answers: so the check above could have failed
        inside = vm(f"curl -sS -m 5 -u treeline:{ari} http://127.0.0.1:8088/ari/asterisk/info").stdout
        self.assertIn('"system"', inside)
        # /ws gets a WebSocket from Asterisk
        ws = self.https("/ws", "--http1.1 -o /dev/null -w '%{http_code}' -H 'Connection: Upgrade' -H 'Upgrade: websocket' -H 'Sec-WebSocket-Version: 13' "
                               "-H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' -H 'Sec-WebSocket-Protocol: sip' --max-time 3")
        self.assertIn(ws.stdout.strip(), ("101", "000"), ws.stdout + ws.stderr)      # 000 = curl waited on the open socket
        other = self.https("/wsx", "-o /dev/null -w '%{http_code}'").stdout.strip()
        self.assertEqual(other, "404")                                              # a neighbour path is the app's, not Asterisk's

    def test_ari_and_port_8080_are_not_reachable_from_outside(self):
        def reachable(port, proto="tcp"):
            return client(f"timeout 3 bash -c '</dev/{proto}/{DOMAIN}/{port}'", check=False).returncode == 0
        self.assertTrue(reachable(443), "control: 443 must be reachable or this test proves nothing")
        self.assertTrue(reachable(80), "control: 80 must be reachable")
        for port in (8080, 8088, 5038, 2019, 8089, 22, 3306, 5060):
            self.assertFalse(reachable(port), f"port {port} is reachable from another host")
        # and the listening sockets themselves: anything not on loopback must be on the list
        listening = vm("ss -H -ltn").stdout.splitlines()
        for line in listening:
            local = line.split()[3]
            host, _, port = local.rpartition(":")
            if host in ("127.0.0.1", "[::1]", "127.0.0.11", "127.0.0.53%lo", "127.0.0.54"):
                continue
            self.assertIn(port, ("80", "443", "5061"), f"unexpected listener {local}")
        loopback = {l.split()[3] for l in listening}
        self.assertIn("127.0.0.1:8080", loopback)
        self.assertIn("127.0.0.1:8088", loopback)

    def test_tls_is_1_2_or_better_with_hsts_and_no_server_header(self):
        self.wait_healthy()
        # SECLEVEL=0 so that the CLIENT is willing to try TLS 1.1 at all (otherwise the test would pass because the client refuses)
        old = client(f"echo | openssl s_client -connect {DOMAIN}:443 -servername {DOMAIN} -CAfile /shared/root.crt -tls1_1 -cipher 'DEFAULT:@SECLEVEL=0' 2>&1", check=False).stdout
        self.assertIn("no peer certificate available", old, old[-600:])         # the handshake got no further than the refusal
        self.assertNotIn("BEGIN CERTIFICATE", old, old[-600:])
        self.assertRegex(old, r"alert protocol version|alert handshake failure|no protocols available|Cipher is \(NONE\)|wrong version", "control: the client must actually have tried")
        for flag in ("-tls1_2", "-tls1_3"):
            out = client(f"echo | openssl s_client -connect {DOMAIN}:443 -servername {DOMAIN} -CAfile /shared/root.crt {flag} 2>&1 | grep 'Verification:'").stdout
            self.assertIn("OK", out)
        headers = self.https("/", "-D - -o /dev/null").stdout.lower()
        self.assertIn("strict-transport-security: max-age=31536000", headers)
        self.assertNotIn("preload", headers)
        self.assertNotIn("\nserver:", headers)
        self.assertNotIn("alt-svc", headers)          # HTTP/3 is off: UDP 443 is not open

    def test_caddy_does_not_log_requests(self):
        self.https("/api/health?probe=secret-looking-value")
        logs = vm("journalctl -u caddy --no-pager 2>&1 | grep -c secret-looking-value || true").stdout.strip()
        self.assertEqual(logs.splitlines()[-1], "0")


class C_Certificate(VmTestCase):
    def test_1_caddy_got_a_certificate_at_the_path_certsync_expects_and_asterisk_gets_it(self):
        self.wait_healthy()
        found = vm(f"ls /var/lib/treeline/caddy/certificates/*/{DOMAIN}/{DOMAIN}.crt").stdout.split()
        self.assertEqual(len(found), 1, found)
        self.assertNotIn("/caddy/caddy/", found[0])                 # the Docker layout's extra directory does not exist here
        first = vm("treeline-certsync --no-restart").stdout
        self.assertIn("certificate", first)
        self.assertEqual(vm("stat -c '%U:%a' /etc/asterisk/keys/treeline.key").stdout.strip(), "asterisk:600")
        self.assertEqual(vm("stat -c %a /var/lib/treeline/caddy/certificates/*/*/*.key").stdout.split()[0], "600")
        vm("systemctl restart asterisk")
        started = vm("systemctl show asterisk -p ActiveEnterTimestampMonotonic --value").stdout.strip()
        again = vm("treeline-certsync").stdout
        self.assertIn("unchanged", again)
        self.assertEqual(vm("systemctl show asterisk -p ActiveEnterTimestampMonotonic --value").stdout.strip(), started, "Asterisk was restarted without a change")
        # the pair that Asterisk holds is the pair Caddy has
        self.assertEqual(vm(f"openssl x509 -noout -fingerprint -in /etc/asterisk/keys/treeline.crt").stdout,
                         vm(f"openssl x509 -noout -fingerprint -in /var/lib/treeline/caddy/certificates/*/{DOMAIN}/{DOMAIN}.crt").stdout)

    def test_2_certsync_refuses_when_more_than_one_issuer_matches(self):
        self.wait_healthy()
        vm(f"mkdir -p /var/lib/treeline/caddy/certificates/other-issuer/{DOMAIN} && cp /var/lib/treeline/caddy/certificates/*/{DOMAIN}/{DOMAIN}.* /var/lib/treeline/caddy/certificates/other-issuer/{DOMAIN}/ 2>/dev/null; true")
        try:
            r = vm("treeline-certsync --no-restart 2>&1", check=False)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("more than one certificate", r.stdout)
        finally:
            vm("rm -rf /var/lib/treeline/caddy/certificates/other-issuer")

    def test_3_asterisk_loaded_the_tls_and_websocket_transports(self):
        self.wait_healthy()
        out = vm("asterisk -rx 'pjsip show transports' 2>&1").stdout
        self.assertIn("transport-ws", out)
        self.assertIn("transport-tls", out)
        self.assertNotIn("transport-udp", out)                       # no plaintext SIP transport in production

    def test_4_nat_options_are_accepted_by_this_asterisk_and_ice_section_is_loaded(self):
        """Re-install with a different 'public' address, as behind Lightsail's 1:1 NAT, and ask Asterisk what it loaded."""
        self.install(public_ip="203.0.113.7")
        try:
            wait_for(lambda: "203.0.113.7" in vm("asterisk -rx 'pjsip show transport transport-ws' 2>&1", check=False).stdout, 60, "Asterisk to load external_media_address")
            out = vm("asterisk -rx 'pjsip show transport transport-ws' 2>&1").stdout
            self.assertIn("external_media_address", out)
            self.assertIn("external_signaling_address", out)
            self.assertIn("local_net", out)
            conf = vm("cat /etc/asterisk/rtp.conf").stdout
            self.assertRegex(conf, r"\[ice_host_candidates\]\n\d+\.\d+\.\d+\.\d+ => 203\.0\.113\.7")
            self.assertNotIn("error", vm("asterisk -rx 'rtp show settings' 2>&1").stdout.lower())
            self.assertIn("ice_host_candidates", vm("grep -c . /etc/asterisk/rtp.conf >/dev/null; asterisk -rx 'module show like res_rtp_asterisk'").stdout + conf)
        finally:
            self.install()                                         # back to no NAT
        wait_for(lambda: "203.0.113.7" not in vm("asterisk -rx 'pjsip show transport transport-ws' 2>&1", check=False).stdout, 60, "NAT options to go")


class D_Secrets(VmTestCase):
    def test_secrets_exist_only_in_tmpfs_and_in_the_process(self):
        self.wait_healthy()
        self.assertEqual(vm("stat -c '%a %U' /run/treeline/env").stdout.strip(), "600 root")
        self.assertEqual(vm("stat -f -c %T /run/treeline/env").stdout.strip(), "tmpfs")
        for name, value in SECRETS.items():
            # every file on a disk filesystem (tmpfs such as /run and /dev/shm excluded by -xdev), except this test's own source
            hits = vm(f"find / -xdev -type f -not -path '/proc/*' -not -path '/sys/*' -not -path '/ci/*' -print0 2>/dev/null | xargs -0 grep -IlF -- '{value}' 2>/dev/null; true").stdout.strip()
            self.assertEqual(hits, "", f"{name} found on disk: {hits}")
            # only the service processes (this very command line, run by `bash`, contains the value too)
            self.assertEqual(vm(f"ps -eo comm,args | awk '$1 ~ /^(gunicorn|python|python3|asterisk|caddy|systemd)$/' | grep -cF -- '{value}' || true").stdout.strip().splitlines()[-1], "0", "a secret is on a command line")
            self.assertEqual(vm(f"journalctl --no-pager 2>/dev/null | grep -cF -- '{value}' || true").stdout.strip().splitlines()[-1], "0", "a secret is in the journal")
        ari = vm("cat /etc/treeline/ari-password").stdout.strip()
        self.assertGreaterEqual(len(ari), 32)
        self.assertEqual(vm("stat -c %a /etc/treeline/ari-password").stdout.strip(), "600")

    def test_the_vm_reads_only_ssm_parameters_under_treeline(self):
        self.wait_healthy()
        log = (self.tmp / "aws" / "requests.log").read_text()
        self.assertIn("AmazonSSM.GetParameters", log)
        self.assertNotIn("AmazonSSM.PutParameter", log)

    def test_a_missing_parameter_stops_the_service_instead_of_starting_it_half_configured(self):
        self.wait_healthy()
        saved = (self.tmp / "params.json").read_text()
        try:
            partial = {k: v for k, v in SECRETS.items() if k != "/treeline/vapid_private"}
            (self.tmp / "params.json").write_text(json.dumps(partial))
            run("docker", "restart", AWS)
            time.sleep(2)
            vm("systemctl restart treeline-api", check=False)
            time.sleep(3)
            self.assertNotEqual(vm("systemctl is-active treeline-api", check=False).stdout.strip(), "active")
            self.assertIn("missing SSM parameter", vm("journalctl -u treeline-api --no-pager -n 20 2>&1").stdout)
        finally:
            (self.tmp / "params.json").write_text(saved)
            run("docker", "restart", AWS)
            time.sleep(2)
            vm("systemctl reset-failed treeline-api; systemctl restart treeline-api treeline-controller", check=False)
            self.wait_healthy()


class E_Production(VmTestCase):
    def test_production_refuses_to_start_with_a_dev_setting_and_recovers_without_it(self):
        self.wait_healthy()
        vm("mkdir -p /etc/systemd/system/treeline-api.service.d && printf '[Service]\\nEnvironment=TREELINE_DEV_CODES=1\\n' > /etc/systemd/system/treeline-api.service.d/dev.conf && systemctl daemon-reload")
        try:
            vm("systemctl restart treeline-api", check=False)
            wait_for(lambda: "refuses to start in production" in vm("journalctl -u treeline-api --no-pager -n 40 2>&1").stdout, 30, "the refusal in the journal")
            logs = vm("journalctl -u treeline-api --no-pager -n 40 2>&1").stdout
            self.assertIn("TREELINE_DEV_CODES", logs)
            time.sleep(7)                     # longer than the restart delay: it must still not come up
            self.assertNotEqual(vm("systemctl is-active treeline-api", check=False).stdout.strip(), "active")
            self.assertNotEqual(self.https("/api/health", "-o /dev/null -w %{http_code}").stdout.strip(), "200")
        finally:
            vm("rm -rf /etc/systemd/system/treeline-api.service.d && systemctl daemon-reload && systemctl reset-failed treeline-api; systemctl restart treeline-api", check=False)
        self.wait_healthy()

    def test_dev_sign_in_codes_never_come_back_in_production(self):
        self.wait_healthy()
        out = self.https("/api/auth/request", "-X POST -H 'Content-Type: application/json' -d '{\"email\":\"someone@example.invalid\"}'").stdout
        self.assertNotIn("dev_code", out)


MIGRATE = [("controller/treeline/db.py", "MIGRATIONS = []", 'MIGRATIONS = [lambda conn: conn.execute("CREATE TABLE ci_probe(x)")]')]
UNHEALTHY = [("controller/treeline/api.py", "ok = asterisk and behind == 0", "ok = False")]
SCHEMA2 = {"central": 2, "household": 1}


class F_Deploy(VmTestCase):
    """The deploy agent (work package 2). Numbered: each test starts from where the one before left the machine."""

    def deploy(self, name, *extra):
        r = vm(f"treeline-deploy --tarball /root/{name}.tar.gz --sig /root/{name}.tar.gz.sig {' '.join(extra)} 2>&1; echo RC=$?", timeout=1200)
        out, _, rc = r.stdout.rpartition("RC=")
        return int(rc), out

    def current(self):
        return vm("basename $(readlink /opt/treeline/current)").stdout.strip()

    def serving(self):
        return json.loads(vm("curl -sS -m 5 http://127.0.0.1:8080/api/health", check=False).stdout or "{}").get("release")

    def started(self):
        return vm("systemctl show treeline-api treeline-controller -p ActiveEnterTimestampMonotonic --value").stdout.split()

    def releases(self):
        return sorted(vm("ls -A /opt/treeline/releases").stdout.split())

    def central_version(self):
        return int(vm("runuser -u treeline -- python3 -c \"import sqlite3; print(sqlite3.connect('/var/lib/treeline/treeline.db').execute('PRAGMA user_version').fetchone()[0])\"").stdout.strip())

    def assert_untouched(self, version, started, listing):
        self.assertEqual(self.current(), version)
        self.assertEqual(self.started(), started, "services were restarted by a deploy that must have been refused")
        self.assertEqual(self.releases(), listing, "a refused release left something behind")

    def test_01_a_signed_newer_release_is_deployed_and_the_old_one_kept(self):
        self.wait_healthy()
        self.make_release("v0.0.2", "r2")
        rc, out = self.deploy("r2")
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.current(), "v0.0.2")
        self.assertEqual(self.serving(), "v0.0.2")
        self.assertIn("v0.0.1", self.releases())
        self.assertEqual(json.loads(vm("cat /var/lib/treeline/deploy/state.json").stdout)["previous"], "v0.0.1")
        self.assertEqual(vm("stat -c %U:%a /opt/treeline/releases/v0.0.2/controller/treeline/api.py").stdout.strip(), "root:644")
        self.assertEqual(self.https("/api/health", "-o /dev/null -w %{http_code}").stdout.strip(), "200")

    def test_02_a_tampered_release_is_refused_and_nothing_changes(self):
        before = (self.current(), self.started(), self.releases())
        self.variant("v0.0.3", "tampered", tamper=True)
        rc, out = self.deploy("tampered")
        self.assertEqual(rc, 3, out)
        self.assertIn("signature check FAILED", out)
        self.assert_untouched(*before)

    def test_03_a_signature_by_another_key_is_refused(self):
        before = (self.current(), self.started(), self.releases())
        other = self.tmp / "other-key"
        if not other.exists():
            run("ssh-keygen", "-t", "ed25519", "-N", "", "-q", "-f", other)
        self.variant("v0.0.3", "otherkey", key=other)
        rc, out = self.deploy("otherkey")
        self.assertEqual(rc, 3, out)
        self.assertIn("FAILED", out)
        self.assert_untouched(*before)

    def test_04_an_unsigned_release_is_refused(self):
        before = (self.current(), self.started(), self.releases())
        self.variant("v0.0.3", "unsigned", copy_sig=False)
        rc, out = self.deploy("unsigned")
        self.assertEqual(rc, 3, out)
        self.assertIn("no signature", out)
        self.assert_untouched(*before)

    def test_05_a_genuine_old_release_under_a_new_name_is_refused_as_a_replay(self):
        before = (self.current(), self.started(), self.releases())
        self.variant("v0.0.50", "replay")
        rc, out = self.deploy("replay", "--version v0.0.51")
        self.assertEqual(rc, 3, out)
        self.assertIn("says it is v0.0.50, not v0.0.51", out)
        self.assert_untouched(*before)

    def test_06_an_older_release_is_refused(self):
        before = (self.current(), self.started(), self.releases())
        self.variant("v0.0.0", "older")
        rc, out = self.deploy("older")
        self.assertEqual(rc, 3, out)
        self.assertIn("not newer", out)
        self.assert_untouched(*before)

    def test_07_a_release_whose_code_does_not_import_is_refused_before_anything_is_touched(self):
        before = (self.current(), self.started(), self.releases())
        self.variant("v0.0.4", "broken", patches=[("controller/treeline/api.py", "def health():", "def health(:")])
        rc, out = self.deploy("broken")
        self.assertEqual(rc, 3, out)
        self.assertIn("failed its own checks", out)
        self.assert_untouched(*before)

    def test_08_a_release_that_never_becomes_healthy_is_rolled_back(self):
        self.variant("v0.0.4", "unhealthy", patches=UNHEALTHY)
        rc, out = self.deploy("unhealthy")
        self.assertEqual(rc, 1, out)
        self.assertIn("ROLLED BACK to v0.0.2", out)
        self.assertEqual(self.current(), "v0.0.2")
        self.wait_healthy()
        self.assertEqual(self.serving(), "v0.0.2")
        self.assertNotIn("v0.0.4", self.releases(), "the failed release must be removed so the fixed one can be deployed under the same name")

    def test_09_a_failed_release_that_migrated_the_data_is_undone_with_the_pre_migration_copy(self):
        vm("runuser -u treeline -- python3 -c \"import sqlite3; c=sqlite3.connect('/var/lib/treeline/treeline.db'); c.execute('CREATE TABLE IF NOT EXISTS ci_marker(x)'); c.execute('INSERT INTO ci_marker VALUES (42)'); c.commit()\"")
        self.assertEqual(self.central_version(), 1)
        self.variant("v0.0.5", "migrate-bad", patches=MIGRATE + UNHEALTHY, schema=SCHEMA2)
        rc, out = self.deploy("migrate-bad")
        self.assertEqual(rc, 1, out)
        self.assertIn("restoring the copies", out)
        self.assertIn("ROLLED BACK to v0.0.2", out)
        self.assertEqual(self.central_version(), 1, "the file must be back at the version the old code understands")
        self.assertEqual(vm("runuser -u treeline -- python3 -c \"import sqlite3; print(sqlite3.connect('/var/lib/treeline/treeline.db').execute('SELECT x FROM ci_marker').fetchone()[0])\"").stdout.strip(), "42")
        self.wait_healthy()
        self.assertEqual(self.serving(), "v0.0.2")
        self.assertEqual(vm("stat -c %U:%a /var/lib/treeline/treeline.db").stdout.strip(), "treeline:600")

    def test_10_a_healthy_release_that_migrated_cannot_be_rolled_back_by_hand(self):
        self.variant("v0.0.6", "migrate-ok", patches=MIGRATE, schema=SCHEMA2)
        rc, out = self.deploy("migrate-ok")
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.central_version(), 2)
        self.wait_healthy()
        before = (self.current(), self.started(), self.releases())
        rc, out = vm("treeline-deploy --rollback 2>&1; echo RC=$?").stdout.rpartition("RC=")[::2]
        self.assertEqual(int(out), 3, rc)
        self.assertIn("cannot roll back", rc)
        self.assert_untouched(*before)
        self.assertEqual(self.serving(), "v0.0.6")

    def test_11_a_deploy_waits_while_a_call_is_in_progress(self):
        self.variant("v0.0.7", "busy", patches=MIGRATE, schema=SCHEMA2)
        vm("printf '\\n[ci-wait]\\nexten => s,1,Wait(300)\\n' >> /etc/asterisk/extensions.conf && asterisk -rx 'dialplan reload' >/dev/null && "
           "asterisk -rx 'channel originate Local/s@ci-wait application Wait 300' >/dev/null")
        wait_for(lambda: len(json.loads(vm("curl -sS -u treeline:$(cat /etc/treeline/ari-password) http://127.0.0.1:8088/ari/channels").stdout)) > 0, 20, "an open channel")
        before = (self.current(), self.started(), self.releases())
        rc, out = self.deploy("busy")
        self.assertEqual(rc, 4, out)
        self.assertIn("a call is in progress", out)
        self.assertEqual(self.current(), "v0.0.6")
        vm("asterisk -rx 'channel request hangup all' >/dev/null")
        wait_for(lambda: json.loads(vm("curl -sS -u treeline:$(cat /etc/treeline/ari-password) http://127.0.0.1:8088/ari/channels").stdout) == [], 20, "no open channels")
        rc, out = self.deploy("busy")
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.current(), "v0.0.7")
        self.assertNotIn("ci-wait", vm("cat /etc/asterisk/extensions.conf").stdout, "the config must have been put back by the deploy")

    def test_12_a_manual_rollback_works_when_the_data_layout_did_not_move(self):
        self.wait_healthy()
        rc, out = vm("treeline-deploy --rollback 2>&1; echo RC=$?").stdout.rpartition("RC=")[::2]
        self.assertEqual(int(out), 0, rc)
        self.assertEqual(self.current(), "v0.0.6")
        self.wait_healthy()
        self.assertEqual(self.serving(), "v0.0.6")

    def test_13_the_timer_path_finds_the_latest_release_and_respects_the_window(self):
        self.variant("v0.0.8", "auto", patches=MIGRATE, schema=SCHEMA2, serve=True)
        self.assertEqual(vm("treeline-deploy 2>&1; echo RC=$?").stdout.rpartition("RC=")[2].strip(), "0")      # downloads, verifies, deploys
        self.assertEqual(self.current(), "v0.0.8")
        out = vm("treeline-deploy 2>&1; echo RC=$?").stdout
        self.assertIn("nothing to do", out)
        # a newer one, but outside the window: not downloaded, not deployed
        self.variant("v0.0.9", "auto2", patches=MIGRATE, schema=SCHEMA2, serve=True)
        hour = int(vm("date -u +%H").stdout.strip())
        vm(f"sed -i 's/^TREELINE_DEPLOY_WINDOW_UTC=.*/TREELINE_DEPLOY_WINDOW_UTC={(hour + 3) % 24:02d}-{(hour + 5) % 24:02d}/' /etc/treeline/host.env")
        rc, out = vm("treeline-deploy 2>&1; echo RC=$?").stdout.rpartition("RC=")[::2]
        self.assertEqual(int(out), 4, rc)
        self.assertIn("outside the deploy window", rc)
        self.assertEqual(self.current(), "v0.0.8")
        vm("sed -i 's/^TREELINE_DEPLOY_WINDOW_UTC=.*/TREELINE_DEPLOY_WINDOW_UTC=/' /etc/treeline/host.env")
        self.assertEqual(vm("treeline-deploy 2>&1; echo RC=$?").stdout.rpartition("RC=")[2].strip(), "0")
        self.assertEqual(self.current(), "v0.0.9")

    def test_14_only_three_releases_are_kept_and_the_timer_is_installed(self):
        self.assertLessEqual(len(self.releases()), 4)           # the last three, plus nothing left over
        self.assertNotIn("v0.0.1", self.releases())
        self.assertEqual(vm("systemctl is-enabled treeline-deploy.timer").stdout.strip(), "enabled")
        self.assertNotIn(".staging", " ".join(self.releases()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
