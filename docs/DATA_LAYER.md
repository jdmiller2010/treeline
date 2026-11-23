# Data layer: one central database and one file per treehouse

Status: **implemented on the `data-layer-split` branch** (unit tests, the SIP scenarios, both browser softphone scripts, the parent-app and installable-app browser tests and a manual two-family call were run against the dev stack; nothing has run on a public server or in S3, and `age` encryption is still deploy work). Decided with the owner: no migration from the old layout. This is the spec to implement before the first deployment
(see the deploy plan in `infra/README.md`). The "Spec review" section at the end lists what the first implementation pass corrected in this document.

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
5. Treehouse rows are never deleted, only marked (`left_at`, `deleted_at`), so a file name `<id>.db` normally
   means the same household. Two cases break that: a **rolled-back create** (SQLite gives the id out again,
   `AUTOINCREMENT` included, because `sqlite_sequence` rolls back too) and a **central database restored from a
   backup** that lost newer treehouses. So creating a household always **replaces** any file already at that
   name, and every household file records its own `treehouse_id` in `meta`; a file whose `meta` disagrees with
   its name is refused, never read.

## Where things live

Paths: the central database stays at `TREELINE_DB` (`/data/treeline.db` in development; `/var/lib/treeline/data/treeline.db` on the production VM, on the attached encrypted disk). Household files are in
`households/<id>.db` next to it (`TREELINE_HOUSEHOLDS_DIR` overrides). The same key shape is used for
local backups and S3: `central/<timestamp>.db` and `households/<id>/<timestamp>.db`
(plus `.age` once encrypted, at deploy time).

### Central (`treeline.db`)

| Table | Why it is central |
|---|---|
| `treehouse` | number lookup, name shown to other families, and the rules `decide()` reads for **both** sides of a call: time zone, quiet hours, paused, max call minutes, daily minutes, `system`, `left_at`, and the parent code's hash and lockout counters (`parent_pin_hash`, `pin_fails`, `pin_locked_until`: the phone's sign-in path needs them by handset). **Loses** `retention_days`, `ack_911`, `consent_at`, `consent_version` (they move to the household). **Gains** `deleted_at` (an explicit state: the name `(deleted)` is only what other families see) and uses `AUTOINCREMENT`. |
| `handset` | looked up by `sip_user`, by `provision_token`, and turned into the PJSIP file. Includes `online` and `last_seen`. |
| `string` | belongs to two households, so to neither. |
| `ladder_code` | redeemed by someone else's household, looked up by code. |
| `grown_up` | **an email is a lookup key** (sign-in, "already in a treehouse"), so it must be central. Splitting it would copy the email into both files and move nothing worth moving. Role and name stay with it (one owner). |
| `login_code`, `session`, `pairing`, `push_subscription`, `setting` | app-wide. |
| `call`, `call_event` | the **ledger**: live state of calls in progress and the recent record that limits are computed from (below). Pruned after `LEDGER_DAYS = 3` (at least two days are needed so a time zone's "today" is always in it), **only rows with `logged = 1`**: an unlogged call is waiting for reconcile and must not be pruned. Gains `logged INTEGER NOT NULL DEFAULT 0`. |

### Household (`households/<id>.db`)

| Table | Contents |
|---|---|
| `meta` (one row) | `treehouse_id`, `retention_days` (default 90), `ack_911`, `consent_at`, `consent_version`, `created_at`. Own `PRAGMA user_version` and migration list. |
| `call_log` | this family's copy of each finished call, same columns as `call` (keeps `describe_call`, `call_json`, the CSV export and every existing screen working), primary key = the ledger's call id. **Written redacted, see below.** |
| `call_event` | the events of those calls, primary key = the ledger's event id, `ON DELETE CASCADE` from `call_log`. Gains `theirs` (the event was the other family's handset; its id is not stored). |
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

**What each copy may contain (redaction happens when the copy is written, not when it is read).** The ledger
holds both sides' raw facts; a copy holds only what that family may see:

- the **caller's copy** never carries the callee's rules: reasons `callee_paused`, `callee_quiet` and
  `callee_daily_limit` are stored as `callee_unavailable` (this also closes R1-3: `call_json` can no longer
  return them, because they are not in the file); for `not_strung` the callee id is not stored, only the number the
  caller dialed; the callee's handset ids (`answered_handset`, events) are not stored;
- the **callee's copy** exists only if `visible_to_callee()` says so, and never carries the caller's handset id or
  the caller's handset ids in events;
- the read path applies `visible_to_callee()` again as a second check.

`visible_to_callee()` moves out of `api.py` into `households.py` (the write path cannot import `api`).

## Writes that touch two files

| Operation | Order | If it stops half way |
|---|---|---|
| Create treehouse | open a central transaction; insert `treehouse`; **create the household file with consent and 911 acknowledgement**; insert `grown_up`; commit | before commit the central rows roll back and the file is removed; if the process dies first an orphan file remains, and the next create of that id replaces it (rule 5) or reconcile removes it |
| Add grown-up / remove grown-up | central only | n/a |
| Finish a call | ledger update; household copies; `logged = 1` | `logged = 0` is picked up by reconcile |
| Change retention | household `meta`; **trim `call_log` now** | nothing to repair; the trim is idempotent |
| Notice / audit entry | household file only (skipped if that household has no file) | n/a |
| Delete all data | **one central transaction** (strings cut, sessions and grown-ups removed, ledger rows scrubbed as today, name set to "(deleted)", `deleted_at` set; today these are separate autocommits); then the notices to the other families; then delete the household file, its `-wal`/`-shm` and its `pre-migrate/` backups | an orphan file is removed by reconcile; the notice is lost, which is harmless (the other way round would announce a string that still exists) |
| Leave but keep records | the household's action-log entry first; then one central transaction as today (`left_at`, strings cut, handsets removed, grown-ups removed); then the notices to the other families. The file stays until its newest record (or `left_at`) is past retention, then the purge job deletes it with its `pre-migrate/` backups (action log included: nobody is left to read it) | n/a |

A notice for a treehouse that was deleted is not written (it has no file). One for a treehouse that has left is still
written to its file and goes with it (cheaper than a second copy of the `left` fact in `meta`, which would break rule 1).

Both the API and the controller (and its jobs thread and timer threads) write household files, as separate
processes and threads. A household file is therefore never opened with SQLite's create-if-missing mode except
by `create()`; every other open is `mode=rw`, so a stale handle can never re-create a deleted household as an
empty file.

### Reconcile (at startup, then hourly)

1. Household files whose treehouse row is missing or has `deleted_at` set, or whose `meta` disagrees with the
   file name: delete (with `-wal`, `-shm` and `pre-migrate/` leftovers).
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
  drops from 14 to 7 days to match, goes by the timestamp in the file name (not the file's mtime), and walks
  every `households/<id>/` directory in the backup folder, including those of households that no longer exist
  (otherwise a deleted family's last backups would never roll off). A household deleted while the backup runs
  is skipped, not a failure.
- The VM can only write backups. The S3 upload, `age` encryption and hourly schedule are deploy work.

## Showing older calls

The calls screen keeps today / week; "all" becomes paged. `GET /api/calls` accepts `before=<call id>`
and `limit` (default 50 for "all", 300 for today and week, max 300) and returns `more: true|false`; the parent app adds a
"Show older" button. Everything on disk is within the household's retention, so there is no archive tier.

## Starting fresh (no migration from the old layout)

Nothing is deployed and the dev data is disposable, so there is **no** upgrade path from the single-file
layout. The new layout is the baseline:

- The existing numbered steps in `db.py` (`MIGRATIONS`: eight entries, including the parent-code columns added
  after this spec was first written) are folded into the new `SCHEMA`, and the
  list starts empty. This is the one free chance to squash; after go-live, steps are never squashed
  while any database could still be below them.
- Each file type carries a marker: `PRAGMA application_id` = a fixed constant for central and another for
  household files, and `user_version` = the schema version (baseline = 1).
- A database without the marker (anything made before this change) is **refused at startup** with one clear
  line: "this is an old-layout dev database; run `./dev clean` to start fresh". It is never opened or
  guessed at ("not modified" means the main file's bytes are unchanged). A household file is refused the same way
  if it carries the central marker, an unknown marker, or a `meta.treehouse_id` that is not its file name.
- `./dev clean` cannot be the cure by itself if it opens the database through the same refusing code. So it
  empties a current-layout database through the application (every household through `households.remove()`, which
  is safe for processes that have the files open), and for an old-layout file it **stops the api and controller
  first**, removes the central file set and `households/`, and starts them again (never delete a database a
  process has open). The old `clean` also listed the long-dropped `number_rest` table and failed on it.

## The shipped central steps

| Step | Version | What | Release |
|---|---|---|---|
| 1 | 1 to 2 | `add_admin_tables`: `app_admin`, `admin_audit`, `session.created_at` (the app's operators, [ADMIN.md](ADMIN.md)). Expand only. | v0.3.0 (first real step; before it `MIGRATIONS` was empty) |

Household files have no steps yet (`HOUSEHOLD_MIGRATIONS` is empty).

## Schema changes after go-live

Once real families are on this, every schema change has to be safe on data that cannot be thrown away.
These rules apply to the central database and to household files alike.

1. **Numbered, append-only steps.** `MIGRATIONS` (central) and `HOUSEHOLD_MIGRATIONS` are lists. A step is
   never edited, reordered or deleted after it has shipped. The baseline is version 1; step *n* (1-based) takes
   the file from version *n* to *n + 1*. Each step and its `user_version` bump run in
   **one transaction** (`BEGIN IMMEDIATE`; SQLite DDL is transactional), and the version is re-read inside
   the transaction, so the API and the controller starting at the same moment cannot both apply a step.
   A step receives the connection and must use `execute`, never `executescript` (which commits). Creating a fresh
   file is the same kind of operation: markers and schema in one transaction, re-checked inside it.
   (Today's `migrate()` is neither transactional nor re-checked: fix it as part of this work.)
2. **Expand, then contract, across two releases.** Release N adds the new column or table and writes both;
   release N+1 stops reading the old one; release N+2 drops it. A release can be rolled back by the deploy
   agent only if its migration was expand-only, so a drop never ships in the same release as the code that
   stops using the column.
3. **Never open a database newer than the code.** If `user_version` is higher than the code knows, refuse to
   start and say so (this is what stops an old release from writing into a newer layout after a rollback of
   code but not data).
4. **Back up before migrating.** Before applying any pending step to a file, take an online backup of that
   file into `pre-migrate/` beside it (`0600`), and delete it after 7 days (it holds the same personal data as the
   file; "delete all my data" and the left-household purge delete a household's copies too). Recovery from a bad migration is: stop, restore that file, deploy the previous release.
5. **Central migrates at startup; households migrate lazily on first open, and are all swept at startup.**
   The sweep opens every household file once, so a failing step shows up when the deploy's health check
   runs, not when a family first opens the app. If a household's migration fails, that household gets a
   clear error and the rest keep working. `/api/health` reports `households_behind` and answers 503 while it is
   not 0 (a number nobody acts on would not make the deploy's health check "show up").
6. **Test against real old shapes.** Every new step ships with a test that builds a file at the *previous*
   schema (a fixture of CREATE statements and rows, not the current `SCHEMA` with a column removed), runs the
   step, checks the data survived and the version moved, runs it again (no-op), and kills it half way and
   reruns. The existing `controller/tests/test_db.py` migration tests are the pattern.
7. **Keep steps cheap.** A step runs while the app is down or a request waits on it. Big data rewrites are
   batched and resumable, and avoid `VACUUM` in a step.
8. **Cross-file changes follow the write-ordering table above**, and a step that changes how the two files
   relate (for example, moving a fact from central to a household) is a release of its own with a
   reconcile pass, not folded into another change.

## Code to change

- `db.py`: new baseline `SCHEMA` (moved columns and tables removed, `logged` and `deleted_at` added, old steps
  folded in), empty `MIGRATIONS`, one generic `prepare()` used for both file kinds (marker check and refusal,
  transactional re-checked migrations, newer-than-code refusal, pre-migration backup), `create_treehouse` without
  consent fields, a ledger-prune helper. `log_action` and `add_notice` **leave `db.py`** for `households.py`
  (`db.py` cannot import it back without a cycle) and take a treehouse id.
- New `households.py`: path, per-thread connection cache **validated against the file's inode** (a file
  deleted by another thread must not be written through a stale handle), an LRU cap (about 32 open files per
  thread, since the jobs thread visits every household), `create`, `conn`, `meta`, `remove`, the household
  schema and `HOUSEHOLD_MIGRATIONS` (empty at baseline), the startup sweep, `record_call`, `trim`, reconcile.
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
- `dev` (`clean_run`, `ui_reset`), `testphones/run_scenarios.py` and `web/tests/smoke.py` (they read and write
  `notice` and create treehouses directly), `controller/tests/helpers.py` (an isolated households directory) and
  the existing tests that read `notice`, `parent_action`, `retention_days` or `consent_*` from central.
- Docs: `README.md` (status and layout), `docs/PLAN.md` (Phase 4 data), `docs/SECURITY.md` (record the
  change; note R1-4 backups), `infra/README.md` (key layout, already matches), `CLAUDE.md` (Architecture:
  `db.py` paragraph).

## Tests (all must exist before merging)

Unit, runnable anywhere (`cd controller && python -m unittest discover -s tests -t .`, 172 pass before this work):

- ownership: a notice, audit entry and call copy land only in the right household file;
- isolation: family A's file never contains family B's blocked attempts, rules, or unstrung dials, and the
  caller's file never contains the callee's quiet hours, pause or daily limit as a reason (regression for the R1-3
  class of leak); a household file whose `meta` disagrees with its name is refused;
- both copies written, repeated write is a no-op, and a crash after the ledger update is repaired by reconcile;
- retention: lowering trims at once, per household, without touching the other family's copy;
- delete: file removed, other family's log shows "(deleted)", orphan file removed by reconcile, stale
  handle in another thread cannot write to a deleted file;
- leave: file kept until past retention, then removed;
- create treehouse: failure while creating the file leaves no central rows; failure after the file exists
  removes the file; a leftover file at a reused id is replaced, not inherited;
- an old-layout database (no marker) is refused with the `./dev clean` message and is not modified;
- a database whose `user_version` is newer than the code is refused;
- the migration runner: two threads starting at once apply a step once; a step that raises leaves the
  version unchanged and the data as it was; a pre-migration backup is taken and restores; a household
  below the current version is migrated on first open and counted by the startup sweep and by
  `/api/health`. (There are no real steps yet, so these use a test-only step list; the first real step
  must add its own fixture test per rule 6.)
- backup: one file per household, restores to a working database, prune at 7 days (including households that
  are gone), a household vanishing mid-run is skipped;
- pagination: `before` and `more`.

Needs the Docker stack (`./dev ...`) and was **not** run when this spec was written:

- `./dev unit`, `./dev check`, `./dev sip` (17 scenarios, ~7 minutes), `./dev web` (both scripts),
  `./dev ui smoke`, `./dev ui pwa`.
- After `./dev clean` (which must also remove `households/`), create two families, make a real call, and
  check that both families' history shows it and that each family's file holds only its own records.

## Not decided here

- Whether `provision_secret` should move out of `handset` (it is a plaintext secret, SECURITY.md R1-2).
- Scaling: jobs sweep every household each 20 seconds. Fine for hundreds. Past a few thousand, add a
  central "households with unsent notices" index.

## Spec review (first implementation pass)

The first draft was written without Docker and without running anything but the unit tests. Checked against the
code, these were wrong or missing, and are corrected above:

1. `MIGRATIONS` has eight entries (the parent-code columns were added after the spec), not five.
2. `log_action`/`add_notice` cannot stay in `db.py` (cycle); `visible_to_callee()` cannot stay in `api.py`.
3. "Ids are never reused" is false after a rolled-back create (even with `AUTOINCREMENT`) and after restoring
   central from a backup; create must replace a leftover file, and `meta` carries the id.
4. "Deleted" had no state of its own (only the display name), so reconcile could not tell deleted from left:
   `deleted_at` added.
5. The **caller's** copy would have carried the callee's quiet hours, pause and daily limit (`callee_quiet`...),
   the callee id of an unstrung dial, and the other family's handset ids. The spec only protected the callee's
   copy. Redaction happens at write time now.
6. `./dev clean` was named as the cure for an old-layout database but would hit the same refusal (and it already
   failed on the dropped `number_rest` table). It must stop the processes first for an old file, and remove
   household files through `households.remove()` otherwise.
7. Both the API and the controller write household files, so a stale-handle reopen must never create a file
   (`mode=rw`), deletion must take `-wal`/`-shm` with it, and `pre-migrate/` copies must go with a household.
8. DELETE `/api/treehouse` was a series of autocommits and wrote the other families' notices before the central
   change; it is one transaction and the notices follow it.
9. The ledger prune would have deleted unlogged calls; the health check would not have failed on a stuck
   migration; backup pruning would have ignored deleted households' folders and used mtime.
10. `rules.py` really needs no change to `decide()`; it keeps reading the central ledger.
