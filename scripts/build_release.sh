#!/usr/bin/env bash
# Build a Treeline release tarball (and, with --sign, its SSH signature).
#
#   scripts/build_release.sh v0.1.0 --asterisk FILE [--sign KEYFILE] [--out DIR] [--allow-dirty]
#
# The tarball holds what the VM runs: controller/, web/ (site + ui), asterisk/ (config, the build's inputs, and the Asterisk build
# itself in asterisk/runtime/), deploy/native/, release.json. The Asterisk build is not a tracked file: --asterisk FILE must be
# the artifact asterisk/build/artifact.lock names (same sha256 and size, and a tar the deploy agent's own validator accepts).
# It holds no environment-specific value and no secret (docs/REPO_RULES.md). It is reproducible: the same commit
# gives the same bytes (sorted names, fixed owner and mtime, no gzip timestamp). The signature is
# `ssh-keygen -Y sign -n treeline-release`; the VM verifies it against /etc/treeline/release_signers, which is set
# at install and is never part of a release (docs/DEPLOY_AWS.md, requirement 6).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
VERSION="${1:-}"; shift || true
SIGN_KEY=""; OUT="$ROOT/dist"; DIRTY=0; AST=""; UNLOCKED=0
while [ $# -gt 0 ]; do
  case "$1" in
    --sign) SIGN_KEY="${2:?--sign needs a key file}"; shift 2 ;;
    --out) OUT="${2:?--out needs a directory}"; shift 2 ;;
    --allow-dirty) DIRTY=1; shift ;;
    --asterisk) AST="${2:?--asterisk needs the artifact file}"; shift 2 ;;
    --asterisk-unlocked) AST="${2:?--asterisk-unlocked needs a file}"; UNLOCKED=1; shift 2 ;;   # tests only: refused with --sign
    *) echo "unknown option $1" >&2; exit 2 ;;
  esac
done
[[ "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+(-[a-z0-9.]+)?$ ]] || { echo "usage: $0 vMAJOR.MINOR.PATCH --asterisk FILE [--sign KEYFILE] [--out DIR] [--allow-dirty]" >&2; exit 2; }
[ -n "$AST" ] || { echo "a release carries its own Asterisk: pass --asterisk FILE (the artifact asterisk/build/artifact.lock names)" >&2; exit 2; }
[ -f "$AST" ] && [ ! -L "$AST" ] || { echo "$AST is not a regular file" >&2; exit 2; }
if [ "$UNLOCKED" = 1 ] && [ -n "$SIGN_KEY" ]; then
  echo "--asterisk-unlocked is for tests and cannot be combined with --sign: a signed release must carry the locked artifact" >&2; exit 2
fi
if [ "$DIRTY" = 0 ] && [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "the working tree has uncommitted changes; commit them or pass --allow-dirty (for local tests only)" >&2; exit 1
fi

# --allow-dirty (local tests) also takes files not committed yet; the .gitignore still keeps secrets and data out.
LS=(git ls-files); [ "$DIRTY" = 0 ] || LS=(git ls-files --cached --others --exclude-standard)
COMMIT="$(git rev-parse HEAD)"
EPOCH="${SOURCE_DATE_EPOCH:-$(git log -1 --format=%ct)}"
STAGE="$(mktemp -d)"; trap 'rm -rf "$STAGE"' EXIT
R="$STAGE/release"
mkdir -p "$R/controller" "$R/web" "$R/asterisk" "$R/deploy"

# ---- the Asterisk build (everything below must hold before a byte of it goes into a release)
if [ "$UNLOCKED" = 1 ]; then
  AST_ID="$(basename "$AST" | sed -n 's/^asterisk-\(.*\)\.tar\.gz$/\1/p')"
  [ -n "$AST_ID" ] || { echo "an unlocked artifact must be named asterisk-<id>.tar.gz" >&2; exit 2; }
else
  python3 -I scripts/asterisk_build.py check --require-lock >/dev/null
  AST_ID="$(python3 -I scripts/asterisk_build.py lock-field ARTIFACT_ID)"
  want_sha="$(python3 -I scripts/asterisk_build.py lock-field ARTIFACT_SHA256)"
  want_size="$(python3 -I scripts/asterisk_build.py lock-field ARTIFACT_SIZE)"
  [ "$(sha256sum "$AST" | cut -d' ' -f1)" = "$want_sha" ] || { echo "$AST is not the artifact asterisk/build/artifact.lock names (sha256 differs)" >&2; exit 1; }
  [ "$(stat -c %s "$AST")" = "$want_size" ] || { echo "$AST is not the size artifact.lock names" >&2; exit 1; }
fi
AST_SHA="$(sha256sum "$AST" | cut -d' ' -f1)"
# the same validator the deploy agent runs, so a release this script makes can never be one the agent refuses for its contents
python3 -I - "$AST" "$AST_ID" <<'PY'
import sys
sys.path.insert(0, "deploy/native/bin")
import treeline_release as rel
try:
    rel.asterisk_archive(open(sys.argv[1], "rb").read(), sys.argv[2])
except rel.ReleaseError as err:
    sys.exit("the Asterisk artifact is not acceptable: %s" % err)
PY
[ -z "$(git ls-files -- asterisk/runtime)" ] || { echo "asterisk/runtime/ must not hold tracked files: it is where the built artifact goes" >&2; exit 1; }
mkdir -p "$R/asterisk/runtime"
cp "$AST" "$R/asterisk/runtime/asterisk-$AST_ID.tar.gz"
cat > "$R/asterisk/SOURCE.txt" <<EOF
The Asterisk and pjproject in asterisk/runtime/ are free software (GNU GPL v2; the texts are in asterisk/licenses/).
Treeline changes nothing in their source: they are built from the upstream release tarballs pinned, with their sha256 and
upstream's signing key fingerprint, in asterisk/build/sources.lock, with the instructions in asterisk/build/ (build.sh,
modules.txt). That is the corresponding source for the binaries in this release.
EOF

# Only tracked files go in (git ls-files), so nothing local can leak into a release.
copy_tracked() {   # copy_tracked SRC_DIR DEST_DIR [exclude-regex]
  local src="$1" dest="$2" ex="${3:-^$}"
  mkdir -p "$dest"
  "${LS[@]}" -z -- "$src" | while IFS= read -r -d '' f; do
    rel="${f#"$src"/}"
    [[ "$rel" =~ $ex ]] && continue
    mkdir -p "$dest/$(dirname "$rel")"; cp -p "$f" "$dest/$rel"
  done
}
copy_tracked controller/treeline "$R/controller/treeline"
for f in run_controller.py backup.py make_vapid.py requirements.txt requirements-prod.lock; do
  # tracked files only, like everything else (an untracked local copy must never be signed and shipped)
  if [ -n "$("${LS[@]}" -- "controller/$f")" ]; then cp -p "controller/$f" "$R/controller/$f"; fi
done
copy_tracked web "$R/web/site" '^tests/'
copy_tracked design/ui "$R/web/ui"
copy_tracked asterisk "$R/asterisk" '^Dockerfile$|^entrypoint\.sh$|^runtime-deps\.txt$|^(dev|runtime)/'
copy_tracked deploy/native "$R/deploy/native" '^(tests|ci)/'
copy_tracked deploy/fail2ban "$R/deploy/fail2ban"
cp -p LICENSE THIRD_PARTY_NOTICES.md "$R/"

# What data layout this code expects: the deploy agent compares it with the files on disk (rollback safety).
SCHEMA="$(cd controller && python3 -I -c '
import json, sys
sys.path.insert(0, ".")
from treeline import db, households
print(json.dumps({"central": len(db.MIGRATIONS) + 1, "household": len(households.HOUSEHOLD_MIGRATIONS) + 1}))')"
python3 -I - "$VERSION" "$COMMIT" "$SCHEMA" "$AST_ID" "$AST_SHA" > "$R/release.json" <<'PY'
import json, sys
version, commit, schema, ast_id, ast_sha = sys.argv[1:6]
print(json.dumps({"version": version, "commit": commit, "schema": json.loads(schema), "format": 2,
                  "asterisk": {"id": ast_id, "sha256": ast_sha}}, indent=2, sort_keys=True))
PY

mkdir -p "$OUT"
TARBALL="$OUT/treeline-$VERSION.tar.gz"
tar --sort=name --owner=0 --group=0 --numeric-owner --mtime="@$EPOCH" --mode='u+rwX,go+rX,go-w' \
    -cf - -C "$R" . | gzip -n -9 > "$TARBALL"
echo "built $TARBALL ($(du -h "$TARBALL" | cut -f1), sha256 $(sha256sum "$TARBALL" | cut -d' ' -f1))"

if [ -n "$SIGN_KEY" ]; then
  rm -f "$TARBALL.sig"
  ssh-keygen -Y sign -q -f "$SIGN_KEY" -n treeline-release "$TARBALL"
  # Check what we just made, against the public half of the same key, before anyone is asked to trust it.
  pub="$(ssh-keygen -y -f "$SIGN_KEY")"
  printf 'treeline-release namespaces="treeline-release" %s\n' "$pub" > "$STAGE/signers"
  ssh-keygen -Y verify -f "$STAGE/signers" -I treeline-release -n treeline-release -s "$TARBALL.sig" < "$TARBALL" >/dev/null
  echo "signed $TARBALL.sig"
fi
