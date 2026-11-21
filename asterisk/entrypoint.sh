#!/bin/sh
# Lay the project's Asterisk config over /etc/asterisk, then run Asterisk in the foreground as the asterisk user, with no
# capabilities. Edit files in asterisk/config, then `docker compose restart asterisk` to pick them up.
#
# The container starts as root only to prepare directories; Asterisk never runs as root.
set -e
: "${ASTERISK_ID:?this image was built without ASTERISK_ID}"
PREFIX="/opt/asterisk/$ASTERISK_ID"
mkdir -p /etc/asterisk
rm -f /etc/asterisk/*.conf
cp /kidphone-config/*.conf /etc/asterisk/
sed "s|@PREFIX@|$PREFIX|g" /asterisk.conf.in > /etc/asterisk/asterisk.conf
mkdir -p /generated /run/asterisk /var/lib/asterisk /var/cache/asterisk /var/spool/asterisk /var/log/asterisk
[ -f /generated/pjsip_handsets.conf ] || : > /generated/pjsip_handsets.conf
chmod 0644 /generated/pjsip_handsets.conf
chown asterisk:asterisk /run/asterisk /var/lib/asterisk /var/cache/asterisk /var/spool/asterisk /var/log/asterisk
chown -R root:asterisk /etc/asterisk
chmod 0750 /etc/asterisk
chmod 0640 /etc/asterisk/*.conf
umask 0027
exec setpriv --reuid=asterisk --regid=asterisk --clear-groups --no-new-privs --inh-caps=-all --bounding-set=-all \
  "$PREFIX/sbin/asterisk" -f -vvv -C /etc/asterisk/asterisk.conf
