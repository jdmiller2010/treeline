# Treeline: server devspace

The server side of a Tin Can-style kids' phone network, ready to run on your
PC. Asterisk handles the calls. A small control app decides which calls may
connect, based on parent rules in `config/family.json`. Scripted fake phones
test the rules, and you can call in from a real softphone on your cell phone.

```
kid phone (softphone today, SIP adapter next, rotary phone later)
        │  SIP + audio
        ▼
   Asterisk ──every call──▶ control app ──reads──▶ config/family.json
                                │
                                └──writes──▶ data/calls.jsonl
```

## What the control app enforces

| Rule | Where it's set |
| --- | --- |
| **Mutual approval**: a call connects only if both households approved each other | `households.<name>.approves` |
| **Speed dials**: Sam presses `1` for Alex, `2` for Grandma | `phones.<ext>.speed_dials` |
| **Quiet hours**, per phone, for calling and being called | `phones.<ext>.quiet_hours` |
| **Pause** a phone instantly | `phones.<ext>.paused` |
| **Time limit** per call, with a warning beep before hanging up | `phones.<ext>.max_call_minutes` |
| **Call log** of every attempt, allowed or blocked, with the reason | `data/calls.jsonl` |

The rules file is re-read on every call, so edits take effect immediately.
No restart needed.

The sample network has four phones:

| Ext | Name | Household | Password (dev only) |
| --- | --- | --- | --- |
| 1001 | Sam | jordan | dev-1001 |
| 1002 | Alex | alex | dev-1002 |
| 1003 | Riley | riley | dev-1003 |
| 1004 | Grandma | grandma | dev-1004 |

Riley's household hasn't approved anyone yet, so Riley's calls are blocked.
That's on purpose, to show mutual approval working.

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
docker compose up -d --build       # Asterisk + control app
docker compose run --rm testphones # scripted test calls
docker compose logs -f controller  # watch calls being allowed or blocked
```

A passing run ends with `9/9 scenarios passed`.

## Call in from your cell phone

1. Install **Linphone** (free, iOS and Android). Zoiper works too.
2. Find your PC's Wi-Fi address: `ipconfig` in PowerShell, under "IPv4 Address".
3. Add a SIP account in Linphone:
   - Username: `1004` (Grandma), password: `dev-1004`
   - Domain: your PC's IPv4 address, for example `192.168.1.50`
   - Transport: **UDP**
4. Set up a second softphone as Sam (`1001` / `dev-1001`). Linphone also
   runs on Windows, or use another phone or tablet.
5. From Grandma's phone, dial **1** (Grandma's speed dial for Sam). Sam's
   phone rings. From Sam's phone, **2** calls Grandma.

Try changing `config/family.json` while you test: pause Sam, set quiet hours
to now, or remove an approval. The next call follows the new rules.

## Scripted test scenarios

| Scenario | Checks |
| --- | --- |
| `approved_call` | Sam presses 1 (Alex): both houses approved, so it connects |
| `one_sided_approval` | Sam presses 3 (Riley): Riley's house hasn't approved, so it's blocked |
| `stranger_calls_in` | Riley dials Sam directly: blocked |
| `unknown_number` | Sam dials a number not on the network: blocked |
| `paused_phone` | Alex's phone is paused: blocked |
| `quiet_hours` | Sam's quiet hours cover right now: blocked |
| `grandma_call` | Sam presses 2 (Grandma): connects |
| `time_limit` | A 9-second limit cuts the call off on time |
| `callee_offline` | Alex's phone is unplugged: the call fails cleanly |

Run one: `docker compose run --rm testphones time_limit`

The test phones are baresip with a test tone as their "voice", so no sound
card is needed. Scenarios that change the rules restore them afterward.

## What has been tested

All 9 scenarios pass against **Asterisk 20.6 and baresip 1.0 from the Ubuntu
24.04 packages**, the same versions these Docker images install, with these
exact config files and scripts. The Docker images themselves weren't built
in that test environment, because it couldn't reach Docker Hub. If a build
fails on your machine, that's the first place to look.

## Files

```
docker-compose.yml       the three services
asterisk/config/         PJSIP accounts, dialplan, ARI (control-app login)
controller/app.py        the parent-rules engine (Python, ~300 lines)
config/family.json       households, phones, approvals, speed dials, limits
testphones/              scripted fake phones and test scenarios
data/calls.jsonl         call log (created on first call)
```

## Before this leaves your house

These settings are for a private test network only:

- **Passwords:** change every `dev-*` password and the ARI password.
- **Encryption:** turn on TLS for SIP and SRTP for audio, so calls are encrypted.
- **Ports:** don't expose ARI (port 8088) to the internet.

## Next steps

The full phased plan is in **[docs/PLAN.md](docs/PLAN.md)**:

1. **Platform core:** treehouses, 4-digit numbers, strings, classic phone sounds and a full call audit (replaces speed dials).
2. **Parent app:** setup, strings, rules, calls and the phone book, built from `design/`.
3. **Tablet rotary softphone** and several handsets on one line.
4. **A real rotary phone** through a SIP adapter (Grandstream HT801).
5. **Deploy and pilot** with 2–3 friend families.
6. **Custom rotary phone:** ESP32-S3, ES8388 codec and AG1171 SLIC.

## Hosting later

- **Parent web app:** Firebase Hosting or GitHub Pages can host it for free.
- **Asterisk:** can't run on Firebase, GitHub or Cloud Run. It needs an
  always-on machine that accepts UDP, so plan on a small VM:
  - **Oracle Cloud Always Free:** an ARM VM at no cost (recently cut to
    2 OCPU / 12 GB). Capacity can be hard to get, and idle VMs can be
    reclaimed.
  - **AWS Lightsail:** about $3.50–5/month, often with 3 months free.
  - **Any $5/month VPS:** for example Hetzner or DigitalOcean.

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
