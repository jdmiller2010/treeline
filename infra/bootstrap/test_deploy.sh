#!/usr/bin/env bash
# Tests for infra/deploy.sh against the fake aws and a fake cdk: it must refuse when the bootstrap check fails, must pass
# the settings to the CDK app in its environment (never on a command line), and must never write them to a file.
#   infra/bootstrap/test_deploy.sh
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA="$(cd "$HERE/.." && pwd)"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
mkdir -p "$T/bin" "$T/tmpfs" "$T/venv/bin"; chmod 700 "$T/tmpfs"
cp "$HERE/testdata/aws" "$T/bin/aws"; chmod +x "$T/bin/aws"
# a fake cdk that records its arguments and the settings it was given in the environment
cat > "$T/cdk" <<'EOS'
#!/usr/bin/env bash
{ echo "ARGS: $*"; env | grep '^TREELINE_' | sort; } >> "$FAKE_CDK_LOG"
EOS
chmod +x "$T/cdk"
export PATH="$T/bin:$PATH" FAKE_AWS_STATE="$T/state.json" TREELINE_LOCAL_DIR="$T/local" TREELINE_TMPFS="$T/tmpfs" AWS_PAGER="" TREELINE_CDK="$T/cdk" FAKE_CDK_LOG="$T/cdk.log" TREELINE_YES=1
export TREELINE_PARAM_GOOGLE_CLIENT_ID="123456789-abcdefg1234.apps.googleusercontent.com" TREELINE_PARAM_GOOGLE_CLIENT_SECRET="GOC""SPX-fake-secret-for-tests-0123456789"
export TREELINE_PARAM_BACKUP_AGE_RECIPIENT="age1$(printf 'q%.0s' $(seq 58))" TREELINE_PARAM_HEALTHCHECK_URL="https://ping.treeline.invalid/0123abcd"
export TREELINE_PARAM_ADMIN_CIDR="203.0.113.9/32" TREELINE_PARAM_ALERT_EMAIL="owner@treeline.invalid"
fails=0
pass() { printf 'ok   %s\n' "$1"; }
fail() { printf 'FAIL %s\n' "$1"; fails=$((fails + 1)); }
expect() { local name="$1"; shift; if "$@"; then pass "$name"; else fail "$name"; fi; }

# deploy.sh looks for the venv in infra/.venv; give the test its own copy of the script and a fake venv beside it.
mkdir -p "$T/infra/bootstrap"; cp "$INFRA/deploy.sh" "$T/infra/"; cp "$INFRA/bootstrap/bootstrap.sh" "$T/infra/bootstrap/"; cp -r "$T/venv" "$T/infra/.venv"; touch "$T/infra/.venv/bin/python"; chmod +x "$T/infra/.venv/bin/python"
D="$T/infra/deploy.sh"

# 1. an account that has not been bootstrapped: refused, and cdk is never started
if "$D" deploy >"$T/out" 2>&1; then fail "deploy must refuse on an account with no bootstrap"; else pass "deploy refuses when the bootstrap check fails"; fi
expect "cdk was never run" test ! -e "$T/cdk.log"
expect "the message says how to fix it" grep -q "bootstrap.sh apply" "$T/out"

# 2. after apply: cdk runs, with the settings in its environment
"$T/infra/bootstrap/bootstrap.sh" apply >/dev/null 2>&1
"$D" deploy >"$T/out" 2>&1 || { cat "$T/out"; fail "deploy failed on a bootstrapped account"; }
expect "cdk deploy ran with the approval rule" grep -q "ARGS: deploy --require-approval broadening --all" "$T/cdk.log"
expect "the SSH address reached the app through the environment" grep -q "TREELINE_ADMIN_CIDR=203.0.113.9/32" "$T/cdk.log"
expect "the hosted zone id was looked up, not stored" grep -q "TREELINE_HOSTED_ZONE_ID=Z0123456789ABCDEFGHIJ" "$T/cdk.log"
expect "a beta allowlist of none is not passed on" bash -c "! grep -q TREELINE_BETA_CIDRS '$T/cdk.log'"
expect "the alert email is not on any command line" bash -c "! grep -q 'ARGS:.*owner@' '$T/cdk.log'"
expect "the planned bundle was shown from the real API" grep -q "Lightsail bundle" "$T/out"
expect "no settings file was written next to the script" bash -c "[ -z \"\$(find '$T/infra' -maxdepth 1 -name '*.json' -o -maxdepth 1 -name '*.env' | head -1)\" ]"

# 3. an allowlist set with bootstrap reaches the app; targets map to stacks
TREELINE_PARAM_BETA_CIDRS="198.51.100.0/24,203.0.113.0/24" "$T/infra/bootstrap/bootstrap.sh" set beta_cidrs >/dev/null 2>&1
: > "$T/cdk.log"
"$D" deploy host >/dev/null 2>&1
expect "the allowlist is passed" grep -q "TREELINE_BETA_CIDRS=198.51.100.0/24,203.0.113.0/24" "$T/cdk.log"
expect "'host' deploys only the host stack" grep -q "ARGS: deploy --require-approval broadening TreelineHost" "$T/cdk.log"
if TREELINE_PARAM_BETA_CIDRS="not-a-cidr" "$T/infra/bootstrap/bootstrap.sh" set beta_cidrs >/dev/null 2>&1; then fail "a bad allowlist must be refused"; else pass "a bad allowlist is refused by bootstrap"; fi

# 4. a missing CDK or venv is explained, not a stack trace
if TREELINE_CDK="$T/nope" "$D" synth >"$T/out" 2>&1; then fail "a missing cdk must stop"; else expect "a missing CDK CLI says how to install it" grep -q "npm ci" "$T/out"; fi

echo
if [ "$fails" -eq 0 ]; then echo "all deploy.sh tests passed"; else echo "$fails deploy.sh test(s) FAILED"; exit 1; fi
