#!/bin/sh
# Copy the project's Asterisk config over the package defaults, then run
# Asterisk in the foreground. Edit files in asterisk/config, then
# `docker compose restart asterisk` to pick them up.
#
# In production, /kidphone-config-prod (deploy/asterisk) is laid over the top,
# and @DOMAIN@ and @ARI_PASS@ in it are filled in from the environment.
set -e
cp /kidphone-config/*.conf /etc/asterisk/
if [ -d /kidphone-config-prod ]; then
  cp /kidphone-config-prod/*.conf /etc/asterisk/
  : "${TREELINE_DOMAIN:?set TREELINE_DOMAIN}" "${ARI_PASS:?set ARI_PASS}"
  esc() { printf '%s' "$1" | sed 's/[&|\\]/\\&/g'; }
  sed -i "s|@DOMAIN@|$(esc "$TREELINE_DOMAIN")|g; s|@ARI_PASS@|$(esc "$ARI_PASS")|g" /etc/asterisk/*.conf
fi
mkdir -p /generated
[ -f /generated/pjsip_handsets.conf ] || : > /generated/pjsip_handsets.conf
exec asterisk -f -vvv
