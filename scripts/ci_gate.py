#!/usr/bin/env python3
"""Does this change need the slow VM-imitation job? Standard library only.

    python3 scripts/ci_gate.py FILE_LIST      one changed path per line (from `git diff --name-only --no-renames`: a rename must list the OLD path too, or moving a root-run file into docs/ would look like a docs change)
    python3 scripts/ci_gate.py --event push   always yes

Prints `run=true` or `run=false` (the form GitHub Actions reads from $GITHUB_OUTPUT).

The VM job proves things about the install and the machine: install.sh, the deploy agent, the units, routing and ports, TLS, secrets,
signed releases and rollback, backups, the Asterisk build, the controller starting in production. A change to the screens, the phone
page, the design kit, the documents or the tests of other things cannot change any of that, so it need not wait for it.

The rule is a short list of places that are SAFE to skip for, and everything else runs the job: a new directory, a file this list has
never heard of, or a change that touches both kinds, runs it. The job still starts, and reports success when it is skipped: a
required check that GitHub does not run at all stays "pending" and blocks the merge.
"""

import re
import sys

# Paths whose changes cannot affect what the VM job tests. Anything not matched here runs the job.
SAFE = (
    r"web/.+", r"design/.+", r"docs/.+", r"testphones/.+", r"infra/.+",
    r"[^/]+\.md",                                   # README.md, CLAUDE.md, ... at the top level
    r"LICENSE", r"THIRD_PARTY_NOTICES\.md", r"\.gitignore", r"\.vuln-ignore",
    r"\.github/dependabot\.yml",
    r"controller/tests/.+",                         # the app's own unit tests (the unit-test job runs them)
    r"scripts/(sbom|vuln_check|check_repo_rules|build_licenses|build_static|build_web_assets|make_locks|os_packages)\.(py|sh)",
    r"scripts/test_(supply_chain|check_repo_rules)\.py",
    r"\.github/workflows/(codeql|dependabot-automerge|refresh-locks|repo-rules|supply-chain)\.yml",
)
SAFE_RE = re.compile(r"(?:" + "|".join(SAFE) + r")")   # used with fullmatch: a prefix of a longer name is not the safe name


def needs_vm(paths):
    """True unless every changed path is one that cannot affect the VM job. An empty list (nothing to compare) runs it."""
    paths = [p.strip() for p in paths if p.strip()]
    if not paths:
        return True
    return any(not SAFE_RE.fullmatch(p) for p in paths)


def main(argv):
    if argv[:2] == ["--event", "push"] or (argv and argv[0] == "--always"):
        print("run=true")
        return 0
    if len(argv) != 1:
        print(__doc__.strip().split("\n\n")[0], file=sys.stderr)
        return 2
    with open(argv[0], encoding="utf-8") as f:
        print("run=" + ("true" if needs_vm(f.read().splitlines()) else "false"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
