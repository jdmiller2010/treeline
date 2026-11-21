# Supply chain: what Treeline depends on, and how we hear when any of it is unsafe

Treeline is a children's phone network, so "a library we use has a hole in it" has to reach the owner without anyone remembering to look. This document says what is watched, by what, how updates happen on their own, and what is still a person's job. A rule with no check behind it is only a wish, so each part names the file that does it.

**What has and has not run.** The scripts' tests (38) run offline. The pull-request job ran on GitHub against the real OSV.dev on 2026-11-20 (319 component versions asked about; the numbers under "First real run" are from it), and so did CodeQL. **Not yet run, because they only run from `main` or on a schedule:** the daily `watch` job and its issue, the dependency-graph submission, the Monday lock refresh (its lock script was exercised here only outside Docker, with a different Python), and the Dependabot auto-merge. Treat those four as written and reviewed, not as tested, until their first runs have been looked at.

## The short version

| Question | Answer | Done by |
|---|---|---|
| What third-party software is in Treeline? | `./dev sbom --table`, or the `sbom` artifact on any `supply chain` run (CycloneDX JSON) | `scripts/sbom.py` |
| Does any of it have a known vulnerability? | Checked on every pull request, every push to `main`, and every day | `scripts/vuln_check.py`, `.github/workflows/supply-chain.yml` |
| How do I hear about it? | An issue is opened in this repo (GitHub emails the owner), new findings add a comment to it, and the daily run fails. GitHub's own Dependabot alerts email too, once turned on | the `watch` job; Settings (below) |
| Who updates the dependencies? | GitHub Actions and the CDK command line: Dependabot, merged automatically when small and green. Python: a Monday job rebuilds the locks and leaves a branch one click from a pull request. Ubuntu packages on the VM: `unattended-upgrades` | `.github/dependabot.yml`, `dependabot-automerge.yml`, `refresh-locks.yml`, `install.sh` |
| Is our own code checked? | CodeQL on every pull request and weekly | `.github/workflows/codeql.yml` |

## What is in the bill of materials

`scripts/sbom.py` reads the repo and executes nothing it reads. One entry per name and version, each marked with where it came from and whether it runs in production.

| Source | What | Checked against OSV |
|---|---|---|
| `controller/requirements-prod.lock` | The app on the VM (Flask, gunicorn, pywebpush and everything they pull in) | yes |
| `deploy/native/requirements-tools.lock` | The VM's root-run tools (boto3) | yes |
| `infra/requirements.lock`, `infra/restore/requirements.lock` | The CDK app and `restore.py`, on the owner's computer and in CI | yes |
| `infra/package-lock.json` | The CDK command line | yes |
| `web/phone/vendor/` | JsSIP and qrcode-generator, copied into the softphone. The version is the one `THIRD_PARTY_NOTICES.md` states | yes |
| `.github/workflows/*.yml` | Every action CI uses | yes when pinned to a commit with a `# v1.2.3` comment (all are, except the one in `release.yml`, whose comment says only `v4`; Dependabot will write the full version the first time it updates it) |
| Dockerfiles, compose files | Base images (`ubuntu:24.04`, `python:3.12-slim`, `caddy:2`, the Playwright image) | no: listed only. The tags float on purpose (they are what the VM runs), and none of them is part of a deployment |
| `asterisk/build/sources.lock` | The upstream Asterisk and the pjproject it bundles that production is moving to, and the toolchain image's digest (see "The Asterisk build" below). Listed with exact versions and sha256; not yet in production, and not yet asked about advisories (OSV does not answer for upstream Asterisk by version: the replacement check is the next change) | not yet |
| `deploy/native/install.sh` | Every Ubuntu package a fresh VM ends up with (about 260, from the 15 that `install.sh` names). `scripts/os_packages.sh` installs them in a throwaway container to get the list | yes, see below |

A test (`scripts/test_supply_chain.py`) fails if a lock cannot be read completely, if a `.js` file appears in `web/phone/vendor/` that the list does not know, if `THIRD_PARTY_NOTICES.md` names a version a lock does not pin, or if `install.sh`'s package line stops being readable. `./dev check` runs it.

**Not covered, known:** the development containers install `controller/requirements.txt` unpinned (so does the `controller unit tests` CI job), so what a developer or CI runs can be newer than the lock that production uses; firmware (Phase 6) does not exist yet; and the list of Ubuntu packages is what a VM installed *today* would have, not what the real VM has. Once there is a VM, its own truth is `dpkg-query -W` on it.

## The vulnerability check

`scripts/vuln_check.py` sends each exact name and version to [OSV.dev](https://osv.dev) (which gathers GitHub's advisories, PyPI's, npm's, Ubuntu's, and the malicious-package reports) and sorts what comes back into three kinds:

- **To act on**: anything in a Python, npm, vendored or Actions dependency. The run fails. There is almost always a fixed version.
- **Watched**: Ubuntu packages named in `OS_WATCH` in the workflow (`caddy`, and `openssl` and `libsrtp2`, the libraries the internet-facing Asterisk links against). These do not fail the run. They are kept in the issue, and each new advisory gets a comment there.
- **Listed**: every other Ubuntu package. In the report only.

If OSV cannot be reached or answers in a shape the script does not expect, the run fails with status 2. A check that did not run never passes as clean.

### When the report finds something

1. **Is there a fixed version?** The report says. For Python: `scripts/make_locks.sh`, review the diff, commit (or run the `refresh locks` workflow by hand from the Actions tab). For the CDK command line or an action: Dependabot has usually already opened the pull request. For a vendored library: replace the file in `web/phone/vendor/`, update its row in `THIRD_PARTY_NOTICES.md`, run `./dev check`.
2. **Does it reach the VM?** The app lock is installed on the VM only from a signed release: merge, tag, approve the release. A fix on `main` protects nobody until then.
3. **No fix, or it does not apply to how Treeline uses the library?** Add a line to `.vuln-ignore` in the repo root:

   ```
   GHSA-xxxx-xxxx-xxxx  until=2027-01-15  only in the debug server, which production never starts
   ```

   `until` is required and at most 90 days away. When it passes, the check stops with status 2 until someone looks again. An entry that no longer matches anything is named in the report so it can be removed.
4. **Malware** (an id starting `MAL-`) is different in kind: assume whatever installed it is compromised. Do not deploy; rotate what that environment could read (`infra/bootstrap/bootstrap.sh`), and record it in [SECURITY.md](SECURITY.md).

### Caddy comes from Ubuntu; Asterisk does not

**Caddy** is installed from Ubuntu 24.04's universe section, patched by `unattended-upgrades`; the daily check watches it. The first real run found no advisory against it.

**Asterisk used to be Ubuntu's package too**, and that was R8-1: the first real run found **76 advisories against `asterisk` 1:20.6.0 with no fixed package** (Ubuntu lists every CVE filed against a package until someone reviews it, and does not even for Ubuntu Pro). Production now runs an upstream Asterisk we compile ourselves: see "The Asterisk build" below, and the sorted advisories in [SECURITY.md](SECURITY.md), Review 9. Ubuntu's package is purged by `install.sh` and pinned out of apt. The libraries it links against (`openssl`, `libsrtp2`, and the others in `asterisk/runtime-deps.txt`) still come from Ubuntu and are patched by `unattended-upgrades`; the daily check watches the two that face the network.

### The Asterisk build

Production is changing from Ubuntu's `asterisk` package (above) to an upstream Asterisk that we compile ourselves from the signed source release, which is the answer to R8-1. This section describes the build and where it ends up. The directory is [asterisk/build/](../asterisk/build/README.md); the reasons for each choice are in the review recorded in [SECURITY.md](SECURITY.md).

- **One place, tightly scoped.** Only `asterisk/build/build.sh` compiles third-party code. It runs in a container with no network, no capabilities and a read-only root, started by `run-build.sh`, on source whose sha256 is pinned in `sources.lock` and whose signature `gpgv` accepted against a committed key with a pinned fingerprint. It never runs on the VM, and never in a job with a write token or a secret. This is the second exception to "don't execute downloaded code" in CLAUDE.md.
- **Only released code.** No cherry-picked upstream commits and no distribution patches of ours. (Asterisk's own tarball applies five patches of its own to the pjproject it bundles; none is a security fix.) Where an advisory has no fix in a release, the answer is a documented option or an entry in `.vuln-ignore` with a reason, until a release carries the fix.
- **Only the modules Treeline uses.** `modules.txt` is the list; the build fails if anything else is enabled or installed. Fewer modules, fewer advisories that apply.
- **Built twice.** `.github/workflows/asterisk.yml` builds the same inputs in two jobs and fails unless the artifacts are byte for byte the same. Publishing is a separate, manual job on `main`, with GitHub's build provenance attestation.
- **A change cannot slip past the lock.** `artifact.lock` holds the artifact's sha256 and a digest of every input in `asterisk/build/`. `scripts/asterisk_build.py check` (in `./dev check` and a required CI job) fails when an input changed without a new artifact.
- **Updating it is now our job.** `unattended-upgrades` will not patch an Asterisk we compiled. The plan for hearing about new upstream releases and advisories, and turning them into a release, is part of the same work and is described here when it lands.

## Updates that happen on their own

| What | How | Cooldown | Merges itself? |
|---|---|---|---|
| GitHub Actions | Dependabot, Mondays, one grouped pull request | 7 days | Patch and minor: yes, when the required checks pass. Not if the pull request touches `release.yml`, `scripts/build_release.sh` or `deploy/native/` |
| CDK command line (`infra/`) | Dependabot, Mondays | 7 days | Patch and minor: yes |
| Anything with a GitHub security advisory in those two | Dependabot security update, at once | none | same rule |
| Python locks (all four) | `refresh locks`, Mondays: `scripts/make_locks.sh` with `LOCK_COOLDOWN=P7D`, updates the versions in `THIRD_PARTY_NOTICES.md` and the licenses pages, checks the result against OSV, pushes branch `deps/refresh-locks`, opens or updates an issue with a link | 7 days | No: one click opens the pull request (see below), then merge when green |
| Ubuntu packages on the VM (Caddy, and the libraries Asterisk links against) | `unattended-upgrades` (installed by `install.sh`). A library update does not reach a *running* Asterisk until it restarts | Ubuntu's | yes, on the VM |
| Asterisk and pjproject | by hand, for now: a new upstream release means new pins in `asterisk/build/sources.lock`, a new artifact, a new release (the automation for noticing and proposing it is a later change) | | no: unattended-upgrades cannot patch what we compile |
| Vendored JsSIP and qrcode-generator | by hand | | no |
| `aws-cdk-lib`, `constructs` (pinned with `==` in `infra/requirements.in`) | by hand, together with the CDK command line | | no |
| Base images | they float; `./dev up` pulls the current one | | n/a |

**Why the cooldown.** Most poisoned releases are noticed and pulled within days. Waiting a week before taking a new version costs little and means an automatic update never picks up something published yesterday. Fixes for known vulnerabilities do not wait.

**Why the Python refresh stops one click short.** [REPO_RULES.md](REPO_RULES.md) keeps "Allow GitHub Actions to create and approve pull requests" off, and a pull request opened with the Actions token does not start the other workflows, so its checks would never run. The owner's click opens it as the owner and everything runs. If full automation is wanted later, the usual way is a small GitHub App whose token opens the pull request; that is a new credential to guard, which is why it is not here.

**Nothing here deploys.** Merging to `main` changes the repo. The VM installs only a signed release, which needs a tag and the owner's approval in the `release` environment. An automatic merge can break CI; it cannot reach a family's phone.

## What the automation is allowed to do

In the spirit of [REPO_RULES.md](REPO_RULES.md):

- Pull-request jobs (`scan`, `codeql`) have a read-only token and no secrets, and never use `pull_request_target`.
- The jobs that can write never run pull-request code: `watch` (issues), `graph` (the dependency graph; GitHub asks for `contents: write` for that API, and the job changes no file), `refresh locks` (pushes one branch, `deps/refresh-locks`, and writes one issue; it runs only from `main`).
- `dependabot auto-merge` holds a token that can merge, so it checks nothing out and runs nothing from the pull request. It only asks GitHub to merge once branch protection is satisfied. With no required checks on `main`, GitHub refuses, deliberately.
- Only GitHub's own actions (`actions/*`, `github/codeql-action`, `dependabot/fetch-metadata`), each pinned to a commit. The scanning itself is our own standard-library Python: no third-party scanner is downloaded or run.
- The issue the jobs maintain is found by its title **and** by having been opened by the Actions bot, because anyone can open an issue with the same title in a public repo.
- The only thing sent to OSV.dev is package names and versions, which this public repo already shows.

## GitHub settings: the owner's one-time checklist

These cannot be set from the repo. Until they are done, the scripts and workflows run, but Dependabot's own alerts are off and nothing merges itself.

1. **Settings, Advanced Security** (or "Code security"): turn on **Dependency graph**, **Dependabot alerts**, **Dependabot security updates** (off on 2026-11-20) and, if offered, **Dependabot malware alerts**. Secret scanning and push protection are already on.
2. **Your notification settings** (github.com/settings/notifications): under Dependabot alerts, choose email.
3. **Settings, General, Pull Requests**: tick **Allow auto-merge**.
4. **Settings, Branches** (or Rules): protect `main` (it is not protected today). Require a pull request and these checks: `rules`, `controller unit tests`, `tests for the VM's tools`, `the CDK app (template assertions and a real cdk synth, no AWS account)`, `the VM imitation (systemd in Docker)`, `bill of materials and vulnerability check (pull request)`, and the three `analyze (...)` jobs. No force pushes. Auto-merge waits for exactly this list, so a check left off it is a check an automatic merge can skip.
5. Leave **"Allow GitHub Actions to create and approve pull requests" off**, as REPO_RULES.md says.
6. Scheduled workflows in a public repo are switched off by GitHub after 60 days without a commit (it emails first). Re-enable `supply chain` and `refresh locks` on the Actions tab if that happens.

## Commands

```bash
./dev sbom --table         # read the bill of materials
./dev sbom -o sbom.json    # CycloneDX 1.5 JSON
./dev vulns                # the daily check, from your computer (no Ubuntu packages)
./dev vulns --os           # ... with the VM's Ubuntu packages (needs Docker)
python3 -m unittest scripts/test_supply_chain.py
python3 scripts/sbom.py --sync-notices && python3 scripts/build_licenses.py   # after changing a lock by hand
```

## First real run (2026-11-20, pull request 1)

- 319 component versions asked about: 47 Python, 3 npm (the CDK command line and the two vendored libraries), the actions pinned with a full version, and the Ubuntu packages.
- **Python, npm, vendored and Actions: no advisories.**
- Ubuntu: 334 advisories with no fixed package, across 42 source packages. The largest: `asterisk` 76, `postgresql-16` 52 (its client library comes in with Asterisk), `python3.12` 38, `unbound` 28, `krb5` 19, `openssl` 13, `glibc` 13. `caddy`: none.
- CodeQL (Python, JavaScript, workflows): the three analyses completed. Their results are under Security, Code scanning; they were not read as part of this work.
