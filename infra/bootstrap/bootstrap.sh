#!/usr/bin/env bash
# Treeline AWS bootstrap: the things the CDK stacks (and the VM) need to exist BEFORE
# anything is deployed, and that must never be checked in: secret/config values in SSM
# Parameter Store, and the two IAM users with their access keys.
#
#   infra/bootstrap/bootstrap.sh check            read-only; says what is missing; exit 1 if anything is
#   infra/bootstrap/bootstrap.sh apply            creates what is missing (asks for values); safe to rerun
#   infra/bootstrap/bootstrap.sh set NAME         replace one value: google_client_id, google_client_secret, beta_code (a NEW code, shown once), admin_cidr, beta_cidrs, alert_email, healthcheck_url,
#                                                 backup_age_recipient, vapid (new key pair), smtp (new key)
#   infra/bootstrap/bootstrap.sh rotate-vm-key    make a second key for the VM user (then install-vm-key, then finish-rotate)
#   infra/bootstrap/bootstrap.sh finish-rotate    delete the VM user's older key(s)
#   infra/bootstrap/bootstrap.sh install-vm-key HOST   copy the local credentials file to the VM
#   add --quiet to hide the passing lines
#
# Run it from your own machine with AWS admin credentials (an IAM Identity Center profile:
# AWS_PROFILE=... ; never the root user). Nothing secret is ever written into this repo:
#   - values are typed at a prompt (or read from TREELINE_PARAM_<NAME> in the environment),
#     and are sent to AWS in a 0600 file on tmpfs, never as command-line arguments;
#   - generated keys go straight to SSM; the one key that has to reach the VM is written to
#     infra/.local/ (gitignored, mode 600) until you install it and delete it.
# See infra/README.md.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
LOCAL_DIR="${TREELINE_LOCAL_DIR:-$ROOT/infra/.local}"
REGION="${TREELINE_AWS_REGION:-us-west-2}"
MAIL_DOMAIN="${TREELINE_MAIL_DOMAIN:-treelinephone.com}"
PREFIX="/treeline"
VM_USER="treeline-vm"
SMTP_USER="treeline-ses-smtp"
BUCKET_BASE="treeline-backups"     # the bucket is ${BUCKET_BASE}-<account id>-<region>; the CDK stack must use the same name
KEY_MAX_AGE_DAYS=90
export AWS_DEFAULT_REGION="$REGION" AWS_PAGER=""

MODE=check
QUIET=0
PROBLEMS=0

say()  { printf '%s\n' "$*"; }
ok()   { [ "$QUIET" = 1 ] || printf '  ✔ %s\n' "$*"; }
bad()  { PROBLEMS=$((PROBLEMS + 1)); printf '  ✘ %s\n' "$*"; }
warn() { printf '  ! %s\n' "$*"; }
die()  { printf 'error: %s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------- AWS helpers
# probe CMD...: run an AWS call. 0 = it worked (output on stdout); 3 = the thing doesn't exist;
# anything else is a real error and stops the script (so a permissions problem is never mistaken for "missing").
probe() {
  local out
  if out=$("$@" 2>&1); then printf '%s' "$out"; return 0; fi
  case "$out" in
    *NoSuchEntity*|*ParameterNotFound*) return 3 ;;
    *) printf 'error: AWS call failed (%s): %s\n' "${*:1:3}" "$out" >&2; return 1 ;;
  esac
}

# param_type NAME: prints the parameter's type; 3 if absent. Never decrypts anything.
param_type() { probe aws ssm get-parameter --name "$PREFIX/$1" --query Parameter.Type --output text; }

# put_param NAME TYPE VALUE OVERWRITE(true|false): the value must stay out of argv (ps would show it).
# AWS CLI v2 cannot read --cli-input-json from stdin: `file:///dev/stdin` fails with "Invalid JSON received"
# (checked on 2.35.17, from a pipe, a here-string, /dev/fd/0 and process substitution), while a regular file works.
# So the request goes in a 0600 file on tmpfs (never on disk) that is removed when the call ends.
put_param() {
  local dir="${TREELINE_TMPFS:-${XDG_RUNTIME_DIR:-/dev/shm}}"
  [ -d "$dir" ] && [ -w "$dir" ] || die "no writable tmpfs directory for the request file (set TREELINE_TMPFS)"
  (
    umask 077
    f=$(mktemp "$dir/treeline-param.XXXXXX")
    trap 'rm -f "$f"' EXIT
    jq -n --arg n "$PREFIX/$1" --arg v "$3" --arg t "$2" --argjson o "$4" \
      '{Name:$n, Value:$v, Type:$t, Overwrite:$o, Tier:"Standard"}' > "$f"
    aws ssm put-parameter --cli-input-json "file://$f" >/dev/null
  )
}

# ---------------------------------------------------------------- values
# name|type|what it is|how to get it
PROMPTED=(
  "google_client_id|String|the Google OAuth client ID (public)|Google Cloud Console > APIs & Services > Credentials; looks like 123-abc.apps.googleusercontent.com"
  "google_client_secret|SecureString|the Google OAuth client SECRET (it stays in SSM; the app uses it to finish sign-in)|Google Cloud Console > APIs & Services > Credentials, the same OAuth client as the ID; the authorized redirect URI must be https://app.treelinephone.com/api/auth/google/callback"
  "backup_age_recipient|String|the age PUBLIC key that backups are encrypted to|run: age-keygen -o treeline-backup.agekey   then keep that FILE in your password manager and paste only the age1... line it prints"
  "admin_cidr|String|the address SSH may be reached from, as a CIDR (SSH is never open to the world)|your public IPv4 address with /32, e.g. 203.0.113.9/32 (search the web for 'what is my IP'); change it with: bootstrap.sh set admin_cidr"
  "alert_email|SecureString|where the AWS budget alert goes|your own email address"
  "healthcheck_url|SecureString|the dead-man ping URL (a free healthchecks-style check: it alerts you when pings STOP)|create a check that expects a ping every 5 minutes with a grace of 15, and paste its ping URL (https://...)"
)

valid() {   # valid NAME VALUE -> 0 if it looks right
  local n="$1" v="$2" e
  [ -n "$v" ] || return 1
  case "$v" in *"<"*">"*|*PLACEHOLDER*|*CHANGE*ME*|*changeme*|*example.com*) return 1 ;; esac
  case "$n" in
    google_client_id) [[ "$v" =~ ^[0-9]+-[a-z0-9]+\.apps\.googleusercontent\.com$ ]] ;;
    backup_age_recipient) [[ "$v" =~ ^age1[a-z0-9]{58}$ ]] ;;
    admin_cidr) [[ "$v" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}/([0-9]|[12][0-9]|3[0-2])$ ]] && [[ "$v" != "0.0.0.0/"* ]] && [[ "${v#*/}" -ge 16 ]] ;;
    beta_cidrs) [[ "$v" == none ]] || { IFS=, read -ra nets <<<"$v"; [ "${#nets[@]}" -gt 0 ] || return 1; for e in "${nets[@]}"; do [[ "$e" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}/([0-9]|[12][0-9]|3[0-2])$ ]] || return 1; done; } ;;
    alert_email) [[ "$v" =~ ^[^@\ ,]+@[^@\ ,]+\.[^@\ ,]+$ ]] ;;
    healthcheck_url) [[ "$v" =~ ^https://[A-Za-z0-9._~:/?#@!$\&\(\)*+,\;=%-]+$ ]] && [[ "$v" != *[[:space:]]* ]] ;;
    google_client_secret) [[ ${#v} -ge 20 && "$v" != *[[:space:]]* ]] ;;
    *) return 0 ;;
  esac
}

normalize() { printf '%s' "$2"; }

# ask NAME LABEL HINT: the value, from TREELINE_PARAM_<NAME> or a prompt on the terminal. Validated.
ask() {
  local name="$1" label="$2" hint="$3" var v tries=0
  var="TREELINE_PARAM_$(printf '%s' "$name" | tr 'a-z' 'A-Z')"
  if [ -n "${!var:-}" ]; then
    v="$(normalize "$name" "${!var}")"
    valid "$name" "$v" || die "$var is not a valid $name"
    printf '%s' "$v"; return
  fi
  [ -r /dev/tty ] || die "nothing to ask $name with (no terminal); set $var in the environment"
  while [ $tries -lt 3 ]; do
    printf '\n%s\n  (%s)\n' "$label" "$hint" >/dev/tty
    read -r -p "  $name: " v </dev/tty >/dev/tty
    v="$(normalize "$name" "$v")"
    if valid "$name" "$v"; then printf '%s' "$v"; return; fi
    printf '  that does not look right; try again\n' >/dev/tty
    tries=$((tries + 1))
  done
  die "gave up on $name"
}

ensure_prompted() {
  local row n t label hint have rc v
  for row in "${PROMPTED[@]}"; do
    IFS='|' read -r n t label hint <<<"$row"
    have=$(param_type "$n") && rc=0 || rc=$?
    if [ $rc -eq 0 ]; then
      if [ "$have" = "$t" ]; then ok "$PREFIX/$n"; else bad "$PREFIX/$n is a $have, should be a $t (fix: $0 set $n)"; fi
    elif [ $rc -ne 3 ]; then exit 1
    elif [ "$MODE" = check ]; then bad "$PREFIX/$n is missing"
    else v="$(ask "$n" "$label" "$hint")"; put_param "$n" "$t" "$v" false; ok "$PREFIX/$n created"
    fi
  done
}

# Optional settings that start with a harmless default. beta_cidrs is the optional firewall allowlist for 443 and the call
# audio ports (comma-separated IPv4 CIDRs); "none" means open to everyone (the beta is gated by an access code instead).
ensure_defaults() {
  local have rc
  have=$(param_type beta_cidrs) && rc=0 || rc=$?
  if [ $rc -eq 0 ]; then ok "$PREFIX/beta_cidrs"
  elif [ $rc -ne 3 ]; then exit 1
  elif [ "$MODE" = check ]; then bad "$PREFIX/beta_cidrs is missing (apply creates it as: none)"
  else put_param beta_cidrs String none false; ok "$PREFIX/beta_cidrs created (none: no allowlist)"
  fi
}

# ---------------------------------------------------------------- the closed-beta access code
# One shared 8-character code lets someone create a treehouse (once). Only its SHA-256 and an expiry are stored; the code itself
# is shown ONCE, here, and never again: if it is lost, make a new one (that also revokes the old one).
BETA_DAYS="${TREELINE_BETA_DAYS:-180}"
new_beta_code() {   # prints the code, then its hash, then the expiry date, one per line
  python3 - "$BETA_DAYS" <<'PY'
import hashlib, secrets, sys, datetime
alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
raw = "".join(secrets.choice(alphabet) for _ in range(8))
print(raw[:4] + "-" + raw[4:])
print(hashlib.sha256(raw.encode()).hexdigest())
print((datetime.date.today() + datetime.timedelta(days=int(sys.argv[1]))).isoformat())
PY
}
issue_beta_code() {
  local out code hash expires
  out=$(new_beta_code) || die "could not generate a beta code"
  code=$(sed -n 1p <<<"$out"); hash=$(sed -n 2p <<<"$out"); expires=$(sed -n 3p <<<"$out")
  put_param beta_code_hash SecureString "$hash" true
  put_param beta_code_expires String "$expires" true
  ok "$PREFIX/beta_code_hash and beta_code_expires stored (valid $BETA_DAYS days, until $expires)"
  printf '\n  The beta access code (shown once; write it down now): %s\n  The app reads it when it starts: restart treeline-api to make an old code stop working at once.\n\n' "$code" >/dev/tty 2>/dev/null || printf '\n  The beta access code (shown once): %s\n\n' "$code"
}
ensure_beta_code() {
  local a b rc
  a=$(param_type beta_code_hash) && a=ok || a=$?
  b=$(param_type beta_code_expires) && b=ok || b=$?
  [ "$a" = ok ] || [ "$a" = 3 ] || exit 1
  [ "$b" = ok ] || [ "$b" = 3 ] || exit 1
  if [ "$a" = ok ] && [ "$b" = ok ]; then
    rc=$(probe aws ssm get-parameter --name "$PREFIX/beta_code_expires" --query Parameter.Value --output text) || exit 1
    if [[ "$rc" < "$(date -u +%F)" ]]; then bad "the beta access code expired on $rc (run: $0 set beta_code)"; else ok "$PREFIX/beta_code_hash (expires $rc)"; fi
    return
  fi
  if [ "$MODE" = check ]; then bad "$PREFIX/beta_code_hash / beta_code_expires missing"; return; fi
  issue_beta_code
}

# ---------------------------------------------------------------- the backup bucket's name
# The VM needs the bucket name, which has the account id in it; the id must not be in the repo, so it is stored in SSM
# (a plain String) from here, where the account is known. The CDK stack must create the bucket with this exact name.
ensure_bucket_param() {
  local have rc
  have=$(probe aws ssm get-parameter --name "$PREFIX/backup_bucket" --query Parameter.Value --output text) && rc=0 || rc=$?
  if [ $rc -eq 0 ] && [ "$have" = "$BUCKET" ]; then ok "$PREFIX/backup_bucket"; return; fi
  [ $rc -eq 0 ] || [ $rc -eq 3 ] || exit 1
  if [ "$MODE" = check ]; then bad "$PREFIX/backup_bucket is $([ $rc -eq 3 ] && echo missing || echo different)"; return; fi
  put_param backup_bucket String "$BUCKET" true
  ok "$PREFIX/backup_bucket set"
}

# ---------------------------------------------------------------- generated values
gen_vapid() {   # prints the public key, then the private key (Web Push / VAPID, P-256, base64url, as controller/make_vapid.py does)
  local txt hp hq
  txt=$(openssl ecparam -name prime256v1 -genkey -noout 2>/dev/null | openssl ec -text -noout 2>/dev/null)
  hq=$(printf '%s\n' "$txt" | awk '/^priv:/{f=1;next} /^pub:/{f=0} f' | tr -d ' :\n')
  hp=$(printf '%s\n' "$txt" | awk '/^pub:/{f=1;next} /^ASN1|^NIST/{f=0} f' | tr -d ' :\n')
  hq="${hq: -64}"
  [[ "$hp" =~ ^04[0-9a-f]{128}$ && "$hq" =~ ^[0-9a-f]{64}$ ]] || die "could not generate a VAPID key pair with openssl"
  printf '%s %s' "$hp" "$hq" | python3 -c '
import sys, base64, binascii
for h in sys.stdin.read().split():
    print(base64.urlsafe_b64encode(binascii.unhexlify(h)).rstrip(b"=").decode())'
}

new_vapid() {   # generates a key pair and stores both halves (a failure inside <(...) would otherwise store nothing, silently)
  local out pub priv
  out=$(gen_vapid) || die "could not generate a VAPID key pair"
  pub=$(sed -n 1p <<<"$out"); priv=$(sed -n 2p <<<"$out")
  [ -n "$pub" ] && [ -n "$priv" ] || die "could not generate a VAPID key pair"
  put_param vapid_public String "$pub" true
  put_param vapid_private SecureString "$priv" true
}

ensure_vapid() {
  local a b
  a=$(param_type vapid_public) && a=ok || a=$?
  b=$(param_type vapid_private) && b=ok || b=$?
  [ "$a" = ok ] && [ "$b" = ok ] && { ok "$PREFIX/vapid_public and vapid_private"; return; }
  [ "$a" = ok ] || [ "$a" = 3 ] || exit 1
  [ "$b" = ok ] || [ "$b" = 3 ] || exit 1
  if [ "$MODE" = check ]; then bad "$PREFIX/vapid_public / vapid_private missing"; return; fi
  new_vapid
  ok "$PREFIX/vapid_public and vapid_private generated"
}

# The SES SMTP password is not the IAM secret: it is derived from it (AWS's documented v4 algorithm, bound to the region).
derive_smtp_password() {
  python3 -c '
import sys, hmac, hashlib, base64
secret, region = sys.stdin.read().strip(), sys.argv[1]
def sign(k, m): return hmac.new(k, m.encode(), hashlib.sha256).digest()
s = sign(("AWS4" + secret).encode(), "11111111")
for part in (region, "ses", "aws4_request", "SendRawEmail"):
    s = sign(s, part)
print(base64.b64encode(bytes([4]) + s).decode())' "$REGION"
}

# ---------------------------------------------------------------- IAM
vm_policy() {
  jq -n -S --arg r "$REGION" --arg a "$ACCOUNT" --arg b "$BUCKET" --arg p "${PREFIX#/}" '{
    Version: "2012-10-17",
    Statement: [
      { Sid: "ReadTreelineParameters", Effect: "Allow",
        Action: ["ssm:GetParameter", "ssm:GetParameters", "ssm:GetParametersByPath"],
        Resource: ["arn:aws:ssm:\($r):\($a):parameter/\($p)", "arn:aws:ssm:\($r):\($a):parameter/\($p)/*"] },
      { Sid: "DecryptViaSsmOnly", Effect: "Allow", Action: "kms:Decrypt",
        Resource: "arn:aws:kms:\($r):\($a):key/*",
        Condition: { StringEquals: { "kms:ViaService": "ssm.\($r).amazonaws.com" } } },
      { Sid: "WriteBackups", Effect: "Allow",
        Action: ["s3:PutObject", "s3:AbortMultipartUpload"],
        Resource: ["arn:aws:s3:::\($b)/central/*", "arn:aws:s3:::\($b)/households/*"] }
    ] }'
}

smtp_policy() {
  jq -n -S --arg r "$REGION" --arg a "$ACCOUNT" --arg d "$MAIL_DOMAIN" '{
    Version: "2012-10-17",
    Statement: [
      { Sid: "SendMailFromOurDomainOnly", Effect: "Allow", Action: "ses:SendRawEmail",
        Resource: "arn:aws:ses:\($r):\($a):identity/\($d)",
        Condition: { StringLike: { "ses:FromAddress": "*@\($d)" } } }
    ] }'
}

# ensure_user NAME POLICY_JSON: the user exists and carries exactly this inline policy ("treeline").
ensure_user() {
  local u="$1" want="$2" rc cur
  probe aws iam get-user --user-name "$u" >/dev/null && rc=0 || rc=$?
  if [ $rc -eq 0 ]; then ok "IAM user $u"
  elif [ $rc -ne 3 ]; then exit 1
  elif [ "$MODE" = check ]; then bad "IAM user $u is missing"; return 1
  else aws iam create-user --user-name "$u" --tags Key=project,Value=treeline >/dev/null; ok "IAM user $u created"
  fi
  cur=$(probe aws iam get-user-policy --user-name "$u" --policy-name treeline --query PolicyDocument --output json) && rc=0 || rc=$?
  if [ $rc -eq 0 ] && [ "$(jq -S . <<<"$cur")" = "$(jq -S . <<<"$want")" ]; then ok "$u policy is as expected"; return 0; fi
  [ $rc -eq 0 ] || [ $rc -eq 3 ] || exit 1
  if [ "$MODE" = check ]; then bad "$u policy is $([ $rc -eq 3 ] && echo missing || echo different)"; return 1; fi
  aws iam put-user-policy --user-name "$u" --policy-name treeline --policy-document "$want"
  ok "$u policy set"
}

key_age_days() {
  python3 -c 'import sys, datetime as d; t = d.datetime.fromisoformat(sys.argv[1].replace("Z", "+00:00")); print((d.datetime.now(d.timezone.utc) - t).days)' "$1"
}

create_vm_key() {   # a new access key for the VM user -> infra/.local/vm-credentials (mode 600). The secret never reaches argv or the screen.
  local kid ksec
  ( umask 077; mkdir -p "$LOCAL_DIR" )
  read -r kid ksec < <(aws iam create-access-key --user-name "$VM_USER" --query 'AccessKey.[AccessKeyId,SecretAccessKey]' --output text) || true
  [ -n "${kid:-}" ] && [ -n "${ksec:-}" ] || die "could not create an access key for $VM_USER"
  ( umask 077; printf '[treeline-vm]\naws_access_key_id = %s\naws_secret_access_key = %s\nregion = %s\n' "$kid" "$ksec" "$REGION" > "$LOCAL_DIR/vm-credentials" )
  ok "new key for $VM_USER written to ${LOCAL_DIR#"$ROOT"/}/vm-credentials (mode 600): install it on the VM, then delete it"
}

ensure_vm_key() {
  local keys n age
  keys=$(aws iam list-access-keys --user-name "$VM_USER" --query 'AccessKeyMetadata[].[AccessKeyId,CreateDate]' --output json)
  n=$(jq length <<<"$keys")
  case "$n" in
    0) if [ "$MODE" = check ]; then bad "$VM_USER has no access key (run apply)"; else create_vm_key; fi ;;
    1) age=$(key_age_days "$(jq -r '.[0][1]' <<<"$keys")")
       if [ "$age" -gt "$KEY_MAX_AGE_DAYS" ]; then warn "the $VM_USER key is $age days old; rotate it ($0 rotate-vm-key)"; else ok "$VM_USER has one access key ($age days old)"; fi ;;
    *) warn "$VM_USER has $n keys: a rotation is in progress. Install the newest on the VM, then run: $0 finish-rotate" ;;
  esac
  [ ! -f "$LOCAL_DIR/vm-credentials" ] || warn "a key file is waiting in ${LOCAL_DIR#"$ROOT"/}/: $0 install-vm-key ubuntu@HOST (this check can't see what is on the VM)"
}

issue_smtp() {   # new key for the SES user (old ones can't be re-read, so they go), derive the SMTP password, store both in SSM
  local k kid ksec pw
  for k in $(aws iam list-access-keys --user-name "$SMTP_USER" --query 'AccessKeyMetadata[].AccessKeyId' --output text); do
    aws iam delete-access-key --user-name "$SMTP_USER" --access-key-id "$k"
  done
  read -r kid ksec < <(aws iam create-access-key --user-name "$SMTP_USER" --query 'AccessKey.[AccessKeyId,SecretAccessKey]' --output text) || true
  [ -n "${kid:-}" ] && [ -n "${ksec:-}" ] || die "could not create an access key for $SMTP_USER"
  pw=$(printf '%s' "$ksec" | derive_smtp_password)
  put_param smtp_user SecureString "$kid" true
  put_param smtp_password SecureString "$pw" true
  ok "$PREFIX/smtp_user and smtp_password issued (nothing to copy; the app reads them from SSM)"
}

ensure_smtp() {
  local a b
  a=$(param_type smtp_user) && a=ok || a=$?
  b=$(param_type smtp_password) && b=ok || b=$?
  [ "$a" = ok ] || [ "$a" = 3 ] || exit 1
  [ "$b" = ok ] || [ "$b" = 3 ] || exit 1
  if [ "$a" = ok ] && [ "$b" = ok ]; then ok "$PREFIX/smtp_user and smtp_password"; return; fi
  if [ "$MODE" = check ]; then bad "$PREFIX/smtp_user / smtp_password missing"; return; fi
  issue_smtp
}

# ---------------------------------------------------------------- commands
preflight() {
  local t arn
  for t in aws jq python3 openssl; do command -v "$t" >/dev/null || die "$t is required"; done
  ACCOUNT=$(aws sts get-caller-identity --query Account --output text) || die "no AWS credentials (set AWS_PROFILE, log in with your SSO profile)"
  arn=$(aws sts get-caller-identity --query Arn --output text)
  case "$arn" in *:root) die "you are signed in as the root user. Use an IAM Identity Center / IAM admin profile instead." ;; esac
  BUCKET="${BUCKET_BASE}-${ACCOUNT}-${REGION}"
  say "region $REGION, mode: $MODE"
}

run_all() {
  preflight
  say; say "Parameters in SSM Parameter Store ($PREFIX/*)"
  ensure_prompted
  ensure_vapid
  ensure_bucket_param
  ensure_beta_code
  ensure_defaults
  ensure_smtp_user_and_params
  say; say "IAM user for the VM ($VM_USER): reads $PREFIX/*, writes backups only"
  if ensure_user "$VM_USER" "$(vm_policy)"; then ensure_vm_key; fi
  say
  if [ "$PROBLEMS" -gt 0 ]; then
    say "NOT READY: $PROBLEMS thing(s) missing or different. Run: $0 apply"; exit 1
  fi
  say "Ready. Everything the CDK stacks and the VM need from this step is in place."
}

ensure_smtp_user_and_params() {
  say; say "IAM user for sending mail ($SMTP_USER): SES from @$MAIL_DOMAIN only"
  if ensure_user "$SMTP_USER" "$(smtp_policy)"; then ensure_smtp; fi
}

cmd_set() {
  local name="${1:?usage: set NAME}" row n t label hint v
  preflight
  case "$name" in
    vapid) warn "a new key pair means every parent must turn notifications on again"
           new_vapid; ok "new VAPID key pair stored" ;;
    beta_code) warn "a new code replaces the old one: anyone with the old code can no longer create a treehouse"
           issue_beta_code ;;
    smtp)  ensure_user "$SMTP_USER" "$(smtp_policy)"; issue_smtp ;;
    beta_cidrs) v="$(ask beta_cidrs "the allowlist for 443 and the call audio ports (comma-separated IPv4 CIDRs), or: none" "for example 198.51.100.0/24,203.0.113.0/24; none opens them to everyone")"
           put_param beta_cidrs String "$v" true; ok "$PREFIX/beta_cidrs updated (run infra/deploy.sh to apply it)" ;;
    *)     for row in "${PROMPTED[@]}"; do
             IFS='|' read -r n t label hint <<<"$row"
             if [ "$n" = "$name" ]; then v="$(ask "$n" "$label" "$hint")"; put_param "$n" "$t" "$v" true; ok "$PREFIX/$n updated"; return; fi
           done
           die "unknown name '$name'" ;;
  esac
}

cmd_rotate_vm_key() {
  preflight
  [ "$(aws iam list-access-keys --user-name "$VM_USER" --query 'length(AccessKeyMetadata)' --output text)" -lt 2 ] || die "$VM_USER already has two keys; run finish-rotate first"
  create_vm_key
  say "Next: $0 install-vm-key ubuntu@HOST, restart the services, confirm the VM still works, then: $0 finish-rotate"
}

cmd_finish_rotate() {
  local k
  preflight
  for k in $(aws iam list-access-keys --user-name "$VM_USER" --query 'sort_by(AccessKeyMetadata,&CreateDate)[:-1].AccessKeyId' --output text); do
    [ "$k" = None ] || { aws iam delete-access-key --user-name "$VM_USER" --access-key-id "$k"; ok "deleted an old key"; }
  done
}

cmd_install_vm_key() {
  local host="${1:?usage: install-vm-key HOST   (for example ubuntu@app.treelinephone.com)}" a
  [[ "$host" =~ ^[A-Za-z0-9][A-Za-z0-9._@-]*$ ]] || die "that does not look like a host"
  [ -f "$LOCAL_DIR/vm-credentials" ] || die "no key file in $LOCAL_DIR (apply or rotate-vm-key makes one)"
  ssh "$host" 'sudo install -D -m 0600 -o root -g root /dev/stdin /etc/treeline/aws-credentials' < "$LOCAL_DIR/vm-credentials"
  ok "installed as /etc/treeline/aws-credentials (root only)"
  read -r -p "Delete the local copy now? [Y/n] " a </dev/tty || a=Y
  case "$a" in n|N) warn "left ${LOCAL_DIR#"$ROOT"/}/vm-credentials in place; delete it when you are done" ;;
    *) if command -v shred >/dev/null; then shred -u "$LOCAL_DIR/vm-credentials"; else rm -f "$LOCAL_DIR/vm-credentials"; fi; ok "local copy deleted" ;;
  esac
}

main() {
  local cmd="${1:-check}" arg=()
  shift || true
  for a in "$@"; do if [ "$a" = --quiet ]; then QUIET=1; else arg+=("$a"); fi; done
  case "$cmd" in
    check) MODE=check; run_all ;;
    apply) MODE=apply; run_all ;;
    set) MODE=apply; cmd_set "${arg[@]}" ;;
    rotate-vm-key) MODE=apply; cmd_rotate_vm_key ;;
    finish-rotate) MODE=apply; cmd_finish_rotate ;;
    install-vm-key) cmd_install_vm_key "${arg[@]}" ;;
    -h|--help|help) sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//' ;;
    *) die "unknown command '$cmd' (try: help)" ;;
  esac
}
main "$@"
