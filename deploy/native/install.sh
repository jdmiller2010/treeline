#!/usr/bin/env bash
# Install Treeline natively on an Ubuntu 24.04 machine (the Lightsail instance). Idempotent: rerun it any time.
#
#   sudo ./deploy/native/install.sh --domain app.treelinephone.com --state-device auto
#
# Run it from an unpacked, signature-checked release (docs/DEPLOY_AWS.md, "First install"). It does not trust
# the network for anything but Ubuntu's own packages and PyPI (hash-pinned wheels).
#
# Options:
#   --domain HOST          the public host name (required)
#   --mail-domain HOST     the domain mail is sent from (default: the domain without its first label)
#   --state-device DEV|auto  the attached disk that holds ALL state; formatted only if blank (see below)
#   --public-ip IP         the instance's static public address (default: instance metadata, then DNS)
#   --signers FILE         the release signing public key file (default: deploy/native/release_signers)
#   --ci                   for the CI job that imitates the VM ONLY: a bind-mounted state directory (--state-dir),
#                          no swap, no fail2ban, a fake AWS endpoint and a local ACME CA may be configured
#   --state-dir DIR        with --ci: a directory to bind-mount as the state disk
#   --aws-endpoint URL     with --ci: send SSM/S3 calls to a fake
#   --acme-dir URL --acme-root FILE   with --ci: a local ACME CA instead of Let's Encrypt
#   --release-repo OWNER/REPO   where the deploy agent looks for releases (GitHub Releases of that public repository)
#   --release-base URL     with --ci: a local release server instead of GitHub
#   --deploy-window HH-HH  the UTC hours in which the timer may deploy (default 09-12); empty = any time
#   --no-start             set everything up but do not start the services
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REL="$(cd "$HERE/../.." && pwd)"
ETC=/etc/treeline; STATE=/var/lib/treeline; OPT=/opt/treeline; LIB=/usr/local/lib/treeline
DOMAIN=""; MAIL_DOMAIN=""; STATE_DEVICE=""; PUBLIC_IP=""; SIGNERS="$HERE/release_signers"
CI=0; STATE_DIR=""; AWS_ENDPOINT=""; ACME_DIR=""; ACME_ROOT=""; START=1; RELEASE_REPO=""; RELEASE_BASE=""; WINDOW="09-12"

say() { printf '==> %s\n' "$*"; }
die() { printf 'install: %s\n' "$*" >&2; exit 1; }

while [ $# -gt 0 ]; do
  case "$1" in
    --domain) DOMAIN="${2:?}"; shift 2 ;;
    --mail-domain) MAIL_DOMAIN="${2:?}"; shift 2 ;;
    --state-device) STATE_DEVICE="${2:?}"; shift 2 ;;
    --public-ip) PUBLIC_IP="${2:?}"; shift 2 ;;
    --signers) SIGNERS="${2:?}"; shift 2 ;;
    --ci) CI=1; shift ;;
    --state-dir) STATE_DIR="${2:?}"; shift 2 ;;
    --aws-endpoint) AWS_ENDPOINT="${2:?}"; shift 2 ;;
    --acme-dir) ACME_DIR="${2:?}"; shift 2 ;;
    --acme-root) ACME_ROOT="${2:?}"; shift 2 ;;
    --release-repo) RELEASE_REPO="${2:?}"; shift 2 ;;
    --release-base) RELEASE_BASE="${2:?}"; shift 2 ;;
    --deploy-window) WINDOW="$2"; shift 2 ;;
    --no-start) START=0; shift ;;
    -h|--help) sed -n '2,24p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "unknown option $1" ;;
  esac
done

[ "$(id -u)" = 0 ] || die "run as root (sudo)"
[ -n "$DOMAIN" ] || die "--domain is required"
[[ "$DOMAIN" =~ ^([a-z0-9]([a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,}$ ]] || die "'$DOMAIN' is not a host name"
[[ -z "$RELEASE_REPO" || "$RELEASE_REPO" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || die "--release-repo must look like OWNER/REPO"
[[ "$WINDOW" =~ ^([0-9]{1,2}-[0-9]{1,2})?$ ]] || die "--deploy-window must look like 09-12 (UTC hours)"
if [ "$CI" = 0 ] && { [ -n "$RELEASE_BASE" ] || [ -n "$STATE_DIR" ] || [ -n "$AWS_ENDPOINT" ] || [ -n "$ACME_DIR" ] || [ -n "$ACME_ROOT" ]; }; then
  die "--state-dir, --aws-endpoint, --acme-dir and --acme-root exist only for the CI job (--ci); a real machine must not use them"
fi
# shellcheck disable=SC1091
. /etc/os-release
[ "${VERSION_ID:-}" = "24.04" ] || [ -n "${TREELINE_ALLOW_OTHER_OS:-}" ] || die "this is for Ubuntu 24.04 (found ${PRETTY_NAME:-unknown}); set TREELINE_ALLOW_OTHER_OS=1 to try anyway"
[ -d /run/systemd/system ] || die "systemd is not running"
[ -f "$REL/release.json" ] || die "run this from an unpacked release (no release.json beside deploy/)"
[ -n "$MAIL_DOMAIN" ] || MAIL_DOMAIN="${DOMAIN#*.}"
# Never from an older release than the one running: it would put back older tools, units and templates (the deploy agent among
# them). New releases arrive through the agent; this script only sets a machine up or repairs it from the current release.
if [ -f "$OPT/current/release.json" ] && [ -z "${TREELINE_ALLOW_OLDER_INSTALL:-}" ]; then
  python3 -I - "$OPT/current/release.json" "$REL/release.json" <<'PY' || die "this release is older than the one running; run install.sh from the current release (/opt/treeline/current), or set TREELINE_ALLOW_OLDER_INSTALL=1 if you really mean it"
import json, re, sys
def key(v):
    m = re.match(r"^v(\d+)\.(\d+)\.(\d+)(?:-(.+))?$", v)
    return (int(m[1]), int(m[2]), int(m[3]), 1 if m[4] is None else 0, m[4] or "")
running, mine = (json.load(open(f))["version"] for f in sys.argv[1:3])
sys.exit(0 if key(mine) >= key(running) else 1)
PY
fi
# The signing key: without one nothing could ever be deployed, so stop now rather than at the first deploy.
grep -qE '^[^#].* (ssh-|sk-ssh-)' "$SIGNERS" 2>/dev/null || [ -s "$ETC/release_signers" ] || \
  die "no release signing key: $SIGNERS has none and $ETC/release_signers does not exist (see docs/DEPLOY_AWS.md, Release signing)"

# ---------------------------------------------------------------- packages
say "packages"
export DEBIAN_FRONTEND=noninteractive
# Do not let the packages start services with their sample configuration (Caddy would serve its welcome page on 80).
printf '#!/bin/sh\nexit 101\n' > /usr/sbin/policy-rc.d; chmod 755 /usr/sbin/policy-rc.d
trap 'rm -f /usr/sbin/policy-rc.d' EXIT
apt-get update -qq
# Asterisk itself is not an Ubuntu package here: each release carries its own build (asterisk/build/README.md), which is linked
# against the libraries on this line (asterisk/runtime-deps.txt lists the same ones; a test keeps the two together).
apt-get install -y -qq --no-install-recommends \
  caddy python3 python3-venv age ca-certificates openssh-client openssl curl iproute2 \
  sox espeak-ng unattended-upgrades logrotate \
  libssl3t64 libsrtp2-1 libjansson4 libxml2 libxslt1.1 libsqlite3-0 libedit2 libuuid1 liburiparser1 libcap2 libsystemd0 \
  $([ "$CI" = 1 ] || echo fail2ban) >/dev/null

# ---------------------------------------------------------------- users and directories
say "users and directories"
getent group treeline >/dev/null || groupadd --system treeline
id treeline >/dev/null 2>&1 || useradd --system --gid treeline --home-dir /nonexistent --no-create-home --shell /usr/sbin/nologin treeline
# The Asterisk user: no login, no supplementary groups (Ubuntu's package put it in dialout and audio, which it does not need),
# its home on the state disk. Also recreated after Ubuntu's package is purged, which may delete it.
ensure_asterisk_user() {
  getent group asterisk >/dev/null || groupadd --system asterisk
  id asterisk >/dev/null 2>&1 || useradd --system --gid asterisk --home-dir "$STATE/asterisk" --no-create-home --shell /usr/sbin/nologin asterisk
  usermod -G "" asterisk 2>/dev/null || true
}
ensure_asterisk_user
install -d -m 0755 -o root -g root "$ETC" "$OPT" "$OPT/releases" "$LIB"

# ---------------------------------------------------------------- the state disk
# ALL state lives on the attached disk: the system disk is not documented as encrypted (Lightsail encrypts attached
# disks), so nothing sensitive may sit there: not the databases, not Caddy's keys, not swap, not logs.
say "state disk"
if mountpoint -q "$STATE"; then
  echo "    $STATE is already a mount point"
else
  install -d -m 0711 "$STATE"
  if [ "$CI" = 1 ] && [ -n "$STATE_DIR" ]; then
    install -d -m 0711 "$STATE_DIR"
    grep -q " $STATE none bind" /etc/fstab || echo "$STATE_DIR $STATE none bind 0 0" >> /etc/fstab
  else
    DEV="$STATE_DEVICE"
    if [ "$DEV" = auto ]; then
      # exactly one whole disk that is not the root disk and holds nothing mounted
      root_src="$(findmnt -n -o SOURCE /)"; root_disk="/dev/$(lsblk -no PKNAME "$root_src" 2>/dev/null | head -1)"
      mapfile -t cand < <(lsblk -dnpo NAME,TYPE | awk '$2=="disk"{print $1}' | grep -vx "$root_disk" || true)
      [ "${#cand[@]}" -eq 1 ] || die "found ${#cand[@]} candidate disks (${cand[*]:-none}); pass --state-device /dev/NAME"
      DEV="${cand[0]}"
    fi
    [ -b "$DEV" ] || die "--state-device is required on a real machine (a block device, or 'auto'); the state must not live on the system disk"
    fstype="$(blkid -p -o value -s TYPE "$DEV" 2>/dev/null || true)"
    if [ -z "$fstype" ]; then
      [ -z "$(lsblk -no NAME "$DEV" | tail -n +2)" ] || die "$DEV has partitions but no filesystem; not touching it"
      say "formatting blank disk $DEV as ext4 (label treeline-state)"
      mkfs.ext4 -q -L treeline-state "$DEV"
    elif [ "$fstype" != ext4 ] || [ "$(blkid -p -o value -s LABEL "$DEV")" != treeline-state ]; then
      die "$DEV already holds a $fstype filesystem that is not ours; not touching it"
    fi
    grep -q "LABEL=treeline-state" /etc/fstab || echo "LABEL=treeline-state $STATE ext4 defaults,noatime,nodev,nosuid 0 2" >> /etc/fstab
  fi
  systemctl daemon-reload
  mount "$STATE"
fi
mountpoint -q "$STATE" || die "$STATE is not a mount point; refusing to put state on the system disk"
# The top of the state disk is root's: the app user owns only its own folders inside it, so it can never swap a folder that a
# root-run tool (backup upload, certsync, the deploy agent) works in for a symlink to somewhere else (SECURITY.md R6-2).
chown root:root "$STATE"; chmod 0711 "$STATE"
install -d -m 0700 -o treeline -g treeline "$STATE/data" "$STATE/data/households"   # the databases (TREELINE_DB), households/, pre-migrate/
install -d -m 0700 -o root -g root "$STATE/backup" "$STATE/deploy"  # root's own records: what was uploaded, the deploy state
install -d -m 2750 -o treeline -g asterisk "$STATE/generated"
# Asterisk's pjsip.conf #includes this file, which the API writes when a handset is added; if it does not exist
# Asterisk refuses the WHOLE pjsip configuration (found by the CI job), so there must always be one.
[ -f "$STATE/generated/pjsip_handsets.conf" ] || install -m 0640 -o treeline -g asterisk /dev/null "$STATE/generated/pjsip_handsets.conf"
install -d -m 0700 -o caddy -g caddy "$STATE/caddy"
install -d -m 0700 -o treeline -g treeline "$STATE/spool"
# The admin page's helper (docs/ADMIN.md): the app may write requests in bridge/req and nowhere else here; the top is root's, so the
# app cannot swap req for a link. own-dir.py never follows a link and replaces whatever is not a plain folder.
python3 -I "$HERE/own-dir.py" 0755 root root "$STATE/bridge"
python3 -I "$HERE/own-dir.py" 0700 treeline treeline "$STATE/bridge/req"
# Everything Asterisk writes lives on the state disk, in asterisk.conf's directories: the contact database (phones' addresses and
# user agents), its spool and cache, and its logs (addresses, account names).
own_asterisk_state() {
  # Asterisk owns these folders, so a compromised Asterisk could replace one with a link and have root re-own and re-mode the target
  # on the next run of this script: own-dir.py never follows a link (SECURITY.md R10-5). The state disk's top is root's (above).
  python3 -I "$HERE/own-dir.py" 0750 asterisk asterisk "$STATE/asterisk" "$STATE/logs"
  python3 -I "$HERE/own-dir.py" 0750 asterisk asterisk "$STATE/asterisk/keys" "$STATE/asterisk/cache" "$STATE/asterisk/spool" "$STATE/logs/asterisk"
  # a purged package may have deleted and re-made the user under another uid: what it owned is re-owned, links are not followed
  chown -R --no-dereference asterisk:asterisk "$STATE/asterisk" "$STATE/logs/asterisk"
  chown -h treeline:asterisk "$STATE/generated" "$STATE/generated/pjsip_handsets.conf" 2>/dev/null || true
  install -d -m 0750 -o root -g asterisk /etc/asterisk /etc/asterisk/keys
}
own_asterisk_state

# ---------------------------------------------------------------- swap (on the state disk)
if [ "$CI" = 0 ]; then
  mem_kb="$(awk '/MemTotal/{print $2}' /proc/meminfo)"
  if [ "$mem_kb" -lt 1500000 ] && ! swapon --show=NAME --noheadings | grep -q treeline; then
    say "swap file (1 GiB) on the state disk"
    [ -f "$STATE/swapfile" ] || { ( umask 077; fallocate -l 1G "$STATE/swapfile" ); mkswap -q "$STATE/swapfile" >/dev/null; }
    chmod 600 "$STATE/swapfile"
    grep -q "$STATE/swapfile" /etc/fstab || echo "$STATE/swapfile none swap sw,x-systemd.requires-mounts-for=$STATE 0 0" >> /etc/fstab
    swapon "$STATE/swapfile" || true
  fi
fi

# ---------------------------------------------------------------- host settings (generated here, never committed)
say "host settings"
private_ip="$(ip -4 -o route get 1.1.1.1 | sed -n 's/.* src \([0-9.]*\).*/\1/p' | head -1)"   # repo-rules: allow (1.1.1.1 is only a route lookup target; nothing is sent to it)
[ -n "$private_ip" ] || die "could not find this machine's private address"
local_net="$(python3 -I -c 'import ipaddress,subprocess,sys; ip=sys.argv[1]
for line in subprocess.run(["ip","-4","-o","addr","show"],capture_output=True,text=True).stdout.splitlines():
    cidr=line.split()[3]
    if cidr.split("/")[0]==ip: print(ipaddress.ip_interface(cidr).network); break' "$private_ip")"
if [ -z "$PUBLIC_IP" ]; then
  # 1) instance metadata (not verified on Lightsail: see docs/DEPLOY_AWS.md), 2) DNS for our own host name
  PUBLIC_IP="$(curl -fsS -m 2 http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || true)"
  [[ "$PUBLIC_IP" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || PUBLIC_IP="$(getent ahostsv4 "$DOMAIN" 2>/dev/null | awk 'NR==1{print $1}')"
fi
if [ -z "$PUBLIC_IP" ]; then
  [ "$CI" = 1 ] && PUBLIC_IP="$private_ip" || die "could not find the public address; pass --public-ip (the static IP)"
fi
python3 -I -c 'import ipaddress,sys; ipaddress.IPv4Address(sys.argv[1])' "$PUBLIC_IP" || die "'$PUBLIC_IP' is not an IPv4 address"
{
  echo "TREELINE_DOMAIN=$DOMAIN"
  echo "TREELINE_MAIL_DOMAIN=$MAIL_DOMAIN"
  echo "TREELINE_AWS_REGION=${TREELINE_AWS_REGION:-us-west-2}"
  echo "TREELINE_PRIVATE_IP=$private_ip"
  echo "TREELINE_PUBLIC_IP=$PUBLIC_IP"
  echo "TREELINE_LOCAL_NET=$local_net"
  [ -z "$RELEASE_REPO" ] || echo "TREELINE_RELEASE_REPO=$RELEASE_REPO"
  [ -z "$RELEASE_BASE" ] || echo "TREELINE_RELEASE_BASE=$RELEASE_BASE"
  echo "TREELINE_DEPLOY_WINDOW_UTC=$WINDOW"
  [ -z "$ACME_DIR" ] || echo "TREELINE_ACME_DIR=$ACME_DIR"
  [ -z "$ACME_ROOT" ] || echo "TREELINE_ACME_ROOT=$ACME_ROOT"
  [ "$CI" = 0 ] || echo "TREELINE_CI=1"
} > "$ETC/host.env.new"; chmod 644 "$ETC/host.env.new"; mv "$ETC/host.env.new" "$ETC/host.env"
[ -z "$AWS_ENDPOINT" ] || { printf '%s\n' "$AWS_ENDPOINT" > "$ETC/aws-endpoint"; chmod 644 "$ETC/aws-endpoint"; }
# The trust anchor: written once. A release can never replace it (to rotate it, replace this file by hand).
if [ ! -s "$ETC/release_signers" ]; then install -m 0644 -o root -g root "$SIGNERS" "$ETC/release_signers"; fi
# The ARI password: generated here, used by Asterisk (ari.conf) and the app (via fetch-secrets); it never leaves the machine.
if [ ! -s "$ETC/ari-password" ]; then ( umask 077; openssl rand -base64 48 | tr -dc 'A-Za-z0-9' | head -c 40 > "$ETC/ari-password" ); fi
chmod 600 "$ETC/ari-password"

# ---------------------------------------------------------------- tools (outside any release)
say "tools"
install -d -m 0755 "$OPT/tools"
if [ ! -x "$OPT/tools/bin/python" ]; then python3 -m venv "$OPT/tools"; fi
"$OPT/tools/bin/pip" install --quiet --disable-pip-version-check --no-cache-dir --require-hashes --no-deps -r "$HERE/requirements-tools.lock"
for f in "$HERE"/bin/*; do install -m 0755 -o root -g root "$f" "$LIB/$(basename "$f")"; done
for t in treeline-deploy treeline-config treeline-certsync treeline-backup treeline-health treeline-admin; do ln -sf "$LIB/$t" "/usr/local/sbin/$t"; done
# The tools' shebang is the tools venv's Python; the library modules sit beside the scripts.
install -d -m 0755 /run/treeline
install -d -m 2750 -o root -g treeline /run/treeline/bridge     # the helper's answers (tmpfs); setgid: the app can read them, nobody else

# ---------------------------------------------------------------- systemd, journald, sysctl
say "services"
S="$HERE/systemd"
for unit in "$S"/*.service "$S"/*.timer "$S"/*.path; do
  [ "$(basename "$unit")" = asterisk.service ] || install -m 0644 "$unit" /etc/systemd/system/    # that one comes with the release, below
done
install -d /etc/systemd/system/caddy.service.d /etc/systemd/journald.conf.d
install -m 0644 "$HERE/logrotate/treeline-asterisk" /etc/logrotate.d/treeline-asterisk
install -m 0644 "$S/drop-ins/caddy.conf" /etc/systemd/system/caddy.service.d/treeline.conf
install -m 0644 "$S/journald-treeline.conf" /etc/systemd/journald.conf.d/treeline.conf
install -m 0644 "$S/tmpfiles-treeline.conf" /etc/tmpfiles.d/treeline.conf
install -m 0644 "$S/sysctl-treeline.conf" /etc/sysctl.d/60-treeline.conf
sysctl -q --system >/dev/null 2>&1 || true
systemctl restart systemd-journald || true
systemctl daemon-reload

# ---------------------------------------------------------------- fail2ban
if [ "$CI" = 0 ]; then
  say "fail2ban"
  install -m 0644 "$REL/deploy/fail2ban/filter.d/treeline-asterisk.conf" /etc/fail2ban/filter.d/treeline-asterisk.conf
  cat > /etc/fail2ban/jail.d/treeline-asterisk.local <<EOF
[treeline-asterisk]
enabled  = true
filter   = treeline-asterisk
backend  = polling
logpath  = $STATE/logs/asterisk/messages
maxretry = 8
findtime = 10m
bantime  = 1h
port     = 5061,443
EOF
  systemctl enable --now fail2ban >/dev/null 2>&1 || true
  systemctl restart fail2ban || true
fi

# ---------------------------------------------------------------- the first release, configuration, start
say "the release"
if [ ! -d "$OPT/releases/$(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' "$REL/release.json")" ]; then
  "$LIB/treeline-deploy" adopt "$REL"
fi
# The current release's own Asterisk build: installed (or its installed copy checked, file by file) by the agent, under its lock.
"$LIB/treeline-deploy" install-asterisk "$OPT/current"

say "Ubuntu's Asterisk"
# Only now, with the replacement in place: remove Ubuntu's package (1:20.6.0, with advisories it never fixed) and stop it coming
# back. A failure before this point leaves the old Asterisk running; one after it is repaired by running this script again.
mapfile -t ubuntu_ast < <(dpkg-query -W -f='${Package}\n' 'asterisk*' 2>/dev/null | sort -u)
if [ "${#ubuntu_ast[@]}" -gt 0 ]; then
  say "removing Ubuntu's packages: ${ubuntu_ast[*]}"
  systemctl stop asterisk 2>/dev/null || true
  systemctl disable asterisk 2>/dev/null || true
  apt-get purge -y -qq "${ubuntu_ast[@]}" >/dev/null
  apt-get autoremove -y -qq --purge >/dev/null
  rm -f /etc/systemd/system/asterisk.service.d/treeline.conf        # the old drop-in; treeline-config writes the new one
  [ ! -L /usr/share/asterisk/sounds/en ] || rm -f /usr/share/asterisk/sounds/en    # the package's alternatives link, left dangling (a real directory is ours)
  rm -rf /usr/share/asterisk/sounds/en_US_f_Allison
  ensure_asterisk_user
fi
printf 'Package: asterisk asterisk-*\nPin: version *\nPin-Priority: -1\n' > /etc/apt/preferences.d/treeline-asterisk
chmod 644 /etc/apt/preferences.d/treeline-asterisk
own_asterisk_state
install -d -m 0755 /usr/share/asterisk/sounds/en
say "sounds"
SOUNDS_SRC="$REL/asterisk/sounds" sh "$REL/asterisk/make_sounds.sh" >/dev/null

say "configuration"
"$LIB/treeline-config" apply --release "$OPT/current"
systemctl daemon-reload
systemctl enable asterisk caddy treeline-api treeline-controller treeline-certsync.timer treeline-deploy.timer treeline-backup.timer treeline-health.timer treeline-bridge.path treeline-bridge-sweep.timer >/dev/null 2>&1
if [ "$START" = 1 ]; then
  systemctl restart asterisk caddy
  systemctl start treeline-certsync.timer treeline-deploy.timer treeline-backup.timer treeline-health.timer treeline-bridge.path treeline-bridge-sweep.timer
  if [ -f "$ETC/aws-credentials" ]; then
    systemctl restart treeline-api treeline-controller
    say "started. Check: curl -fsS https://$DOMAIN/api/health"
  else
    say "Not started: $ETC/aws-credentials is missing. Install the VM key (infra/bootstrap/bootstrap.sh install-vm-key), then:"
    echo "    sudo systemctl start treeline-api treeline-controller"
  fi
fi
say "done"
