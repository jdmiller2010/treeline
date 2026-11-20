# Work plan: the infra code review

Source: the review of `infra/` on 2026-11-20 (CDK app, `deploy.sh`, `bootstrap.sh`, `restore.py`, locks). Nothing here has been
run on AWS; items marked **needs AWS** can only be closed by the first real `cdk diff` or deploy. Each package is one branch or
commit set, with its own test, and updates [SECURITY.md](SECURITY.md) when it is a security change. Order is by risk: things that
could stop the first deploy come first, then security hardening, then cost and tidiness.

| # | Package | Findings closed | Test that must exist | Effort |
|---|---|---|---|---|
| 1 | **First-deploy risk reducers** (before the owner's first `cdk deploy`) | Disk attached through `Hardware.Disks` is unproven; forecast budget alert may be rejected; existing SES identity or apex record would collide; IMDSv1 call in `install.sh` | Template assertion for whatever shape we choose. Needs AWS to confirm. | small |
| 2 | **Backup overwrite protection** | A stolen VM key can overwrite a recent backup key | Template test: bucket policy denies `PutObject` without `If-None-Match: *` on `central/*` and `households/*`; `treeline-backup` sends it; the fake S3 rejects a second write to the same key | small |
| 3 | **S3 TLS floor** | `enforce_ssl` only denies plain HTTP | Template test: `minimum_tls_version` 1.2 statement present | trivial |
| 4 | **DNS hardening and TTL** | No CAA record; 30-minute A-record TTL slows recovery after a host replacement | Template test: CAA allows only `letsencrypt.org`; both A records have a 300-second TTL | trivial |
| 5 | **CDK feature flags** | 83 unset flags: legacy defaults | `cdk flags` result committed; all template tests still pass; `cdk diff` shows no unexpected replacement | small |
| 6 | **ASCII-only script output** | `bootstrap.sh` prints non-ASCII marks that depend on the terminal; `--quiet` and a test depend on the exact bytes | `bootstrap.sh` tests: output is pure ASCII (`LC_ALL=C grep -P '[^\x00-\x7F]'`) | trivial |
| 7 | **SES production readiness** | No configuration set or bounce and complaint handling; DMARC relies on DKIM alone | Template test: configuration set with SNS event destination for bounce and complaint; optional custom MAIL FROM. Needs AWS. | medium |
| 8 | **Deploy credentials** | `CliCredentialsStackSynthesizer` runs with the admin profile: no least-privilege deploy role | Decision first: keep (no assets, owner-only) or bootstrap with a permissions boundary. If we switch: `cdk bootstrap` step in the checklist and a synth test for the qualifier. | decision |
| 9 | **Short-lived VM credentials** | The VM holds a static IAM key (Lightsail has no instance role) | Spike: IAM Roles Anywhere with a certificate on the VM; compare the extra moving parts with the 90-day rotation we already warn about. No code until decided. | spike |
| 10 | **Small tidiness** | `cdk.json` relies on a Linux path; no Node pin; `deploy.sh` prompt needs a terminal | `engines` in `package.json`; documented WSL/Linux requirement; non-interactive failure message tested in `test_deploy.sh` | trivial |

## Details and decisions to make first

- **Package 1** is the only one with a real chance of failing the first deploy. Plan: leave the code as it is, run `cdk diff`
  and `cdk deploy TreelineFoundation` first, and have the fallbacks ready as small patches: attach the disk with
  `aws lightsail attach-disk` (and drop `Hardware.Disks`), and make the budget a single `ACTUAL` 80% notification. Pre-flight
  in `deploy.sh`: `aws sesv2 get-email-identity` and `aws route53 list-resource-record-sets` to stop early with a clear message if
  the identity or the apex record already exists. For IMDS, `install.sh` already falls back to DNS or `--public-ip`; the change is
  to try IMDSv2 (token) first and keep the fallbacks.
- **Package 2** needs the upload change and the bucket policy in the same release, or uploads start failing. Keys already contain a
  timestamp, so a duplicate key only happens in a retry: the tool must treat "precondition failed" on a file it already uploaded
  as success.
- **Package 5** can change resource shapes; do it before anything is deployed, never after.
- **Package 8** is a decision for the owner, not a code task: with only the owner deploying, the admin profile is acceptable; with CI deploys it is not.
- Do not commit `cdk.context.json` (the skill's default advice): the app uses no context lookups, and the repo rules forbid it.

## Suggested sequence

1. Packages 3, 4, 6, 10 together (all trivial; one PR).
2. Package 5 (flags), alone, so its diff is reviewable.
3. Package 2 (backup overwrite protection), with SECURITY.md.
4. Package 1 prepared as patches, applied only if the first real deploy needs them.
5. Packages 7, 8, 9 after the first successful deploy.
