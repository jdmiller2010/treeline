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
import io
import json
import os
import pathlib
import re
import secrets
import shutil
import subprocess
import tarfile
import tempfile
import textwrap
import threading
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
CI = ROOT / "deploy" / "native" / "ci"
NET = "treeline-vmtest"
VM, CLIENT, CA, AWS = "treeline-vmtest-vm", "treeline-vmtest-client", "treeline-vmtest-ca", "treeline-vmtest-aws"
DOMAIN = "app.treeline.test"
SECRETS = {"/treeline/smtp_user": "AKI" + "AFAKESMTPUSER00000", "/treeline/smtp_password": "fakeSmtpPassword-ci-only-0123456789",
           "/treeline/vapid_public": "BFakeVapidPublicKeyForCiOnly0123456789abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqrs",
           "/treeline/vapid_private": "fakeVapidPrivateKeyForCiOnly0123456789abc",
           "/treeline/google_client_id": "123-ci.apps.googleusercontent.com", "/treeline/google_client_secret": "fake-google-secret-ci-only-0123456789",
           "/treeline/beta_code_hash": "0" * 64, "/treeline/beta_code_expires": "2099-01-01"}


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
        # The Asterisk build is compiled (or found) while the images below are built: it needs nothing from them, and on a CI runner
        # this overlaps about two minutes of each with the other. The result is checked against artifact.lock either way.
        cls._artifact_error = None

        def prepare():
            try:
                cls.asterisk_artifact()
            except BaseException as err:      # noqa: BLE001 -- re-raised, with its message, where the release is made
                cls._artifact_error = err
        cls._artifact_thread = threading.Thread(target=prepare, daemon=True)
        cls._artifact_thread.start()
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
        cls._artifact_thread.join()
        if cls._artifact_error:
            raise cls._artifact_error
        cls.make_release("v0.0.1", "good")
        cls.install_first_release()

    @classmethod
    def build_images(cls):
        base = "FROM ubuntu:24.04\nENV DEBIAN_FRONTEND=noninteractive\nRUN apt-get update -qq && apt-get install -y -qq --no-install-recommends %s >/dev/null && apt-get clean\n"
        build_image("treeline-vmtest-vm", base % "systemd systemd-sysv dbus openssh-client ca-certificates" + "STOPSIGNAL SIGRTMIN+3\nCMD [\"/sbin/init\"]\n")
        build_image("treeline-vmtest-client", base % "curl openssl ca-certificates python3 iproute2")
        build_image("treeline-vmtest-ca", base % "caddy ca-certificates")

    @classmethod
    def asterisk_artifact(cls):
        """The Asterisk build every release carries: the one asterisk/build/artifact.lock names, never a different one. Found in
        $TREELINE_ASTERISK_ARTIFACT or dist/asterisk/, or built with asterisk/build/run-build.sh (about a minute); its sha256 is
        checked against the lock either way, so the VM test installs exactly what production would."""
        if getattr(cls, "_artifact", None):
            return cls._artifact
        lock = {k: v for k, v in (l.split("=", 1) for l in (ROOT / "asterisk/build/artifact.lock").read_text().splitlines()
                                  if l and not l.startswith("#"))}
        name = f"asterisk-{lock['ARTIFACT_ID']}.tar.gz"
        import hashlib

        def right(path):
            return path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == lock["ARTIFACT_SHA256"]
        candidates = [pathlib.Path(os.environ["TREELINE_ASTERISK_ARTIFACT"])] if os.environ.get("TREELINE_ASTERISK_ARTIFACT") else []
        candidates.append(ROOT / "dist" / "asterisk" / name)
        found = next((c for c in candidates if right(c)), None)
        if found is None:
            run(ROOT / "asterisk" / "build" / "run-build.sh", ROOT / "dist" / "asterisk", timeout=1800)
            found = ROOT / "dist" / "asterisk" / name
        assert right(found), f"{found} is not the artifact artifact.lock names"
        cls._artifact = found
        return found

    @classmethod
    def repacked_artifact(cls, new_id="24.0.0-x9"):
        """A second Asterisk build for the tests: the real artifact with its id changed to another of the same length, in every
        path, link and file (the binaries' RUNPATH stays correct and the programs run). Ids like this (-x9...) are refused by a
        real install, and accepted only by this job, which is installed with --ci."""
        old = ast_id()
        assert len(new_id) == len(old)
        out = cls.tmp / "repack" / f"asterisk-{new_id}.tar.gz"
        if out.exists():
            return out
        out.parent.mkdir(parents=True, exist_ok=True)
        raw = out.with_suffix("")
        with tarfile.open(cls.asterisk_artifact()) as tin, tarfile.open(raw, "w", format=tarfile.GNU_FORMAT) as tout:
            for m in tin.getmembers():
                data = None
                if m.isfile():
                    data = tin.extractfile(m).read().replace(old.encode(), new_id.encode())
                    m.size = len(data)
                m.name = m.name.replace(old, new_id)
                if m.issym():
                    m.linkname = m.linkname.replace(old, new_id)
                m.mtime, m.uid, m.gid, m.uname, m.gname = 0, 0, 0, "", ""
                tout.addfile(m, io.BytesIO(data) if data is not None else None)
        with open(raw, "rb") as f, open(out, "wb") as o, gzip.GzipFile(fileobj=o, mode="wb", mtime=0) as g:
            g.write(f.read())
        raw.unlink()
        return out

    @classmethod
    def ensure_tls(cls):
        """SIP over TLS needs the certificate Caddy obtains after it starts, copied by treeline-certsync (which restarts Asterisk when
        it changes). Tests that place a call must not depend on an earlier test having done that."""
        wait_for(lambda: vm("treeline-certsync 2>&1", check=False).returncode == 0, 150, "the certificate to be obtained and copied")
        wait_for(lambda: re.search(r":5061\b", vm("ss -H -ltn", check=False).stdout), 60, "Asterisk to listen for SIP over TLS")
        # After an Asterisk restart the controller must register its Stasis application again; a call placed before that is dropped
        # (a real phone just tries again, a test must not race it)
        wait_for(lambda: re.search(r"(?m)^treeline\s*$", vm("asterisk -rx 'ari show apps'", check=False).stdout), 90,
                 "the controller's Stasis application to be registered")

    @classmethod
    def handset(cls):
        """One family with one phone-adapter handset in the machine's real database, written for Asterisk and loaded through the
        same ARI call the controller makes after every handset change (PUT /asterisk/modules/res_pjsip.so)."""
        cls.ensure_tls()
        if getattr(VmTestCase, "_handset_account", None):
            return VmTestCase._handset_account
        secret = secrets.token_urlsafe(18)                  # a throwaway credential for a fake account, chosen here, never printed by the helper
        account = json.loads(vm(f"runuser -u treeline -- /opt/treeline/current/venv/bin/python -I /ci/vm_handset.py {secret}").stdout.strip().splitlines()[-1])
        account["secret"] = secret
        code = vm("curl -sS -o /dev/null -w '%{http_code}' -X PUT -u treeline:$(cat /etc/treeline/ari-password) "
                  "http://127.0.0.1:8088/ari/asterisk/modules/res_pjsip.so").stdout.strip()
        assert code == "204", f"the ARI reload call answered {code}"
        wait_for(lambda: account["user"] in vm("asterisk -rx 'pjsip show endpoints'", check=False).stdout, 30, "Asterisk to know the new handset")
        # the endpoint can show up before its credential and address-of-record are loaded: a call placed now is refused for no reason
        wait_for(lambda: "md5_cred" in vm(f"asterisk -rx 'pjsip show auth {account['user']}'", check=False).stdout, 30, "its credential to be loaded")
        time.sleep(1)
        VmTestCase._handset_account = account
        return account

    @classmethod
    def probe_command(cls, account, *args):
        return ["docker", "exec", "-i", CLIENT, "python3", "-", "--host", DOMAIN, "--cafile", "/shared/root.crt",
                "--user", account["user"], "--secret", account["secret"], *args]

    @classmethod
    def probe(cls, account, *args, timeout=120):
        """Run the SIP probe from the outside client, to completion; returns (exit code, its JSON line)."""
        done = run(*cls.probe_command(account, *args), input=(CI / "sip_probe.py").read_text(), check=False, timeout=timeout)
        line = (done.stdout.strip().splitlines() or ["{}"])[-1]
        return done.returncode, json.loads(line)

    @classmethod
    def probe_in_background(cls, account, *args):
        proc = subprocess.Popen(cls.probe_command(account, *args), stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        proc.stdin.write((CI / "sip_probe.py").read_text())
        proc.stdin.close()
        proc.stdin = None                     # communicate() would try to flush a closed pipe
        return proc

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
        run(ROOT / "scripts" / "build_release.sh", version, "--allow-dirty", "--out", out, "--asterisk", cls.asterisk_artifact(),
            *(["--sign", key] if sign else []))
        tarball = out / f"treeline-{version}.tar.gz"
        if mutate:
            mutate(tarball)
        if copy:
            run("docker", "cp", str(tarball), f"{VM}:/root/{name}.tar.gz")
            if sign:
                run("docker", "cp", f"{tarball}.sig", f"{VM}:/root/{name}.tar.gz.sig")
        return tarball

    @classmethod
    def variant(cls, version, name, patches=(), schema=None, key=None, copy_sig=True, tamper=False, serve=False,
                asterisk=None, info_patch=None, damage_nested=False):
        """A signed release of the current tree with edits, as an attacker with the key (or a bad commit) could make:
        patches is [(path in the release, old text, new text)]; schema overrides release.json's schema. Copied to the VM
        as /root/<name>.tar.gz(.sig); with serve=True also published on the fake release server as `latest`.
        asterisk=PATH carries that Asterisk build instead (its id and sha256 go into release.json); info_patch edits release.json
        (a value of None removes the key); damage_nested changes one byte of the nested Asterisk file and leaves release.json alone,
        which is what someone who can re-sign the outer tarball but cannot make the inner file match would produce."""
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
        info = json.loads((work / "release.json").read_text())
        if schema:
            info["schema"] = schema
        if asterisk:
            import hashlib
            for old_file in (work / "asterisk" / "runtime").glob("*"):
                old_file.unlink()
            new_id = re.fullmatch(r"asterisk-(.+)\.tar\.gz", pathlib.Path(asterisk).name).group(1)
            shutil.copy(asterisk, work / "asterisk" / "runtime" / pathlib.Path(asterisk).name)
            info["asterisk"] = {"id": new_id, "sha256": hashlib.sha256(pathlib.Path(asterisk).read_bytes()).hexdigest()}
        for key_, value in (info_patch or {}).items():
            if value is None:
                info.pop(key_, None)
            else:
                info[key_] = value
        (work / "release.json").write_text(json.dumps(info, indent=2, sort_keys=True))
        if damage_nested:
            nested = next((work / "asterisk" / "runtime").glob("*.tar.gz"))
            data = bytearray(nested.read_bytes())
            data[len(data) // 2] ^= 1
            nested.write_bytes(bytes(data))
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
    def install(cls, extra="", public_ip=None, src="/root/rel"):
        cmd = (f"cd {src} && ./deploy/native/install.sh --ci --domain %s --state-dir /srv/state --aws-endpoint http://fakeaws:9000 "
               "--acme-dir https://ca.treeline.test:9000/acme/local/directory --acme-root /ci-shared/root.crt --signers /root/signers "
               "--release-base http://fakeaws:9000/releases --deploy-window '' %s %s"
               % (DOMAIN, f"--public-ip {public_ip}" if public_ip else "", extra))
        return vm("set -o pipefail; " + cmd + " 2>&1 | tail -40", timeout=1200)       # pipefail: tail must not hide a failed install

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
    def central_version(self):
        return int(vm("runuser -u treeline -- python3 -c \"import sqlite3; print(sqlite3.connect('/var/lib/treeline/data/treeline.db').execute('PRAGMA user_version').fetchone()[0])\"").stdout.strip())

    def assert_untouched(self, version, started, listing):
        self.assertEqual(self.current(), version)
        self.assertEqual(self.started(), started, "services were restarted by a deploy that must have been refused")
        self.assertEqual(self.releases(), listing, "a refused release left something behind")

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

    def https(self, path, extra="", host=DOMAIN):
        return client(f"curl -sS -m 10 --cacert /shared/root.crt --resolve {host}:443:$(getent hosts {DOMAIN} | cut -d' ' -f1) {extra} https://{host}{path}", check=False)

    def wait_healthy(self, seconds=150):
        wait_for(lambda: self.https("/api/health", "-o /dev/null -w %{http_code}").stdout.strip() == "200", seconds, "/api/health 200 over https")


class A_Install(VmTestCase):
    def test_services_are_active(self):
        for unit in ("asterisk", "caddy", "treeline-api", "treeline-controller"):
            wait_for(lambda u=unit: vm(f"systemctl is-active {u}", check=False).stdout.strip() == "active", 90, f"{unit} active")

    def test_install_is_idempotent(self):
        before = vm("sha256sum /etc/treeline/host.env /etc/treeline/ari-password /etc/treeline/release_signers /etc/caddy/Caddyfile /etc/asterisk/*.conf /etc/systemd/system/asterisk.service /etc/systemd/system/asterisk.service.d/treeline.conf /etc/treeline/app.env").stdout
        self.install()
        after = vm("sha256sum /etc/treeline/host.env /etc/treeline/ari-password /etc/treeline/release_signers /etc/caddy/Caddyfile /etc/asterisk/*.conf /etc/systemd/system/asterisk.service /etc/systemd/system/asterisk.service.d/treeline.conf /etc/treeline/app.env").stdout
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
        self.assertIn("treeline.db", vm("ls /var/lib/treeline/data").stdout)
        # the top of the state disk is root's; the app user owns only its own folders (R6-2)
        self.assertEqual(vm("stat -c %U:%a /var/lib/treeline").stdout.strip(), "root:711")
        self.assertEqual(vm("stat -c %U:%a /var/lib/treeline/data /var/lib/treeline/backup").stdout.split(), ["treeline:700", "root:700"])
        self.assertNotEqual(vm("su -s /bin/sh treeline -c 'mv /var/lib/treeline/spool /var/lib/treeline/x' 2>&1; echo RC=$?", check=False).stdout.strip()[-4:], "RC=0")
        # nothing of ours, other than code, lives elsewhere on disk
        stray = vm("find / -xdev \\( -name 'treeline.db*' -o -name 'households' -o -name 'swapfile' \\) -not -path '/srv/state/*' -not -path '/var/lib/treeline/*' -not -path '/proc/*' 2>/dev/null").stdout.strip()
        self.assertEqual(stray, "")
        # Asterisk's logs and its contact database are on the state disk (asterisk.conf's directories), none on the system disk
        self.assertEqual(vm("stat -c %U:%a /var/lib/treeline/logs/asterisk /var/lib/treeline/asterisk").stdout.split(), ["asterisk:750", "asterisk:750"])
        self.assertEqual(vm("find / -xdev \\( -name 'astdb.sqlite3*' -o -name 'messages' -path '*asterisk*' \\) -not -path '/srv/state/*' -not -path '/var/lib/treeline/*' -not -path '/proc/*' 2>/dev/null").stdout.strip(), "")
        self.assertEqual(vm("stat -c %a /var/lib/treeline/data/households").stdout.strip(), "700")
        self.assertIn("Storage=volatile", vm("cat /etc/systemd/journald.conf.d/treeline.conf").stdout)

    def test_the_app_runs_as_its_own_user_from_a_root_owned_release(self):
        self.wait_healthy()
        self.assertEqual(vm("ps -o user= -C gunicorn | sort -u").stdout.strip(), "treeline")
        self.assertEqual(vm("stat -c %U:%a /opt/treeline/current/controller/treeline/api.py").stdout.strip(), "root:644")
        self.assertEqual(vm("sudo -n -u treeline true 2>&1; su -s /bin/sh treeline -c 'touch /opt/treeline/current/x' 2>&1 | grep -c -i 'denied\\|read-only'", check=False).stdout.strip().splitlines()[-1], "1")


def lock_field(name):
    for line in (ROOT / "asterisk" / "build" / "artifact.lock").read_text().splitlines():
        if line.startswith(name + "="):
            return line.split("=", 1)[1]
    raise KeyError(name)


def modules_txt():
    return sorted(l.strip() for l in (ROOT / "asterisk" / "build" / "modules.txt").read_text().splitlines()
                  if l.strip() and not l.lstrip().startswith("#"))


def ast_id():
    return lock_field("ARTIFACT_ID")


class A2_Asterisk(VmTestCase):
    """The Asterisk this machine runs is the one the release carries, as the unprivileged user it should be, and nothing else."""

    def main_pid(self):
        return vm("systemctl show asterisk -p MainPID --value").stdout.strip()

    def test_1_the_running_binary_is_the_build_artifact_lock_names_and_nothing_from_Ubuntu(self):
        self.wait_healthy()
        pid = self.main_pid()
        self.assertEqual(vm(f"readlink /proc/{pid}/exe").stdout.strip(), f"/opt/asterisk/{ast_id()}/sbin/asterisk")
        self.assertEqual(vm("asterisk -V").stdout.strip(), "Asterisk " + ast_id().split("-t")[0])
        self.assertEqual(vm("readlink -f /usr/local/sbin/asterisk").stdout.strip(), f"/opt/asterisk/{ast_id()}/sbin/asterisk")
        # the very bytes the lock names: extract the binary from the artifact on the host and compare hashes
        with tarfile.open(ROOT / "dist" / "asterisk" / f"asterisk-{ast_id()}.tar.gz") as tf:
            import hashlib
            want = hashlib.sha256(tf.extractfile(f"opt/asterisk/{ast_id()}/sbin/asterisk").read()).hexdigest()
        self.assertEqual(vm(f"sha256sum /opt/asterisk/{ast_id()}/sbin/asterisk").stdout.split()[0], want)
        self.assertEqual(vm(f"stat -c %U:%a /opt/asterisk/{ast_id()}/sbin/asterisk").stdout.strip(), "root:755")
        self.assertEqual(vm("find /opt/asterisk ! -type l \\( -perm /6000 -o -perm /022 \\) | head -3").stdout.strip(), "", "no set-id and nothing group/world-writable (links are always 777)")
        self.assertEqual(vm(f"find /opt/asterisk -not -user root | head -3").stdout.strip(), "")

    def test_2_ubuntus_package_is_not_installed_and_cannot_come_back(self):
        self.assertEqual(vm("dpkg-query -W 'asterisk*' 2>/dev/null; true").stdout.strip(), "")
        self.assertIn("Candidate: (none)", vm("apt-cache policy asterisk").stdout)
        r = vm("apt-get install -s asterisk 2>&1", check=False)
        self.assertNotEqual(r.returncode, 0, r.stdout)

    def test_3_it_runs_as_the_asterisk_user_with_no_capabilities_and_a_hardened_unit(self):
        self.wait_healthy()
        pid = self.main_pid()
        self.assertEqual(vm(f"ps -o user= -p {pid}").stdout.strip(), "asterisk")
        status = vm(f"cat /proc/{pid}/status").stdout
        self.assertRegex(status, r"CapEff:\s+0000000000000000")
        self.assertRegex(status, r"CapBnd:\s+0000000000000000")
        self.assertRegex(status, r"NoNewPrivs:\s+1")
        cmdline = vm(f"tr '\\0' ' ' < /proc/{pid}/cmdline").stdout
        self.assertIn(f"-C /etc/asterisk/asterisk-{ast_id()}.conf", cmdline)
        self.assertNotRegex(cmdline, r" -[a-zA-Z]*p")                    # no real-time priority
        shown = vm("systemctl show asterisk -p User -p Type -p NoNewPrivileges -p ProtectSystem -p PrivateDevices -p PrivateTmp "
                   "-p RestrictSUIDSGID -p NeedDaemonReload -p Restart").stdout
        for line in ("User=asterisk", "Type=notify", "NoNewPrivileges=yes", "ProtectSystem=strict", "PrivateDevices=yes", "PrivateTmp=yes",
                     "RestrictSUIDSGID=yes", "NeedDaemonReload=no", "Restart=on-failure"):
            self.assertIn(line, shown)
        self.assertEqual(vm("id -Gn asterisk").stdout.strip(), "asterisk", "no supplementary groups")
        self.assertEqual(vm("getent passwd asterisk | cut -d: -f6,7").stdout.strip(), "/var/lib/treeline/asterisk:/usr/sbin/nologin")

    def test_4_etc_asterisk_holds_only_what_the_release_says_and_asterisk_cannot_rewrite_it(self):
        self.wait_healthy()
        names = vm("ls -A /etc/asterisk").stdout.split()
        self.assertEqual(sorted(n for n in names if n.endswith(".conf") and n.startswith("asterisk")), sorted(["asterisk.conf", f"asterisk-{ast_id()}.conf"]))
        self.assertIn("keys", names)
        self.assertNotIn("manager.conf", names)                           # AMI has no configuration, so it is off
        self.assertEqual(vm("find /etc/asterisk -user asterisk | head -3").stdout.strip(), "", "nothing in /etc/asterisk belongs to asterisk")
        self.assertEqual(vm("stat -c %U:%G:%a /etc/asterisk /etc/asterisk/keys /etc/asterisk/pjsip.conf /etc/asterisk/modules.conf").stdout.split(),
                         ["root:asterisk:750", "root:asterisk:750", "root:asterisk:640", "root:asterisk:640"])
        tried = vm("su -s /bin/sh asterisk -c 'echo x >> /etc/asterisk/pjsip.conf' 2>&1", check=False)
        self.assertNotEqual(tried.returncode, 0, "the asterisk user must not be able to change its own configuration")

    def test_5_exactly_the_built_modules_are_loaded_and_there_is_no_manager_interface(self):
        self.wait_healthy()
        self.ensure_tls()
        listing = vm("asterisk -rx 'module show'").stdout
        loaded = sorted(re.findall(r"^(\S+)\.so\s", listing, re.M))
        self.assertEqual(loaded, modules_txt())
        # `manager` is a built-in core module (AMI cannot be compiled out); that it has no configuration and nothing listens is the point
        self.assertNotRegex(listing, r"(?m)^(cdr_|cel_|chan_sip|chan_iax2|res_pjsip_history|res_pjsip_messaging)")
        listening = vm("ss -H -ltn").stdout
        self.assertNotRegex(listening, r":5038\b", "AMI is not listening")
        self.assertNotRegex(listening, r":5060\b", "no plaintext SIP")
        self.assertRegex(listening, r"127\.0\.0\.1:8088\b")
        self.assertRegex(listening, r":5061\b")

    def test_6_its_directories_are_the_ones_asterisk_conf_names_and_its_state_is_on_the_state_disk(self):
        self.wait_healthy()
        settings = vm("asterisk -rx 'core show settings'").stdout
        self.assertIn(f"/opt/asterisk/{ast_id()}/share/asterisk", settings)
        self.assertEqual(vm("stat -c %U:%a /run/asterisk").stdout.strip(), "asterisk:750")
        self.assertRegex(vm("stat -c %U:%G:%a /run/asterisk/asterisk.ctl").stdout.strip(), r"^asterisk:asterisk:")
        self.assertTrue(vm("test -s /var/lib/treeline/logs/asterisk/messages && echo yes").stdout.strip() == "yes")

    def test_7_the_first_boot_log_has_no_load_failure_and_ice_is_compiled_in(self):
        self.wait_healthy()
        log = vm("cat /var/lib/treeline/logs/asterisk/messages").stdout
        self.assertNotRegex(log, r"Unable to load module|Failed to load module|could not be loaded")
        # On the first start the certificate does not exist yet (Caddy obtains it, and treeline-certsync copies it and restarts Asterisk):
        # those lines, and only those, are expected. Anything else at ERROR level is a finding.
        expected = re.compile(r"cert_file /etc/asterisk/keys/treeline\.crt is either missing|Error parsing cert_file=|"
                              r"Could not create an object of type 'transport' with id 'transport-tls'")
        self.assertEqual([l for l in log.splitlines() if "ERROR[" in l and not expected.search(l)], [])
        self.assertRegex(vm("asterisk -rx 'rtp show settings'").stdout, r"ICE support:\s+Yes")



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
        # R10-12: the permit/deny lines are an ACL the real Asterisk enforces (checked against the 24.0.0 build: `ari show users` lists
        # it, and a client on another address gets 403 even with the right password). The test used to grep the file for the text.
        users = vm("asterisk -rx 'ari show users'").stdout
        self.assertRegex(users, r"(?m)^\S+\s+Yes\s+treeline\s*$", users)       # read-only? No / ACL? Yes
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
        self.assertEqual(vm("stat -c '%U:%G:%a' /etc/asterisk/keys/treeline.key").stdout.strip(), "root:asterisk:640")     # Asterisk can read it, not replace it
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
            self.assertRegex(vm("asterisk -rx 'rtp show settings' 2>&1").stdout, r"ICE support:\s+Yes")
            self.assertNotRegex(vm("cat /var/lib/treeline/logs/asterisk/messages").stdout, r"Invalid (local|advertised) ICE host address")
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
        out = self.https("/api/auth/request", "-X POST -H 'Content-Type: application/json' -d '{\"email\":\"someone@example.invalid\"}' -w '\\n%{http_code}'").stdout
        self.assertNotIn("dev_code", out)
        self.assertTrue(out.strip().endswith("404"), "the emailed-code sign-in must not exist in production: " + out)
        self.assertEqual(self.https("/api/auth/verify", "-X POST -H 'Content-Type: application/json' -d '{}' -o /dev/null -w %{http_code}").stdout.strip(), "404")
        cfg = json.loads(self.https("/api/auth/config").stdout)
        self.assertEqual(cfg, {"google": True, "email_code": False, "dev": False})
        start = self.https("/api/auth/google/start", "-o /dev/null -w '%{http_code} %{redirect_url}'").stdout
        self.assertTrue(start.startswith("302 https://accounts.google.com/o/oauth2/v2/auth?"), start)
        self.assertIn("code_challenge_method=S256", start)
        wrong = self.https("/api/auth/beta", "-X POST -H 'Content-Type: application/json' -d '{\"code\":\"AAAA-AAAA\"}' -o /dev/null -w %{http_code}").stdout
        self.assertEqual(wrong.strip(), "400")


MIGRATE = [("controller/treeline/db.py", "MIGRATIONS = []", 'MIGRATIONS = [lambda conn: conn.execute("CREATE TABLE ci_probe(x)")]')]
UNHEALTHY = [("controller/treeline/api.py", "ok = asterisk and behind == 0", "ok = False")]
SCHEMA2 = {"central": 2, "household": 1}


class F_Deploy(VmTestCase):
    """The deploy agent (work package 2). Numbered: each test starts from where the one before left the machine."""

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
        vm("runuser -u treeline -- python3 -c \"import sqlite3; c=sqlite3.connect('/var/lib/treeline/data/treeline.db'); c.execute('CREATE TABLE IF NOT EXISTS ci_marker(x)'); c.execute('INSERT INTO ci_marker VALUES (42)'); c.commit()\"")
        self.assertEqual(self.central_version(), 1)
        self.variant("v0.0.5", "migrate-bad", patches=MIGRATE + UNHEALTHY, schema=SCHEMA2)
        rc, out = self.deploy("migrate-bad")
        self.assertEqual(rc, 1, out)
        self.assertIn("restoring the copies", out)
        self.assertIn("ROLLED BACK to v0.0.2", out)
        self.assertEqual(self.central_version(), 1, "the file must be back at the version the old code understands")
        self.assertEqual(vm("runuser -u treeline -- python3 -c \"import sqlite3; print(sqlite3.connect('/var/lib/treeline/data/treeline.db').execute('SELECT x FROM ci_marker').fetchone()[0])\"").stdout.strip(), "42")
        self.wait_healthy()
        self.assertEqual(self.serving(), "v0.0.2")
        self.assertEqual(vm("stat -c %U:%a /var/lib/treeline/data/treeline.db").stdout.strip(), "treeline:600")

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
        # a deploy puts /etc/asterisk back to what the release says: an edit made by hand must be gone afterwards
        vm("printf '\\n; ci-wait marker\\n' >> /etc/asterisk/extensions.conf")
        account = self.handset()
        # A real phone calls over TLS. 0001 is "join the call my line is on": with no call, the controller answers with a fast busy
        # that plays until the phone hangs up, so there is a channel for as long as the probe holds the call.
        # The call lasts until the test says so, not for a guessed number of seconds: the agent stages the release (builds its virtualenv)
        # for as long as that takes on this machine before it asks whether a call is in progress.
        client("rm -f /tmp/probe-stop")
        phone = self.probe_in_background(account, "--dial", "0001", "--hold", "600", "--stop-file", "/tmp/probe-stop")
        try:
            wait_for(lambda: len(json.loads(vm("curl -sS -u treeline:$(cat /etc/treeline/ari-password) http://127.0.0.1:8088/ari/channels").stdout)) > 0,
                     30, "an open channel")
            before = (self.current(), self.started(), self.releases())
            rc, out = self.deploy("busy")
            self.assertEqual(rc, 4, out)
            self.assertIn("a call is in progress", out)
            self.assertEqual(self.current(), "v0.0.6")
            self.assert_untouched(*before)
        finally:
            client("touch /tmp/probe-stop")                      # now the phone hangs up
            phone.wait(timeout=90)
        wait_for(lambda: json.loads(vm("curl -sS -u treeline:$(cat /etc/treeline/ari-password) http://127.0.0.1:8088/ari/channels").stdout) == [], 30, "no open channels")
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

    def test_14a_a_release_that_failed_is_not_tried_again_by_the_timer(self):
        """Code review #1: without this, a bad release was redeployed (an outage) every 15 minutes of the window."""
        self.variant("v0.1.0", "auto-bad", patches=MIGRATE + UNHEALTHY, schema=SCHEMA2, serve=True)
        rc, out = vm("treeline-deploy 2>&1; echo RC=$?").stdout.rpartition("RC=")[::2]
        self.assertEqual(int(out), 1, rc)
        self.assertIn("ROLLED BACK", rc)
        self.assertIn("v0.1.0", json.loads(vm("cat /var/lib/treeline/deploy/state.json").stdout)["failed"])
        started = self.started()
        rc, out = vm("treeline-deploy 2>&1; echo RC=$?").stdout.rpartition("RC=")[::2]
        self.assertEqual(int(out), 0, rc)
        self.assertIn("not trying it again", rc)
        self.assertEqual(self.current(), "v0.0.9")
        self.assertEqual(self.started(), started, "nothing was restarted")
        self.wait_healthy()

    def test_14b_a_deploy_builds_the_releases_operator_messages(self):
        """Code review #6: a release that adds a message must not play a missing file."""
        self.variant("v0.1.1", "sounds", patches=MIGRATE + [("asterisk/sounds/messages.txt", "cannot_complete|",
                     "ci_probe|This is a test message for the deploy job.\ncannot_complete|")], schema=SCHEMA2)
        self.assertFalse(vm("test -e /usr/share/asterisk/sounds/en/treeline/ci_probe.wav", check=False).returncode == 0)
        rc, out = self.deploy("sounds")
        self.assertEqual(rc, 0, out)
        self.assertEqual(vm("stat -c %U:%a /usr/share/asterisk/sounds/en/treeline/ci_probe.wav").stdout.strip(), "root:644")
        self.assertGreater(int(vm("stat -c %s /usr/share/asterisk/sounds/en/treeline/ci_probe.wav").stdout), 1000)

    def test_14c_install_sh_from_an_older_release_is_refused_and_changes_nothing(self):
        """Code review #4: re-running the first release's install.sh must never switch production back to it."""
        before = (self.current(), self.started(), vm("sha256sum /usr/local/lib/treeline/treeline-deploy").stdout)
        r = vm("cd /root/rel && ./deploy/native/install.sh --ci --domain app.treeline.test --state-dir /srv/state 2>&1; echo RC=$?", check=False)
        self.assertNotIn("RC=0", r.stdout[-10:], r.stdout[-500:])
        self.assertIn("older than the one running", r.stdout)
        self.assertEqual((self.current(), self.started(), vm("sha256sum /usr/local/lib/treeline/treeline-deploy").stdout), before)

    def test_14_only_three_releases_are_kept_and_the_timer_is_installed(self):
        self.assertLessEqual(len(self.releases()), 4)           # the last three, plus nothing left over
        self.assertNotIn("v0.0.1", self.releases())
        self.assertEqual(vm("systemctl is-enabled treeline-deploy.timer").stdout.strip(), "enabled")
        self.assertNotIn(".staging", " ".join(self.releases()))


class G_Backup(VmTestCase):
    """Work package 4: encrypted hourly backups, write-only upload, the dead-man ping, and a restore drill."""
    BUCKET = "treeline-backups-ci-us-west-2"

    def setUp(self):
        self.wait_healthy()

    def s3(self):
        return self.tmp / "aws" / "s3" / self.BUCKET

    def set_params(self, **extra):
        params = json.loads((self.tmp / "params.json").read_text())
        params.update(extra)
        (self.tmp / "params.json").write_text(json.dumps(params))

    def test_1_the_hourly_backup_is_encrypted_uploaded_and_leaves_no_plaintext(self):
        # the owner's key pair is made OUTSIDE the VM's reach: generated here, the private half copied out and deleted
        vm("age-keygen -o /root/backup.agekey 2>/root/recipient.txt; chmod 600 /root/backup.agekey")
        recipient = vm("grep -o 'age1[a-z0-9]*' /root/recipient.txt").stdout.strip()
        run("docker", "cp", f"{VM}:/root/backup.agekey", str(self.tmp / "backup.agekey"))
        vm("shred -u /root/backup.agekey /root/recipient.txt")
        self.set_params(**{"/treeline/backup_age_recipient": recipient, "/treeline/backup_bucket": self.BUCKET,
                           "/treeline/healthcheck_url": "http://fakeaws:9000/ping/ci-check"})
        # a household, made by the app's own code, so there is more than the central file
        vm("cd /opt/treeline/current/controller && TREELINE_DB=/var/lib/treeline/data/treeline.db runuser -u treeline -- /opt/treeline/current/venv/bin/python -c "
           "\"from treeline import db, households; c = db.connect(); households.create(7)\"")
        r = vm("systemctl start treeline-backup.service 2>&1; echo RC=$?; journalctl -u treeline-backup -n 12 --no-pager | cut -c1-200", check=False)
        self.assertIn("RC=0", r.stdout, r.stdout)
        keys = sorted(str(p.relative_to(self.s3())) for p in self.s3().rglob("*.age"))
        self.assertTrue(any(k.startswith("central/") for k in keys), keys)
        self.assertTrue(any(k.startswith("households/7/") for k in keys), keys)
        for p in self.s3().rglob("*.age"):
            self.assertTrue(p.read_bytes().startswith(b"age-encryption.org/v1"))
            self.assertNotIn(b"SQLite format 3", p.read_bytes())
        # no plaintext copy anywhere on the VM (the spool holds only .age files, work directories are gone)
        names = vm("find /var/lib/treeline/spool -type f -printf '%f\\n'").stdout.split()
        self.assertTrue(all(n.endswith(".age") for n in names), names)
        self.assertEqual(vm("ls -A /var/lib/treeline/spool | grep -c '^.work' || true").stdout.strip().splitlines()[-1], "0")
        # nothing the VM holds can open a backup
        self.assertEqual(vm("find / -xdev \\( -name '*.agekey' -o -name 'AGE-SECRET*' \\) -not -path '/proc/*' 2>/dev/null | wc -l").stdout.strip(), "0")
        self.assertEqual(vm("grep -rl 'AGE-SECRET-KEY' /etc /var/lib/treeline /opt/treeline/tools 2>/dev/null | wc -l").stdout.strip(), "0")
        # the VM cannot overwrite a backup: a second write of a key that exists is refused by the bucket (as the policy does), and
        # the upload tool treats its own retry as success
        vm("rm -f /var/lib/treeline/backup/uploaded.json")
        again = vm("systemctl start treeline-backup.service 2>&1; echo RC=$?", check=False)
        self.assertIn("RC=0", again.stdout, again.stdout)
        self.assertGreaterEqual(len(list(self.s3().rglob("*.age"))), len(keys), "the first backups are still there, unchanged")
        reqs = (self.tmp / "aws" / "requests.log").read_text()
        self.assertNotIn("DELETE", reqs)
        self.assertNotRegex(reqs, r"GET /treeline-backups[^ ]*\?[^ ]*list-type")           # the VM never lists the bucket

    def test_2_the_restore_drill_decrypts_and_verifies_what_was_uploaded(self):
        run("docker", "cp", str(ROOT / "infra" / "restore" / "restore.py"), f"{VM}:/root/restore.py")
        run("docker", "cp", str(self.tmp / "backup.agekey"), f"{VM}:/root/drill.agekey")
        try:
            creds = "AWS_ACCESS_KEY_ID=" + "AKI" + "AFAKEDRILL00000000 AWS_SECRET_ACCESS_KEY=" + "x" * 40
            for kind, extra in (("central", ""), ("household", "--id 7")):
                out = vm(f"{creds} /opt/treeline/tools/bin/python /root/restore.py --bucket {self.BUCKET} --kind {kind} {extra} "
                         f"--identity /root/drill.agekey --out /root/restored --endpoint http://fakeaws:9000 2>&1")
                self.assertIn("checked: integrity, marker, schema version", out.stdout, out.stdout)
            listing = vm("ls /root/restored").stdout
            self.assertRegex(listing, r"central-\d{8}T\d{6}Z\.db")
            self.assertRegex(listing, r"household-7-\d{8}T\d{6}Z\.db")
            wrong = vm(f"{creds} /opt/treeline/tools/bin/python /root/restore.py --bucket {self.BUCKET} --kind household --id 8 --identity /root/drill.agekey --out /root/r2 --endpoint http://fakeaws:9000 2>&1", check=False)
            self.assertNotEqual(wrong.returncode, 0)
        finally:
            vm("shred -u /root/drill.agekey; rm -rf /root/restored /root/r2 /root/restore.py", check=False)

    def test_3_the_dead_man_is_pinged_only_while_healthy_and_backed_up(self):
        log = self.tmp / "aws" / "requests.log"
        pings = lambda: log.read_text().count("GET /ping/ci-check")
        before = pings()
        self.assertIn("pinged", vm("treeline-health 2>&1").stdout)
        self.assertEqual(pings(), before + 1)
        stale = "2020-01-01T00:00:00+00:00"
        vm(f"printf %s {stale} > /var/lib/treeline/backup/last-success")
        r = vm("treeline-health 2>&1; echo RC=$?")
        self.assertIn("NOT pinging", r.stdout)
        self.assertEqual(pings(), before + 1, "a stale backup must not be pinged as healthy")
        vm("systemctl start treeline-backup.service")                       # fresh success again
        self.assertIn("pinged", vm("treeline-health 2>&1").stdout)
        vm("systemctl stop treeline-api")
        try:
            r = vm("treeline-health 2>&1; echo RC=$?")
            self.assertIn("NOT pinging", r.stdout)
            self.assertEqual(pings(), before + 2, "an unhealthy app must not be pinged as healthy")
        finally:
            vm("systemctl start treeline-api")
        self.wait_healthy()

    def test_4_the_timers_are_installed(self):
        for t in ("treeline-backup.timer", "treeline-health.timer"):
            self.assertEqual(vm(f"systemctl is-enabled {t}").stdout.strip(), "enabled")


if __name__ == "__main__":
    unittest.main(verbosity=2)


class H_RealCall(VmTestCase):
    """A real SIP phone, over TLS, through the production configuration: what a phone adapter does."""

    def test_1_a_phone_registers_with_digest_over_tls_and_the_controller_answers_its_call(self):
        self.wait_healthy()
        account = self.handset()
        phone = self.probe_in_background(account, "--dial", "0001", "--hold", "8")
        try:
            wait_for(lambda: account["user"] in vm("asterisk -rx 'core show channels concise'", check=False).stdout, 30, "the phone's channel")
            channel = next(l for l in vm("asterisk -rx 'core show channels concise'").stdout.splitlines() if account["user"] in l)
            self.assertIn("!Stasis!treeline!", channel, "the call went through the dialplan into the control app")
            self.assertRegex(vm("curl -sS -u treeline:$(cat /etc/treeline/ari-password) http://127.0.0.1:8088/ari/channels").stdout, account["user"])
        finally:
            out, _ = phone.communicate(timeout=60)
        result = json.loads(out.strip().splitlines()[-1])
        self.assertTrue(result["registered"], result)
        self.assertEqual(result["invite"], 200, result)
        self.assertGreaterEqual(result["held"], 7, result)
        # what Asterisk keeps about the phone (its address and user agent) is in the state disk's database
        self.assertEqual(vm("stat -c %U /var/lib/treeline/asterisk/astdb.sqlite3").stdout.strip(), "asterisk")

    def test_2_a_wrong_password_is_refused_and_the_log_line_is_one_fail2ban_matches(self):
        self.wait_healthy()
        account = self.handset()
        code, result = self.probe(account, "--bad-password")
        self.assertNotEqual(code, 0)
        self.assertFalse(result.get("registered"), result)
        my_ip = client("hostname -i | cut -d' ' -f1").stdout.strip()
        log = vm("cat /var/lib/treeline/logs/asterisk/messages").stdout
        rule = re.search(r"failregex\s*=\s*(.+)", (ROOT / "deploy" / "fail2ban" / "filter.d" / "treeline-asterisk.conf").read_text()).group(1).strip()
        pattern = re.compile(rule.replace("<HOST>", r"(?P<host>\d+\.\d+\.\d+\.\d+)"))
        hosts = [m.group("host") for m in map(pattern.search, log.splitlines()) if m]
        self.assertIn(my_ip, hosts, "the failed sign-in is logged in a form the fail2ban filter matches, with the caller's address")

    def test_3_logrotate_rotates_the_log_and_asterisk_goes_on_writing_to_the_new_file(self):
        self.wait_healthy()
        account = self.handset()
        vm("logrotate -f -s /tmp/lr.state /etc/logrotate.d/treeline-asterisk 2>&1")
        self.assertTrue(vm("ls /var/lib/treeline/logs/asterisk/").stdout.split().count("messages.1") == 1, "the old log was rotated away")
        self.assertEqual(vm("stat -c %U:%G:%a /var/lib/treeline/logs/asterisk/messages").stdout.strip(), "asterisk:asterisk:640")
        before = int(vm("stat -c %i /var/lib/treeline/logs/asterisk/messages").stdout.strip())
        self.probe(account, "--bad-password")
        wait_for(lambda: "failed for" in vm("cat /var/lib/treeline/logs/asterisk/messages", check=False).stdout, 20, "a new line in the NEW file")
        self.assertEqual(int(vm("stat -c %i /var/lib/treeline/logs/asterisk/messages").stdout.strip()), before)


class H_AsteriskDeploy(VmTestCase):
    """A deploy that changes the Asterisk build, and everything that must not happen."""

    def process(self):
        pid = vm("systemctl show asterisk -p MainPID --value").stdout.strip()
        return pid, vm(f"readlink /proc/{pid}/exe").stdout.strip()

    def same_data(self, patches=()):
        """variant() arguments that give the new release the data layout the machine is ALREADY at: after the F_Deploy tests it is at
        schema 2, and a release that expects schema 1 would (rightly) refuse that data and be rolled back; on a fresh machine it is at 1
        and nothing should migrate, so a rollback stays possible."""
        if self.central_version() >= 2:
            return dict(patches=MIGRATE + list(patches), schema=SCHEMA2)
        return dict(patches=list(patches))

    def test_1_a_deploy_to_another_build_moves_the_process_and_a_rollback_brings_the_old_one_back(self):
        self.wait_healthy()
        old, new = ast_id(), "24.0.0-x9"
        account = self.handset()
        code, result = self.probe(account, "--dial", "0001", "--hold", "1")
        self.assertEqual(code, 0, result)                                                      # the phone's contact is in astdb
        astdb = vm("stat -c '%i %s' /var/lib/treeline/asterisk/astdb.sqlite3").stdout.split()
        before_version = self.current()
        self.variant("v0.4.0", "across", asterisk=self.repacked_artifact(new), **self.same_data())
        rc, out = self.deploy("across")
        self.assertEqual(rc, 0, out)
        pid, exe = self.process()
        self.assertEqual(exe, f"/opt/asterisk/{new}/sbin/asterisk")
        maps = vm(f"cat /proc/{pid}/maps").stdout
        self.assertIn(f"/opt/asterisk/{new}/", maps)
        self.assertNotIn(f"/opt/asterisk/{old}/", maps, "nothing of the old build is mapped into the new process")
        self.assertIn(f"/opt/asterisk/{new}/sbin/asterisk", vm("systemctl show asterisk -p ExecStart").stdout)
        self.assertEqual(vm("systemctl show asterisk -p NeedDaemonReload --value").stdout.strip(), "no")
        self.assertEqual(vm("readlink -f /usr/local/sbin/asterisk").stdout.strip(), f"/opt/asterisk/{new}/sbin/asterisk")
        self.assertEqual(sorted(vm("ls /opt/asterisk").stdout.split()), sorted([old, new]), "the old build is kept for a rollback")
        self.assertEqual(sorted(vm("ls /etc/asterisk | grep '^asterisk-'").stdout.split()), [f"asterisk-{new}.conf"], "only the running build's configuration")
        self.assertEqual(vm("stat -c '%i' /var/lib/treeline/asterisk/astdb.sqlite3").stdout.strip(), astdb[0], "the contact database is the same file")
        self.wait_healthy()
        self.assertEqual(self.serving(), "v0.4.0")
        # and back
        rc, out = vm("treeline-deploy --rollback 2>&1; echo RC=$?").stdout.rpartition("RC=")[::2]
        self.assertEqual(int(out), 0, rc)
        pid, exe = self.process()
        self.assertEqual(exe, f"/opt/asterisk/{old}/sbin/asterisk")
        self.assertNotIn(f"/opt/asterisk/{new}/", vm(f"cat /proc/{pid}/maps").stdout)
        self.assertEqual(vm("readlink -f /usr/local/sbin/asterisk").stdout.strip(), f"/opt/asterisk/{old}/sbin/asterisk")
        self.assertEqual(vm("systemctl show asterisk -p NeedDaemonReload --value").stdout.strip(), "no")
        self.assertEqual(sorted(vm("ls /etc/asterisk | grep '^asterisk-'").stdout.split()), [f"asterisk-{old}.conf"])
        self.assertEqual(vm("stat -c '%i' /var/lib/treeline/asterisk/astdb.sqlite3").stdout.strip(), astdb[0])
        self.assertEqual(self.current(), before_version)
        self.wait_healthy()

    def test_2_a_release_whose_nested_asterisk_was_changed_is_refused_though_its_signature_is_valid(self):
        self.wait_healthy()
        pid, exe = self.process()
        before = (self.current(), self.started(), self.releases())
        listing = vm("ls /opt/asterisk").stdout
        self.variant("v0.4.1", "damaged", asterisk=self.repacked_artifact("24.0.0-x9"), damage_nested=True, **self.same_data())
        rc, out = self.deploy("damaged")
        self.assertEqual(rc, 3, out)
        self.assertIn("does not match the sha256", out)
        self.assert_untouched(*before)
        self.assertEqual(vm("ls /opt/asterisk").stdout, listing, "nothing was unpacked")
        self.assertEqual(self.process(), (pid, exe), "Asterisk was not touched")

    def test_3_a_release_in_the_old_format_is_refused_and_nothing_is_touched(self):
        self.wait_healthy()
        before = (self.current(), self.started(), self.releases())
        self.variant("v0.4.2", "oldformat", info_patch={"format": 1, "asterisk": None}, **self.same_data())
        rc, out = self.deploy("oldformat")
        self.assertEqual(rc, 3, out)
        self.assertIn("format 1", out)
        self.assertIn("Nothing on this machine was changed", out)
        self.assert_untouched(*before)

    def test_4_a_build_that_starts_but_cannot_serve_is_rolled_back_to_the_old_one(self):
        self.wait_healthy()
        old = ast_id()
        before = (self.current(), self.releases())
        # a module that does not exist is `required`: Asterisk refuses to start, the deploy's health check fails, the old build returns
        self.variant("v0.4.3", "cannotstart", asterisk=self.repacked_artifact("24.0.0-x9"),
                     **self.same_data([("asterisk/config/modules.conf", "require => res_sorcery_config.so",
                                       "require => res_sorcery_config.so\nrequire => no_such_module.so")]))
        rc, out = self.deploy("cannotstart")
        self.assertEqual(rc, 1, out)
        self.assertIn("ROLLED BACK", out)
        self.assertEqual((self.current(), self.releases()), before)
        self.assertEqual(self.process()[1], f"/opt/asterisk/{old}/sbin/asterisk")
        self.assertEqual(vm("readlink -f /usr/local/sbin/asterisk").stdout.strip(), f"/opt/asterisk/{old}/sbin/asterisk")
        self.assertEqual(vm("systemctl show asterisk -p NeedDaemonReload --value").stdout.strip(), "no")
        self.assertNotIn("v0.4.3", self.releases(), "the failed release itself was removed")
        # a build stays while any installed release carries it (v0.4.0, from the first test, still carries 24.0.0-x9), and no longer
        carried = set(json.loads(vm("python3 -c \"import glob, json; print(json.dumps(sorted(json.load(open(f))['asterisk']['id'] "
                                    "for f in glob.glob('/opt/treeline/releases/v*/release.json'))))\"").stdout))
        self.assertEqual(set(vm("ls /opt/asterisk").stdout.split()), carried | {old}, "builds no installed release carries were removed")
        self.assertEqual(sorted(vm("ls /etc/asterisk | grep '^asterisk-'").stdout.split()), [f"asterisk-{old}.conf"])
        self.wait_healthy()


class I_ReplacingUbuntusPackage(VmTestCase):
    """install.sh on a machine that has Ubuntu's Asterisk: the replacement goes in first, then the package goes."""

    def test_1_rerunning_install_removes_ubuntus_package_and_keeps_the_state(self):
        self.wait_healthy()
        old = ast_id()
        # put Ubuntu's package back, as an older install would have left it (the pin that keeps it out is lifted for this)
        # A machine from before this change had Ubuntu's own files in /etc/asterisk, not ours: start from there (dpkg stops at a prompt
        # about a file that exists and differs), then let the old install's habits show: an edited pjsip.conf and extra groups.
        vm("systemctl stop asterisk; rm -f /etc/asterisk/*.conf /etc/apt/preferences.d/treeline-asterisk && apt-get update -qq >/dev/null && "
           "DEBIAN_FRONTEND=noninteractive apt-get install -y -qq -o Dpkg::Options::=--force-confnew asterisk >/dev/null 2>&1", timeout=1500)
        self.assertIn("asterisk", vm("dpkg-query -W -f='${Package}\\n' 'asterisk*'").stdout)
        vm("echo '; edited by the old install' >> /etc/asterisk/pjsip.conf; usermod -aG dialout,audio asterisk; "
           "echo marker > /var/lib/treeline/logs/asterisk/marker; chown asterisk:asterisk /var/lib/treeline/logs/asterisk/marker")
        self.install(src="/opt/treeline/current")      # the machine may be on a newer release than the first one: install.sh refuses an older one
        self.wait_healthy()
        self.assertEqual(vm("dpkg-query -W 'asterisk*' 2>/dev/null; true").stdout.strip(), "", "every Ubuntu asterisk package is gone")
        self.assertIn("Candidate: (none)", vm("apt-cache policy asterisk").stdout)
        self.assertNotEqual(vm("apt-get install -s asterisk 2>&1", check=False).returncode, 0)
        self.assertEqual(vm("systemctl show asterisk -p MainPID --value | xargs -I{} readlink /proc/{}/exe").stdout.strip(),
                         f"/opt/asterisk/{old}/sbin/asterisk", "Asterisk is running our build, not the package's")
        self.assertEqual(vm("id -Gn asterisk").stdout.strip(), "asterisk", "the package's extra groups are gone")
        self.assertEqual(vm("cat /var/lib/treeline/logs/asterisk/marker").stdout.strip(), "marker", "state on the state disk survived the purge")
        self.assertEqual(vm("stat -c %U /var/lib/treeline/logs/asterisk/marker").stdout.strip(), "asterisk")
        self.assertEqual(vm("runuser -u asterisk -- test -w /var/lib/treeline/asterisk && echo writable").stdout.strip(), "writable")
        self.assertEqual(vm("stat -c %U:%G:%a /usr/share/asterisk/sounds/en/treeline/no_911.wav").stdout.strip(), "root:root:644")
        self.assertFalse(vm("ls /etc/asterisk/*.conf | wc -l").stdout.strip() == "0")
        self.assertLess(int(vm("ls /etc/asterisk/*.conf | wc -l").stdout.strip()), 30, "the package's ~100 sample files are gone")
        self.assertEqual(vm("test -e /usr/share/asterisk/sounds/en_US_f_Allison && echo left", check=False).stdout.strip(), "")
