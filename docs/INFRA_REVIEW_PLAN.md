# Infra review and work plan

Reviewed: `infra/` (the CDK app, `deploy.sh`, `bootstrap.sh`, `restore.py`, locks) on 2026-11-20, then **re-reviewed and every finding
re-verified against the code at the end of work package 5**. Nothing here has been run on AWS. "Verified" says how a finding was
confirmed; **needs AWS** means only the first real `cdk diff` or deploy can settle it. Each work package below is one branch or
commit set with its own test, and updates [SECURITY.md](SECURITY.md) when it is a security change.

## Done (2026-11-20) and left for follow-up

**Implemented and tested offline:** packages 2, 3, 4, 5, 6 and 10 (F5, F6, F7, F8, F9, F13, F14, N1, N2, N3), in three commits on
`deploy-aws/07-infra-hardening`. The feature-flag change was checked by synthesizing both stacks before and after: the resources are
identical, so nothing is replaced. One flag is left unset on purpose (`core:defaultCrossStackReferences`: the stacks share no references).
Security details are in SECURITY.md Review 5. **Left for follow-up (troubleshooting after the first real deploy, or when decided):**
package 1 (F1 disk attachment, F3 pre-flight, F4 IMDSv2, F2 note), package 7 (SES readiness), package 8 (deploy credentials, a decision),
package 9 (short-lived VM credentials, a spike). F11, F12, F15 and F16 need no code change now.

## What changed since the first review (work package 5)

WP5 touched `infra/bootstrap/bootstrap.sh`, its two test scripts and `infra/README.md` only. The CDK app (`app.py`, `treeline_infra/`,
`cdk.json`) is unchanged, so no CDK finding moved. New SSM parameters (`google_client_secret`, `beta_code_hash`, `beta_code_expires`)
sit under `/treeline/*`, which the VM's IAM policy already reads, so no policy change was needed. It also means a stolen VM key can read
the Google client secret. No non-ASCII characters were added. Three small new findings (N1 to N3) are in the table.

## Findings, with how each was verified

| ID | Finding | Verified how | Status | Package |
|---|---|---|---|---|
| F1 | The state disk is attached through `Hardware.Disks` (`host.py`) with a made-up path `/dev/xvdf`. AWS's reference lists `DiskName` and `Path` as required and **not updatable** (so editing the entry would replace the instance), but does not say how a standalone `AWS::Lightsail::Disk` is linked | Read AWS's CloudFormation reference (search) and the template | **Needs AWS.** Fallback ready in the plan | 1 |
| F2 | The `FORECASTED` 100% budget alert | **Corrected.** AWS says forecast alerts need about 5 weeks of usage history and do not fire before that. The first review said it "may be rejected"; that was too strong. It is accepted but silent for ~5 weeks. The `ACTUAL` 80% alert works from day one | AWS Budgets best-practices page; template shows both notifications | 1 (note only) |
| F3 | Creating the SES identity or the apex A record fails if one already exists | Logic: CloudFormation create semantics; template has one `EmailIdentity` and an apex `RecordSet` | **Needs AWS**; a cheap pre-flight in `deploy.sh` avoids it | 1 |
| F4 | `install.sh` calls IMDS with IMDSv1 (`curl 169.254.169.254`, line 162). CloudFormation's `CfnInstance` has no metadata-options property (checked in the pinned CDK library). Lightsail does support `aws lightsail update-instance-metadata-options --http-tokens required` after creation, so it can be enforced by `deploy.sh` or the checklist, and `install.sh` must then use the IMDSv2 token flow. Not every blueprint supports IMDSv2; the Ubuntu 24.04 blueprint is **unverified** | Checked the library's signature; AWS docs for the CLI option | Confirmed; fix is easy; blueprint support needs AWS | 1 |
| F5 | The bucket policy denies plain HTTP but sets no TLS 1.2 floor | Template statement list has only the `SecureTransport` deny; the library supports `minimum_tls_version` | **Verified** | 3 |
| F6 | A stolen VM key can overwrite a known recent backup (`central/<stamp>.db.age`): versioning is off and the upload sends no `If-None-Match` | `treeline-backup` has none; S3's `s3:if-none-match` condition key exists (announced Nov 2024). Caveat from AWS: with that policy, copy operations into those prefixes stop working | **Verified** | 2 |
| F7 | No CAA record; both A records use the default 30-minute TTL | Template: A-record TTL `1800`, no `CAA` record; the library has `CaaRecord` and `ARecord(ttl=...)` | **Verified** | 4 |
| F8 | 83 CDK feature flags are unset, so legacy defaults apply | `cdk synth` prints exactly that | **Verified** | 5 |
| F9 | Non-ASCII output: `bootstrap.sh` lines 41-42 print check and cross marks, and `test_bootstrap.sh:79` depends on those exact bytes; `infra/README.md` has an ellipsis. All CDK files are pure ASCII | `grep -P '[^\x00-\x7F]'` over `infra/` | **Verified**, harmless to a deploy | 6 |
| F10 | No SES configuration set or bounce and complaint handling; DMARC relies on DKIM alone | Template has an `EmailIdentity` and a DMARC TXT, no configuration set | **Verified** (absence); AWS may ask for it at production access | 7 |
| F11 | `CliCredentialsStackSynthesizer` deploys with the admin profile: no least-privilege deploy role | `app.py:16` | **Verified**; a decision, not a bug | 8 |
| F12 | The VM holds a static IAM key (Lightsail has no instance role) | `bootstrap.sh`; AWS | **Verified**; rotation warning at 90 days exists | 9 |
| F13 | `cdk.json` runs `.venv/bin/python` (Linux or WSL only); no Node pin in `package.json`; `deploy.sh` needs a terminal for its prompt unless `TREELINE_YES=1` | Read the files; `package.json` has no `engines` | **Verified** | 10 |
| F14 | SSH is limited to one `/32`; an address change locks you out until `set admin_cidr` and a host deploy | Template: port 22 `Cidrs` | **Verified**, intended | 10 (document) |
| F15 | IPv6: only IPv4 CIDRs are listed, relying on `PutInstancePublicPorts` replacing both firewalls | Template: no `Ipv6Cidrs` anywhere | Absence verified; the behaviour is **unverified on AWS** | owner checklist |
| F16 | Costs: nano bundle, 8 GB disk, a 7-day-expiry bucket, SES, SSM Standard parameters, two free budgets | Template resources only. **Prices were not verified**; `deploy.sh` prints the bundle's real price from the API before deploying | Nothing found that is idle or orphaned (the static IP is deleted with the Host stack) | none |
| N1 | `bootstrap.sh issue_beta_code` prints the access code to stdout when there is no terminal, so a piped or logged run captures it | Read the code (new in WP5) | **Verified**, low | 6 |
| N2 | `TREELINE_BETA_DAYS` is not validated (a non-number fails in Python with a stack trace) | Read the code (new in WP5) | **Verified**, trivial | 6 |
| N3 | `restore.py` needs boto3 on the owner's machine, which is neither pinned nor in `infra/requirements.lock` | `restore.py:12`; `requirements.in` has only the CDK packages | **Verified**, low | 10 |

## Work packages

| # | Package | Findings | Test that must exist | Effort |
|---|---|---|---|---|
| 1 | **First-deploy risk reducers** | F1, F3, F4 (F2 as a note) | Template assertion for the shape chosen; `test_deploy.sh` for the pre-flight (identity or apex already exists); `install.sh` test that tries the IMDSv2 token flow first and still falls back. Needs AWS to confirm F1 | small |
| 2 | **Backup overwrite protection** | F6 | Template: bucket policy denies `PutObject` without `If-None-Match: *` on `central/*` and `households/*`. `treeline-backup` sends it; a retry of a key it already uploaded counts as success. The fake S3 rejects a second write to the same key. SECURITY.md entry | small |
| 3 | **S3 TLS floor** | F5 | Template: `minimum_tls_version` 1.2 statement present | trivial |
| 4 | **DNS hardening and TTL** | F7 | Template: CAA allows only `letsencrypt.org`; both A records have a 300-second TTL | trivial |
| 5 | **CDK feature flags** | F8 | `cdk flags` result committed; the 21 template tests still pass; `cdk diff` shows no replacement | small |
| 6 | **ASCII output and small script fixes** | F9, N1, N2 | `bootstrap.sh` output is pure ASCII; a non-numeric `TREELINE_BETA_DAYS` is refused with a message; the code is never printed without a terminal unless asked | trivial |
| 7 | **SES production readiness** | F10 | Template: configuration set with a bounce and complaint destination; optional custom MAIL FROM. Needs AWS | medium |
| 8 | **Deploy credentials** | F11 | Owner decision first (keep the admin profile, or bootstrap a bounded deploy role); then a synth test for the qualifier | decision |
| 9 | **Short-lived VM credentials** | F12 | Spike: IAM Roles Anywhere with a certificate on the VM; no code until decided | spike |
| 10 | **Tidiness and docs** | F13, F14, N3 | `engines` in `package.json`; documented Linux or WSL requirement; pin boto3 for `restore.py` (or document it); a non-interactive failure message in `test_deploy.sh`; document the SSH lockout recovery | trivial |

## Decisions and notes

- **Package 1** is the only one with a real chance of failing the first deploy. Run `cdk diff`, then `cdk deploy TreelineFoundation`, before
  the host. Fallbacks as small patches: attach the disk with `aws lightsail attach-disk` and drop `Hardware.Disks`; keep both budget
  notifications (the forecast one is just silent at first). Enforce IMDSv2 after the host exists with
  `aws lightsail update-instance-metadata-options --instance-name treeline-vm --http-tokens required`, and only once `install.sh` uses the token flow.
- **Package 2** needs the upload change and the bucket policy in the same release, or uploads start failing.
- **Package 5** can change resource shapes; do it before anything is deployed, never after.
- **Package 8** is the owner's decision: with only the owner deploying, the admin profile is acceptable; with CI deploys it is not.
- Do not commit `cdk.context.json`: the app uses no context lookups, and the repo rules forbid it.
- Not changed by WP5 and still open: everything in the table above except the three new rows, which are small.

## Suggested sequence

1. Packages 3, 4, 6, 10 together (all trivial; one change).
2. Package 5 (flags), alone, so its diff is reviewable.
3. Package 2 (backup overwrite protection), with SECURITY.md.
4. Package 1 prepared as patches, applied only if the first real deploy needs them.
5. Packages 7, 8, 9 after the first successful deploy.
