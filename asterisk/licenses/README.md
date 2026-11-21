# Licenses of the Asterisk build

Treeline's releases carry a compiled Asterisk and the pjproject it bundles (asterisk/build/README.md). Both are free software
under the GNU General Public License, version 2; these are the texts shipped with the sources we build, copied unchanged from
the tarballs pinned in `asterisk/build/sources.lock` (Asterisk 24.0.0 and pjproject 2.17).

- `ASTERISK-COPYING.txt`, `ASTERISK-LICENSE.txt`: Asterisk's license and its notes on linking with OpenSSL.
- `PJPROJECT-COPYING.txt`: pjproject's license.

The corresponding source for what is shipped is the pinned upstream tarballs (URLs and sha256 in `asterisk/build/sources.lock`)
and the build instructions in `asterisk/build/` (`build.sh`, `modules.txt`): Treeline changes nothing in the source. Each release
also lists where to get both (`asterisk/SOURCE.txt` inside the release). This is our reading of the licenses, not legal advice.
