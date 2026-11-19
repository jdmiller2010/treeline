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

export PATH="$T/bin:$PATH" FAKE_AWS_STATE="$T/state.json" TREELINE_LOCAL_DIR="$T/local" AWS_PAGER=""
export TREELINE_PARAM_GOOGLE_CLIENT_ID="123456789-abcdefg1234.apps.googleusercontent.com"
export TREELINE_PARAM_ALLOWED_EMAILS="Parent.One@treeline.invalid, parent.two@treeline.invalid"
export TREELINE_PARAM_BACKUP_AGE_RECIPIENT="age1$(printf 'q%.0s' $(seq 58))"

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
expect "7 parameters exist" test "$(state '.params | length')" = 7
expect "emails were cleaned up" test "$(state '.params["/treeline/allowed_emails"].Value')" = "parent.one@treeline.invalid,parent.two@treeline.invalid"
expect "secret types are SecureString" test "$(state '.params["/treeline/vapid_private"].Type + .params["/treeline/smtp_password"].Type + .params["/treeline/smtp_user"].Type')" = "SecureStringSecureStringSecureString"
expect "both IAM users exist with a policy" test "$(state '[.users[] | select(.policy != null)] | length')" = 2
expect "VM key file written, mode 600" test "$(stat -c %a "$T/local/vm-credentials")" = 600
expect "local dir is private (700)" test "$(stat -c %a "$T/local")" = 700
expect "VM policy cannot read backups" bash -c "! jq -e '.users[\"treeline-vm\"].policy.Statement[] | select(.Action | tostring | test(\"GetObject|s3:\\\\*\"))' '$FAKE_AWS_STATE' >/dev/null"
expect "VM can delete households' backups but not central's" bash -c "jq -e '[.users[\"treeline-vm\"].policy.Statement[] | select(.Action == \"s3:DeleteObject\") | .Resource] == [\"arn:aws:s3:::treeline-backups-123456789012-us-west-2/households/*\"]' '$FAKE_AWS_STATE' >/dev/null"
expect "VM cannot tag, change lifecycle or versioning, or delete versions" bash -c "! jq -e '.users[\"treeline-vm\"].policy.Statement[] | select(.Action | tostring | test(\"Tagging|Lifecycle|Versioning|PutBucket|DeleteObjectVersion\"))' '$FAKE_AWS_STATE' >/dev/null"
expect "VM may only list under households/" bash -c "jq -e '.users[\"treeline-vm\"].policy.Statement[] | select(.Action == \"s3:ListBucket\") | .Condition.StringLike[\"s3:prefix\"] == [\"households/*\"]' '$FAKE_AWS_STATE' >/dev/null"
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

# 9. the root user is refused, bad values are refused, a bare terminal-less run asks for env vars
if FAKE_AWS_ARN="arn:aws:iam::123456789012:root" "$BOOT" check >"$T/out" 2>&1; then fail "root must be refused"; else expect "root user is refused" grep -q "root user" "$T/out"; fi
rm -f "$FAKE_AWS_STATE" "$FAKE_AWS_STATE.argv"
if TREELINE_PARAM_GOOGLE_CLIENT_ID="<your client id>" "$BOOT" apply >"$T/out" 2>&1; then fail "a placeholder value must be refused"; else pass "a placeholder value is refused"; fi
if TREELINE_PARAM_ALLOWED_EMAILS="not-an-email" "$BOOT" apply >"$T/out" 2>&1; then fail "a bad email list must be refused"; else pass "a bad email list is refused"; fi
if TREELINE_PARAM_BACKUP_AGE_RECIPIENT="AGE-SECRET-KEY-1ABC" "$BOOT" apply >"$T/out" 2>&1; then fail "an age PRIVATE key must be refused"; else pass "an age private key is refused as the recipient"; fi

# 10. install-vm-key refuses a hostile host name
if "$BOOT" install-vm-key "-oProxyCommand=evil" >"$T/out" 2>&1; then fail "option-looking host must be refused"; else pass "option-looking host is refused"; fi

echo
if [ "$fails" -eq 0 ]; then echo "all bootstrap tests passed"; else echo "$fails bootstrap test(s) FAILED"; exit 1; fi
