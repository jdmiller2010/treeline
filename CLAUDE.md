# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## UI work

Follow design/CLAUDE.md and build screens from design/ui (plain-HTML kit: tokens, components, page templates). There is no parent app yet; it is Phase 2 of the plan.

## What this is

Server side of a kid-safe phone network (Tin Can style). Asterisk handles SIP calls; a Python control app decides which calls may connect based on parent rules in `config/family.json`. See [README.md](README.md) for WSL setup and softphone instructions, and [docs/PLAN.md](docs/PLAN.md) for the phased development plan.

**Current vs. planned:** the code below is the pre-Phase-1 devspace (phones, speed dials, `family.json`). [docs/PLAN.md](docs/PLAN.md) replaces it with treehouses, 4-digit numbers, approved "strings", SQLite, a REST API for the parent app, classic phone sounds and a full call audit. Speed dials go away. Check the plan before extending the rules engine or the data model.

## Commands

Everything runs through Docker Compose (host networking; Asterisk, controller and test phones all share the host network):

```bash
docker compose up -d --build        # start Asterisk + controller
docker compose logs -f controller   # watch calls allowed/blocked
docker compose run --rm testphones  # run all scenarios (passing = "9/9 scenarios passed")
docker compose run --rm testphones time_limit   # run one scenario
docker compose run --rm testphones --list       # list scenarios
```

There is no linter or unit-test suite; the scripted scenarios are the tests and need the full stack running.

## Architecture

- **Asterisk never routes on its own.** [asterisk/config/extensions.conf](asterisk/config/extensions.conf) sends every call from the `from-phones` context (set on all PJSIP endpoints in `pjsip.conf`) into `Stasis(kidphone)`, i.e. ARI.
- **[controller/app.py](controller/app.py)** is an ARI websocket client and the whole rules engine. `decide(caller, dialed, rules)` returns `(callee, reason)`; `reason` is `None` when allowed. Order of checks: caller paused → caller quiet hours → speed-dial resolution → unknown number → mutual household approval → callee paused → callee quiet hours. `Call` tracks bridging, the time-limit timer and warning beep. Every attempt (allowed or blocked, with reason) is appended to `data/calls.jsonl`.
- **[config/family.json](config/family.json)** is re-read on every call, so rule edits apply immediately with no restart. Approval is mutual and per-household (`households.<h>.approves` lists phone extensions); phones carry `speed_dials`, `quiet_hours`, `max_call_minutes`, `paused`.
- **[testphones/run_scenarios.py](testphones/run_scenarios.py)** drives baresip instances (test tone, no sound card) as the four sample phones, places calls through Asterisk, then asserts on the entries the controller wrote to the call log. Scenarios that mutate `family.json` restore it afterward.

## Keeping things in sync

Adding or changing a phone touches several places: the extension and `dev-*` password in `asterisk/config/pjsip.conf`, the entry in `config/family.json`, and the `PHONES` table (with a unique local port) in `testphones/run_scenarios.py`. ARI credentials (`kidphone` / `kidphone-dev`) are in both `asterisk/config/ari.conf` and the controller env in `docker-compose.yml`.

## Notes

- Dev passwords and ARI creds are placeholders for a private network only.
- `data/*.jsonl` is gitignored.
- README states the Docker images haven't been built in the original test environment; a build failure is a plausible first thing to check.
- **No 911, said plainly.** Treeline cannot call 911 or any outside number, and every phone, softphone and the parent app must say so (see docs/PLAN.md, "Safety and no 911").
- Code is PolyForm Noncommercial 1.0.0 ([LICENSE](LICENSE)); design assets are CC BY-NC 4.0; third-party licenses are in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
