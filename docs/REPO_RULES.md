# What may and may not be committed

This repository is **public**. Anything committed is readable by anyone, forever: deleting it later does not un-publish it (clones, forks and caches keep it, and so does git history). Treeline is a children's phone network, so the bar is high. These rules are enforced by `scripts/check_repo_rules.py`, by a pre-commit hook, and by CI on every pull request. A rule with no check behind it is only a wish.

## Never commit

| What | Why | What to do instead |
| --- | --- | --- |
| **Secrets** of any kind: passwords, API keys, tokens, private keys (`*.pem`, `*.key`, `*.agekey`, SSH keys), VAPID private keys, SMTP passwords, the factory key, AWS access keys, OAuth client secrets | Anyone could use them | AWS SSM Parameter Store for the server (set up by `infra/bootstrap/bootstrap.sh`); `deploy/.env` (gitignored) is only for a hand-run server. Placeholders go in `deploy/env.example` |
| **Real people**: names, emails (other than the project contact), phone numbers, street addresses, anything that identifies a family or a child | The users are children and their parents | Invented names (`Example house`), `@example.com`, and the reserved `.invalid` domain |
| **Where the kids are**: the park, school, street or neighborhood the pilot families live near | Together with the maintainer's name it points at real children | "friend families", "the neighborhood". Put real place names in `.repo-rules.local` (see below) so the scanner stops them |
| **IP addresses of real machines or people**: the server, family home networks, anyone's phone | They are the beta allowlist and a map to the server | Documentation ranges (`203.0.113.0/24`, `198.51.100.0/24`, `192.0.2.0/24`) and private ranges. The allowlist lives in the AWS console or `infra/.local/` (gitignored) |
| **AWS account details**: the 12-digit account ID (so ARNs with one), access keys, profile names, `cdk.context.json`, `cdk.out/`, Terraform state | They help an attacker target the account | Read them at run time (`aws sts get-caller-identity`) or from the environment; the fake ID `123456789012` is fine in tests |
| **Data**: database files (`*.db`, `*.sqlite`), backups, call logs or CSV exports, a copy of anything under `data/`, screenshots or recordings from real families | Real families' records | Throwaway test data created and removed by the tests |
| **Local deny-list**: `.repo-rules.local` | It names the very things we keep out | It stays on your machine; CI gets the same list from the `REPO_RULES_EXTRA` repository secret |
| **Infrastructure state or credentials waiting to be installed**: `infra/.local/`, files named `credentials` | They are keys | They are gitignored; delete them once installed |

## Fine to commit

Code, tests, docs and design assets; `deploy/env.example` and other files with **placeholders** (`change-me`, `<your value>`); parameter *names* (`/treeline/vapid_private`) but never values; the public domain name (`app.treelinephone.com`); the project contact address; fake values in tests (an access-key-shaped string assembled in code, the account ID `123456789012`, made-up client addresses under `tests/`).

If something is fine on purpose but trips a check, put `repo-rules: allow` in a comment on that line and say why.

## How it is enforced

1. **`./dev hooks`** (once per clone) makes git refuse a commit that adds any of the above. It reads what is *staged*, not your working copy.
2. **`./dev check`** runs the same scan, so it is in your normal loop.
3. **CI** (`.github/workflows/repo-rules.yml`) scans the whole tree and every line each pull request adds in *every* commit, so a secret committed and then deleted inside a PR is still caught.
4. **`.repo-rules.local`**: one regex per line, gitignored, for names that must not appear anywhere (a park, a street, a family). Copy the same lines into a GitHub repository secret named `REPO_RULES_EXTRA` so CI enforces them too. Fork pull requests do not receive repository secrets, so for those the deny-list is not applied, and review decides.

The scanner is regex-based. It will miss things (it cannot know a stranger's name), so it backs up your attention; it does not replace it.

## GitHub settings (these cannot be set from the repo; do them once)

- **Settings, Code security**: turn on **secret scanning** and **push protection** (free for public repos), and **private vulnerability reporting**.
- **Dependabot alerts and security updates, auto-merge, and the required checks on `main`**: the list is in [SUPPLY_CHAIN.md](SUPPLY_CHAIN.md), "GitHub settings". The workflows there follow the rules on this page (first-party actions pinned to a commit, `pull_request` only, no job that can write ever runs pull-request code).
- **Settings, Branches**: protect `main`: require a pull request and the `repo rules` check to pass, and no force pushes.
- **Settings, Actions, General**: "Require approval for all outside collaborators" before a fork's workflow runs; default workflow permissions **read-only**; do not allow Actions to create or approve pull requests.
- **Never** add a self-hosted runner to a public repo, and never use `pull_request_target` in a workflow.
- **Secrets** (Settings, Secrets and variables): `REPO_RULES_EXTRA` (repository secret) and `RELEASE_SIGNING_KEY` (a secret of the protected **`release` environment** only, never a repository secret). Deploys do not use GitHub-stored cloud credentials: the VM pulls signed releases, so no AWS key is in GitHub.
- **The `release` environment** (Settings, Environments): add a **required reviewer** (the owner), and **deployment tag rules** so only `v*` tags can use it; protect the `v*` tag pattern (Settings, Rules) so nobody else can create or move one. Whoever can run that job can sign a release that the VM, running as root, will install: treat it like the VM's root password.

## If something gets through

1. **Assume it is public.** Rotate/revoke it first, before cleaning anything: a leaked AWS key by `aws iam` (`bootstrap.sh set` / `rotate-vm-key`), a VAPID key by `bootstrap.sh set vapid`, a leaked family detail by telling that family.
2. Remove it from the current tree and commit.
3. Rewriting history (`git filter-repo`) removes it from the repo's own history, but not from forks, clones or caches, so it is a tidy-up and never a substitute for step 1. It needs a force push, so do it deliberately.
4. If it was a security-relevant leak, record it in [SECURITY.md](SECURITY.md) the way reviews are recorded there.
5. Add a case to `scripts/test_check_repo_rules.py` so the same kind of mistake is caught next time.
