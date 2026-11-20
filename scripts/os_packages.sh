#!/usr/bin/env bash
# The Ubuntu packages a fresh Treeline VM ends up with, for the bill of materials (scripts/sbom.py --os-packages).
#
#   scripts/os_packages.sh > os-packages.tsv
#
# It installs exactly the packages deploy/native/install.sh installs (the list is read from that script, never kept
# twice) into a throwaway ubuntu:24.04 container and prints every installed package: binary name, version, source
# package, source version, architecture, tab-separated. Nothing from the container is run on this machine.
#
# What this is and is not: it is what a VM installed TODAY would have. A VM installed last month has whatever
# unattended-upgrades has brought it to since; the VM's own truth is `dpkg-query -W` on the VM (docs/SUPPLY_CHAIN.md).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
pkgs="$(python3 "$ROOT/scripts/sbom.py" --apt-packages | tr '\n' ' ')"
[ -n "$pkgs" ] || { echo "os_packages: no package list" >&2; exit 2; }
# The names were checked against [a-z0-9+.-] by sbom.py; they are passed as arguments, never pasted into the script.
# shellcheck disable=SC2086
docker run --rm ubuntu:24.04 sh -c '
set -e
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq >/dev/null
apt-get install -y -qq --no-install-recommends "$@" >/dev/null 2>&1 || { echo "os_packages: apt-get install failed" >&2; exit 1; }
dpkg-query -W -f "\${binary:Package}\t\${Version}\t\${source:Package}\t\${source:Version}\t\${Architecture}\n"
' _ $pkgs
