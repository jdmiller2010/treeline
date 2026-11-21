#!/bin/bash
# Build Asterisk from the pinned, verified source. Runs INSIDE the toolchain image, as an ordinary user, with
# `docker run --network none` (asterisk/build/run-build.sh does that). Nothing here is ever run on the VM.
#
#   /in   (read only)  sources.lock, asterisk-release-key.asc, modules.txt, the Asterisk and pjproject tarballs and
#                      Asterisk's signature file, all fetched and hash-checked by run-build.sh already
#   /out  (writable)   asterisk-<BUILD_ID>.tar.gz (the artifact), asterisk-<BUILD_ID>.bom.txt
#
# This is the one place third-party code is configured and compiled (CLAUDE.md, "Second exception").
set -euo pipefail
IN="${IN:-/in}"; OUT="${OUT:-/out}"; WORK="${WORK:-/work}"
die() { echo "build.sh: $*" >&2; exit 1; }

lock() {   # lock KEY: one value from sources.lock, which is read as data and never sourced
  local v; v="$(grep -E "^$1=" "$IN/sources.lock" | head -n1 | cut -d= -f2-)"
  [ -n "$v" ] || die "sources.lock has no $1"; printf '%s' "$v"
}
AST_VER="$(lock ASTERISK_VERSION)"; AST_SHA="$(lock ASTERISK_SHA256)"; AST_SIZE="$(lock ASTERISK_SIZE)"; FPR="$(lock ASTERISK_KEY_FPR)"
PJ_VER="$(lock PJPROJECT_VERSION)"; PJ_SHA="$(lock PJPROJECT_SHA256)"; PJ_MD5="$(lock PJPROJECT_MD5)"; PJ_SIZE="$(lock PJPROJECT_SIZE)"
BUILD_ID="$(lock BUILD_ID)"; EPOCH="$(lock SOURCE_DATE_EPOCH)"
[[ "$AST_VER" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "bad ASTERISK_VERSION"
[[ "$PJ_VER" =~ ^[0-9]+\.[0-9]+(\.[0-9]+)?$ ]] || die "bad PJPROJECT_VERSION"
[[ "$BUILD_ID" =~ ^[0-9]+\.[0-9]+\.[0-9]+-t[0-9]+$ ]] || die "bad BUILD_ID"
[[ "$EPOCH" =~ ^[0-9]+$ ]] || die "bad SOURCE_DATE_EPOCH"
[[ "$FPR" =~ ^[0-9A-F]{40}$ ]] || die "bad ASTERISK_KEY_FPR"
AST_TAR="$IN/asterisk-$AST_VER.tar.gz"; PJ_TAR="$IN/pjproject-$PJ_VER.tar.bz2"
PREFIX="/opt/asterisk/$BUILD_ID"
mkdir -p "$OUT" "$WORK"; cd "$WORK"

echo "[${SECONDS}s] == 1. verify the inputs again, inside the sealed container"
for f in "$AST_TAR" "$PJ_TAR"; do [ -f "$f" ] || die "missing $f"; done
[ "$(stat -c %s "$AST_TAR")" = "$AST_SIZE" ] || die "Asterisk tarball size differs from sources.lock"
[ "$(stat -c %s "$PJ_TAR")" = "$PJ_SIZE" ] || die "pjproject tarball size differs from sources.lock"
echo "$AST_SHA  $AST_TAR" | sha256sum -c --status || die "Asterisk tarball sha256 differs from sources.lock"
echo "$PJ_SHA  $PJ_TAR" | sha256sum -c --status || die "pjproject tarball sha256 differs from sources.lock"
echo "$PJ_MD5  $PJ_TAR" | md5sum -c --status || die "pjproject tarball md5 differs from sources.lock"

# The signature: a throwaway keyring holding only the committed key, whose fingerprint must be the pinned one.
export GNUPGHOME="$WORK/gnupg"; mkdir -m 700 "$GNUPGHOME"
gpg --batch --quiet --import "$IN/asterisk-release-key.asc" 2>/dev/null
[ "$(gpg --batch --with-colons --fingerprint | awk -F: '/^fpr:/{print $10}' | head -n1)" = "$FPR" ] \
  || die "the committed key is not the pinned fingerprint"
gpg --batch --export > "$WORK/keyring.gpg"
STATUS="$(gpgv --keyring "$WORK/keyring.gpg" --status-fd 1 "$IN/asterisk-$AST_VER.tar.gz.asc" "$AST_TAR" 2>/dev/null)" \
  || die "the Asterisk signature does not verify"
grep -q "^\[GNUPG:\] VALIDSIG $FPR " <<<"$STATUS" || die "the Asterisk signature is not from the pinned key"
echo "   sha256, size, md5 and the signature (key $FPR) are good"

echo "[${SECONDS}s] == 2. unpack, and check what the signed tarball itself says about pjproject"
tar --no-same-owner -xzf "$AST_TAR"
SRC="$WORK/asterisk-$AST_VER"; [ -d "$SRC" ] || die "the tarball has no asterisk-$AST_VER directory"
grep -qx "PJPROJECT_VERSION=$PJ_VER" "$SRC/third-party/versions.mak" || die "versions.mak pins another pjproject than sources.lock"
[ "$(awk '{print $1}' "$SRC/third-party/pjproject/pjproject-$PJ_VER.tar.bz2.md5")" = "$PJ_MD5" ] \
  || die "the md5 inside the signed tarball differs from sources.lock"
mkdir "$WORK/cache"; cp "$PJ_TAR" "$WORK/cache/"   # a verified copy where Asterisk's own build looks first

echo "[${SECONDS}s] == 3. a sealed, repeatable environment"
# A fake downloader: configure insists on finding one, so any attempt to fetch something fails the build.
# `date`, `uname` and `id` are what Asterisk stamps into build.h: fixed here so a second build can match this one.
SHIM="$WORK/shims"; mkdir "$SHIM"
printf '#!/bin/sh\necho "build.sh: a network fetch was attempted: wget $*" >&2\nexit 1\n' > "$SHIM/wget"
cat > "$SHIM/date" <<SH
#!/bin/sh
for a in "\$@"; do case "\$a" in -u|--utc) exec /usr/bin/date -u -d "@$EPOCH" "+%Y-%m-%d %H:%M:%S" ;; esac; done
exec /usr/bin/date "\$@"
SH
printf '#!/bin/sh\ncase "$1" in -n) echo treeline-build;; -r) echo 0;; *) /usr/bin/uname "$@";; esac\n' > "$SHIM/uname"
# make_build_h also records who ran the build (`id` with no arguments): a runner's user and a developer's are different.
cat > "$SHIM/id" <<'SH'
#!/bin/sh
[ "$#" -eq 0 ] && { echo "uid=2000(build) gid=2000(build) groups=2000(build)"; exit 0; }
exec /usr/bin/id "$@"
SH
chmod 755 "$SHIM"/*
export PATH="$SHIM:$PATH" SOURCE_DATE_EPOCH="$EPOCH" TZ=UTC LC_ALL=C
# PJSIP_DONT_SWITCH_TO_TLS=1: pjproject 2.17's advisory GHSA-j4c2-253v-jgxw (a crash in pjsip_get_dest_info() when a dialog's
# route set holds a non-SIP URI) has no released fix; its documented workaround is this compile-time setting, which only
# turns off the automatic switch to TLS for sips: addresses, which Treeline does not use. It reaches pjproject through CFLAGS.
export CFLAGS="-O2 -ffile-prefix-map=$WORK=/build -DPJSIP_DONT_SWITCH_TO_TLS=1"
export LDFLAGS="-Wl,-z,relro,-z,now"

echo "[${SECONDS}s] == 4. configure"
cd "$SRC"
./configure --prefix="$PREFIX" --sysconfdir=/etc --localstatedir=/var \
  --with-externals-cache="$WORK/cache" --without-jansson-bundled --without-libjwt-bundled \
  --disable-dev-mode >"$WORK/configure.log" 2>&1 || { tail -40 "$WORK/configure.log" >&2; die "configure failed"; }

echo "[${SECONDS}s] == 5. choose the modules"
make menuselect/menuselect menuselect-tree >"$WORK/menuselect-build.log" 2>&1 || { tail -30 "$WORK/menuselect-build.log" >&2; die "menuselect did not build"; }
# menuselect rewrites menuselect.makeopts with the defaults whenever it runs WITHOUT that file as an argument (even
# for --category-list), so the category list is read once, here, before anything is chosen, and the result is read
# back by reading the file itself (it lists, per category, the modules that are switched OFF).
CATS=()
while read -r c; do
  case "$c" in MENUSELECT_CFLAGS|MENUSELECT_CHANNELSTORAGE) ;; *) CATS+=("$c") ;; esac   # build options, not modules
done < <(menuselect/menuselect --category-list)
[ "${#CATS[@]}" -ge 15 ] || die "menuselect lists only ${#CATS[@]} categories"
# Only these categories are loadable modules, so only they are held to modules.txt. The helper programs (UTILS) and
# AGI scripts are not modules and some cannot be switched off here: what ships from them is decided when packing.
MODCATS=(MENUSELECT_ADDONS MENUSELECT_APPS MENUSELECT_BRIDGES MENUSELECT_CDR MENUSELECT_CEL MENUSELECT_CHANNELS
         MENUSELECT_CODECS MENUSELECT_FORMATS MENUSELECT_FUNCS MENUSELECT_PBX MENUSELECT_RES)
for c in "${MODCATS[@]}"; do printf '%s\n' "${CATS[@]}" | grep -qx "$c" || die "menuselect has no category $c"; done
ALL="$(for c in "${MODCATS[@]}"; do menuselect/menuselect --list-category "$c" | awk '{print $2}'; done | sort -u)"
rm -f menuselect.makeopts menuselect.makedeps
MS=(menuselect/menuselect)
for c in "${CATS[@]}"; do MS+=(--disable-category "$c"); done
MS+=(--disable BUILD_NATIVE)   # no CPU-specific code: the runner and the VM are different machines
WANT="$(grep -vE '^[[:space:]]*(#|$)' "$IN/modules.txt" | sort -u)"
[ -n "$WANT" ] || die "modules.txt is empty"
for m in $WANT; do MS+=(--enable "$m"); done
"${MS[@]}" menuselect.makeopts >/dev/null
menuselect/menuselect --check-deps menuselect.makeopts >/dev/null
# Every module we asked for must have survived the dependency check, and nothing else may be enabled.
# The file has one line per category listing what is switched off, MENUSELECT_DEPSFAILED lines for modules whose
# libraries are missing (so they cannot build at all), and MENUSELECT_BUILD_DEPS (not a list of disabled modules).
CATRE="^($(IFS='|'; echo "${MODCATS[*]}"))$"
OFF="$( { awk -F= -v re="$CATRE" '$1 ~ re {print $2}' menuselect.makeopts | tr ' ' '\n'
          awk -F= -v re="$CATRE" '$1 == "MENUSELECT_DEPSFAILED" && $2 ~ re {print $3}' menuselect.makeopts; } | grep . | sort -u)"
ENABLED="$(comm -23 <(echo "$ALL") <(echo "$OFF"))"
[ "$ENABLED" = "$WANT" ] || { echo "modules.txt (<) vs what menuselect enabled (>):" >&2; diff <(echo "$WANT") <(echo "$ENABLED") >&2 || true; die "the enabled modules are not exactly modules.txt"; }

echo "[${SECONDS}s] == 6. compile"
make -j"$(nproc)" >"$WORK/make.log" 2>&1 || { tail -60 "$WORK/make.log" >&2; die "make failed"; }
if grep -q "build.sh: a network fetch" "$WORK/make.log" "$WORK/configure.log"; then die "something tried to download"; fi

echo "[${SECONDS}s] == 7. install into a staging tree and pack only what belongs to the artifact"
DEST="$WORK/dest"
make install DESTDIR="$DEST" >"$WORK/install.log" 2>&1 || { tail -40 "$WORK/install.log" >&2; die "make install failed"; }
ROOT="$DEST$PREFIX"; [ -d "$ROOT" ] || die "nothing was installed under $PREFIX"
# Only the daemon and its console ship from sbin/. The helper scripts (safe_asterisk, astgenkey, autosupport, the core dump and
# log grabbers) are not used, and the manual pages are not needed on a server.
rm -rf "$ROOT/share/man" "$ROOT/bin"
find "$ROOT/sbin" -mindepth 1 -not -name asterisk -not -name rasterisk -delete
[ "$(ls "$ROOT/sbin" | sort | tr '\n' ' ')" = "asterisk rasterisk " ] || die "sbin/ is not exactly asterisk and rasterisk: $(ls "$ROOT/sbin")"
find "$ROOT" -type f \( -name '*.so' -o -perm -u+x \) -exec sh -c 'file -b "$1" | grep -q "^ELF" && strip --strip-unneeded "$1"' _ {} \; 2>/dev/null || true
echo "[${SECONDS}s]    checks on what was built"
# Things Treeline relies on that would otherwise be lost without a sound: each was true of the real build when this was written.
# (grep reads all of its input and discards the output: `grep -q` would exit early, the writer would get SIGPIPE, and
# `pipefail` would call that a failure.)
PJ="$SRC/third-party/pjproject/source"
contains() { grep -F -- "$1" >/dev/null; }          # contains TEXT < input
grep -F "PJSIP_DONT_SWITCH_TO_TLS=1" "$PJ/build.mak" >/dev/null || die "PJSIP_DONT_SWITCH_TO_TLS=1 did not reach pjproject's build"
grep -F "PJSIP_DONT_SWITCH_TO_TLS" "$PJ/pjsip/include/pjsip/sip_config.h" >/dev/null || die "this pjproject has no PJSIP_DONT_SWITCH_TO_TLS setting any more"
objdump -p "$ROOT/sbin/asterisk" | grep 'NEEDED.*libsystemd' >/dev/null || die "asterisk was built without systemd support (the unit is Type=notify)"
strings -a "$ROOT/lib/asterisk/modules/res_pjsip.so" | contains "Request '%s' from '%s' failed for '%s' (callid: %s) - %s" \
  || die "the log line fail2ban's filter matches is not in res_pjsip.so"
strings -a "$ROOT/lib/asterisk/modules/res_rtp_asterisk.so" | contains "icesupport" || die "ICE support was compiled out of res_rtp_asterisk"
while IFS= read -r f; do
  file -b "$f" | grep '^ELF' >/dev/null || continue
  readelf -lW "$f" | grep GNU_RELRO >/dev/null || die "$f has no RELRO"
  readelf -dW "$f" | grep BIND_NOW >/dev/null || die "$f is not linked with BIND_NOW"
  if readelf -lW "$f" | grep GNU_STACK | grep RWE >/dev/null; then die "$f has an executable stack"; fi
done < <(find "$ROOT" -type f)
INSTALLED="$(find "$ROOT/lib/asterisk/modules" -name '*.so' -printf '%f\n' | sed 's/\.so$//' | sort -u)"
[ "$INSTALLED" = "$WANT" ] || { diff <(echo "$WANT") <(echo "$INSTALLED") >&2 || true; die "the installed modules are not exactly modules.txt"; }
# Asterisk's data directory defaults to /var/lib/asterisk. ARI needs rest-api/ and the CLI needs the XML documentation at
# run time, so they travel inside the artifact (asterisk.conf's astdatadir points at <prefix>/share/asterisk); the sample web
# files, images and helper scripts are not used and are dropped.
DATA="$DEST/var/lib/asterisk"
mkdir -p "$ROOT/share/asterisk"
for d in documentation rest-api; do
  [ -d "$DATA/$d" ] || die "expected $DATA/$d from make install"
  mv "$DATA/$d" "$ROOT/share/asterisk/$d"
done
rm -rf "$DATA/images" "$DATA/static-http" "$DATA/scripts"
OUTSIDE="$(cd "$DEST" && find . -mindepth 1 \( -type f -o -type l \) -not -path "./${PREFIX#/}/*" | sort)"
[ -z "$OUTSIDE" ] || { echo "installed outside $PREFIX:" >&2; echo "$OUTSIDE" >&2; die "files outside the prefix: decide where they belong (asterisk/build/README.md)"; }

ART="$OUT/asterisk-$BUILD_ID.tar.gz"
( cd "$DEST" && tar --sort=name --owner=0 --group=0 --numeric-owner --mtime="@$EPOCH" --format=gnu -cf - "${PREFIX#/}" ) \
  | gzip -9n > "$ART"

echo "[${SECONDS}s] == 8. the bill of materials"
{
  echo "asterisk $AST_VER  pjproject $PJ_VER  build $BUILD_ID  source-date-epoch $EPOCH"
  echo "artifact sha256 $(sha256sum "$ART" | cut -d' ' -f1)"
  echo "-- modules"; echo "$INSTALLED"
  echo "-- needed shared libraries (soname  package)"
  find "$ROOT" -type f -exec sh -c 'file -b "$1" | grep -q "^ELF" && objdump -p "$1" | awk "/NEEDED/{print \$2}"' _ {} \; | sort -u |
    while read -r so; do p="$(dpkg -S "*/$so" 2>/dev/null | head -n1 | cut -d: -f1 || true)"; echo "$so  ${p:-(ours)}"; done
} > "$OUT/asterisk-$BUILD_ID.bom.txt"
echo "built $ART"
