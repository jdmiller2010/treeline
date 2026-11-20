# Deploying Treeline to AWS: the plan

Status: **design, not yet implemented.** Nothing here has been run on AWS or on a public server.
This replaces the Docker-based production plan in [DEPLOY.md](DEPLOY.md) and
`deploy/docker-compose.prod.yml`, which are retired when this is built (keep their still-valid parts:
the softphone/tablet setup, the pilot checklist and the monitoring notes).

What already exists and is relied on:

- The data layer (one central database plus one file per treehouse): [DATA_LAYER.md](DATA_LAYER.md).
- `infra/bootstrap/bootstrap.sh` (idempotent SSM + IAM setup; tested only against a fake `aws`) and
  [infra/README.md](../infra/README.md).
- The repo rules that keep this public repo safe: [REPO_RULES.md](REPO_RULES.md).
- Production-leaning Asterisk and Caddy config in `deploy/` (written for Docker, never run on a public server).

## Decisions already made

| Topic | Decision | Why |
|---|---|---|
| Account and domain | A new AWS account. `treelinephone.com` is registered in Route 53. | |
| Host | One **Lightsail** Ubuntu 24.04 instance with a **static IP** and an **attached state disk**. Start on the smallest bundle that runs everything (planned: the 0.5 GB one), resize later. | Asterisk needs an always-on host with UDP; Lightsail is the cheapest fit. Resizing a Lightsail instance means a new instance from a snapshot (or a rebuild), so state must not live on the boot disk. |
| Runtime | **Native** on the VM: apt Asterisk, Caddy, a Python venv, systemd units. **No Docker in production.** | Docker adds memory and a layer to debug on a tiny box. Docker stays for local development and for a CI job that imitates the VM. |
| Hostname | `app.treelinephone.com`. The bare `treelinephone.com` redirects to it (a Caddy block, free). | **Confirm the spelling with the owner**: the first request typed a different name and this was read as a dictation slip. `bootstrap.sh` hard-codes `treelinephone.com`. |
| Deploys | GitHub Actions builds a release tarball, attached to a GitHub Release. A **pull-based deploy agent on the VM** (a systemd timer) fetches, verifies, switches a symlink, health-checks and rolls back. The repo stays public so the VM pulls anonymously. | No inbound SSH from CI, no deploy credentials in GitHub. |
| Sign-in | **Google only.** The emailed-code sign-in is removed from production. Invite-only for the beta. | One identity provider, no password or code handling. |
| Secrets | SSM Parameter Store (SecureString, standard tier). Fetched to a tmpfs file at start. The ARI password is generated on the VM. The VM holds one IAM-user key (Lightsail has no instance roles). | Free, simple, nothing in the repo or the database. |
| Mail | SES, domain-verified (DKIM in Route 53), production access requested. | |
| Backups | SQLite files to S3 only (no volume snapshots), hourly, `age`-encrypted on the VM, write-only IAM, 7-day expiry. | See [infra/README.md](../infra/README.md). |
| Infrastructure as code | CDK (Python) in `infra/`: a retained **Foundation** stack and a replaceable **Host** stack. `infra/deploy.sh` runs `bootstrap.sh check` and refuses to deploy if it fails. | |
| Beta access | A Lightsail firewall allowlist for the beta, kept out of git. | |

## Layout on the VM

```
/opt/treeline/releases/<version>/      the unpacked release (read-only, root-owned)
/opt/treeline/current  ->  releases/<version>      the symlink the agent flips
/var/lib/treeline/                     the attached disk (mount here)
    treeline.db, households/           the data (owner: treeline, mode 0700)
    pre-migrate/                       pre-migration copies (7 days)
    caddy/                             Caddy's certificates and ACME state
    spool/                             backups waiting for upload
/etc/treeline/aws-credentials          the VM user's key (root, 0600), installed by hand
/run/treeline/env                      secrets fetched from SSM at start (tmpfs, 0600)
```

Services (systemd, all `Restart=on-failure`, hardened with `NoNewPrivileges`, `ProtectSystem`, etc.):
`caddy`, `asterisk` (the package's unit, with the project's config laid over it), `treeline-api` (gunicorn on
`127.0.0.1:8080`), `treeline-controller`, plus timers: `treeline-backup` (hourly), `treeline-deploy`
(quiet-hours poll), `treeline-certsync`, `treeline-health` (the dead-man ping). Caddy passes only `/ws` to
Asterisk; ARI stays on localhost.

## Security requirements (each needs a test or a check, below)

1. **HTTPS everywhere.** Port 80 only redirects and answers ACME. HSTS on (no preload). TLS 1.2 minimum.
2. **Encrypted in transit on every hop that leaves the machine:** browser to Caddy (TLS), browser calls
   (DTLS-SRTP), adapters (SIP over TLS with SDES SRTP, no plaintext fallback), SES (STARTTLS **with
   certificate verification**, which fixes SECURITY.md R1-1), SSM and S3 (HTTPS; the bucket policy denies
   non-TLS). Hops that stay on `127.0.0.1` (Caddy to gunicorn, Caddy to Asterisk's WebSocket, ARI) are
   allowed to be plain, and are bound to loopback so nothing else can reach them.
3. **Encrypted at rest:** the S3 bucket (default encryption) and the backups (`age`, client-side); the
   state disk (attached Lightsail disks are encrypted; **verify and record it**; the instance's own system
   disk may not be, which is why nothing sensitive lives there). Records the result in SECURITY.md
   (R1-4 and R2-6).
4. **No secret in git, argv, logs or the image.** Release tarballs contain no environment-specific values.
   `TREELINE_ENV=production` makes the app refuse to start if any dev setting is present
   (`TREELINE_DEV_CODES`, the default ARI login, a missing SSM value).
5. **Least privilege.** The VM key can read `/treeline/*` and write backups, nothing else. The deploy agent
   runs as root only for the switch and restart steps.
6. **Release integrity.** The agent runs as root, so a tampered release is a root compromise. It must verify
   a signature, not just a checksum that sits next to the file. Recommended: `ssh-keygen -Y sign` /
   `-Y verify` (nothing extra to install on the VM), with the private key stored as a secret in a
   protected GitHub environment that only tag builds on `main` can use, and the public key committed.
   (Alternative: GitHub artifact attestations with `gh attestation verify`.) Pick one, record why.
7. **Firewall.** Beta: 80 open to all (ACME and the redirect), 443 and UDP 10000-10100 open to the beta
   allowlist, 22 to the owner's address only. 5061/tcp stays closed until an adapter is tried. The allowlist
   is stored in SSM as a plain `String` (`/treeline/beta_cidrs`; add it to `bootstrap.sh`), read by CDK at
   deploy time, and never committed. **Limit to document:** families on mobile data or changing addresses
   are locked out of calls; the allowlist is a beta tool, not a design.

## Work packages, in order

Each is its own branch or PR, with tests that pass before the next starts.

### 1. Native install and release build

- `deploy/native/install.sh` (idempotent): packages (Asterisk, Caddy, python3-venv, `age`, `awscli` or boto3,
  sox for the sounds), users, directories, mounts the disk, venv, units, a swap file (the small bundle will
  need it), `ufw` or none (the Lightsail firewall is the boundary; decide and record).
- Systemd units and timers; the env file is built by a small `treeline-fetch-secrets` from SSM into `/run`.
- **Asterisk behind Lightsail's 1:1 NAT.** The instance has a private address and a static public one.
  Asterisk must advertise the public address for media and ICE: `external_media_address` and
  `external_signaling_address` on the transport, `local_net`, and `ice_host_candidates` in `rtp.conf` for
  browser phones. These **must be generated at install from the detected private and public addresses**, never
  committed. Check each option against the Asterisk version the package installs (24.04 ships 20.x).
- **Certificates for SIP-TLS.** Caddy owns them and its key files are not readable by Asterisk. Pin Caddy to
  one ACME issuer so the directory is predictable, and add `treeline-certsync` that copies the pair to a
  directory Asterisk can read (owner `asterisk`, 0600) and restarts Asterisk **only if it changed**. Check the
  real path and the issuer syntax against Caddy, as CLAUDE.md requires; do not rely on the Docker paths in
  `deploy/asterisk/pjsip.conf`.
- Caddyfile: the app host, the apex redirect, HSTS, and an `/api/health`-safe configuration.
- The release build: a script that makes a versioned tarball of `controller/`, `web/`, `design/ui`,
  `asterisk/` and `deploy/native/`, plus the signature. A GitHub Actions release workflow on a version tag
  (`permissions` as narrow as possible, no `pull_request_target`).
- Fix R1-1 (verified STARTTLS) with a regression test.

### 2. The deploy agent

`treeline-deploy` (timer, plus a manual `treeline-deploy --version vX.Y.Z`): fetch the release, verify the
signature, unpack beside the current one, run the new code's checks, flip the symlink, restart, wait for
`/api/health`, and **roll back automatically** on failure. It deploys in a quiet window and skips while a call is
in progress (no open ARI channels). Rollback is only safe because migrations are expand-only (see
[DATA_LAYER.md](DATA_LAYER.md), "Schema changes after go-live"); the agent must refuse to roll back past a
migration that was not, and say so.

### 3. A CI job that imitates the VM

A workflow job that runs `install.sh` and the deploy agent inside an `ubuntu:24.04` container with systemd
(a "systemd in Docker" image), then checks: the services start, `/api/health` is 200, port 80 only redirects,
only `/ws` reaches Asterisk, ARI is not reachable from outside, a bad signature is rejected, a failed health
check rolls back. It cannot test NAT, Let's Encrypt, SES or real firewalls; it exists to catch install breakage
before the VM does.

### 4. Backups

`treeline-backup` (hourly): SQLite's online backup of the central file and each household file (the existing
`controller/backup.py` already does the per-file layout), `age`-encrypt to the recipient in SSM, upload to
`central/` and `households/<id>/` in S3, write only. A dead-man ping (for example a free healthchecks-style
URL kept in SSM) on success. A **restore script and a drill**: pull, decrypt with the private key from the
owner's password manager, open, check. Local spool pruned at 7 days.

### 5. Google sign-in

- **Decide the mechanism first** (ask the owner): (a) Google Identity Services in the browser, which needs
  Google's script on our origin and a looser Content-Security-Policy on the sign-in page, or (b) the
  **authorization-code flow with PKCE**, where the server redirects to Google and exchanges the code, which
  keeps `script-src 'self'` and needs a client secret in SSM. (b) is recommended: the token comes straight
  from Google over TLS, so no signature library is needed, but `iss`, `aud`, `exp`, `nonce` and
  `email_verified` must still be checked.
- Who may sign in: an email on the invite list in SSM (`/treeline/allowed_emails`) may create a treehouse;
  a grown-up a parent added may sign in too. Confirm this with the owner.
- Remove the emailed-code routes from production. **The test suites depend on dev codes**: keep that path
  only when `TREELINE_DEV_CODES=1` (private addresses only) and make production refuse to start with it set.
  Add a dev sign-in that the browser tests can use without Google.
- A security entry in [SECURITY.md](SECURITY.md) and tests: wrong audience, expired, unverified email,
  replayed nonce or state, not on the list.

### 6. Infrastructure with CDK

`infra/` CDK app (Python): **Foundation** (retained: the backup bucket with TLS-only policy, default
encryption, a 7-day lifecycle rule, versioning off, the SES identity and DKIM records, DNS records, the state
disk, a budget alert) and **Host** (replaceable: the instance, static IP, firewall rules from
`/treeline/beta_cidrs`, the disk attachment). Import the existing hosted zone, do not create one.
`infra/deploy.sh` runs `bootstrap.sh check --quiet` first. `cdk.context.json` and `cdk.out/` are gitignored
(already). CDK's CLI is npm: add an exception to CLAUDE.md's "no `npm install`" rule **scoped to `infra/`**
and pin the version. Keep the bucket name identical to the one in `bootstrap.sh`.

### 7. First deploy and drills (needs the real account and the owner)

Run `bootstrap.sh apply`; `cdk deploy`; install the VM key; first release. Then, and only then, verify:
certificate issued; `/api/health`; Google sign-in with an invited account; a **cross-network call** (a phone
on mobile data to a browser on the allowlisted network, with audio both ways, which is the NAT check);
Asterisk memory under a call on the small bundle (resize if it swaps); a backup lands in S3 and **restores**;
a deploy and a rollback; an SES message arrives (after production access); the allowlist blocks a non-listed
address. Record what was and was not done in README (Phase 4) and SECURITY.md.

## What can and cannot be tested before AWS

| Can be tested locally or in CI | Only on the real account |
|---|---|
| Install script on a systemd container; the deploy agent, signature check and rollback; Caddy redirects and `/ws`-only routing; backup, encryption and restore against a local fake S3; the CDK app (`cdk synth`, assertions on the template); `bootstrap.sh` against the fake `aws`; Google flow against a fake issuer; STARTTLS verification against a test server with a bad certificate | `bootstrap.sh` against real IAM, SSM and `file:///dev/stdin`; CDK deploy; Let's Encrypt issuance and the cert path; NAT and one-way audio; Lightsail firewall behaviour and disk encryption; SES production access and DKIM; real memory use on the small bundle; the real Google consent screen |

## Decide before building

1. The hostname spelling (see the table).
2. The Google mechanism (work package 5) and who may sign in.
3. Release signing: SSH signatures or attestations.
4. Whether `ufw` runs on the VM or the Lightsail firewall alone is the boundary.
5. Confirm the current Lightsail bundles and prices when creating the instance; they change. Plan for the
   small bundle, and for resizing if Asterisk and the app do not fit.
6. SES production access takes a request and can take days; start it early. Until it is granted, SES only
   sends to verified addresses.

## What this does not cover

The pilot with real families ([PILOT.md](PILOT.md)); phone adapters and SIP-TLS on port 5061
([ADAPTER.md](ADAPTER.md), later); a legal review of children's privacy before families beyond friends join;
the `provision_secret` and other open SECURITY.md items unrelated to deployment.
