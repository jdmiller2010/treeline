# Deploying Treeline

This puts Treeline on one small cloud machine so families can use it every day, on softphones or phone adapters. It follows Phase 4 of [PLAN.md](PLAN.md).

> **What has and hasn't been tested.** Everything here was written against the same Docker images and configuration that pass the project's tests on a development machine: the call rules, the API, the parent app, the softphone and real calls. The production pieces below (Caddy and Let's Encrypt, SIP over TLS, SRTP, the backup service, fail2ban) were **not** run on a public server, because the work was done without one. Expect to fix small things on first deploy, and read the logs.

## What you need

- A small virtual machine: 1–2 vCPU and 1–2 GB of memory is plenty for a pilot. Ubuntu 24.04. A public IPv4 address that doesn't change.
  - Oracle Cloud Always Free (ARM), AWS Lightsail (about $3.50–5 a month), Hetzner or DigitalOcean all work. Asterisk needs an always-on machine that accepts UDP, so serverless hosts won't do.
- A domain name, with an `A` record pointing at the machine, for example `phone.example.com`.
- An email service for sign-in codes (any SMTP account). Without one, no sign-in code is ever sent.

Open these ports, in the cloud firewall and `ufw` if you use it:

| Port | Why |
| --- | --- |
| 80/tcp, 443/tcp | Caddy: the website, the API and the secure WebSocket for softphones. Port 80 is for getting the certificate. |
| 5061/tcp | SIP over TLS, for phone adapters and the Treeline rotary phone |
| 10000–10100/udp | Call audio (encrypted) |

Don't open 8080 or 8088. The API and Asterisk's web server (which holds its REST interface, ARI) listen on `127.0.0.1` only. Caddy passes on `/ws` and nothing else from Asterisk.

## Install

```bash
sudo apt update && sudo apt install -y docker.io docker-compose-v2 git
git clone https://github.com/<you>/treeline.git && cd treeline
cp deploy/env.example deploy/.env      # then edit deploy/.env
```

In `deploy/.env` set `TREELINE_DOMAIN`, a long random `ARI_PASS` (`openssl rand -base64 36`), and your SMTP details. To get notifications on parents' phones, make a key pair and paste both lines in:

```bash
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env run --rm --no-deps --entrypoint python api make_vapid.py
```

Start Caddy first, so it can get the certificate Asterisk's TLS needs, then everything else:

```bash
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env up -d caddy
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env logs -f caddy     # wait for "certificate obtained"
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env up -d --build
```

Check it:

- `https://YOUR-DOMAIN/api/health` says `{"ok": true, ...}`.
- `https://YOUR-DOMAIN/parent/` shows sign-in. Sign in, set up a treehouse, and add a softphone.
- `docker compose ... logs controller` shows `connected; waiting for calls`.

## Softphones (on a tablet, phone or computer)

The softphone (`https://YOUR-DOMAIN/phone/`) **needs HTTPS** so the browser will let it use the microphone. That's why a plain `http://192.168.x.x` address from the development stack won't work on a tablet, even though `localhost` does. Deploying with a real domain is the simplest fix.

Set up each device once, then leave it (a dedicated tablet is the simplest, but any phone or computer with a browser works):

1. Open `https://YOUR-DOMAIN/phone/` in Chrome (Android) or Safari (iPad). Add it to the home screen and open it from there, so it runs full screen.
2. A parent scans the QR code, or types the six digits under Our treehouse, Add a phone, Softphone (app).
3. Keep it plugged in, with the screen kept on. The phone asks the browser to hold a wake lock; also set the tablet's own screen timeout to never.
4. Lock it to the app so kids can't leave it: on iPad turn on Guided Access (Settings, Accessibility); on Android use screen pinning. Treeline shows no menus and has nothing to sign out of.
5. The browser lets the phone ring only after one tap since it opened. If the tablet restarts, tap once ("Tap to turn the phone on").

A tablet that is closed, asleep or offline can't ring, and callers hear fast busy. Parents are emailed when a phone has been offline for 10 minutes.

## Backups

The `backup` service copies the central database and every household file (`data/households/<id>.db`) every night at 03:00 UTC into `data/backups/central/` and `data/backups/households/<id>/`, one file each, and keeps `BACKUP_KEEP_DAYS` days (7 by default, the same rule as the bucket in `infra/README.md`), by the timestamp in each file's name. A household that deleted its data stops being backed up and its folder rolls off within the week. Backups contain emails and call records: keep that folder as private as the database, and copy it off the machine (an `rsync` or object-storage job) so one lost disk doesn't lose everything.

To restore:

```bash
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env stop api controller backup
cp data/backups/treeline-YYYYMMDD-HHMMSS.db data/treeline.db
rm -f data/treeline.db-wal data/treeline.db-shm
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env start api controller backup
```

## Watching it

- Point an uptime monitor at `https://YOUR-DOMAIN/api/health`. It answers 200 when the database and Asterisk are fine, and 503 when Asterisk can't be reached. `deploy/uptime-check.sh` does the same from cron.
- If the server is down, softphones can't register and callers hear fast busy. Phone adapters should be set to play a fast-busy (reorder) tone when they aren't registered; see [ADAPTER.md](ADAPTER.md).
- Brute-force guessing at SIP passwords is limited by every handset having its own random secret. For more, `deploy/fail2ban/` has a filter and jail for Asterisk's log. They are **untested**; you also need Asterisk's log on the host (a `./logs:/var/log/asterisk` volume and a `[logfiles]` entry in `logger.conf`).

## Certificate renewal

Caddy renews the certificate by itself. Asterisk reads it when it starts and does not pick up a renewed one while running. Restart Asterisk about once a month, at night, from cron:

```
0 4 1 * *  cd /home/you/treeline && docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env restart asterisk
```

A restart drops any call in progress, so pick a quiet hour.

## Updating

```bash
git pull
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env up -d --build
```

The database changes itself to match (numbered migrations in `controller/treeline/db.py`), keeping your data. Take a backup first all the same.

## Before inviting families

- Read [PRIVACY and consent](PLAN.md#phase-4-deploy-and-pilot): every parent ticks a privacy box in setup, and the app has a plain-language page on what is stored, for how long and who sees it. Make sure the copy still matches what you do.
- The US children's privacy law (COPPA) may apply once families beyond friends and neighbors join. Get advice before that.
- Run through [PILOT.md](PILOT.md).

## Web pages on a static host (optional)

If you would rather host the parent app and softphone on Firebase Hosting or GitHub Pages, and keep only the API and Asterisk on the machine:

```bash
python3 scripts/build_static.py --api https://phone.example.com --out dist
```

Upload `dist/`. On the server set `TREELINE_CORS_ORIGINS=https://your-static-site.example` in `deploy/.env`. The build writes a Content-Security-Policy for Firebase in `dist/firebase.json`. Tablets still reach Asterisk through your server's `/ws`.

## Development stack versus production

The files at the project root (`docker-compose.yml`) are for a machine on your own network. They return sign-in codes in the API response to private addresses (`TREELINE_DEV_CODES=1`), use a default ARI password, listen on every address, and don't encrypt SIP. Never expose that stack to the internet.
