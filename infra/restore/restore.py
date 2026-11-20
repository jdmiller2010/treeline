#!/usr/bin/env python3
"""Restore (or drill a restore of) a Treeline backup. Run it on YOUR computer, not on the VM: the VM cannot read the bucket,
and only you hold the age private key.

    python3 infra/restore/restore.py --bucket NAME --kind central --identity ~/treeline-backup.agekey --out ./restore
    python3 infra/restore/restore.py --bucket NAME --kind household --id 7 --at 20260110T120000Z ...

It lists the newest backup (or the one at --at) under central/ or households/<id>/, downloads it, decrypts it with your
private key, and CHECKS it: SQLite's integrity check, the file's marker (central or household), its schema version, and for a
household that its own `meta` says it is that household. The result is written to <out>/<kind>[-<id>]-<stamp>.db (mode 0600)
and is never put over a live file: to restore for real, stop the services, put it in place yourself (docs/DEPLOY_AWS.md,
"Restore drill"), and start them. Needs: boto3 (pip install boto3), the `age` command, and AWS credentials that may read the
bucket (your admin profile: AWS_PROFILE=...). --endpoint is for tests against a fake S3.
"""

import argparse
import os
import re
import sqlite3
import subprocess
import sys

CENTRAL_APP_ID = 0x54524C43          # controller/treeline/db.py
HOUSEHOLD_APP_ID = 0x54524C48
NAME = re.compile(r"(\d{8}T\d{6}Z)\.db\.age$")


def list_keys(s3, bucket, prefix):
    keys, token = [], None
    while True:
        kw = {"Bucket": bucket, "Prefix": prefix}
        if token:
            kw["ContinuationToken"] = token
        page = s3.list_objects_v2(**kw)
        keys += [o["Key"] for o in page.get("Contents", [])]
        if not page.get("IsTruncated"):
            return keys
        token = page["NextContinuationToken"]


def pick(keys, at=None):
    named = sorted((m.group(1), k) for k in keys for m in [NAME.search(k)] if m)
    if not named:
        raise SystemExit("no backups found under that prefix")
    if at:
        for stamp, key in named:
            if stamp == at:
                return key
        raise SystemExit(f"no backup at {at}; the available ones are: " + ", ".join(s for s, _ in named[-8:]))
    return named[-1][1]


def decrypt(blob, identity):
    done = subprocess.run(["age", "-d", "-i", identity], input=blob, capture_output=True)
    if done.returncode != 0:
        raise SystemExit("age could not decrypt it with that identity: " + done.stderr.decode()[-200:])
    return done.stdout


def verify(path, kind, hid=None):
    """Raise SystemExit unless the file is a sound database of the right kind. Returns a summary."""
    c = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        try:
            ok = c.execute("PRAGMA integrity_check").fetchone()[0]
        except sqlite3.DatabaseError as err:
            raise SystemExit(f"not a readable SQLite database: {err}") from err
        if ok != "ok":
            raise SystemExit(f"integrity check failed: {ok}")
        app_id = c.execute("PRAGMA application_id").fetchone()[0]
        version = c.execute("PRAGMA user_version").fetchone()[0]
        want = CENTRAL_APP_ID if kind == "central" else HOUSEHOLD_APP_ID
        if app_id != want:
            raise SystemExit(f"this is not a {kind} database (marker {app_id:#x})")
        if version < 1:
            raise SystemExit("the schema version is missing")
        tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        counts = {t: c.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in tables}
        if kind == "household":
            row = c.execute("SELECT treehouse_id FROM meta WHERE id=1").fetchone()
            if row is None or row[0] != hid:
                raise SystemExit(f"this file says it belongs to treehouse {row[0] if row else '(none)'}, not {hid}")
        return {"schema_version": version, "tables": counts}
    finally:
        c.close()


def restore(s3, bucket, kind, hid, at, identity, out):
    prefix = "central/" if kind == "central" else f"households/{int(hid)}/"
    key = pick(list_keys(s3, bucket, prefix), at)
    stamp = NAME.search(key).group(1)
    plain = decrypt(s3.get_object(Bucket=bucket, Key=key)["Body"].read(), identity)
    os.makedirs(out, mode=0o700, exist_ok=True)
    dest = os.path.join(out, f"{kind}{'-' + str(int(hid)) if kind == 'household' else ''}-{stamp}.db")
    if os.path.exists(dest):
        raise SystemExit(f"{dest} already exists; not overwriting")
    fd = os.open(dest, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(plain)
    try:
        summary = verify(dest, kind, int(hid) if hid is not None else None)
    except BaseException:
        os.remove(dest)                        # never leave a file that did not verify looking like a good backup
        raise
    return dest, key, summary


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--bucket", required=True)
    ap.add_argument("--kind", choices=("central", "household"), required=True)
    ap.add_argument("--id", type=int)
    ap.add_argument("--at", help="a timestamp such as 20260110T120000Z (default: the newest)")
    ap.add_argument("--identity", required=True, help="your age private key file")
    ap.add_argument("--out", required=True)
    ap.add_argument("--endpoint")
    ap.add_argument("--region", default="us-west-2")
    a = ap.parse_args(argv)
    if a.kind == "household" and a.id is None:
        ap.error("--id is required for a household")
    import boto3
    s3 = boto3.client("s3", region_name=a.region, **({"endpoint_url": a.endpoint} if a.endpoint else {}))
    dest, key, summary = restore(s3, a.bucket, a.kind, a.id, a.at, a.identity, a.out)
    print(f"restored s3://{a.bucket}/{key}\n  -> {dest}  (schema version {summary['schema_version']})")
    for table, n in summary["tables"].items():
        print(f"     {table}: {n} row(s)")
    print("checked: integrity, marker, schema version" + (", household id" if a.kind == "household" else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
