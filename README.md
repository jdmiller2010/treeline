# Treeline

*Safe calls for neighborhood kids.*

A house-to-house phone for kids who live near each other, with parents holding
the keys. Every household is a **treehouse** with one phone line and one
**4-digit number**. A kid lifts a real rotary phone (or a rotary phone on a
tablet), hears a dial tone, dials four digits, and the other treehouse's phone
rings. It only connects when both families' parents have approved a **string**
between their treehouses. It sounds like a 1960s phone, and it can't call 911
or any outside number.

This repository is the whole system: the call server, the parent app, the
softphone, and the plan for real phones. [docs/PLAN.md](docs/PLAN.md) is the
phased plan, [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) shows how it fits together (with diagrams); the status of each phase is below.

```
 softphone (WebRTC) ─┐
 phone adapter + rotary ─┼── SIP/WebRTC ──▶ Asterisk ──every call──▶ control app ──▶ SQLite (central + one file per treehouse)
 Treeline rotary phone ─┘                                   ▲                         ▲
                                           parent app ──▶ API ───────────────────────┘
```

## Status

| Phase | What | State |
| --- | --- | --- |
| 1 | **Platform core**: treehouses, numbers, strings, call rules, classic tones, call audit, API | Built and tested: 301 unit tests and 22 scripted SIP scenarios |
| 2 | **Parent app**: setup, strings, calls, quiet hours, phone book, settings, privacy | Built and tested in a real browser (286 checks; 6 widths, both themes) |
| 3 | **Rotary softphone** and several phones on one line | Built and tested with real browser softphones on real calls (35 checks, with audio; the softphone's screen 90) |
| 4 | **Deploy and pilot** | Backups, health check, push alerts and privacy are built. **AWS deployment** ([docs/DEPLOY_AWS.md](docs/DEPLOY_AWS.md)): the native install, signed releases, the deploy agent with rollback, encrypted backups with a restore drill, and the CDK app are written and tested **only in a CI job that imitates the VM** (40 tests: Ubuntu 24.04, systemd in Docker, fake SSM/S3, local ACME CA), 58 tests of the VM's tools, and 25 offline CDK assertions. Ten reviews are recorded in [docs/SECURITY.md](docs/SECURITY.md) (nine security reviews, the last an independent review of the Asterisk replacement, and a dependency audit); dependencies are listed and checked against known vulnerabilities every day, and updated mostly on their own ([docs/SUPPLY_CHAIN.md](docs/SUPPLY_CHAIN.md); the scheduled parts have not had their first run). **Never run on AWS or a public server: NAT and call audio, Let's Encrypt, SES, Lightsail's firewall and disk, real IAM.** Google sign-in with a beta access code is built and tested with a fake Google, never against the real one; the pilot hasn't happened. The older Docker plan is in [docs/DEPLOY.md](docs/DEPLOY.md) (retired for production); [docs/PILOT.md](docs/PILOT.md) |
| 5 | **A real rotary phone** through an adapter | Server side tested; guide written. **Not tried on an adapter.** See [docs/ADAPTER.md](docs/ADAPTER.md) |
| 6 | **Custom rotary phone** (ESP32-S3) | Server-side pairing built and tested. **No firmware or board.** See [docs/HARDWARE.md](docs/HARDWARE.md) |

## What the control app enforces

Every call is checked in this order (see `controller/treeline/rules.py`):

| Rule | What happens |
| --- | --- |
| **911** | The phone says it can't call 911 |
| A number that **isn't four digits** | "Your call cannot be completed as dialed" |
| The caller's line is **paused**, in **quiet hours**, out of **daily minutes** or **busy** | Fast busy (or busy) |
| Too many **calls to a number that isn't strung** (hunting) | Fast busy, and the parents get a note |
| The number doesn't exist | Three rising tones, "Your call cannot be completed as dialed" |
| **No live string** between the two treehouses | "You can't call that number from this phone. Ask a grown-up." The parents get a note |
| Too many **repeat calls** to one treehouse | Fast busy |
| The other line is **paused**, in **quiet hours** or out of minutes | "The treehouse you're calling isn't taking calls right now." (The same words for each, so one family's schedule isn't revealed) |
| The other line is **in use** | Busy |
| Nothing on the other line is **online** | Fast busy |
| Otherwise | Every phone on that line rings; the first to answer takes the call |

A call ends at the shorter of both treehouses' **call-length limits**, with three
pips a minute before. Another phone on a line can **join** a call in progress.
Every attempt, allowed or blocked, is written to the **call audit** with its
result. Audio is never recorded.

## Setup on Windows with WSL 3

### 1. Update WSL and install Ubuntu

In **PowerShell as Administrator**:

```powershell
wsl --update
wsl --version                      # should show WSL version 3.x
wsl --install -d Ubuntu-24.04
```

### 2. Let phones on your Wi-Fi reach it (mirrored networking)

So your cell phone's softphone can call in, WSL should share your PC's network
address instead of hiding behind its own NAT. Create or edit
`%UserProfile%\.wslconfig`:

```ini
[wsl2]
networkingMode=mirrored
```

Then allow SIP and call audio through the firewalls. In Administrator
PowerShell:

```powershell
# Windows Firewall
New-NetFirewallRule -DisplayName "KidPhone SIP+audio" -Direction Inbound `
  -Protocol UDP -LocalPort 5060,10000-10100 -Action Allow
New-NetFirewallRule -DisplayName "Treeline web" -Direction Inbound `
  -Protocol TCP -LocalPort 8080 -Action Allow

# Hyper-V firewall that sits in front of WSL in mirrored mode
Set-NetFirewallHyperVVMSetting -Name '{40E0AC32-46A5-438A-A0B2-2B479E8F2E90}' `
  -DefaultInboundAction Allow

wsl --shutdown                     # restart WSL so the setting applies
```

> **Check the WSL 3 docs for these settings.** This is the WSL 2 setup.
> If WSL 3 renamed the `.wslconfig` section or the networking mode, use the
> new names. If you only want the scripted test phones, skip this step;
> everything runs inside WSL.

### 3. Install Docker inside Ubuntu

WSL 3 includes its own container tool (`wslc`), but its Compose support is
still in development. This project uses the regular Docker Engine inside
Ubuntu:

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2
sudo usermod -aG docker $USER      # then close and reopen the Ubuntu window
```

### 4. Run it

Put the project in your Linux home folder (much faster than under `/mnt/c`):

```bash
git clone https://github.com/<you>/treeline.git ~/treeline
cd ~/treeline
./dev up                           # Asterisk, the control app and the API
```

The first time, `./dev up` builds the Asterisk that production runs, from the signed upstream source in a sealed container
(about a minute; [asterisk/build/README.md](asterisk/build/README.md)), then checks it against `asterisk/build/artifact.lock` before the
image is made. It needs Docker and nothing else.

Then open **http://localhost:8080/** (the parent app) and sign in. This is a
test server on your own network: it shows your sign-in code on the page, so no
email is needed. The softphone is at **http://localhost:8080/phone/**.

```bash
docker compose logs -f controller  # watch calls being allowed or blocked
```

## Tests

`./dev all` runs everything below in order (`./dev unit` for the unit tests); `./dev help` lists the individual commands (and takes a lock so two runs can't overlap).

| What | Command | Proves |
| --- | --- | --- |
| Unit tests | `docker compose run --rm --no-deps --entrypoint python controller -m unittest discover -s tests -t .` | The rules, the API, the database, backups |
| Scripted SIP phones | `docker compose run --rm testphones` | 22 scenarios: real SIP calls through Asterisk and the rules |
| Softphones | `docker compose run --rm webtests` | Two and three real browser softphones on real WebRTC calls, with audio |
| The softphone's screen | `docker compose run --rm webtests phone_ui.py` | Pairing and the dial |
| The parent app | `./dev ui smoke` | A local API on a throwaway database and a real browser; 286 checks across screens and widths, including the Google sign-in screen |
| The installable app | `./dev ui pwa` | The manifest, the service worker, the launcher and the install prompts |
| The VM's tools | `./dev native` | 143 tests: secrets, certificates, configuration rendering, signed releases (and the Asterisk build inside them: every way a hostile artifact could be built is refused), the deploy agent's logic (which build is running, when Asterisk restarts, what a rollback restores), backups and restore (backup tests need `age`) |
| The production install | `./dev vm` (CI skips it for a change that cannot affect it, such as a screen or a document: `scripts/ci_gate.py`) | 40 tests: the real `install.sh` and deploy agent on Ubuntu 24.04 with systemd in Docker: routing, ports, TLS, secrets, signed releases, rollback, backups. About 10 minutes; needs privileged Docker |
| AWS scripts and CDK | `./dev infra`, `./dev cdk` | `bootstrap.sh` and `deploy.sh` against a fake `aws`; the CDK templates' assertions and a real `cdk synth` (no AWS account) |

A passing scripted run ends with `22/22 scenarios passed`. The scripted tests
make a small world of treehouses numbered `01xx` (a range real families never
get) and remove it afterwards. Run them on a development database, not one with
real families in it.

> **If your Docker is Docker Desktop** (rather than Docker Engine inside
> Ubuntu), host-networked ports aren't reachable from the host itself, so run
> the browser tests through the `webtests` container as above.

## Try it with phones

**A softphone in a browser.** Open `http://localhost:8080/phone/` on the same machine
(a browser only lets a page use the microphone on `localhost` or over HTTPS, so
another device on your network needs the local HTTPS setup in [docs/LOCAL_HTTPS.md](docs/LOCAL_HTTPS.md)).
Or, from the parent app on that same device, press **Use this device as a phone** under Our treehouse: no code needed. Otherwise sign in to the parent app, then Our treehouse, Add a phone, Softphone (app), and type the
six digits the phone shows. The phone page shows your treehouse's name and what the phone is doing, with a card file of your strings' numbers beside the phone; **How to dial** walks a kid through it in pictures. Make two treehouses, string them with a ladder code,
and call one from the other. Each phone has a switch under Our treehouse (and on Home) to disconnect it for now: it stops ringing and can't call out, and your other phones carry on.

**A softphone on your cell phone** (SIP over UDP, on your Wi-Fi). In the parent
app add a **Phone adapter** (it gives you a user ID and password), then in
Linphone or Zoiper add a SIP account with that user ID and password, the domain
set to your PC's address, and transport UDP. Dial another treehouse's four digits.

## Where the data lives

One **central** SQLite database (`data/treeline.db`) holds what routing needs (treehouses, handsets, strings, sign-ins) and a short call ledger. Each treehouse also has **its own file** (`data/households/<id>.db`) with that family's call history, notes, audit log and consent, kept for the family's own retention (7 to 365 days). One family can be backed up, trimmed or deleted without touching another. Backups are one file each (`central/` and `households/<id>/`) and expire after 7 days. In production the files live on the VM's attached, encrypted disk (`/var/lib/treeline/data/`), and every hour each one is encrypted with `age` to a key only the owner holds and uploaded to S3, write-once ([docs/DEPLOY_AWS.md](docs/DEPLOY_AWS.md)). There is no upgrade path from the earlier single-file layout: `./dev clean` starts fresh. Rules, write order and the schema-migration process: [docs/DATA_LAYER.md](docs/DATA_LAYER.md).

## Files

```
docker-compose.yml        the development stack (Asterisk, control app, API, test containers)
asterisk/                 Asterisk image, config, indications (tones), operator messages
controller/treeline/      rules.py (the rules), calls.py (call engine), api.py (the API),
                          db.py (central SQLite, markers, migrations), households.py (one file per treehouse),
                          jobs.py (alerts, retention, reconcile), pjsip.py
controller/tests/         unit tests
testphones/               scripted SIP phones and the 22 scenarios
web/parent/               the parent app    web/phone/   the rotary softphone
web/shared/               API client and UI builders    web/tests/   browser tests
design/                   the design system (tokens, components, logo)
deploy/native/            production on the VM: install.sh, systemd units, config templates, the root-run tools
                          (deploy agent, secrets, certificates, backups, dead-man ping), the CI job that imitates the VM
deploy/                   also the retired Docker production files (kept until the first real deploy), fail2ban
infra/                    AWS: bootstrap.sh (IAM, SSM), the CDK app (Foundation and Host stacks), deploy.sh, restore
docs/                     PLAN, ARCHITECTURE, DATA_LAYER, DEPLOY_AWS, SECURITY, REPO_RULES, SUPPLY_CHAIN, INFRA_REVIEW_PLAN,
                          ADAPTER, HARDWARE, PILOT, LOCAL_HTTPS (DEPLOY is the retired Docker plan)
scripts/                  build_release.sh (signed releases), make_locks.sh (hash-pinned dependencies), build_web_assets.py,
                          build_licenses.py, build_static.py, check_repo_rules.py
.github/workflows/        repo rules, the VM imitation and unit tests, the signed release build
```

## Before this leaves your house

The files at the project root are for your own network only: sign-in codes
appear on the page, passwords are defaults, and SIP isn't encrypted. For
anything beyond that, use the production setup in [docs/DEPLOY_AWS.md](docs/DEPLOY_AWS.md):
HTTPS everywhere, sign-in with Google and a beta access code, SIP over TLS with SRTP, a private ARI,
unique passwords for every phone, and hourly encrypted backups. A deployed release refuses
to start with any of the development settings above.

## Next steps

Phases 1 to 3 are done. What's left needs things this repository can't supply:
the first deploy to the real AWS account (the owner checklist in [docs/DEPLOY_AWS.md](docs/DEPLOY_AWS.md)), real families for the pilot ([docs/PILOT.md](docs/PILOT.md)),
an adapter and a rotary phone to check [docs/ADAPTER.md](docs/ADAPTER.md)
against, and the hardware for [docs/HARDWARE.md](docs/HARDWARE.md). Also still
to do: record the operator messages (`asterisk/sounds/README.md`).

## Not an emergency phone

Treeline only connects treehouses on the Treeline. **It cannot call 911** or any
outside number, and outside numbers can't call in. Every phone, softphone and
the parent app must say so plainly. Kids need another way to reach help.

## License

Copyright (c) 2026 Jordan Miller.

- **Code:** [PolyForm Noncommercial 1.0.0](LICENSE). Use it, change it and share
  it for any noncommercial purpose, keeping the copyright notice. Making money
  from it needs permission: email jdmiller2010@gmail.com.
- **Design assets** (logo, art, icons, guidelines in `design/`):
  [CC BY-NC 4.0](design/LICENSE-ASSETS.txt), credit "Treeline by Jordan Miller".
  The Treeline name and logo aren't licensed as your own brand.
- **Third-party software** keeps its own licenses: see
  [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Because commercial use is restricted, Treeline is *source-available* rather than
"open source" in the OSI sense.

## Contact and support

Questions, ideas or bug reports: **jdmiller2010@gmail.com**

If Treeline helps your neighborhood, you can buy me a coffee:
**https://buymeacoffee.com/REPLACE-ME** *(link coming soon)*
