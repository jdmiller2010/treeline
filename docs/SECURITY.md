# Security reviews

The record of every security review of Treeline: what was reviewed, when, what was found, and what was done about it. Newest review first. Keep this file current (see "How to record a review" below).

Treeline's security model in one paragraph: a family signs in with an emailed code and holds a 30-day session (stored hashed on the server). Handsets authenticate to Asterisk with digest credentials generated from the database. Calls connect only over strings both families approved, and what each family sees of a call is filtered. No recording, no outside numbers, no 911. See [ARCHITECTURE.md](ARCHITECTURE.md) and [DEPLOY.md](DEPLOY.md).

## Open items

Everything not yet fixed, from every review. Move a row to its review's "Remediation" when it is done.

| Ref | Item | Severity | Found | Status |
|---|---|---|---|---|
| R1-1 | SMTP STARTTLS does not verify the server certificate (`controller/treeline/mail.py`) | Medium | 2026-11-19 | **Fixed** in 45ff030: `starttls(context=ssl.create_default_context())`. Tests: `test_prod.SmtpVerifiesCertificates` (a local SMTP server with an untrusted certificate, a trusted one for the wrong name, and a trusted one for the right name). Not run against SES itself from the app (the connection was checked with OpenSSL and Python) |
| R1-2 | Adapter SIP secret stored in plaintext, and the provisioning token is unhashed and reusable (`db.py`, `api.py`) | Low–Medium | 2026-11-19 | Open |
| R1-3 | Call JSON returns the callee's raw block reason to the caller (`api.py` `call_json`) | Low | 2026-11-19 | **Fixed** in 659d180 (the caller's copy is written with the reason redacted) and 9f0065a (the API reads those copies). Test: `test_api.CallLogs.test_the_callers_json_never_carries_why_the_callee_would_not_take_the_call`, `test_calllog.Isolation` |
| R1-4 | Backups and the database are unencrypted at rest; backup file is `chmod`ed after creation | Low | 2026-11-19 | **Backups: fixed, in the VM job** (`age` to a public key, the VM holds no private key; test `vm_test.G_Backup`); **database at rest: documented by AWS, not observed** (Lightsail says attached disks are encrypted; everything is on one, see Review 3). Earlier: The permission part is fixed in 787f646 (every backup is created `0600` in a `0700` directory from its first byte; `test_ops.Backups`). Encryption at rest is still deploy work |
| R1-5 | Provisioning and pairing tokens appear in the gunicorn access log | Low | 2026-11-19 | **Fixed** for the VM: query strings and `/api/provision/<token>` are redacted (`accesslog.py`; test `test_prod.AccessLogKeepsTokensOut`), the journal is volatile, Caddy does not log requests (VM job). The Docker prod compose still logs them (retired) |
| R1-6 | Push subscription endpoint accepts any `https://` host (blind SSRF) | Low | 2026-11-19 | Open |
| R1-7 | Phone lock applied only to the installed app; a parent token can sit on a phone device | Informational | 2026-11-19 | Mostly fixed (uncommitted at time of writing): the lock now applies in every tab, and leaving needs the server-checked parent code. The parent token still stays on the device; it is unusable there while the device is a phone. A person who clears the browser's site data can still escape it. Also by design: "Sign out of this browser" on the phone (no code needed, for a forgotten code) ends phone mode and the browser's parent session, so a child can take a phone out of phone mode that way, but it opens nothing and the parent sees `handset_signed_out` in the action log |
| R1-8 | `ws://` fallback when `TREELINE_PUBLIC_WS_URL` is unset (dev stack only) | Informational | 2026-11-19 | **Fixed for production**: `TREELINE_ENV=production` refuses to start without a `wss://` URL (`test_prod.ProductionGuard`, and the VM job). The dev fallback remains by design |
| R1-9 | Bearer token and SIP secret held in `localStorage` | Informational | 2026-11-19 | Accepted (standard for this design) |
| R2-1 | The caller's copy of a call would have held the callee's pause, quiet hours or daily limit, an unstrung dial's callee id, and the other family's handset ids (found in the spec, before code) | Low | 2026-11-19 | **Fixed** in 659d180: redacted when the copy is written. Tests: `test_calllog.Isolation` |
| R2-2 | Reconcile could delete a new household's file: the API makes it inside a still-open central transaction, so it has no row yet (data loss, not disclosure) | Medium (availability) | 2026-11-19 | **Fixed** in 659d180: only files that have sat for an hour are treated as orphans. Test: `test_calllog.Reconcile.test_files_with_no_treehouse_are_removed_but_not_while_a_create_may_be_in_flight` |
| R2-3 | A stale handle to a deleted household (another thread or process) could write through it or bring it back as an empty file | Low | 2026-11-19 | **Fixed** in 7435536: `mode=rw` opens, inode-checked cache. Tests: `test_households.Opening`, `test_api.History.test_a_handle_in_another_thread_cannot_write_to_a_household_deleted_through_the_api` |
| R2-4 | At startup a file another process was creating could be read as an old-layout file and refused (availability) | Low | 2026-11-19 | **Fixed** in 0284536: one snapshot for the marker read. Test: `test_db.Migrations.test_several_processes_creating_the_same_new_file_at_once_make_it_once` |
| R2-5 | The central ledger still holds both families' raw facts (including the callee's own rules) for three days, and the API process can open any household file by id: isolation between families on the read path still depends on every call site passing the signed-in family's id | Informational | 2026-11-19 | Open (by design; all current call sites use the session's treehouse, and notes to *other* families are write-only) |
| R2-6 | Household files, their backups and pre-migration copies are not encrypted at rest | Informational | 2026-11-19 | Backups: as R1-4. Live files and pre-migration copies: only the attached-disk encryption AWS documents, **not verified**. Open until the real account shows it |
| R3-x | See Review 3 above for R3-1 to R3-10 | | | see the review |
| R2-7 | "Delete all my data" removes the live file at once, but backups of it (central, and the household's own) live up to 7 days; the VM cannot delete them | Informational | 2026-11-19 | Accepted, documented ([DATA_LAYER.md](DATA_LAYER.md), `infra/README.md`) and warned about in the app when retention is shortened |

## Review 3: 2026-11-20, the AWS deployment work (reviewed by its author, not independently)

**Scope.** Work packages 1 to 4 and 6 of [DEPLOY_AWS.md](DEPLOY_AWS.md): `deploy/native/` (installer, units, templates, the root-run tools, the deploy agent, backups), `scripts/build_release.sh`, the release and CI workflows, `controller/treeline/prod.py`, `mail.py`, `accesslog.py`, `infra/` (bootstrap, deploy.sh, restore, the CDK app). Not covered: anything on AWS or a public server; Google sign-in (work package 5, not built); the web client; Asterisk's own code.

**Method.** Not `/security-review`. The author wrote tests for each property and ran them: unit tests, the VM-imitating job (real `install.sh`, real deploy agent, Asterisk 20.6 and Caddy 2.6.2 from Ubuntu 24.04 under systemd in Docker, a fake SSM/S3, a local ACME CA, an outside client container), and a mutation check that breaks seven properties on purpose and requires the matching test to fail (all seven were caught). The spec was checked against the real components first (verification record in DEPLOY_AWS.md). The fakes are not AWS: IAM evaluation, KMS, SES, the Lightsail firewall and disk, NAT and Let's Encrypt were not exercised.

| Ref | Finding | Severity | Status |
|---|---|---|---|
| R3-1 | `bootstrap.sh` wrote every SSM value through `--cli-input-json file:///dev/stdin`, which the real AWS CLI v2 rejects ("Invalid JSON received"); the fake `aws` had asserted the broken form. The obvious workarounds put the secret in argv | Medium (would have broken first use, or invited an unsafe workaround) | **Fixed**: a `0600` file on tmpfs, deleted at once. Tests: `test_bootstrap.sh` (the fake now rejects `/dev/*`; request files are 0600, on tmpfs, deleted; the old script fails the new test) |
| R3-2 | A release is root code: a checksum next to the file would not stop a tampered release (design finding, before code) | High if unmitigated | **Fixed by design and tests**: `ssh-keygen -Y verify` before anything is unpacked, against `/etc/treeline/release_signers`, which no release can replace; the release's own version must equal the requested one (replay); older releases refused. Tests: `test_tools.Releases`, `vm_test.F_Deploy` 02 to 06 (nothing changed, nothing left behind) |
| R3-3 | Whoever can run the release workflow can get root on the VM (the signing key is a GitHub environment secret) | Residual risk | **Accepted, documented**: protected `release` environment with a required reviewer, `v*` tag rules, tags must be on `main`; REPO_RULES.md. Not testable here |
| R3-4 | Rollback was inconsistent with DATA_LAYER rule 3 (old code refuses a newer file) | Medium (availability, data) | **Fixed without changing the data layer**: failed release restores the pre-migration copies, all or nothing; manual rollback refused once the layout moved. Tests: `vm_test.F_Deploy` 08 to 10, `test_tools.DeployAgentLogic` |
| R3-5 | Asterisk refuses its WHOLE pjsip configuration when the `#include`d generated file is missing | Medium (availability) | **Fixed**, found by the VM job (the installer creates it); covered by `vm_test` (transports loaded) |
| R3-6 | The deploy agent failed on `systemctl restart` with no units, on copying a directory in the config snapshot (rollback itself failed), and left a staged release after a "busy" refusal | Medium | **Fixed**, found by the VM job; covered by `F_Deploy` 01, 08, 11 |
| R3-7 | Secrets: fetched to tmpfs at each start, never on disk, argv or the journal; `age` public key only on the VM; ARI password generated on the VM | Checked | Clean in the VM job (`D_Secrets`, `G_Backup`). The real IAM policy (read `/treeline/*`, write-only to the bucket) was written in `bootstrap.sh` and checked against the fake only |
| R3-8 | Reachability: only 80, 443 (and 5061 when a certificate exists) listen on non-loopback addresses; ARI, 8080, 5038, 2019 refused from another host; port 80 only redirects (any host, any path, POST); only `/ws` reaches Asterisk; TLS 1.2+; HSTS; no request logging | Checked | Clean in the VM job with controls (`B_Network`) and mutation-checked. Lightsail's firewall and IPv6 behaviour: **not verified** |
| R3-9 | IPv6: Lightsail has a separate IPv6 firewall; CloudFormation has no IPv4-only switch | Unknown | The CDK lists IPv4 CIDRs only, relying on `PutInstancePublicPorts` replacing both firewalls. **Unverified on AWS** |
| R3-10 | With the beta gated by an access code (not by address), the web server, `/ws` and the media ports are reachable by anyone; the emailed-code sign-in is still in the app until work package 5 | Open | Open: the optional allowlist exists; sign-in is work package 5 |

**Checked and clean.** SQL and path handling in the new tools (host names validated, `glob.escape`, tar "data" filter plus explicit path checks, size caps); hostile `host.env` values refused before rendering; `install.sh` refuses `--ci` options on a real machine, refuses to put state on the system disk, formats only a blank disk; dependencies installed only with `--require-hashes`; no account id, address or secret in the repository (repo-rules scan, CDK template check).

**Not done / limits.** Nothing ran on AWS. Not independently reviewed. The `age` plaintext copy exists briefly on the (encrypted) state disk before encryption. Lock files are for CPython 3.12 on x86_64 only. Let's Encrypt's issuer-key directory name is derived by the same rule as the local CA's and was not seen. The fail2ban filter is still untested against a live log.

## Review 2: 2026-11-19, the data-layer split (reviewed by its author, not independently)

**Scope.** The `data-layer-split` branch: `db.py` (markers, refusal, migration runner), the new `households.py`, `api.py` (treehouse create, leave, delete, the call history and paging, health), `calls.py`, `jobs.py`, `backup.py`, `dev` (clean), and the tests. Not covered: the web client's changes beyond reading them, the deploy files beyond the backup default, and anything on a public server.

**Method.** Not `/security-review`: the author of the change read the spec against the code (the findings below that were found in the spec are marked), wrote tests that scan every row of a family's file for another family's data, and ran real files, real threads and a second process. It was not an independent review, so it should not be taken as one.

**Result.** R2-1 to R2-7 in the table above. No disclosure of one family's data to another was found in the code as written; R2-1 would have been one, and was caught in the spec.

**Now structurally prevented** (rather than checked on each read): a query for one family cannot reach another family's rows, because they are in different files; retention, deletion and backup are per family; a caller's file cannot return why a callee refused, because that is not in it (closes R1-3); a household file whose `meta.treehouse_id` is not its file name, or which carries the wrong marker, is refused; a database newer than the code, or without the marker, is refused and left byte-for-byte unchanged, so an older release cannot write into a newer layout.

**Not prevented.** R2-5: the API opens a household by id, so a call site that passed the wrong id would read another family. The tests cover each current call site with two families.

**Checked and clean.** Path traversal through a household id (ids go through `int()`); SQL injection (parameterised; the only f-strings build column lists from fixed names); file permissions (household files, backups and pre-migration copies are created `0600` in `0700` directories); deleting a household removes its `-wal`/`-shm` files and pre-migration copies.

**Remediation taken.** See each finding. Everything marked Fixed has a test that was run (`./dev unit`, 253 tests). What was not run: nothing on a public server, and the browser tests of the two parent-app changes are listed in the data-layer report, not here.

## Review 1: 2026-11-19, installable app (PWA) branch, plus transit and at-rest encryption

**Scope.** The changes on `main` ahead of `origin/main` (commits e657ddb, 7959a37, f314a0d, 273cfe1: calling-phone audio, busy tones, the installable app with one manifest and one service worker, the launcher, push handling, the phone lock), and, at the owner's request, the whole solution with a focus on encryption in transit and at rest. Files covered: the Flask API, the call engine and rules, the database layer, mail, jobs and push, the backup script, the deploy files (compose, Caddy, Asterisk overlay), and the web apps and service worker.

**Method.** `/security-review`. Three analysis passes (backend and data, telephony and deploy, web client) produced nine candidate findings. Each candidate was then re-checked by an independent reviewer against the exclusion rules, and anything under confidence 8 was dropped. Read-only: nothing was run against a live system. The web-client pass had no search tools and did not read every file (for example `quiet.js`, `install.js`, `tones.js`, `format.js`).

**Result.** No finding reached the reporting threshold. Nine items were verified at confidence 6 or lower; they are listed below and in the open-items table because several matter for the encryption goal.

| Ref | Finding | Where | Verified confidence | Severity |
|---|---|---|---|---|
| R1-1 | On Python 3.12 `starttls()` with no context does not check the certificate or hostname, so an active attacker between the API and the mail relay could read the SMTP password and sign-in codes (and so sign in as a parent). Stripping STARTTLS fails closed. | `controller/treeline/mail.py:33-34` | 6 | Medium |
| R1-2 | `handset.provision_secret` is plaintext; the provisioning token is unhashed, never rotated, and returns the secret on every fetch. `sip_md5` is a password-equivalent digest (required by Asterisk's `md5_cred`). Needs a copy of the database or a backup. | `db.py:47`, `api.py:~873`, `api.py:972-979` | 5 | Low–Medium |
| R1-3 | `call_json` returns `callee_paused`, `callee_quiet` or `callee_daily_limit` to the calling family, which `describe_call` deliberately hides. The CSV and the web client do not expose it. | `api.py:319-322` | 6 | Low |
| R1-4 | Backups are plain SQLite copies on the same volume, created with the default umask and `chmod 0600` afterwards. Same trust domain as the live database. | `controller/backup.py:30-47` | 3 | Low |
| R1-5 | gunicorn logs the request line, so provisioning and pairing tokens reach container logs. Caddy does not log requests. A log reader already has the database. | `deploy/docker-compose.prod.yml:47-48` | 3 | Low |
| R1-6 | Any `https://` push endpoint is accepted and later POSTed to. Blind, fixed body, no reach to anything sensitive found. | `api.py:1250-1261`, `jobs.py:58-61` | 2 | Low |
| R1-7 | The lock that keeps an installed phone out of the dashboard does not apply in a browser tab, and `useThisDevice` leaves the parent token in place. Not new, and documented as incomplete. | `web/shared/pwa.js:25`, `web/parent/js/house.js:71-83` | 2 | Informational |
| R1-8 | `ws_url()` falls back to `ws://host:8088/ws`. Production sets a `wss://` URL and binds ports to loopback, so plaintext exists only on the documented dev/LAN stack. | `api.py:828-838` | 2 | Informational |
| R1-9 | Session token and SIP secret in `localStorage`. Token is hashed server-side, expires in 30 days and is revoked on sign-out. No XSS path found. | `web/shared/api.js:8`, `web/phone/js/pair.js:9` | 2 | Informational |

**Checked and clean.** SQL injection (parameterised queries throughout); path traversal in file serving; cross-treehouse access (every query is scoped to the caller's treehouse); XSS (the `html` tag escapes everything, `attrs` strings are developer-written, the CSP is `script-src 'self'`, `base-uri 'none'`, `frame-ancestors 'none'`); session, login-code and pairing tokens (random, stored as SHA-256, compared in constant time); production transport (TLS/SRTP-only SIP, HTTPS via Caddy with HSTS, only `/ws` reaches Asterisk, ARI and gunicorn on loopback); generated pjsip config (usernames are generated, no injection); no call recording.

**Remediation taken.** None yet. This review found nothing at the reporting threshold, so no code was changed. The owner asked to do what can be done now for encryption; the intended fixes, in order, are:

1. R1-1: verify the SMTP certificate (`ssl.create_default_context()`), with a unit test that `starttls` receives a verifying context.
2. R1-3: return a generic reason to the caller for callee-side blocks, with a regression test.
3. R1-2: clear `provision_secret` after the first successful provisioning fetch, and hash the provisioning token.
4. R1-4: create backups under `umask 077` in a `0700` directory, and encrypt them (age or gpg) before the off-host copy; document encrypting the data volume in [DEPLOY.md](DEPLOY.md).
5. R1-5: log without the query string and exclude `/api/provision/`.
6. R1-7: when the parent-code phase lands, clear or re-gate the parent token when a device becomes a phone.
7. R1-8: refuse to start in production mode unless `TREELINE_PUBLIC_WS_URL` starts with `wss://`.

Update this section as each is done (commit, test that covers it).

## How to record a review

Claude: do this every time a security review is run (`/security-review`, a review of auth, crypto, transport or storage, or any audit the owner asks for), and every time a security fix lands.

1. **Add a new "Review N" section** at the top of the reviews, under "Open items". Use the date from the system, not a guess (`date +%F`). Include: **Scope** (what code, which commits or branch, what was and was not read), **Method** (how it was reviewed, and what the review could not see), **Result** (every finding with file and line, severity, and verified confidence, including ones dropped as below threshold), **Checked and clean** (what was looked at and held up), and **Remediation taken** (what changed, in which commit, and what test covers it; "None yet" if nothing).
2. **Give each finding a ref** `R<review>-<n>` and add it to the "Open items" table. When it is fixed, change its status to "Fixed in <commit>" and note the regression test. A security fix without a test is not finished (see CLAUDE.md).
3. **Be honest about limits.** Say what was not reviewed, what was not run, and what only works on a real device or public server. Never record a finding as fixed that was only discussed.
4. **Record dropped findings too**, with the reason, so the next review doesn't redo the work.
5. **Update when fixing later.** A fix in a later session edits the original review's "Remediation" and the open-items row; don't leave the record saying "open".
6. **Commit the doc with the change it describes** (or right after), and keep [README.md](../README.md)'s docs list and the review's `Open items` in step.
