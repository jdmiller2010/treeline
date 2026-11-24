# Treeline Admin

The page and the tools for the people who **run** Treeline (not for families): see and install releases, read the machine's logs,
look after treehouses, and add other admins, so that day-to-day operation does not need ssh. Designed 2026-11-23 from a read of the
code and an adversarial review of the design; this file is the record of what was decided and the rules the build must keep. It
says what is **built** and what is not yet (the "Status" table); do not read a design line as a shipped feature.

## Decisions (the owner's)

- **Releases and logs first, then treehouse and admin management; both get built.**
- **Install a release from the page:** the web app only writes a request holding a version; a small **root** service re-checks it
  (published, newer, signed) and runs the existing `treeline-deploy`. The web app never gets root.
- **Logs:** a root helper reads a fixed list of services, line-capped; each view is audited. Safe sources first (deploy, backup,
  health, Caddy, the bridge itself); the API and controller logs only after their call numbers and emails are removed at the source.
- **Removing a treehouse archives it for 14 days** (hidden, handsets cut off, cannot call), restorable; then erased. A family
  deleting its own data still erases at once. **Silent for now** (no email to the family); an optional notice later. *The designers
  advised a notice and a fixed reason list; the owner chose silent for now. Revisit before archive ships.*
- **Restore from backup:** the page generates the commands (`restore.py` on the owner's computer, `scp`, then a root tool on the VM
  that puts the verified file back). **No upload through the web app.** The VM holds no backup key and cannot read the bucket, by design.
- **An admin sees** a treehouse's name and number, created date, handset count, last check-in and the grown-ups' emails (on the detail page also each grown-up's role, parent or sitter, and each phone by position with its kind and last check-in: removing the right one needs them, and none is a name). Never calls,
  notes, strings, quiet hours, handset names, or anything in a family's file. No impersonation. An admin cannot add a person or a phone.
- **The admin is the owner's own parent email.** So every admin action needs a young session (12 hours at most), and destructive
  actions need a **fresh Google confirmation**: a round trip to Google in the same browser, for the same account, within 15 minutes
  (`prompt=select_account` with `login_hint`; Google cannot be made to ask for the password again, so there is no `auth_time`
  check: SECURITY.md Review 19).

## Rules the build keeps (each has a test)

1. Admin is an email in `app_admin`, never a role in `grown_up`; deleting a grown-up or a treehouse cannot change it.
2. The server is the only gate: every `/api/admin/*` route re-checks the table, and a non-admin gets what an unknown address gets (404).
3. `controller/treeline/admin.py` never imports `households`, never sets `g.th` or `g.gu`, never inserts a grown-up, handset, session,
   pairing or ladder code, and answers with explicit column lists. Source lint, key-set and route-snapshot tests enforce it.
4. Root treats the web app as hostile: a bridge request carries no path, URL, flag or free text, root opens everything without
   following links, and removes whatever is in a request folder whatever its type.
5. Log text is never stored; an audit row records the fact of a view, not its content. The audit holds ids and actions, never a
   family's name or a grown-up's email, and is trimmed after 365 days.
6. Every family-facing state this adds says Treeline never connects to 911.

## Status

| PR | What | State |
|---|---|---|
| 1 | Central migration (admin tables), the gate on `/api/admin`, `treeline-admin` (first admin over ssh) | built |
| 2 | The root bridge, safe logs, `install.sh` units (needs one `install.sh` run on the VM: the tools and units are not updated by a deploy) | built |
| 3 | The admin shell, menu item, Logs, Releases (read-only), Admins and Audit pages | built |
| 4 | Step-up (a fresh Google confirmation for the same account in the same browser; Review 19) and the destructive-action tier; adding and removing admins from the page | built |
| 5 | Release install from the page: the bridge `deploy` op (no change to the agent) and the Install button | built |
| 6 | Treehouse management: archive through every code path, archive, restore, the 14-day erase, remove a grown-up or a phone | built |
| 7 | Logging cleanup, then the API and controller log sources | not started |
| 8 | Restore commands and the VM-side restore tool | not started |

## Archive and rollbacks

The review worried that rolling back to a release that does not know `archived_at` would bring archived families back online. The data
layer's rule already prevents it: the column arrives with central step 3, and older code refuses a newer database (DATA_LAYER.md rule 3),
so the agent can only go back to such a release by restoring the pre-migration copy, which was taken before any archive existed. The one
loss: an archive made during the few minutes a just-migrated release is being health-checked is undone if that release is rolled back.

## Requirements the review added (not yet built; do not ship the PR they belong to without them)

- **Bridge (PR 2):** the app can plant a directory or a nest of them in a request folder; root must clear every entry whatever its
  type, with caps, and a VM test must plant them. Prefer a short systemd timer to a `.path` unit if the path unit's trigger limit
  can be tripped. Capabilities must be proven by the VM sandbox test. Results are deleted on first fetch and swept every few minutes.
  `status.json` and every log source go through control-character stripping and a leak grep (IPs, `@`, account and bucket patterns).
- **Install (PR 5):** an explicit `--version` must not change how the root agent downloads; split the agent change (a read-only
  `releases` command, then the flag) from the bridge op; share one ETag cache for the GitHub list; give the agent distinct exit codes
  for outside-window, calls-active and lock-held.
- **Archive (PR 6):** a rollback to a release that does not know `archived_at` would bring archived families back online: the agent
  must refuse that rollback while archived rows exist. An archived family can still delete its own data and leave. A pairing or
  string code aimed at an archived treehouse answers exactly like an unknown code. Archive hangs up live calls explicitly. The audit
  row's label is cleared when the treehouse is erased. A test runs every non-admin route as an archived member.
- **Admin identity (PR 4):** add-admin must not be possible with a stolen session alone (step-up, and a delay or second admin);
  record the Google `sub` and `email_verified` when an admin signs in.
- **Reads are audited** (detail views, and list pages past the first, with a count), and rate-limited tighter than family routes.
