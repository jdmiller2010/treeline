# Security reviews

The record of every security review of Treeline: what was reviewed, when, what was found, and what was done about it. Newest review first. Keep this file current (see "How to record a review" below).

Treeline's security model in one paragraph: a family signs in with an emailed code and holds a 30-day session (stored hashed on the server). Handsets authenticate to Asterisk with digest credentials generated from the database. Calls connect only over strings both families approved, and what each family sees of a call is filtered. No recording, no outside numbers, no 911. See [ARCHITECTURE.md](ARCHITECTURE.md) and [DEPLOY.md](DEPLOY.md).

## Open items

Everything not yet fixed, from every review. Move a row to its review's "Remediation" when it is done.

| Ref | Item | Severity | Found | Status |
|---|---|---|---|---|
| R1-1 | SMTP STARTTLS does not verify the server certificate (`controller/treeline/mail.py`) | Medium | 2026-11-19 | Open |
| R1-2 | Adapter SIP secret stored in plaintext, and the provisioning token is unhashed and reusable (`db.py`, `api.py`) | Low–Medium | 2026-11-19 | Open |
| R1-3 | Call JSON returns the callee's raw block reason to the caller (`api.py` `call_json`) | Low | 2026-11-19 | Open |
| R1-4 | Backups and the database are unencrypted at rest; backup file is `chmod`ed after creation | Low | 2026-11-19 | Open |
| R1-5 | Provisioning and pairing tokens appear in the gunicorn access log | Low | 2026-11-19 | Open |
| R1-6 | Push subscription endpoint accepts any `https://` host (blind SSRF) | Low | 2026-11-19 | Open |
| R1-7 | Phone lock applied only to the installed app; a parent token can sit on a phone device | Informational | 2026-11-19 | Mostly fixed (uncommitted at time of writing): the lock now applies in every tab, and leaving needs the server-checked parent code. The parent token still stays on the device; it is unusable there while the device is a phone. A person who clears the browser's site data can still escape it. Also by design: "Sign out of this browser" on the phone (no code needed, for a forgotten code) ends phone mode and the browser's parent session, so a child can take a phone out of phone mode that way, but it opens nothing and the parent sees `handset_signed_out` in the action log |
| R1-8 | `ws://` fallback when `TREELINE_PUBLIC_WS_URL` is unset (dev stack only) | Informational | 2026-11-19 | Open |
| R1-9 | Bearer token and SIP secret held in `localStorage` | Informational | 2026-11-19 | Accepted (standard for this design) |

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
