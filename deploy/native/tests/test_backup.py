"""Backups: every database file is copied with SQLite's online backup, encrypted with age to a PUBLIC key, uploaded write-only,
and the monitor is only pinged when the app is healthy and backups are arriving. Needs the `age` binary (apt install age)."""

import datetime as dt
import http.server
import json
import os
import pathlib
import shutil
import sqlite3
import subprocess
import tempfile
import threading
import unittest

import helpers

backup = helpers.load("treeline-backup")
health = helpers.load("treeline-health")
import treeline_common as common  # noqa: E402

AGE = shutil.which("age") and shutil.which("age-keygen")
sys_path_controller = str(helpers.ROOT / "controller")


def identity(directory):
    key = pathlib.Path(directory) / "backup.agekey"
    done = subprocess.run(["age-keygen", "-o", str(key)], capture_output=True, text=True, check=True)
    recipient = [w for w in (done.stderr + done.stdout).split() if w.startswith("age1")][0]
    return key, recipient


def make_db(path, rows, marker_table="t"):
    path.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(path)
    c.execute(f"CREATE TABLE {marker_table}(x)")
    c.executemany(f"INSERT INTO {marker_table} VALUES (?)", [(r,) for r in rows])
    c.commit()
    c.close()


class ClientError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.response = {"Error": {"Code": code}}


class FakeS3:
    """Behaves like the bucket policy: a write must say IfNoneMatch="*", and a key that exists is not overwritten."""

    def __init__(self, fail_on=None):
        self.objects, self.fail_on, self.calls = {}, fail_on, []

    def put_object(self, **kw):
        self.calls.append(kw)
        if self.fail_on and self.fail_on in kw["Key"]:
            raise OSError("connection reset")
        if kw.get("IfNoneMatch") != "*":
            raise ClientError("AccessDenied")
        if kw["Key"] in self.objects:
            raise ClientError("PreconditionFailed")
        self.objects[kw["Key"]] = kw["Body"]


@unittest.skipUnless(AGE, "age is not installed (apt install age); the VM job runs these against the real binary")
class Backups(unittest.TestCase):
    def setUp(self):
        self.d = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.d, True)
        self.state = self.d / "state"
        (self.state / "spool").mkdir(parents=True)
        real = common.STATE
        common.STATE = str(self.state)
        self.addCleanup(setattr, common, "STATE", real)
        make_db(self.state / "treeline.db", ["central-row"])
        make_db(self.state / "households" / "3.db", ["household-three"])
        make_db(self.state / "households" / "12.db", ["household-twelve"])
        self.key, self.recipient = identity(self.d)
        import sys
        if sys_path_controller not in sys.path:
            sys.path.insert(0, sys_path_controller)
        import backup as backup_module
        self.module = backup_module
        self.now = dt.datetime(2026, 1, 10, 12, 0, 0, tzinfo=dt.timezone.utc)

    def make(self, recipient=None, now=None):
        return backup.make(self.recipient if recipient is None else recipient, now=now or self.now, db=str(self.state / "treeline.db"),
                           households=str(self.state / "households"), backup_module=self.module)

    def decrypt(self, path):
        out = self.d / "plain.db"
        subprocess.run(["age", "-d", "-i", str(self.key), "-o", str(out), str(path)], check=True, capture_output=True)
        return out

    def test_every_file_is_spooled_encrypted_in_the_layout_the_bucket_uses_and_no_plaintext_is_left(self):
        files, failure = self.make()
        self.assertIsNone(failure)
        rel = sorted(os.path.relpath(f, self.state / "spool") for f in files)
        self.assertEqual(rel, ["central/20260110T120000Z.db.age", "households/12/20260110T120000Z.db.age", "households/3/20260110T120000Z.db.age"])
        for folder, _, names in os.walk(self.state / "spool"):
            for n in names:
                self.assertTrue(n.endswith(".age"), f"{n}: a plaintext or half-written file is in the spool")
        self.assertEqual([p for p in os.listdir(self.state / "spool") if p.startswith(".work")], [])
        for f in files:
            self.assertEqual(oct(os.stat(f).st_mode & 0o777), "0o600")
            self.assertTrue(open(f, "rb").read().startswith(b"age-encryption.org/v1"))

    def test_the_owner_can_decrypt_and_the_copy_is_a_working_database(self):
        files, _ = self.make()
        central = [f for f in files if "central" in f][0]
        plain = self.decrypt(central)
        c = sqlite3.connect(plain)
        self.assertEqual(c.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        self.assertEqual(c.execute("SELECT x FROM t").fetchone()[0], "central-row")

    def test_the_vm_itself_cannot_decrypt_what_it_wrote(self):
        """age encrypts to a public key: nothing on the VM can open a backup. A different identity must fail."""
        files, _ = self.make()
        other = self.d / "other.agekey"
        subprocess.run(["age-keygen", "-o", str(other)], check=True, capture_output=True)
        done = subprocess.run(["age", "-d", "-i", str(other), "-o", str(self.d / "x"), files[0]], capture_output=True)
        self.assertNotEqual(done.returncode, 0)

    def test_it_refuses_to_back_up_without_a_proper_public_key(self):
        for bad in ("", "AGE-SECRET-KEY-1ABC", "not-a-key", "age1short"):
            with self.assertRaises(SystemExit):
                self.make(recipient=bad)
        self.assertEqual([p for p in (self.state / "spool").rglob("*") if p.is_file()], [], "nothing may be written when the key is wrong")

    def test_a_household_deleted_while_backing_up_is_skipped_and_one_unreadable_file_still_lets_the_rest_through(self):
        (self.state / "households" / "12.db").write_bytes(b"this is not a database")
        files, failure = self.make()
        self.assertIn("12", failure or "")
        self.assertTrue(any("central" in f for f in files) and any("/3/" in f for f in files))

    def test_upload_sends_only_encrypted_files_once_and_records_success(self):
        self.make()
        s3 = FakeS3()
        n = backup.upload(s3, "treeline-backups-123456789012-us-west-2", now=self.now)
        self.assertEqual(n, 3)
        self.assertEqual(sorted(s3.objects), ["central/20260110T120000Z.db.age", "households/12/20260110T120000Z.db.age", "households/3/20260110T120000Z.db.age"])
        self.assertTrue(all(c["ServerSideEncryption"] == "AES256" and c["Bucket"].startswith("treeline-backups-") for c in s3.calls))
        self.assertTrue(all(b.startswith(b"age-encryption.org/v1") for b in s3.objects.values()))
        self.assertTrue((self.state / "spool" / "last-success").exists())
        before = len(s3.calls)
        backup.upload(s3, "treeline-backups-123456789012-us-west-2", now=self.now)
        self.assertEqual(len(s3.calls), before, "files already uploaded must not be sent again")

    def test_every_write_says_if_none_match_and_an_existing_backup_is_never_overwritten(self):
        self.make()
        s3 = FakeS3()
        backup.upload(s3, "b", now=self.now)
        self.assertTrue(all(c["IfNoneMatch"] == "*" for c in s3.calls))
        original = dict(s3.objects)
        # the same files sent again (the record of uploads was lost): the bucket says "exists", which is success, and nothing changes
        (self.state / "spool" / "uploaded.json").unlink()
        self.assertEqual(backup.upload(s3, "b", now=self.now), 3)
        self.assertEqual(s3.objects, original)
        # a different object under a key that exists is refused by the bucket, and the tool does not pretend otherwise
        with self.assertRaises(ClientError):
            s3.put_object(Bucket="b", Key="central/20260110T120000Z.db.age", Body=b"age-encryption.org/v1 other")

    def test_an_access_denied_from_the_policy_is_a_failure_not_a_success(self):
        self.make()
        class Denying(FakeS3):
            def put_object(self, **kw):
                raise ClientError("AccessDenied")
        with self.assertRaises(ClientError):
            backup.upload(Denying(), "b", now=self.now)
        self.assertFalse((self.state / "spool" / "last-success").exists())

    def test_a_failed_upload_is_not_recorded_as_success_and_is_retried(self):
        self.make()
        s3 = FakeS3(fail_on="households/12")
        with self.assertRaises(OSError):
            backup.upload(s3, "b", now=self.now)
        self.assertFalse((self.state / "spool" / "last-success").exists(), "the dead-man must not see a success that did not happen")
        s3.fail_on = None
        backup.upload(s3, "b", now=self.now)
        self.assertEqual(len(s3.objects), 3)
        self.assertTrue((self.state / "spool" / "last-success").exists())

    def test_a_file_that_is_not_age_output_is_never_uploaded(self):
        folder = self.state / "spool" / "central"
        folder.mkdir()
        (folder / "20260110T120000Z.db.age").write_bytes(b"SQLite format 3\0 plaintext!")
        s3 = FakeS3()
        with self.assertRaises(SystemExit):
            backup.upload(s3, "b", now=self.now)
        self.assertEqual(s3.objects, {})

    def test_the_spool_is_pruned_at_seven_days_by_the_name_and_empty_household_folders_go(self):
        self.make(now=self.now - dt.timedelta(days=9))
        s3 = FakeS3()
        backup.upload(s3, "b", now=self.now - dt.timedelta(days=9))
        self.make(now=self.now)
        backup.upload(s3, "b", now=self.now)
        left = sorted(os.path.relpath(os.path.join(d, n), self.state / "spool") for d, _, ns in os.walk(self.state / "spool") for n in ns if n.endswith(".age"))
        self.assertEqual(left, ["central/20260110T120000Z.db.age", "households/12/20260110T120000Z.db.age", "households/3/20260110T120000Z.db.age"])
        self.assertNotIn("central/20260101T120000Z.db.age", json.load(open(self.state / "spool" / "uploaded.json")))


@unittest.skipUnless(AGE, "age is not installed")
class Restore(unittest.TestCase):
    """infra/restore/restore.py against a fake bucket: it finds the newest, decrypts, and verifies; it refuses what is wrong."""

    def setUp(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("restore", helpers.ROOT / "infra" / "restore" / "restore.py")
        self.restore = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.restore)
        self.d = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.d, True)
        self.key, self.recipient = identity(self.d)

    def bucket(self, objects):
        class S3:
            def list_objects_v2(self_, Bucket, Prefix, ContinuationToken=None):
                return {"Contents": [{"Key": k} for k in sorted(objects) if k.startswith(Prefix)], "IsTruncated": False}

            def get_object(self_, Bucket, Key):
                import io
                return {"Body": io.BytesIO(objects[Key])}
        return S3()

    def sealed(self, db_path):
        done = subprocess.run(["age", "-r", self.recipient], input=pathlib.Path(db_path).read_bytes(), capture_output=True, check=True)
        return done.stdout

    def central(self, name="c.db", version=1, app_id=0x54524C43):
        p = self.d / name
        c = sqlite3.connect(p)
        c.execute("CREATE TABLE treehouse(id)")
        c.execute("INSERT INTO treehouse VALUES (1)")
        c.execute(f"PRAGMA application_id={app_id}")
        c.execute(f"PRAGMA user_version={version}")
        c.commit()
        c.close()
        return p

    def household(self, tid, name="h.db"):
        p = self.d / name
        c = sqlite3.connect(p)
        c.execute("CREATE TABLE meta(id INTEGER PRIMARY KEY, treehouse_id INTEGER)")
        c.execute("INSERT INTO meta VALUES (1, ?)", (tid,))
        c.execute(f"PRAGMA application_id={0x54524C48}")
        c.execute("PRAGMA user_version=1")
        c.commit()
        c.close()
        return p

    def test_it_restores_the_newest_central_backup_and_checks_it(self):
        s3 = self.bucket({"central/20260101T000000Z.db.age": b"old", "central/20260102T000000Z.db.age": self.sealed(self.central())})
        dest, key, summary = self.restore.restore(s3, "b", "central", None, None, str(self.key), str(self.d / "out"))
        self.assertTrue(key.endswith("20260102T000000Z.db.age"))
        self.assertEqual(summary["tables"], {"treehouse": 1})
        self.assertEqual(oct(os.stat(dest).st_mode & 0o777), "0o600")

    def test_a_household_backup_must_belong_to_the_household_asked_for(self):
        s3 = self.bucket({"households/7/20260102T000000Z.db.age": self.sealed(self.household(8))})
        with self.assertRaises(SystemExit) as caught:
            self.restore.restore(s3, "b", "household", 7, None, str(self.key), str(self.d / "out"))
        self.assertIn("belongs to treehouse 8", str(caught.exception))
        self.assertEqual(os.listdir(self.d / "out"), [], "a file that did not verify must not be left behind")

    def test_the_wrong_kind_a_damaged_file_and_the_wrong_key_are_refused(self):
        wrong_kind = self.bucket({"central/20260102T000000Z.db.age": self.sealed(self.household(7))})
        with self.assertRaises(SystemExit):
            self.restore.restore(wrong_kind, "b", "central", None, None, str(self.key), str(self.d / "o1"))
        good = self.sealed(self.central())
        other = self.d / "other.agekey"
        subprocess.run(["age-keygen", "-o", str(other)], check=True, capture_output=True)
        with self.assertRaises(SystemExit):
            self.restore.restore(self.bucket({"central/20260102T000000Z.db.age": good}), "b", "central", None, None, str(other), str(self.d / "o2"))
        damaged = pathlib.Path(self.d / "damaged.db")
        damaged.write_bytes(self.central("d.db").read_bytes()[:900] + b"\0" * 200)
        with self.assertRaises(SystemExit):
            self.restore.restore(self.bucket({"central/20260102T000000Z.db.age": self.sealed(damaged)}), "b", "central", None, None, str(self.key), str(self.d / "o3"))

    def test_a_chosen_time_is_found_and_a_missing_one_lists_what_exists_and_nothing_is_overwritten(self):
        blob = self.sealed(self.central())
        s3 = self.bucket({"central/20260101T000000Z.db.age": blob, "central/20260102T000000Z.db.age": blob})
        dest, key, _ = self.restore.restore(s3, "b", "central", None, "20260101T000000Z", str(self.key), str(self.d / "out"))
        self.assertTrue(key.endswith("20260101T000000Z.db.age"))
        with self.assertRaises(SystemExit) as caught:
            self.restore.restore(s3, "b", "central", None, "20250101T000000Z", str(self.key), str(self.d / "out"))
        self.assertIn("20260102T000000Z", str(caught.exception))
        with self.assertRaises(SystemExit):
            self.restore.restore(s3, "b", "central", None, "20260101T000000Z", str(self.key), str(self.d / "out"))      # already there


class DeadManPing(unittest.TestCase):
    def setUp(self):
        self.d = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.d, True)
        self.now = dt.datetime(2026, 1, 10, 12, 0, tzinfo=dt.timezone.utc)

    def server(self, status, body):
        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(status)
                self.end_headers()
                self.wfile.write(json.dumps(body).encode())

            def log_message(self, *a):
                pass
        srv = http.server.HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.shutdown)
        return f"http://127.0.0.1:{srv.server_port}/api/health"

    def test_the_age_of_the_last_backup_comes_from_the_success_file_else_from_the_install(self):
        (self.d / "last-success").write_text((self.now - dt.timedelta(hours=2)).isoformat())
        self.assertEqual(health.backup_age(self.now, str(self.d), str(self.d / "nope")), dt.timedelta(hours=2))
        (self.d / "last-success").unlink()
        host = self.d / "host.env"
        host.write_text("x")
        os.utime(host, ((self.now - dt.timedelta(minutes=30)).timestamp(),) * 2)
        self.assertEqual(health.backup_age(self.now, str(self.d), str(host)), dt.timedelta(minutes=30))
        self.assertEqual(health.backup_age(self.now, str(self.d), str(self.d / "missing")), dt.timedelta.max)

    def test_it_pings_only_when_the_app_is_healthy_and_a_backup_is_recent(self):
        (self.d / "last-success").write_text(dt.datetime.now(dt.timezone.utc).isoformat())
        real_health, real_common_state = health.HEALTH, common.STATE
        try:
            common.STATE = str(self.d.parent)
            os.makedirs(self.d.parent / "spool", exist_ok=True)
            shutil.copy(self.d / "last-success", self.d.parent / "spool" / "last-success")
            health.HEALTH = self.server(200, {"ok": True})
            self.assertIsNone(health.check())
            health.HEALTH = self.server(503, {"ok": False})
            self.assertIn("says", health.check())
            health.HEALTH = "http://127.0.0.1:9/api/health"
            self.assertIn("unreachable", health.check())
            health.HEALTH = self.server(200, {"ok": True})
            (self.d.parent / "spool" / "last-success").write_text((dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=4)).isoformat())
            self.assertIn("last backup", health.check())
        finally:
            health.HEALTH, common.STATE = real_health, real_common_state
            shutil.rmtree(self.d.parent / "spool", ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
