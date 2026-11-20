#!/bin/bash
# Build the Asterisk artifact: fetch the pinned sources, check them, then run build.sh in a sealed container.
#
#   asterisk/build/run-build.sh [OUT_DIR]        (default: dist/asterisk)
#
# Used by CI (.github/workflows/asterisk.yml) and by the dev image. It needs Docker and nothing else; it never runs
# anything it downloaded outside the container, and the container has no network when the build starts.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
OUT="${1:-$ROOT/dist/asterisk}"
CACHE="${ASTERISK_SRC_CACHE:-$ROOT/.cache/asterisk-src}"
die() { echo "run-build.sh: $*" >&2; exit 1; }
lock() { local v; v="$(grep -E "^$1=" "$HERE/sources.lock" | head -n1 | cut -d= -f2-)"; [ -n "$v" ] || die "sources.lock has no $1"; printf '%s' "$v"; }

AST_VER="$(lock ASTERISK_VERSION)"; PJ_VER="$(lock PJPROJECT_VERSION)"
AST_TAR="asterisk-$AST_VER.tar.gz"; PJ_TAR="pjproject-$PJ_VER.tar.bz2"
mkdir -p "$CACHE" "$OUT"
OUT="$(cd "$OUT" && pwd)"   # docker reads a relative path as a volume name
CACHE="$(cd "$CACHE" && pwd)"

fetch() {   # fetch URL FILE SHA256 SIZE: download only when the file is missing or wrong, then insist it is right
  local url="$1" file="$CACHE/$2" sha="$3" size="$4"
  if ! { [ -f "$file" ] && echo "$sha  $file" | sha256sum -c --status; }; then
    case "$url" in https://*) ;; *) die "refusing a non-https source: $url" ;; esac
    curl -fsSL --proto '=https' --tlsv1.2 --retry 3 -A "treeline-build" -o "$file.part" "$url"; mv "$file.part" "$file"
  fi
  echo "$sha  $file" | sha256sum -c --status || die "$2 does not match the sha256 in sources.lock"
  [ "$(stat -c %s "$file")" = "$size" ] || die "$2 is not the size in sources.lock"
}
fetch "$(lock ASTERISK_URL)" "$AST_TAR" "$(lock ASTERISK_SHA256)" "$(lock ASTERISK_SIZE)"
fetch "$(lock PJPROJECT_URL)" "$PJ_TAR" "$(lock PJPROJECT_SHA256)" "$(lock PJPROJECT_SIZE)"
# The signature file has no pin of its own: it is checked against the pinned key, so a wrong one fails there.
SIG="$CACHE/$AST_TAR.asc"
[ -s "$SIG" ] || curl -fsSL --proto '=https' --tlsv1.2 --retry 3 -A "treeline-build" -o "$SIG" "$(lock ASTERISK_SIG_URL)"

# The toolchain image, tagged by everything that goes into it, so a changed pin builds a new one.
TAG="treeline-asterisk-toolchain:$( (cat "$HERE/Dockerfile" "$HERE/build-deps.txt"; lock BASE_IMAGE; lock APT_SNAPSHOT) | sha256sum | cut -c1-16)"
if ! docker image inspect "$TAG" >/dev/null 2>&1; then
  docker build -q -t "$TAG" --build-arg BASE_IMAGE="$(lock BASE_IMAGE)" --build-arg APT_SNAPSHOT="$(lock APT_SNAPSHOT)" \
    -f "$HERE/Dockerfile" "$HERE" >/dev/null
fi

# What the container sees: exactly the inputs, read only.
IN="$(mktemp -d)"; trap 'rm -rf "$IN"' EXIT
cp "$HERE/sources.lock" "$HERE/asterisk-release-key.asc" "$HERE/modules.txt" "$IN/"
cp "$CACHE/$AST_TAR" "$CACHE/$PJ_TAR" "$IN/"; cp "$SIG" "$IN/$AST_TAR.asc"
chmod 755 "$IN"; chmod 644 "$IN"/*

# ASTERISK_BUILD_CPUS (for example 0-3) limits the CPUs the build sees: used to check the result does not depend on them.
docker run --rm --network none ${ASTERISK_BUILD_CPUS:+--cpuset-cpus "$ASTERISK_BUILD_CPUS"} --hostname treeline-build --user "$(id -u):$(id -g)" -e HOME=/tmp \
  --cap-drop ALL --security-opt no-new-privileges --read-only --tmpfs /tmp --tmpfs /work:exec,size=6g \
  -v "$IN:/in:ro" -v "$OUT:/out" -v "$HERE/build.sh:/build.sh:ro" "$TAG" /build.sh
echo "artifact: $OUT/asterisk-$(lock BUILD_ID).tar.gz"
