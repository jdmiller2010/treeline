#!/usr/bin/env bash
# Tests for bootstrap.sh against a fake `aws` (testdata/aws), so they need no AWS account:
#   infra/bootstrap/test_bootstrap.sh
# They check what matters: rerunning changes nothing, `check` never writes, the root user is refused,
# bad values are refused, drift is fixed, a lost SMTP secret is reissued, and NO secret value is ever
# passed on a command line (where `ps` would show it) or left in the repo.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOOT="$HERE/bootstrap.sh"
T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT
mkdir -p "$T/bin"
cp "$HERE/testdata/aws" "$T/bin/aws"; chmod +x "$T/bin/aws"

mkdir -p "$T/tmpfs"; chmod 700 "$T/tmpfs"
export TREELINE_TMPFS="$T/tmpfs"
export PATH="$T/bin:$PATH" FAKE_AWS_STATE="$T/state.json" TREELINE_LOCAL_DIR="$T/local" AWS_PAGER=""
export TREELINE_PARAM_GOOGLE_CLIENT_ID="123456789-abcdefg1234.apps.googleusercontent.com"
export TREELINE_PARAM_GOOGLE_CLIENT_SECRET="GOC""SPX-fake-secret-for-tests-0123456789"
export TREELINE_PARAM_BACKUP_AGE_RECIPIENT="age1$(printf 'q%.0s' $(seq 58))"
export TREELINE_PARAM_ADMIN_CIDR="203.0.113.9/32"
export TREELINE_PARAM_ALERT_EMAIL="owner@treeline.invalid"
export TREELINE_PARAM_HEALTHCHECK_URL="https://ping.treeline.invalid/0123abcd-0000-4000-8000-000000000000"

fails=0
pass() { printf 'ok   %s\n' "$1"; }
fail() { printf 'FAIL %s\n' "$1"; fails=$((fails + 1)); }
expect() { local name="$1"; shift; if "$@"; then pass "$name"; else fail "$name"; fi; }
state() { jq -r "$1" "$FAKE_AWS_STATE"; }
calls() { grep -c -E "$1" "$FAKE_AWS_STATE.argv" || true; }

# 1. an empty account is "not ready", and checking wrote nothing
if "$BOOT" check >"$T/out" 2>&1; then fail "check on an empty account must fail"; else pass "check fails on an empty account"; fi
expect "check wrote nothing" test "$(calls 'put-parameter|create-user|create-access-key|put-user-policy')" = 0
expect "check says what is missing" grep -q "is missing" "$T/out"

# 2. apply creates everything
"$BOOT" apply >"$T/out" 2>&1 || { cat "$T/out"; fail "apply failed"; }
expect "request files were 0600" test "$(sort -u "$FAKE_AWS_STATE.argv.modes" | awk '{print $1}' | tr '\n' ' ')" = "600 "
expect "request files were on the tmpfs directory" test "$(awk '{print $2}' "$FAKE_AWS_STATE.argv.modes" | sort -u)" = "$TREELINE_TMPFS"
expect "request files were deleted" test -z "$(find "$TREELINE_TMPFS" -mindepth 1 | head -1)"
expect "stdin is refused by the fake as by the real CLI (regression: file:///dev/stdin)" bash -c "! echo '{}' | '$T/bin/aws' ssm put-parameter --cli-input-json file:///dev/stdin 2>/dev/null"
expect "14 parameters exist" test "$(state '.params | length')" = 14
expect "the SSH address and the alert email are stored (email as SecureString)" test "$(state '.params["/treeline/admin_cidr"].Type + .params["/treeline/alert_email"].Type')" = "StringSecureString"
expect "the optional allowlist starts as none" test "$(state '.params["/treeline/beta_cidrs"].Value')" = none
expect "the dead-man URL is a SecureString" test "$(state '.params["/treeline/healthcheck_url"].Type')" = SecureString
expect "the bucket name is stored, with the account in it, as a plain String" test "$(state '.params["/treeline/backup_bucket"].Value + .params["/treeline/backup_bucket"].Type')" = "treeline-backups-123456789012-us-west-2String"
expect "the Google client secret is a SecureString" test "$(state '.params["/treeline/google_client_secret"].Type')" = SecureString
expect "secret types are SecureString" test "$(state '.params["/treeline/vapid_private"].Type + .params["/treeline/smtp_password"].Type + .params["/treeline/smtp_user"].Type')" = "SecureStringSecureStringSecureString"
expect "both IAM users exist with a policy" test "$(state '[.users[] | select(.policy != null)] | length')" = 2
expect "VM key file written, mode 600" test "$(stat -c %a "$T/local/vm-credentials")" = 600
expect "local dir is private (700)" test "$(stat -c %a "$T/local")" = 700
expect "VM policy cannot read backups" bash -c "! jq -e '.users[\"treeline-vm\"].policy.Statement[] | select(.Action | tostring | test(\"GetObject|s3:\\\\*\"))' '$FAKE_AWS_STATE' >/dev/null"
expect "VM policy cannot delete, tag or list" bash -c "! jq -e '.users[\"treeline-vm\"].policy.Statement[] | select(.Action | tostring | test(\"Delete|Tagging|ListBucket\"))' '$FAKE_AWS_STATE' >/dev/null"
expect "VM cannot change lifecycle or versioning, or delete versions" bash -c "! jq -e '.users[\"treeline-vm\"].policy.Statement[] | select(.Action | tostring | test(\"Lifecycle|Versioning|PutBucket|DeleteObjectVersion\"))' '$FAKE_AWS_STATE' >/dev/null"
expect "VM policy has no wildcard resources" bash -c "! jq -e '.users[\"treeline-vm\"].policy.Statement[] | select(.Resource == \"*\")' '$FAKE_AWS_STATE' >/dev/null"
expect "SMTP user is limited to our domain" bash -c "jq -e '.users[\"treeline-ses-smtp\"].policy.Statement[0].Condition.StringLike[\"ses:FromAddress\"] == \"*@treelinephone.com\"' '$FAKE_AWS_STATE' >/dev/null"
# the generated VAPID pair has the shape the app expects: 65-byte point and 32-byte scalar, base64url
pub="$(state '.params["/treeline/vapid_public"].Value')"; priv="$(state '.params["/treeline/vapid_private"].Value')"
expect "VAPID public key is 87 chars base64url" test "${#pub}" = 87
expect "VAPID private key is 43 chars base64url" test "${#priv}" = 43

# 3. the SMTP password is the documented derivation of the IAM secret (checked with an independent HMAC chain in openssl)
secret="$(state '.keys["treeline-ses-smtp"][0].secret')"
hex() { od -An -tx1 | tr -d ' \n'; }
h="$(printf '%s' "AWS4$secret" | hex)"
for part in 11111111 us-west-2 ses aws4_request SendRawEmail; do
  h="$(printf '%s' "$part" | openssl dgst -sha256 -mac HMAC -macopt "hexkey:$h" -binary | hex)"
done
expected="$(python3 -c 'import sys, binascii, base64; print(base64.b64encode(binascii.unhexlify("04" + sys.argv[1])).decode())' "$h")"
expect "SMTP password matches the documented derivation" test "$(state '.params["/treeline/smtp_password"].Value')" = "$expected"

# 4. a second apply, and a check, change nothing (idempotent)
: > "$FAKE_AWS_STATE.argv"
"$BOOT" apply >"$T/out" 2>&1 || { cat "$T/out"; fail "second apply failed"; }
expect "second apply creates nothing" test "$(calls 'put-parameter|create-user|create-access-key|delete-access-key')" = 0
"$BOOT" check --quiet >"$T/out" 2>&1 && pass "check passes after apply" || { cat "$T/out"; fail "check should pass"; }
expect "check output has no passing lines with --quiet" bash -c "! grep -q '✔' '$T/out'"

# 5. no secret value ever appeared in a command line
bad=0
for v in "$priv" "$secret" "$(state '.params["/treeline/smtp_password"].Value')" "$(state '.keys["treeline-vm"][0].secret')"; do
  grep -qF -- "$v" "$FAKE_AWS_STATE.argv" && bad=1
done
expect "no secret in any aws command line" test "$bad" = 0
expect "no key material anywhere but the 600 file" bash -c "! grep -rqF '$(state '.keys["treeline-vm"][0].secret')' '$T/out'"

# 6. drift is reported, then fixed
jq '.users["treeline-vm"].policy.Statement += [{"Effect":"Allow","Action":"s3:*","Resource":"*"}]' "$FAKE_AWS_STATE" > "$T/s" && mv "$T/s" "$FAKE_AWS_STATE"
if "$BOOT" check >"$T/out" 2>&1; then fail "check must notice a widened policy"; else pass "check notices a widened policy"; fi
"$BOOT" apply >/dev/null 2>&1
expect "apply puts the policy back" bash -c "! jq -e '.users[\"treeline-vm\"].policy.Statement[] | select(.Action == \"s3:*\")' '$FAKE_AWS_STATE' >/dev/null"

# 6b. a bucket parameter that points at the wrong bucket is reported and corrected
jq '.params["/treeline/backup_bucket"].Value = "somebody-elses-bucket"' "$FAKE_AWS_STATE" > "$T/s" && mv "$T/s" "$FAKE_AWS_STATE"
if "$BOOT" check >"$T/out" 2>&1; then fail "check must notice a wrong bucket name"; else pass "check notices a wrong bucket name"; fi
"$BOOT" apply >/dev/null 2>&1
expect "apply corrects the bucket name" test "$(state '.params["/treeline/backup_bucket"].Value')" = "treeline-backups-123456789012-us-west-2"

# 7. a lost SMTP parameter reissues the key (the secret can't be shown twice)
old_id="$(state '.keys["treeline-ses-smtp"][0].id')"
jq 'del(.params["/treeline/smtp_password"])' "$FAKE_AWS_STATE" > "$T/s" && mv "$T/s" "$FAKE_AWS_STATE"
"$BOOT" apply >/dev/null 2>&1
expect "SMTP key was replaced" test "$(state '.keys["treeline-ses-smtp"] | length')" = 1
expect "SMTP key is a new one" test "$(state '.keys["treeline-ses-smtp"][0].id')" != "$old_id"
expect "SMTP password exists again" test "$(state '.params["/treeline/smtp_password"].Type')" = SecureString

# 8. rotation of the VM key: a second key, then the old one goes
rm -f "$T/local/vm-credentials"
"$BOOT" rotate-vm-key >/dev/null 2>&1
expect "rotate makes a second key" test "$(state '.keys["treeline-vm"] | length')" = 2
expect "rotate writes the new key file" test -f "$T/local/vm-credentials"
"$BOOT" finish-rotate >/dev/null 2>&1
expect "finish-rotate keeps one key" test "$(state '.keys["treeline-vm"] | length')" = 1
expect "the kept key is the newest" grep -q "$(state '.keys["treeline-vm"][0].id')" "$T/local/vm-credentials"

# 8b. the beta code: only its hash and an expiry are stored; the code is shown once and is 8 characters; a new one replaces the old
"$BOOT" apply >"$T/out" 2>&1 || true
state_hash="$(state '.params["/treeline/beta_code_hash"].Value')"
expect "the beta code hash is a SHA-256 SecureString" test "${#state_hash}-$(state '.params["/treeline/beta_code_hash"].Type')" = "64-SecureString"
expect "the expiry is a date about 180 days away" python3 -c "import datetime,sys; d=(datetime.date.fromisoformat(sys.argv[1])-datetime.date.today()).days; sys.exit(0 if 178<=d<=181 else 1)" "$(state '.params["/treeline/beta_code_expires"].Value')"
"$BOOT" set beta_code >"$T/out" 2>&1 </dev/null
shown="$(grep -o '[A-Z2-9]\{4\}-[A-Z2-9]\{4\}' "$T/out" | head -1)"
expect "a new code is shown once, as 4+4 characters" test -n "$shown"
expect "the new hash is the hash of what was shown" test "$(state '.params["/treeline/beta_code_hash"].Value')" = "$(printf '%s' "${shown/-/}" | sha256sum | cut -d' ' -f1)"
expect "the old hash is gone" test "$(state '.params["/treeline/beta_code_hash"].Value')" != "$state_hash"
expect "the code itself is never stored or sent on a command line" bash -c "! grep -rqF '${shown/-/}' '$FAKE_AWS_STATE' '$FAKE_AWS_STATE.argv'"
jq '.params["/treeline/beta_code_expires"].Value = "2020-01-01"' "$FAKE_AWS_STATE" > "$T/s" && mv "$T/s" "$FAKE_AWS_STATE"
if "$BOOT" check >"$T/out" 2>&1; then fail "check must notice an expired beta code"; else expect "check notices an expired beta code" grep -q "expired" "$T/out"; fi

# 9. the root user is refused, bad values are refused, a bare terminal-less run asks for env vars
if FAKE_AWS_ARN="arn:aws:iam::123456789012:root" "$BOOT" check >"$T/out" 2>&1; then fail "root must be refused"; else expect "root user is refused" grep -q "root user" "$T/out"; fi
rm -f "$FAKE_AWS_STATE" "$FAKE_AWS_STATE.argv"
if TREELINE_PARAM_GOOGLE_CLIENT_ID="<your client id>" "$BOOT" apply >"$T/out" 2>&1; then fail "a placeholder value must be refused"; else pass "a placeholder value is refused"; fi
if TREELINE_PARAM_HEALTHCHECK_URL="http://plain.example.invalid/ping" "$BOOT" apply >"$T/out" 2>&1; then fail "a non-https dead-man URL must be refused"; else pass "a non-https dead-man URL is refused"; fi
rm -f "$FAKE_AWS_STATE" "$FAKE_AWS_STATE.argv"
for bad_cidr in 0.0.0.0/0 10.0.0.0/8 203.0.113.9 "not-a-cidr"; do
  rm -f "$FAKE_AWS_STATE" "$FAKE_AWS_STATE.argv"
  if TREELINE_PARAM_ADMIN_CIDR="$bad_cidr" "$BOOT" apply >"$T/out" 2>&1; then fail "SSH address '$bad_cidr' must be refused"; else pass "SSH address '$bad_cidr' is refused"; fi
done
rm -f "$FAKE_AWS_STATE" "$FAKE_AWS_STATE.argv"
if TREELINE_PARAM_GOOGLE_CLIENT_SECRET="short" "$BOOT" apply >"$T/out" 2>&1; then fail "a too-short Google secret must be refused"; else pass "a too-short Google secret is refused"; fi
if TREELINE_PARAM_BACKUP_AGE_RECIPIENT="AGE-SECRET-KEY-1ABC" "$BOOT" apply >"$T/out" 2>&1; then fail "an age PRIVATE key must be refused"; else pass "an age private key is refused as the recipient"; fi

# 10. install-vm-key refuses a hostile host name
if "$BOOT" install-vm-key "-oProxyCommand=evil" >"$T/out" 2>&1; then fail "option-looking host must be refused"; else pass "option-looking host is refused"; fi

echo
if [ "$fails" -eq 0 ]; then echo "all bootstrap tests passed"; else echo "$fails bootstrap test(s) FAILED"; exit 1; fi
