#!/usr/bin/env python3
"""Proof that the VM imitation can fail. Brings up a fresh VM imitation, then breaks it on purpose, one way at a time
(inside the container, never in the repo), and requires the test that guards that property to FAIL, then fixes it and
requires the test to pass again. A safety net that has never been seen to catch anything is a wish.

    python3 deploy/native/ci/mutation_check.py          (about 15 minutes)

Each mutation names the requirement from docs/DEPLOY_AWS.md it stands for.
"""

import os
import subprocess
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
from deploy.native.ci import vm_test as t  # noqa: E402

PY = "/usr/local/lib/treeline/treeline_release.py"
DEPLOY = "/usr/local/lib/treeline/treeline-deploy"
NET = "deploy.native.ci.vm_test.B_Network."
DEP = "deploy.native.ci.vm_test.F_Deploy."

# (what is broken, requirement, shell to break it, shell to fix it, test that must catch it)
MUTATIONS = [
    ("the signature check accepts anything", "a bad signature must be rejected",
     f"cp {PY} /root/orig-release.py && sed -i 's/^def verify(tarball, sig, signers):/def verify(tarball, sig, signers):\\n    return/' {PY}",
     f"cp /root/orig-release.py {PY}", [DEP + "test_02_a_tampered_release_is_refused_and_nothing_changes"]),
    ("gunicorn listens on every interface", "port 8080 must not be reachable from outside",
     "cp /opt/treeline/current/deploy/native/gunicorn.conf.py /root/orig-gunicorn.conf.py && chmod u+w /opt/treeline/current/deploy/native/gunicorn.conf.py && "
     "sed -i 's/127.0.0.1:8080/0.0.0.0:8080/' /opt/treeline/current/deploy/native/gunicorn.conf.py && systemctl restart treeline-api",
     "cp /root/orig-gunicorn.conf.py /opt/treeline/current/deploy/native/gunicorn.conf.py && systemctl restart treeline-api", [NET + "test_ari_and_port_8080_are_not_reachable_from_outside"]),
    ("Asterisk's web server (ARI) listens on every interface", "ARI must not be reachable from outside",
     "sed -i 's/^bindaddr=.*/bindaddr=0.0.0.0/' /etc/asterisk/http.conf && systemctl restart asterisk",
     "treeline-config apply --release /opt/treeline/current --restart", [NET + "test_ari_and_port_8080_are_not_reachable_from_outside"]),
    ("port 80 serves a page instead of redirecting", "port 80 must serve only a redirect",
     "cp /etc/caddy/Caddyfile /root/orig-Caddyfile && sed -i 's|redir https://[^ ]*{uri} 308|respond \"Treeline in the clear\" 200|' /etc/caddy/Caddyfile && systemctl restart caddy",
     "cp /root/orig-Caddyfile /etc/caddy/Caddyfile && systemctl restart caddy", [NET + "test_port_80_only_redirects"]),
    ("Caddy forwards ARI to Asterisk", "only /ws may reach Asterisk",
     "cp /etc/caddy/Caddyfile /root/orig-Caddyfile && sed -i 's|@asterisk_ws path /ws|@asterisk_ws path /ws /ari/*|' /etc/caddy/Caddyfile && systemctl restart caddy",
     "cp /root/orig-Caddyfile /etc/caddy/Caddyfile && systemctl restart caddy", [NET + "test_only_ws_reaches_asterisk"]),
    ("a failed health check is not rolled back", "a failed health check must roll back",
     f"cp {DEPLOY} /root/orig-deploy && sed -i 's/^def roll_back(p, prev_dir, prev_version, snap, before, changed, failed_dir=None):/def roll_back(p, prev_dir, prev_version, snap, before, changed, failed_dir=None):\\n    return 1/' {DEPLOY}",
     f"cp /root/orig-deploy {DEPLOY}", [DEP + "test_08_a_release_that_never_becomes_healthy_is_rolled_back"]),
    ("production mode is switched off", "production must refuse a dev setting",
     "cp /etc/treeline/app.env /root/orig-app.env && sed -i 's/^TREELINE_ENV=production/TREELINE_ENV=development/' /etc/treeline/app.env",
     "cp /root/orig-app.env /etc/treeline/app.env && systemctl restart treeline-api", [t.__name__ + ".E_Production.test_production_refuses_to_start_with_a_dev_setting_and_recovers_without_it"]),
]


def attempt(test_id, env):
    return subprocess.run([sys.executable, "-m", "unittest", test_id], env=env, cwd=t.ROOT, capture_output=True, text=True).returncode


def main():
    t.VmTestCase.bring_up()
    env = dict(os.environ, TREELINE_VM_REUSE="1", TREELINE_VM_TMP=str(t.VmTestCase.tmp), TREELINE_VM_KEEP="1")
    problems = []
    try:
        # a deployed v0.0.2 for the rollback and health tests to start from
        if attempt(DEP + "test_01_a_signed_newer_release_is_deployed_and_the_old_one_kept", env) != 0:
            problems.append("the baseline test_01 failed before any mutation")
        for what, requirement, apply_cmd, fix_cmd, tests in MUTATIONS:
            t.vm(apply_cmd, check=False)
            t.vm("sleep 3")
            caught = {x: attempt(x, env) != 0 for x in tests}
            t.vm(fix_cmd, check=False)
            t.vm("sleep 8")
            for x in tests:
                recovered = attempt(x, env) == 0 if "test_01" not in x and "test_08" not in x and "test_02" not in x else True
                status = "CAUGHT" if caught[x] else "NOT CAUGHT"
                print(f"{status:10s} {what}  ->  {x.split('.')[-1]}   ({requirement})" + ("" if recovered else "   [did not recover after the fix]"))
                if not caught[x]:
                    problems.append(f"{what}: {x} did not fail")
                if not recovered:
                    problems.append(f"{what}: {x} did not pass after the fix")
    finally:
        t.VmTestCase.bring_down() if os.environ.get("TREELINE_VM_KEEP") != "1" else None
    print()
    print("every mutation was caught" if not problems else "PROBLEMS:\n  " + "\n  ".join(problems))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
