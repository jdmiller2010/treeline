# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Treeline: a house-to-house phone network for kids, with parents holding the keys. Each household is a **treehouse** with one line, one 4-digit number, and any number of handsets. Calls connect only over a **string** both families approved. No 911, no outside numbers, no recording. [docs/PLAN.md](docs/PLAN.md) is the phased plan and the source of the decisions; [README.md](README.md) has the status of each phase and the setup. The README says plainly which parts were never run on real hardware or a public server (Phase 4 deploy, Phase 5 adapter, Phase 6 firmware): don't describe them as tested.

## Commands

The stack runs in Docker Compose with host networking. On Docker Desktop, host-networked ports aren't reachable from the host, so run anything that needs Asterisk or the API inside a container.

```bash
docker compose up -d --build                       # asterisk, controller, api (http://localhost:8080 inside the VM)
docker compose logs -f controller                  # watch calls

# unit tests (always build first; the image bakes the code in)
docker compose build controller
docker compose run --rm --no-deps --entrypoint python controller -m unittest discover -s tests -t .
docker compose run --rm --no-deps --entrypoint python controller -m unittest tests.test_rules   # one module

docker compose run --rm testphones [scenario ...]  # real SIP calls via baresip (17 scenarios; --list)
docker compose run --rm webtests [script.py]       # browser tests in the stack: phone_calls.py (default), phone_ui.py, smoke.py
```

- Tests must never touch the dev database: `controller/tests/helpers.py` forces a temp DB and a fake Asterisk. Scripted tests build and remove treehouses numbered `01xx`.
- Rebuild the `api` and `controller` images after Python changes (`docker compose up -d --build api controller`). `web/` and `design/ui` are mounted, so edits show on reload. Asterisk config changes need `docker compose restart asterisk`.
- The parent app's browser test (`web/tests/smoke.py`) runs best against a local API on a throwaway DB; its header explains how. It needs Playwright.
- Regenerate after the design kit or notices change: `python3 scripts/build_web_assets.py` (icons/art/brand into `web/shared/assets.js`) and `python3 scripts/build_licenses.py` (licenses pages from `THIRD_PARTY_NOTICES.md`).

## Architecture

- **Asterisk never routes on its own.** `asterisk/config/extensions.conf` sends every handset call into `Stasis(treeline)` (ARI). PJSIP accounts for handsets are **generated** from the database into `/generated/pjsip_handsets.conf` by `treeline/pjsip.py`, then Asterisk is told to reload (ARI `PUT /asterisk/modules/res_pjsip.so`; POST *loads*). Asterisk stores only md5 digests (`md5_cred`) of handset secrets. `[global] default_realm` must equal `SIP_REALM` or browser phones can't sign in.
- **`controller/treeline/rules.py`**: `decide()` is the whole call flow, pure logic over the DB (see the README table for the order). Daily minutes, quiet hours (own time zone, per-night days), repeat/hunting limits, busy and offline are all here. Quiet-hours and paused reasons are kept distinct in the audit but sound the same to the caller.
- **`calls.py`** is the ARI call engine: ring every online handset, bridge the first to answer, limit timers with pips, join a call in progress by dialing `0001`, full audit in `call` and `call_event`. It runs on the websocket thread plus timer threads, so it uses `db.local_conn()` (SQLite connections are per-thread). Tones are **named** in `asterisk/config/indications.conf` and played as `tone:<name>`: never put a raw tone string in an ARI `media` list, its commas split the list.
- **`api.py`** (Flask) is everything the apps need: email-code sign-in, treehouse, strings (ladder codes, both families approve), handsets, QR/code pairing, adapter settings XML, call log and CSV, push, factory device registration, and it serves the web pages with a CSP. A call involves two families, so what each sees is filtered (`visible_to_callee`, `describe_call`): never leak the other family's quiet hours, rules or unstrung attempts.
- **`db.py`**: SQLite, WAL. New columns go in the numbered `MIGRATIONS` list (never edit old steps; `CREATE TABLE IF NOT EXISTS` doesn't alter). `jobs.py` runs handset check-ins, alert email and push, and retention (one family's retention removes only *its side* of a call).
- **`web/`**: framework-free ES modules. `web/shared/ui.js` builds the design system's exact markup; its `html` tag escapes everything, and button `attrs` must be an **object** when any value comes from data (a string is raw HTML). `web/parent/` is the hash-routed parent app; `web/phone/` is the tablet rotary phone (JsSIP, Web Audio tones, a dial you really turn). Vendored libraries are in `web/phone/vendor/` and listed in `THIRD_PARTY_NOTICES.md`.
- **`deploy/`** is production: Caddy for TLS (only `/ws` reaches Asterisk; ARI stays on localhost), an Asterisk overlay with TLS SIP and SRTP, backups, fail2ban. Untested on a public server.

## UI work

Follow [design/CLAUDE.md](design/CLAUDE.md) and build from `design/ui` (tokens, components, the four page templates, both themes). Every screen sits in the shell or `.tl-root`; one `h1`; at most one primary button; the footer line and the plain "can't call 911" statement where the design requires them. Test at 360, 390, 768, 1024, 1280 and 1440 in both themes. Known kit issue: at narrow widths `.tl-card--breeze`'s extra right padding is overridden, so keep breeze titles short.

## Notes

- Dev passwords and the dev ARI login (`treeline` / `treeline-dev`) are for a private network only. `TREELINE_DEV_CODES=1` returns sign-in codes (to private addresses only): never in production.
- No 911, said plainly: every phone, the softphone and the parent app must state it (see docs/PLAN.md, "Safety and no 911").
- Code is PolyForm Noncommercial 1.0.0 ([LICENSE](LICENSE)); design assets are CC BY-NC 4.0; third-party licenses are in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Add a dependency there when you add it.
- The code-review findings fixed so far are all covered by tests; keep it that way (a bug found by hand or by review gets a regression test).
