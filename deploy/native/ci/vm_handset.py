#!/usr/bin/env python3
"""CI only. Run inside the VM-imitating container as the `treeline` user, with the release's own interpreter:

    runuser -u treeline -- /opt/treeline/current/venv/bin/python -I /ci/vm_handset.py

Makes one family with one phone-adapter handset in the machine's real database and writes that handset's account for Asterisk,
the way the API does when a parent adds a phone (the digest of the secret goes to Asterisk, never the secret). Prints the account
as one JSON line. The caller asks Asterisk to reload (an ARI call): that call is part of what the test checks.
"""

import json
import os
import sys

sys.path.insert(0, "/opt/treeline/current/controller")
os.environ.setdefault("TREELINE_DB", "/var/lib/treeline/data/treeline.db")

from treeline import db, households, pjsip  # noqa: E402

conn = db.local_conn()
treehouse = db.create_treehouse(conn, "CI house", number=None, timezone="America/Los_Angeles", quiet_enabled=0)
households.create(treehouse)
handset_id, sip_user, secret = db.create_handset(conn, treehouse, "ata", "Hall")
pjsip.write(conn, path=os.environ.get("TREELINE_PJSIP_FILE", "/var/lib/treeline/generated/pjsip_handsets.conf"), reload=False)
print(json.dumps({"treehouse": treehouse, "handset": handset_id, "user": sip_user, "secret": secret}))
