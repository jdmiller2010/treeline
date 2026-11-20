#!/usr/bin/env bash
# Deploy the AWS infrastructure (CDK). Run it from your own computer with AWS admin credentials (an SSO profile; never root).
#
#   infra/deploy.sh synth                    print nothing, check that the app builds (needs the settings below)
#   infra/deploy.sh diff [foundation|host]   what would change
#   infra/deploy.sh deploy [foundation|host|all]   (default all; Foundation first)
#   infra/deploy.sh bootstrap                CDK's one-time setup in the account (the CDKToolkit stack: a small S3 bucket the
#                                            CLI uploads each template to, and a few IAM roles). Needed once, before the first deploy.
#
# It runs `bootstrap.sh check --quiet` first and REFUSES to continue unless that passes, so a deploy cannot start with a
# secret missing, a policy that drifted, or no VM key issued. It then reads the environment-specific settings (your SSH
# address, the allowlist, the alert email, the hosted zone id) from SSM and Route 53 into environment variables for the CDK
# app: they are never written to a file or to this repository (docs/REPO_RULES.md). `synth` in CI has no account and
# skips all of this: it passes dummy values itself (see infra/tests).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CDK="${TREELINE_CDK:-$HERE/node_modules/.bin/cdk}"
REGION="${TREELINE_AWS_REGION:-us-west-2}"
export AWS_DEFAULT_REGION="$REGION" AWS_PAGER=""
cmd="${1:-help}"; target="${2:-all}"
case "$cmd" in synth|diff|deploy|bootstrap) ;; *) sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'; exit 2 ;; esac
case "$target" in foundation) stacks=(TreelineFoundation) ;; host) stacks=(TreelineHost) ;; all) stacks=(--all) ;; *) echo "unknown target '$target'" >&2; exit 2 ;; esac

"$HERE/bootstrap/bootstrap.sh" check --quiet || { echo >&2; echo "deploy.sh: the bootstrap check failed, so nothing was deployed. Run: infra/bootstrap/bootstrap.sh apply" >&2; exit 1; }

[ -x "$CDK" ] || { echo "deploy.sh: the CDK command line is not installed. Run once:  (cd infra && npm ci --ignore-scripts)" >&2; exit 1; }
[ -x "$HERE/.venv/bin/python" ] || { echo "deploy.sh: no Python environment. Run once:  python3 -m venv infra/.venv && infra/.venv/bin/pip install --require-hashes --no-deps -r infra/requirements.lock" >&2; exit 1; }

get() { aws ssm get-parameter --name "/treeline/$1" --with-decryption --query Parameter.Value --output text; }
TREELINE_ADMIN_CIDR="$(get admin_cidr)"; export TREELINE_ADMIN_CIDR
TREELINE_ALERT_EMAIL="$(get alert_email)"; export TREELINE_ALERT_EMAIL
beta="$(get beta_cidrs)"; if [ "$beta" != none ]; then TREELINE_BETA_CIDRS="$beta"; export TREELINE_BETA_CIDRS; fi
zone="$(aws route53 list-hosted-zones-by-name --dns-name treelinephone.com --max-items 1 --query 'HostedZones[0].[Id,Name]' --output text)"
[ "$(awk '{print $2}' <<<"$zone")" = "treelinephone.com." ] || { echo "deploy.sh: the hosted zone for treelinephone.com was not found in this account" >&2; exit 1; }
TREELINE_HOSTED_ZONE_ID="$(awk '{print $1}' <<<"$zone" | sed 's|/hostedzone/||')"; export TREELINE_HOSTED_ZONE_ID

if [ "$cmd" = bootstrap ]; then
  account="$(aws sts get-caller-identity --query Account --output text)"
  # Run from outside infra/ so the CLI does not build the app (it only needs the account and region).
  cd "$(mktemp -d)" && exec "$CDK" bootstrap "aws://$account/$REGION"
fi

if [ "$cmd" != synth ]; then
  # The CLI uploads each stack's template to CDK's bootstrap bucket, even with no other assets (found on the first real deploy).
  toolkit="$(aws cloudformation describe-stacks --stack-name CDKToolkit --query 'Stacks[0].StackStatus' --output text 2>/dev/null || true)"
  case "$toolkit" in
    CREATE_COMPLETE|UPDATE_COMPLETE) ;;
    *) echo "deploy.sh: CDK's one-time setup is missing in this account and region (stack CDKToolkit: ${toolkit:-none}). Run once:  infra/deploy.sh bootstrap" >&2; exit 1 ;;
  esac
  # Bundles and prices change: show what the planned bundle is today, from the real API, and stop if it does not exist.
  bundle="${TREELINE_BUNDLE_ID:-nano_3_0}"
  info="$(aws lightsail get-bundles --query "bundles[?bundleId=='$bundle'].[bundleId,ramSizeInGb,cpuCount,price,supportedPlatforms[0]]" --output text)"
  [ -n "$info" ] || { echo "deploy.sh: Lightsail has no bundle '$bundle' any more. See: aws lightsail get-bundles; then set TREELINE_BUNDLE_ID" >&2; exit 1; }
  echo "Lightsail bundle (id, RAM GB, vCPUs, USD/month, platform): $info"
  if [ "$cmd" = deploy ] && [ "${TREELINE_YES:-}" != 1 ]; then
    { : >/dev/tty; } 2>/dev/null || { echo "deploy.sh: there is no terminal to ask on. Run it from a terminal, or set TREELINE_YES=1 to deploy without asking." >&2; exit 1; }
    read -r -p "Deploy ${stacks[*]}? [y/N] " a </dev/tty; [ "$a" = y ] || exit 1
  fi
fi

cd "$HERE"
case "$cmd" in
  synth) "$CDK" synth --quiet "${stacks[@]}" ;;
  diff) "$CDK" diff "${stacks[@]}" ;;
  deploy) "$CDK" deploy --require-approval broadening "${stacks[@]}" ;;
esac
