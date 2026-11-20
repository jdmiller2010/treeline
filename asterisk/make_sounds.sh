#!/bin/sh
# Build the operator messages. Placeholder voice first, then any real
# recordings from /sounds-src win over it.
set -e
OUT="${SOUNDS_OUT:-/usr/share/asterisk/sounds/en/treeline}"
TMP="${TMPDIR:-/tmp}"
mkdir -p "$OUT"
while IFS='|' read -r name text; do
  [ -z "$name" ] && continue
  espeak-ng -v en-us+f3 -s 135 -p 35 -w "$TMP/$name.raw.wav" "$text"
  sox "$TMP/$name.raw.wav" -r 8000 -c 1 -b 16 "$OUT/$name.wav" gain -n -3 pad 0.3 0.2
  rm "$TMP/$name.raw.wav"
done < "${SOUNDS_SRC:-/sounds-src}/messages.txt"
for f in "${SOUNDS_SRC:-/sounds-src}"/*.wav; do
  [ -e "$f" ] && cp "$f" "$OUT/"
done
echo "built:" && ls "$OUT"
