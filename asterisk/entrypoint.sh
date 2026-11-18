#!/bin/sh
# Copy the project's Asterisk config over the package defaults, then run
# Asterisk in the foreground. Edit files in asterisk/config, then
# `docker compose restart asterisk` to pick them up.
set -e
cp /kidphone-config/*.conf /etc/asterisk/
mkdir -p /generated
[ -f /generated/pjsip_handsets.conf ] || : > /generated/pjsip_handsets.conf
exec asterisk -f -vvv
