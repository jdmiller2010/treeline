# Data layer: one central database and one file per treehouse

Status: **design, not yet implemented.** This is the spec to implement before the first deployment
(see the deploy plan in `infra/README.md`). Nothing here has been built or run.

## Why

- A household's own records (call history, notes, audit log, consent) live in **their own SQLite file**.
  Backing up, restoring, trimming and deleting one family never touches another family's data.
- The **central database** holds only what the app needs to route calls and find a household from an
  outside key (a number, an email, a SIP user, a code).
- Call history gets the household's own **retention** (7 to 365 days), enforced by trimming their file.

What this does *not* do: it does not make deletion instant in backups. Every backup (central and
household) expires after 7 days, and the VM has no permission to delete backups (`infra/README.md`).
"Delete all my data" deletes the live files at once and the backups roll off within the week.

## Rules

1. **One owner per fact.** A fact lives in exactly one file. If a second file needs it for lookup, that
   copy is an index that can be rebuilt, and the doc says which file wins.
2. **No transaction spans two files.** No `ATTACH`. SQLite does not make a write across files atomic
   in WAL mode. Every operation that touches two files is ordered so a crash leaves something harmless
   and repairable (see "Writes that touch two files").
3. **Access follows the central database.** A household file can only ever have *extra* data after a
   crash, never be the thing that grants access.
4. **Never leak across households.** A household file contains only what that family may see. The
   callee's copy of a call is written only if `visible_to_callee()` says so, and the read path keeps the
   same filter as a second check.
5. Treehouse ids are never reused (rows are never deleted, only marked), so a file name `<id>.db`
   always means the same household.

## Where things live

Paths: the central database stays at `TREELINE_DB` (`/data/treeline.db`). Household files are in
`households/<id>.db` next to it (`TREELINE_HOUSEHOLDS_DIR` overrides). The same key shape is used for
local backups and S3: `central/<timestamp>.db` and `households/<id>/<timestamp>.db`
(plus `.age` once encrypted, at deploy time).

### Central (`treeline.db`)

| Table | Why it is central |
|---|---|
| `treehouse` | number lookup, name shown to other families, and the rules `decide()` reads for **both** sides of a call: time zone, quiet hours, paused, max call minutes, daily minutes, `system`, `left_at`. **Loses** `retention_days`, `ack_911`, `consent_at`, `consent_version` (they move to the household). |
| `handset` | looked up by `sip_user`, by `provision_token`, and turned into the PJSIP file. Includes `online` and `last_seen`. |
| `string` | belongs to two households, so to neither. |
| `ladder_code` | redeemed by someone else's household, looked up by code. |
| `grown_up` | **an email is a lookup key** (sign-in, "already in a treehouse"), so it must be central. Splitting it would copy the email into both files and move nothing worth moving. Role and name stay with it (one owner). |
| `login_code`, `session`, `pairing`, `push_subscription`, `setting` | app-wide. |
| `call`, `call_event` | the **ledger**: live state of calls in progress and the recent record that limits are computed from (below). Pruned after `LEDGER_DAYS = 3`. Gains `logged INTEGER NOT NULL DEFAULT 0`. |

### Household (`households/<id>.db`)

| Table | Contents |
|---|---|
| `meta` (one row) | `treehouse_id`, `retention_days` (default 90), `ack_911`, `consent_at`, `consent_version`, `created_at`. Own `PRAGMA user_version` and migration list. |
| `call_log` | this family's copy of each finished call, same columns as `call` (keeps `describe_call`, `call_json`, the CSV export and every existing screen working), primary key = the ledger's call id. |
| `call_event` | the events of those calls, primary key = the ledger's event id. |
| `notice` | notes for the parents (alerts, requests). Pruned at 90 days. |
| `parent_action` | the audit log of what grown-ups changed. Pruned at 365 days. |

Moving `notice` and `parent_action` here means a family's personal records are in one deletable file.
Other families still cause notices (a string request, "approved", "number changed"): that is a single
insert into the other household's file, written by the central-side code.

## Calls: the ledger and the two copies

`decide()` needs, for the caller **and** the callee, who is on a call right now, minutes talked today,
and recent attempts. That is cross-household and short-lived, so it stays in the central `call` ledger
exactly as now. `rules.py` does not change.

The family-facing history is a **copy per side**:

- When a call ends (or a blocked attempt is recorded), the engine writes the copy into the caller's
  `call_log` and, if `visible_to_callee()`, the callee's. `INSERT OR IGNORE` by call id, so it can be
  repeated safely. Then it sets `call.logged = 1`.
- A reconcile job writes any ended call with `logged = 0` (a crash between the ledger update and the
  copies, or a server restart that ended open calls). It skips a household whose file is gone, and then
  sets `logged = 1`.
- Each family's retention trims **its own** `call_log` and `call_event` (replacing the "null out my side"
  logic in `jobs.purge`). Nobody's retention affects anyone else's copy.
- The other treehouse is stored as an id and its name is looked up live, as now, so when a family deletes
  its data its name in other families' logs becomes "(deleted)".

## Writes that touch two files

| Operation | Order | If it stops half way |
|---|---|---|
| Create treehouse | open a central transaction; insert `treehouse`; **create the household file with consent and 911 acknowledgement**; insert `grown_up`; commit | before commit the central rows roll back; an orphan household file may remain and is overwritten on a later create or removed by reconcile |
| Add grown-up / remove grown-up | central only | n/a |
| Finish a call | ledger update; household copies; `logged = 1` | `logged = 0` is picked up by reconcile |
| Change retention | household `meta`; **trim `call_log` now** | nothing to repair; the trim is idempotent |
| Notice / audit entry | household file only (skipped if that household has no file) | n/a |
| Delete all data | central first (strings cut, sessions and grown-ups removed, ledger rows scrubbed as today, name set to "(deleted)"); then delete the household file | an orphan file is removed by reconcile |
| Leave but keep records | central as today (`left_at`, strings cut, handsets removed, grown-ups removed); the file stays until its newest record is past retention, then the purge job deletes it (action log included: nobody is left to read it) | n/a |

### Reconcile (at startup, then hourly)

1. Household files with no matching, non-deleted treehouse: delete.
2. Active treehouses with no household file (central restored from a backup): recreate empty with default
   retention, consent unset, and log a warning.
3. Ended calls with `logged = 0`: write the copies.
4. Left treehouses past retention: delete the file.

## Retention and backups

- Retention is 7 to 365 days per household (already validated by the API). Lowering it trims the live
  file immediately. The parent app warns on lowering: "Calls older than N days will be removed from
  Treeline right away. Copies in our backups can take up to a week to disappear."
- Backups: one rule, 7 days, for both `central/` and `households/` (hourly 3 days, daily 7 days is
  optional; one 7-day rule is the default). `backup.py` backs up the central file and every household
  file with SQLite's online backup, one file each, into the key layout above. Local pruning default
  drops from 14 to 7 days to match.
- The VM can only write backups. The S3 upload, `age` encryption and hourly schedule are deploy work.

## Showing older calls

The calls screen keeps today / week; "all" becomes paged. `GET /api/calls` accepts `before=<call id>`
and `limit` (default 50 for "all", max 300) and returns `more: true|false`; the parent app adds a
"Show older" button. Everything on disk is within the household's retention, so there is no archive tier.

## Migrating an existing single-file database

One new central migration step (the numbered `MIGRATIONS` list; never edit old steps), run once:

1. Copy the database to `treeline.db.pre-split` with SQLite's backup API (first time only). It is a
   plain copy of everything: delete it once the upgrade is verified.
2. For each treehouse, create its household file and copy in `meta` (from the old `treehouse` columns),
   its `notice` and `parent_action` rows, and the calls it was part of (`call` + `call_event`, applying
   `visible_to_callee` to the callee side). All with idempotent inserts keyed by the old ids, so the
   step can be repeated after an interruption.
3. In **one central transaction**: delete ledger rows older than `LEDGER_DAYS` (mark the rest
   `logged = 1`), drop `notice` and `parent_action`, drop the four moved `treehouse` columns, set
   `user_version`.

Only the dev database holds data today; nothing is deployed. The step still needs a real upgrade test.

## Code to change

- `db.py`: remove moved columns and tables from `SCHEMA` for new databases, add the migration, change
  `create_treehouse` (no consent fields), `log_action` and `add_notice` (take a treehouse id, write to the
  household), add a ledger-prune helper.
- New `households.py`: path, per-thread connection cache **validated against the file's inode** (a file
  deleted by another thread must not be written through a stale handle), an LRU cap (about 32 open files per
  thread, since the jobs thread visits every household), `create`, `conn`, `meta`, `remove`, the household
  schema and migrations, `record_call`, `trim`, reconcile.
- `api.py`: `th_json` reads retention from `meta`; `treehouse_create`, `treehouse_update`
  (retention), `treehouse_delete`, `treehouse_leave`, `home`, `notice_dismiss`, `calls_for`, `call_json`,
  `call_detail`, `calls_csv`, `actions_list`, `audit`, and the `add_notice` calls.
- `calls.py`: write the household copies at finish and on blocked attempts; `add_notice` for 911 and
  unstrung notes.
- `jobs.py`: `check_handsets` notices, `send_alert_emails` (iterate households), `purge` (ledger, per-household
  retention, notice and audit age, left households), reconcile.
- `backup.py`: one file each for central and households, new layout, 7-day prune.
- `run_controller.py`: run reconcile at startup.
- `web/parent/js/account.js`: the retention warning; the calls screen: "Show older".
- `dev` (`clean_run` lists the tables to empty: it must also delete household files), 
  `testphones/run_scenarios.py` and `web/tests/smoke.py` (they read and write `notice` directly).
- Docs: `README.md` (status and layout), `docs/PLAN.md` (Phase 4 data), `docs/SECURITY.md` (record the
  change; note R1-4 backups), `infra/README.md` (key layout, already matches), `CLAUDE.md` (Architecture:
  `db.py` paragraph).

## Tests (all must exist before merging)

Unit, runnable anywhere (`cd controller && python -m unittest discover -s tests -t .`, 161 pass today):

- ownership: a notice, audit entry and call copy land only in the right household file;
- isolation: family A's file never contains family B's blocked attempts, rules, or unstrung dials
  (regression for the R1-3 class of leak);
- both copies written, repeated write is a no-op, and a crash after the ledger update is repaired by reconcile;
- retention: lowering trims at once, per household, without touching the other family's copy;
- delete: file removed, other family's log shows "(deleted)", orphan file removed by reconcile, stale
  handle in another thread cannot write to a deleted file;
- leave: file kept until past retention, then removed;
- create treehouse: failure while creating the file leaves no central rows;
- migration: build a database with the **old** schema and real-looking data, upgrade it, check every
  household file, check the central tables, run it twice, and kill it after step 2 and rerun;
- backup: one file per household, restores to a working database, prune at 7 days;
- pagination: `before` and `more`.

Needs the Docker stack (`./dev ...`) and was **not** run when this spec was written:

- `./dev unit`, `./dev check`, `./dev sip` (17 scenarios, ~7 minutes), `./dev web` (both scripts),
  `./dev ui smoke`, `./dev ui pwa`.
- A dev database that already holds a family, upgraded in place, then a real call and a check that both
  families' history shows it.

## Not decided here

- Whether `provision_secret` should move out of `handset` (it is a plaintext secret, SECURITY.md R1-2).
- Scaling: jobs sweep every household each 20 seconds. Fine for hundreds. Past a few thousand, add a
  central "households with unsent notices" index.
