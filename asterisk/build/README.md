# The Asterisk build

Production runs an upstream Asterisk that we compile from the signed source tarball, not Ubuntu's `asterisk` package
(which has dozens of advisories and no fixed version: docs/SECURITY.md, R8-1). This directory holds everything that
decides what the compiled result is. It is the only place third-party code is configured and compiled
(CLAUDE.md, "Second exception"), and it never happens on the VM.

| File | What it is |
|---|---|
| `sources.lock` | The pins: Asterisk and pjproject (url, size, sha256, md5), the upstream signing key's fingerprint, the base image digest, the Ubuntu snapshot date, the build number |
| `asterisk-release-key.asc` | The upstream release signing key. Changing it is a trust-anchor change and needs the owner's review |
| `modules.txt` | The modules that get built, and only those. Fewer modules, fewer advisories that apply |
| `Dockerfile`, `build-deps.txt` | The toolchain image: the pinned Ubuntu image with build packages from a dated archive snapshot |
| `run-build.sh` | Fetches the sources (https only), checks their hashes, builds the toolchain image, runs `build.sh` in a container |
| `build.sh` | The build itself. Runs in a container with **no network**, no capabilities and a read-only root |
| `artifact.lock` | The sha256 and size of the artifact production runs, plus a digest of every other file here |

## How it is made safe

1. `run-build.sh` downloads over https, then insists on the sha256 and size in `sources.lock`. A changed upstream file fails.
2. `build.sh` checks them again inside the container, then checks Asterisk's GPG signature (`gpgv`) against the committed
   key, whose fingerprint must be the pinned one, and checks that the pjproject checksum inside the signed tarball is the
   pinned one.
3. Asterisk normally downloads pjproject while building. Here the verified tarball is put where Asterisk looks first, and a
   fake `wget` that always fails makes the build fail if anything else tries to fetch. The container has no network
   anyway.
4. menuselect turns every category off, then enables `modules.txt`. The build fails if the enabled set, or the set that
   ends up installed, is anything but exactly that list.
5. Only released upstream code is built. Nothing is patched. Where an upstream advisory has no released fix, the answer is a
   documented option, or an entry in `.vuln-ignore` with a reason (docs/SECURITY.md, Review 9).

## What the artifact contains

One tarball, `asterisk-<BUILD_ID>.tar.gz`, holding only `opt/asterisk/<BUILD_ID>/`: `sbin/asterisk` and `sbin/rasterisk`, the
modules in `lib/asterisk/modules/` plus `libasteriskpj` and `libasteriskssl`, and `share/asterisk/` with the ARI definition
files (`rest-api/`) and the XML documentation. Binaries are stripped and look for their libraries in
`/opt/asterisk/<BUILD_ID>/lib` (a RUNPATH), so it must be unpacked at `/`, and several versions can sit side by side.
Nothing else ships: no configuration (`/etc/asterisk` is Treeline's own, written at install), no sounds, no helper scripts,
no manual pages. The build also writes `asterisk-<BUILD_ID>.bom.txt`: the module list and the shared libraries the binaries
need, with the Ubuntu package each comes from, which is what `install.sh` must install.

Asterisk's compiled-in directories point at `/etc`, `/var` and `/var/lib/asterisk`; the artifact does not rely on them. The
installed `asterisk.conf` sets every directory explicitly, including `astdatadir`.

Measured on 2026-11-20: a build takes about a minute on 16 CPUs and a little over a minute on 4, the artifact is 3.5 MB, and
builds with different CPU counts give the same bytes.

## Changing it

Edit the inputs, run `asterisk/build/run-build.sh`, and run it again to check the two builds give the same bytes.
`python3 scripts/asterisk_build.py check` (also part of `./dev check`) fails whenever a file here changed after
`artifact.lock` was written, so a new artifact has to be built, published and recorded
(`python3 scripts/asterisk_build.py write-lock FILE`) before anything that changes the result can be merged and released.
Bump `BUILD_ID` (`24.0.0-t1` to `24.0.0-t2`) whenever the instructions change but the Asterisk version does not.

## Moving to a new Asterisk

Change `ASTERISK_*` and `PJPROJECT_*` in `sources.lock` together (pjproject's version is in the new tarball's
`third-party/versions.mak`, and its md5 beside it), and fetch the new `.asc` to check it verifies. Read the release's
ChangeLog and UPGRADE notes for what Treeline depends on: the ARI module reload, `tone:` names, `md5_cred`,
`default_realm`, `ice_host_candidates`, `external_media_address`. Then run `./dev sip` and `./dev web`.
