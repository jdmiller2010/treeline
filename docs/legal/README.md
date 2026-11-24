# Treeline legal documents

| File | What it is | Public page |
|---|---|---|
| [terms.md](terms.md) | Terms of Service | `/legal/terms/` |
| [privacy.md](privacy.md) | Privacy Policy, including the kids' privacy (COPPA) section | `/legal/privacy/` |
| [acceptable-use.md](acceptable-use.md) | Acceptable Use Policy | `/legal/acceptable-use/` |

These markdown files are the only source. `scripts/build_legal.py` turns each one into a page under `web/legal/`, and `./dev check` regenerates them and fails if the committed pages are stale. HTML comments (the `TODO(Jordan)` notes) are dropped from the pages, but they are still public in this repository, so write nothing in them you wouldn't post.

These documents are adapted from the [Basecamp open-source policies](https://github.com/basecamp/policies), which are licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The license requires the credit line at the bottom of each file. Keep it. The same credit is on the open-source licenses page (`THIRD_PARTY_NOTICES.md`). These policy texts are under CC BY 4.0, not Treeline's code license.

## Status

**Not reviewed by a lawyer yet.** The kids' privacy section and the liability clause need that review before the beta grows past friends and family.

The operator is Jordan Miller personally for now. Running Treeline under an LLC (for example StrataGuild LLC) would put a company between the service and personal assets. If that happens, change the "we" line in all three files, the trademark line in terms.md, and the contact details.

## Open items

Search for `TODO(Jordan)` in these files.

1. **Lawyer review** (see Status).
2. **Operator** (see Status).
3. **Contact email.** Every page uses the maintainer's own address (`CONTACT` in `web/shared/ui.js`). A dedicated address such as privacy@ or hello@treelinephone.com would need an update there and in every mailto link here.
4. **Encryption at rest.** privacy.md says data is encrypted at rest. The claim to cite in an audit is the [Lightsail block storage FAQ](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-faq-block-storage.html): "all Lightsail attached disks and disk snapshots are encrypted at rest by default", "using keys that Lightsail manages on your behalf". It says nothing about the system disk, so assume that one isn't encrypted. The quote is recorded in docs/DEPLOY_AWS.md (the verification table) and docs/SECURITY.md (R1-4). Treeline is built for that: all state lives on the attached disk (the databases and household files, Caddy's keys, swap, the Asterisk logs, the backup spool under `/var/lib/treeline`), and system logs stay in memory (`Storage=volatile`). Before publishing:
   * ~~`findmnt -T /var/lib/treeline/data`~~ seen 2026-11-23: `/var/lib/treeline`, which holds every state path, is its own mount on `/dev/nvme1n1`, not the boot disk (docs/DEPLOY_AWS.md, verification table);
   * ~~`lsblk -o NAME,SIZE,MOUNTPOINT`~~ seen 2026-11-23: `nvme1n1` is 8G (the state disk's size) at `/var/lib/treeline`; the boot disk is the 20G `nvme0n1`, so the state root is the attached disk;
   * still to see: `swapon --show` (no swap, or only `/var/lib/treeline/swapfile`);
   * keep any new place that stores family data on the attached disk too.

## What was checked against the code (November 2026)

* **Call audio is never stored.** No Record, MixMonitor or VoiceMail in the dialplan, and the controller never calls ARI's recording or snoop endpoints. (`res_stasis_recording` and `res_stasis_snoop` are still loaded in `asterisk/config/modules.conf`. Unloading them would make "not recorded" true by construction.)
* **Data fields.** Google sign-in asks only for `openid email`. A grown-up's name is optional and typed in at setup. Per phone: name, kind, a generated SIP account (md5 digest only), online and last check-in. The phone book is built from strings and isn't stored.
* **What other treehouses can see.** `string_json`, `call_json` and `describe_call` in `controller/treeline/api.py`.
* **Log retention.** journald is memory-only with a 64 MB cap (`deploy/native/systemd/journald-treeline.conf`), Caddy has no access log, and the Asterisk log rotates weekly with 4 kept (about five weeks). There's no fixed day count. For one, add `MaxRetentionSec=` to the journald config.
* **Leaving and deleting.** Home → "Leave the Treeline" or "Delete everything" (`/api/treehouse/leave`, `DELETE /api/treehouse`).
* **Providers.** AWS (Oregon), Amazon SES, Google sign-in, the browsers' push services, GitHub.

Recheck these whenever the code they describe changes.

## In the app

* **Where they're linked:** the setup step where a parent agrees, the app's Privacy and safety page, the About page, and the public `/privacy/` page (which the footer's "Privacy" link opens on every page). A separate "Terms" link in the footer was tried and left out: at phone width it wraps the footer onto another line, which takes the room the page doodles need (the smoke test's doodle check fails).
* **The short version:** `web/parent/js/privacy-content.js` holds the plain-language answers parents read at setup, which the app also serves at `/privacy/` (the link Google's sign-in setup uses). Keep it in agreement with privacy.md.
* **Agreement is recorded.** Every grown-up agrees before using the app: the parent who creates the treehouse at setup, and anyone added later (a co-parent or a sitter) on a screen the app shows before anything else (`POST /api/agreement`; `/api/me` says `agreed`). Each agreement is a row in the household's own file, `agreement`: the email, the version, the 911 acknowledgement and the time (`households.record_agreement`). It is kept as long as the family is and that grown-up is in it: removing a grown-up deletes theirs (at once for a parent's removal; `households.reconcile` catches any other way within the hour), and "Delete everything" erases them all. It is never stored in the central database or in this repository. The server enforces it, not only the app's screens: until a grown-up has agreed to the current version, every endpoint answers 403 `agreement_needed` except who they are, agreeing, signing out, leaving and deleting, and the app shows the agree screen whenever it sees that answer (so an app left open asks again after the documents change).
* **The version** is `AGREEMENT_VERSION` in `controller/treeline/api.py`: the newest "Last updated" date of the three files. `scripts/test_legal.py` (run by `./dev check`) fails if they differ.

## Changing a policy

1. Edit the markdown here and set its "*Last updated: …*" line to today.
2. Set `AGREEMENT_VERSION` to the same date.
3. Run `./dev check`, which regenerates `web/legal/`, and commit the markdown and the pages together.
4. If the change is significant, tell parents before it takes effect, as the documents promise. A new version asks every grown-up to agree again the next time they open the app. Families created before the agreement table existed (household step 1) are asked once too, because their file names nobody.
