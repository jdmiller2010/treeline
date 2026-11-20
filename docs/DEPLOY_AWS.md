# Deploying Treeline to AWS: the plan

Status: **work packages 1 to 6 are built** (5, Google sign-in with the beta access code, with the owner's answers recorded below); 7 needs the real account. Everything runs only in the VM-imitating CI job (`./dev vm`), unit tests and
offline CDK assertions. **Nothing has been run on AWS or on a public server**; the "Verification record" at the end says
what was checked against the real components and what could not be, and the "Owner checklist" is what is left.
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
| Hostname | `app.treelinephone.com` (**confirmed by the owner**). The bare `treelinephone.com` redirects to it (a Caddy block, free). | The hostname is one setting (`TREELINE_DOMAIN`, from SSM `/treeline/domain` at install), never hard-coded in the app or Caddyfile. `bootstrap.sh` still defaults its mail domain to `treelinephone.com`. |
| Deploys | GitHub Actions builds a release tarball, attached to a GitHub Release. A **pull-based deploy agent on the VM** (a systemd timer) fetches, verifies, switches a symlink, health-checks and rolls back. The repo stays public so the VM pulls anonymously. | No inbound SSH from CI, no deploy credentials in GitHub. |
| Sign-in | **Google only.** The emailed-code sign-in is removed from production. **Closed beta by access code** (owner's decision, replacing the invite list): a visitor enters a beta access code, and once it is accepted may register with any Google account. No one is invited by address. | One identity provider, no password handling. Details are settled at work package 5. |
| Secrets | SSM Parameter Store (SecureString, standard tier). Fetched to a tmpfs file at start. The ARI password is generated on the VM. The VM holds one IAM-user key (Lightsail has no instance roles). | Free, simple, nothing in the repo or the database. |
| Mail | SES, domain-verified (DKIM in Route 53), production access requested. With Google-only sign-in, mail is only for alert emails (and the sandbox is enough until real families join). | |
| Backups | SQLite files to S3 only (no volume snapshots), hourly, `age`-encrypted on the VM, write-only IAM, 7-day expiry. | See [infra/README.md](../infra/README.md). |
| Infrastructure as code | CDK (Python) in `infra/`: a retained **Foundation** stack and a replaceable **Host** stack. `infra/deploy.sh` runs `bootstrap.sh check` and refuses to deploy if it fails. | |
| Beta access | The beta access code (work package 5) gates **accounts**. The Lightsail firewall allowlist stays as an **optional** extra: SSM `/treeline/beta_cidrs` (a plain `String`, empty or absent means open to all), never committed. | The owner does not plan to invite people by address, so an allowlist may not fit; it is kept because it is the only thing that narrows who can reach the ports. **Review this.** |

## Layout on the VM

```
/opt/treeline/releases/<version>/      the unpacked release (read-only, root-owned)
/opt/treeline/current  ->  releases/<version>      the symlink the agent flips
/var/lib/treeline/                     the attached disk (mount here); owned by root, 0711
    data/                              the app's: treeline.db, households/, pre-migrate/ (owner: treeline, 0700)
    backup/, deploy/                   root's own records (what was uploaded, the deploy state; 0700)
    caddy/                             Caddy's storage root (`storage file_system`): certificates/<issuer-key>/<host>/<host>.crt
    spool/                             backups waiting for upload
/etc/treeline/aws-credentials          the VM user's key (root, 0600), installed by hand
/etc/treeline/release_signers          the release signing PUBLIC key(s): the trust anchor (root, 0644), set at install, never replaced by a release
/etc/treeline/host.env                 non-secret settings the installer detected (domain, private and public address)
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
   state disk (the Lightsail FAQ says attached disks and their snapshots are encrypted at rest by default with
   Lightsail-managed keys; it says nothing about the system disk, so **assume the system disk is not encrypted**
   and keep nothing sensitive on it, including logs, the swap file and `/tmp`: see work package 1). Record the
   result in SECURITY.md (R1-4 and R2-6) as documented-by-AWS, not observed.
4. **No secret in git, argv, logs or the image.** Release tarballs contain no environment-specific values.
   `TREELINE_ENV=production` makes the app refuse to start if any dev setting is present
   (`TREELINE_DEV_CODES`, the default ARI login, a missing SSM value).
5. **Least privilege.** The VM key can read `/treeline/*` and write backups, nothing else. The deploy agent
   runs as root only for the switch and restart steps.
6. **Release integrity.** The agent runs as root, so a tampered release is a root compromise. It must verify
   a signature, not just a checksum that sits next to the file. **Decided (owner): `ssh-keygen -Y sign` /
   `-Y verify`** (nothing extra to install on the VM, and the tamper test runs offline in CI). The private
   key is a secret in a protected GitHub environment that only tag builds on `main` can use; the public key is
   committed and copied to `/etc/treeline/release_signers` **at install**. The trust anchor never ships inside a
   release (a release must not be able to replace the key that judges it), and the verifier is the installed
   agent, not the release's copy. **Limit to document:** whoever can push a tag on `main` through that
   environment can get root on the VM, so the environment needs a required reviewer and tag protection
   (GitHub settings, listed in the owner checklist and in REPO_RULES.md).
7. **Firewall.** Lightsail has **two independent firewalls per instance, IPv4 and IPv6**, and a new
   instance starts with default rules (SSH and HTTP open to everyone) on both. Open: 80/tcp (ACME and the
   redirect), 443/tcp, UDP 10000-10100 (call audio); 443 and the UDP range are limited to
   `/treeline/beta_cidrs` **when that optional list is set** (80 stays open: ACME and the redirect). 22/tcp is restricted to the owner's address, read from
   SSM `/treeline/admin_cidr` (a plain `String`, added to `bootstrap.sh`; never committed). 5061/tcp stays
   closed until an adapter is tried. IPv6 stays closed because no rule lists an IPv6 CIDR (see work package 6);
   if IPv6 is ever wanted, the rules must be mirrored. With no allowlist set (the beta is
   gated by an access code, see Sign-in), the web server, the `/ws` WebSocket and the media ports are
   reachable by anyone: the defences are that nothing is served without sign-in or a registered handset, the
   rate limits, and fail2ban.

## Work packages, in order

Each is its own branch or PR, with tests that pass before the next starts.

### 1. Native install and release build

- `deploy/native/install.sh` (idempotent): packages (Asterisk 20.6, Caddy 2.6.2, python3-venv, `age`,
  `ca-certificates`, sox and `fail2ban` from Ubuntu 24.04's own repositories; **there is no `awscli` apt
  package on 24.04**, so the VM uses **boto3**, pinned in `controller/requirements-prod.txt`, in the venv),
  users, directories, mounts the disk (found by its size or label at install, not by a hard-coded device
  name), venv, units, a swap file **on the state disk** (the small bundle will need it; nothing sensitive may
  sit unencrypted on the system disk, and swap can hold anything), `journald` kept volatile, no core dumps,
  and `ufw`: **not installed**; the Lightsail firewall is the boundary and a second one that can disagree
  with it costs more than it protects here (recorded as a decision to review).
- A `TREELINE_ENV=production` guard in the app (see requirement 4), including `TREELINE_PUBLIC_WS_URL` starting
  with `wss://` (SECURITY.md R1-8), gunicorn logging that omits the query string and the provisioning and
  pairing paths (R1-5), and a systemd journal that is not kept on the system disk.
- Systemd units and timers; the env file is built by a small `treeline-fetch-secrets` from SSM into `/run`.
- **Asterisk behind Lightsail's 1:1 NAT.** The instance has a private address and a static public one.
  Asterisk must advertise the public address for media and ICE: `external_media_address`,
  `external_signaling_address` and `local_net` are **options on each pjsip transport**; `ice_host_candidates`
  is **not an option but a section of `rtp.conf`** (`[ice_host_candidates]`, lines of
  `<private address> => <public address>`), which is what browser phones need (their media is negotiated with
  ICE). These **must be generated at install from the detected private and public addresses** into
  `/etc/treeline/host.env` and the Asterisk config, never committed. The public address comes from, in order:
  `--public-ip`, the instance metadata service, DNS for the host name (the metadata service was not
  verified on Lightsail: see the verification record). All of these option names were checked against the
  documentation shipped in Ubuntu 24.04's Asterisk 20.6.0.
- **Certificates for SIP-TLS.** Caddy owns them and its key files are not readable by Asterisk. Pin Caddy to
  one ACME issuer (`tls { issuer acme { dir ... } }`, valid in Caddy 2.6.2) and set
  `storage file_system /var/lib/treeline/caddy` so the files are at
  `<storage>/certificates/<issuer-key>/<host>/<host>.crt` and `.key`. **The Docker path in
  `deploy/asterisk/pjsip.conf` has an extra `caddy/` component that does not exist with an explicit storage
  root.** `treeline-certsync` (root) finds the one matching pair, copies it to a directory Asterisk can read
  (owner `asterisk`, 0600 key) and restarts Asterisk **only if it changed**; it refuses to act if zero or more
  than one pair match (a second issuer would otherwise be picked silently).
- Caddyfile: the app host, the apex redirect, HSTS, and an `/api/health`-safe configuration.
- The release build: a script that makes a versioned tarball of `controller/`, `web/`, `design/ui`,
  `asterisk/` and `deploy/native/`, plus the signature. A GitHub Actions release workflow on a version tag
  (`permissions` as narrow as possible, no `pull_request_target`).
- Fix R1-1 (verified STARTTLS) with a regression test. (Confirmed in the Python 3.12 source:
  `starttls()` without a context uses an unverified one.)
- **`bootstrap.sh` has a bug that this spec's own dependency caused:** `--cli-input-json file:///dev/stdin`, which
  it uses for every SSM write, is rejected by AWS CLI v2 ("Invalid JSON received", verified on 2.35.17) while a
  regular file works. The fake `aws` in its tests asserted the broken form, so the tests could not see it.
  Fix: write the request to a `0600` file on tmpfs (`$XDG_RUNTIME_DIR`, else `/dev/shm`), delete it on exit, and make the fake
  reject `/dev/stdin` as the real CLI does. Same fix to the example in `infra/README.md`.

### 2. The deploy agent

`treeline-deploy` (timer, plus a manual `treeline-deploy --version vX.Y.Z`): fetch the release, verify the
signature, unpack beside the current one, run the new code's checks, flip the symlink, restart, wait for
`/api/health`, and **roll back automatically** on failure. It deploys in a quiet window and skips while a call is
in progress (no open ARI channels). **Rollback and migrations (the spec was inconsistent here):** DATA_LAYER.md rule
3 makes the *old* code refuse to open a file whose `user_version` is newer than it knows, so expand-only does not
by itself make a code-only rollback possible. The agent therefore records every data file's `user_version`
before the switch. If the new release fails its health check and no file's version moved, it flips the
symlink back. If a version did move, it stops the services, restores those files from the pre-migration copies
the data layer took (`pre-migrate/`; the release never became healthy, so nothing a family did is lost beyond
the failed window) and then flips back; if a copy is missing it **refuses to roll back, stays where it is, and
says so**. A manual `treeline-deploy --rollback` is refused whenever any version differs from what the
previous release expects, because by then families have written data; the message points at the restore
procedure. The data layer is not changed.

### 3. A CI job that imitates the VM

A workflow job that runs `install.sh` and the deploy agent inside an `ubuntu:24.04` container with systemd
(a "systemd in Docker" image), then checks: the services start, `/api/health` is 200, port 80 only redirects,
only `/ws` reaches Asterisk, ARI and port 8080 are not reachable from outside the container's loopback (checked
from a second container on the same network, so the test can fail), a bad signature and a tampered tarball are
rejected, a failed health check rolls back, a production start with any dev setting present is refused. SSM and S3 are
replaced by a small fake that the VM tools reach through a documented endpoint override. Caddy gets its
certificate from a Caddy acting as a local ACME server, which checks the real certificate path that
`treeline-certsync` reads (but not Let's Encrypt's own issuer name). It cannot test NAT, Let's Encrypt, SES or real firewalls; it exists to catch install breakage
before the VM does.

### 4. Backups

`treeline-backup` (hourly; today's `backup.py --daemon` runs nightly and is replaced by a timer): SQLite's online backup of the central file and each household file (the existing
`controller/backup.py` already does the per-file layout), `age`-encrypt to the recipient in SSM, upload to
`central/` and `households/<id>/` in S3, write only. A dead-man ping (for example a free healthchecks-style
URL kept in SSM) on success. A **restore script and a drill**: pull, decrypt with the private key from the
owner's password manager, open, check. Local spool pruned at 7 days.

### 5. Google sign-in

- **Mechanism decided (owner): (b), the authorization-code flow with PKCE.** The alternatives were: (a) Google Identity Services in the browser, which needs
  Google's script on our origin and a looser Content-Security-Policy on the sign-in page, or (b) the
  **authorization-code flow with PKCE**, where the server redirects to Google and exchanges the code, which
  keeps `script-src 'self'` and needs a client secret in SSM. (b) is recommended: the token comes straight
  from Google over TLS, so no signature library is needed, but `iss`, `aud`, `exp`, `nonce` and
  `email_verified` must still be checked. (Original wording: (a) ... (b) is recommended)
- **Who may sign in (owner's decision, replacing the invite list):** a **beta access code** the owner hands
  out. A visitor enters it on a private page; once accepted, they may register with any Google account.
  `/treeline/allowed_emails` and its prompt in `bootstrap.sh` are replaced by a hashed code (and
  `/treeline/google_client_secret` is added). **Decided and built:** one shared 8-character code; it expires (180 days by default, `TREELINE_BETA_DAYS`); no use counting; needed once, to create a treehouse; revoked by making a new one (`bootstrap.sh set beta_code`, then restart `treeline-api`); guessing limited to 10 tries per address and 60 overall per hour with identical answers for wrong, expired and unset; a grown-up a parent added signs in with Google alone; one treehouse per email. See SECURITY.md Review 4.
- Remove the emailed-code routes from production. **The test suites depend on dev codes**: keep that path
  only when `TREELINE_DEV_CODES=1` (private addresses only) and make production refuse to start with it set.
  Add a dev sign-in that the browser tests can use without Google.
- A security entry in [SECURITY.md](SECURITY.md) and tests: wrong audience, expired, unverified email,
  replayed nonce or state, not on the list.

### 6. Infrastructure with CDK

`infra/` CDK app (Python): **Foundation** (retained: the backup bucket with TLS-only policy, default
encryption, a 7-day lifecycle rule, versioning off, the SES identity and DKIM records, DNS records, the state
disk, a budget alert) and **Host** (replaceable: the instance, static IP, firewall rules (22 from `/treeline/admin_cidr`),
the disk attachment). Import the existing hosted zone, do not create one.
The instance's default firewall rules are replaced (requirement 7). (CloudFormation's `AWS::Lightsail::Instance` has no IPv4-only property, so the IPv6 firewall is kept closed by giving every rule IPv4 CIDRs only; `PutInstancePublicPorts` replaces the rules of both firewalls. **Unverified on AWS.**) The static IP and the A records are in **Host**, not Foundation: CloudFormation attaches a static IP from the IP's side (`AttachedTo`), so it cannot live in a stack that the instance's stack depends on. A replaced host gets a new address; DNS follows it. `infra/deploy.sh` runs `bootstrap.sh check --quiet` first. `cdk.context.json` and `cdk.out/` are gitignored
(already). CDK's CLI is npm: add an exception to CLAUDE.md's "no `npm install`" rule **scoped to `infra/`**
and pin the version. Keep the bucket name identical to the one in `bootstrap.sh`.

### 7. First deploy and drills (needs the real account and the owner)

Run `bootstrap.sh apply`; `cdk deploy`; install the VM key; first release. Then, and only then, verify:
certificate issued; `/api/health`; Google sign-in with an invited account; a **cross-network call** (a phone
on mobile data to a browser on another network, with audio both ways, which is the NAT check);
Asterisk memory under a call on the small bundle (resize if it swaps); a backup lands in S3 and **restores**;
a deploy and a rollback; an SES message arrives (after production access); if `/treeline/beta_cidrs` is set, a non-listed
address is blocked. Record what was and was not done in README (Phase 4) and SECURITY.md.

## What can and cannot be tested before AWS

| Can be tested locally or in CI | Only on the real account |
|---|---|
| Install script on a systemd container; the deploy agent, signature check and rollback; Caddy redirects and `/ws`-only routing; backup, encryption and restore against a local fake S3; the CDK app (`cdk synth`, assertions on the template); `bootstrap.sh` against the fake `aws`; Google flow against a fake issuer; STARTTLS verification against a test server with a bad certificate | `bootstrap.sh` against real IAM and SSM (the CLI's own handling of the request file was checked locally); CDK deploy; Let's Encrypt issuance and the cert path; NAT and one-way audio; Lightsail firewall behaviour and disk encryption; SES production access and DKIM; real memory use on the small bundle; the real Google consent screen |

## Decisions

Settled by the owner: the hostname (`app.treelinephone.com`), release signing (SSH signatures), the Google
mechanism (authorization code with PKCE), and the closed-beta rule (an access code, then any Google account).
Decided here, to review: the firewall allowlist is optional rather than dropped; no `ufw`; boto3 rather than the AWS CLI on the VM; swap and logs on the state disk
or in memory. Still open: the access-code details (work package 5). Confirm the current Lightsail bundles and
prices when creating the instance; they change. SES production access takes a request and can take days; start
it early. Until it is granted, SES only sends to verified addresses.

## What this does not cover

The pilot with real families ([PILOT.md](PILOT.md)); phone adapters and SIP-TLS on port 5061
([ADAPTER.md](ADAPTER.md), later); a legal review of children's privacy before families beyond friends join;
the `provision_secret` and other open SECURITY.md items unrelated to deployment.

## Verification record

Checked in work on this spec, **against the real components**, not recalled. "Not verified" says why.

| Claim | Result | How |
|---|---|---|
| Asterisk version on Ubuntu 24.04 | **20.6.0** (`1:20.6.0~dfsg+~cs6.13.40431414-2build5`) | installed it in an `ubuntu:24.04` container |
| `external_media_address`, `external_signaling_address`, `local_net` | transport options in `res_pjsip`; present in the shipped documentation XML | read `/usr/share/asterisk/documentation/core-en_US.xml` |
| `ice_host_candidates` | **a section of `rtp.conf`**, `<local> => <advertised>`, for one-to-one NAT; the spec called it an option | read the shipped `rtp.conf` |
| Caddy on 24.04 | **2.6.2** from Ubuntu's repository (security-patched); not Caddy's own apt repository (no extra signing key to trust) | installed it |
| Caddy issuer pinning and storage syntax | `tls { issuer acme { dir <url> } }` and `storage file_system <dir>` both accepted by `caddy validate`/`adapt` | ran Caddy 2.6.2 |
| Caddy certificate path with an explicit storage root | `<root>/certificates/<issuer-key>/<host>/<host>.crt`; no extra `caddy/` component (that comes from the data directory default) | checked with a local ACME server in the CI job (work package 3); the Let's Encrypt **issuer-key spelling** (`acme-v02.api.letsencrypt.org-directory`) is derived from the same rule but **not verified** without a real issuance |
| Asterisk can read Caddy's key | **No** (Caddy writes directories `0700`, keys `0600`, owned by `caddy`); the certsync copy is needed | Caddy's behaviour, and the package units' users (`caddy`, `asterisk`) |
| Lightsail: attached disk encrypted | Documented: attached disks and snapshots are encrypted at rest by default, with Lightsail-managed keys | AWS Lightsail FAQ (block storage). **Not observed** on a real disk |
| Lightsail: system disk encrypted | **Not stated** in the documentation; assume not | same |
| Lightsail firewall | **Separate IPv4 and IPv6 firewalls**, preconfigured default rules on both; the spec only addressed IPv4 | AWS Lightsail firewall documentation |
| SES SMTP | `email-smtp.us-west-2.amazonaws.com:587` STARTTLS, TLS 1.3, certificate chains to the system CA store and matches the host name; a wrong host name is rejected by `ssl.create_default_context()` | connected from here with OpenSSL and Python |
| R1-1 | Confirmed in the Python 3.12 source: `starttls()` with no context uses `ssl._create_stdlib_context()` (no certificate or host check) | read `smtplib.py` |
| AWS CLI and `--cli-input-json file:///dev/stdin` | **Rejected** ("Invalid JSON received") from a pipe, a here-string, `/dev/fd/0` and process substitution; a regular file works | ran CLI v2.35.17 against a local fake endpoint |
| `awscli` apt package on 24.04 | **None** (no candidate) | `apt-cache policy` |
| Lightsail instance metadata service for the public address | **Not verified**; the installer takes the address from an option or DNS if it is absent | needs a real instance |
| IAM `kms:Decrypt` with `kms:ViaService` on the AWS-managed SSM key, and SES `SendRawEmail` authorisation in the sandbox | **Not verified** | needs a real account |

## First install (the owner, once the VM exists)

The first release is verified by hand, with a public key you already know, before anything from it runs as root.

1. On your computer: download `treeline-vX.Y.Z.tar.gz` and its `.sig` from the GitHub Release. Verify with the public key you committed:
   `ssh-keygen -Y verify -f deploy/native/release_signers -I treeline-release -n treeline-release -s treeline-vX.Y.Z.tar.gz.sig < treeline-vX.Y.Z.tar.gz`
   (it must print "Good signature"). Copy both files to the VM (`scp`; SSH is open to your address only).
2. On the VM: `mkdir rel && tar -xzf treeline-vX.Y.Z.tar.gz -C rel && sudo ./rel/deploy/native/install.sh --domain app.treelinephone.com --state-device auto --release-repo OWNER/REPO` (use your GitHub owner and repository; `--public-ip` if the metadata service does not answer). It formats the attached disk **only if blank**, installs packages, and stops before starting the app because the VM key is missing.
3. On your computer: `infra/bootstrap/bootstrap.sh install-vm-key ubuntu@app.treelinephone.com`, then on the VM `sudo systemctl start treeline-api treeline-controller`, then `curl -fsS https://app.treelinephone.com/api/health`.
4. Later releases: tag `vX.Y.Z` on `main`; the release job (a reviewer approves) signs it; the VM's deploy agent picks it up in its window (default 09-12 UTC) when no call is in progress. `sudo treeline-deploy --version vX.Y.Z` does it now; `sudo treeline-deploy status` shows what is running.

**Rollback.** An unhealthy release rolls back by itself. If it had migrated data, the agent restores the data layer's pre-migration copies at the old version (all or nothing; refuses if one is missing). A manual `sudo treeline-deploy --rollback` is refused once the data layout moved: stop the services, restore from a backup with `infra/restore/restore.py` and the matching pre-migration copy, deploy the previous release.

**Restore drill** (do it before real families, and after any change to backups). On your computer, with your admin profile and the age private key: `python3 infra/restore/restore.py --bucket treeline-backups-<account>-us-west-2 --kind central --identity ~/treeline-backup.agekey --out ./restore` (and `--kind household --id N`). It prints row counts and says what it checked. It never writes over a live file.

## Owner checklist: what only the real account can do

1. Make the release signing key: `ssh-keygen -t ed25519 -N '' -f release-signing -C treeline-release`. Put the **public** line into `deploy/native/release_signers` as `treeline-release namespaces="treeline-release" <public key>` (own commit). Put the **private** file's contents into the `release` environment secret `RELEASE_SIGNING_KEY`, then delete the file. In GitHub: the `release` environment with you as required reviewer and deployment tags `v*`; tag protection for `v*`; Actions defaults read-only; secret scanning and push protection (docs/REPO_RULES.md).
2. Generate the backup key: `age-keygen -o treeline-backup.agekey`; keep the **file** in your password manager (without it no backup can be opened); paste only the `age1...` line to bootstrap.
3. Make a dead-man check at a healthchecks-style service (period 5 minutes, grace 15 minutes) and keep its https ping URL for bootstrap.
4. `AWS_PROFILE=... infra/bootstrap/bootstrap.sh apply` (first run against real IAM, SSM and the real CLI: read what it prints); then `infra/deploy.sh diff` and `infra/deploy.sh deploy` (first run against real CloudFormation and Lightsail; the bundle shown must still be what you want).
5. Request SES production access (until granted, SES sends only to verified addresses); check DKIM shows verified.
6. First install (above), then verify, writing down what you saw: the certificate was issued (`https://app.treelinephone.com`); `/api/health`; **a call between a phone on mobile data and a browser on another network with audio both ways** (this is the NAT check: `external_media_address`, `local_net`, `ice_host_candidates`, UDP 10000-10100); Asterisk memory during a call on the small bundle (`free -m`, swap use; resize if it swaps); the state disk really is a separate encrypted attached disk (`lsblk`, the Lightsail console) and nothing sensitive is on the system disk; a backup appears in S3 and the restore drill works; a deploy of a second release and a rollback; an alert email arrives; the dead-man alerts when you stop the timer; the Lightsail firewall shows only 22 (your address), 80, 443 and UDP 10000-10100 on IPv4 and nothing on IPv6; `ss -ltnu` on the VM shows nothing unexpected.
7. In Google Cloud Console make an OAuth client (type: web application) with the authorized redirect URI `https://app.treelinephone.com/api/auth/google/callback`; give its client ID and secret to `bootstrap.sh apply`, and note the beta access code it prints once. Then verify with a real account: a new person with the code, the same person signing in again, a grown-up a parent added signing in without the code, a stranger without the code turned away, and that the code stops working after `set beta_code` and a restart.
8. Record the results in README (Phase 4) and docs/SECURITY.md; delete the retired Docker files (`deploy/docker-compose.prod.yml`, `deploy/Caddyfile`, `deploy/asterisk/`).
9. Optional: `/treeline/beta_cidrs` (an allowlist for 443 and the call audio ports), `bootstrap.sh set beta_cidrs`, then `infra/deploy.sh deploy host`.
