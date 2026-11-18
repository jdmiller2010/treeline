#!/bin/sh
# Is Treeline up? Exits 0 if the database answers and Asterisk is reachable.
# Run it every minute from cron on another machine, or point a monitor (for
# example healthchecks.io or UptimeRobot) at  https://YOUR-DOMAIN/api/health
# which answers 200 when all is well and 503 when Asterisk can't be reached.
#
#   * * * * * /path/to/uptime-check.sh phone.example.com || echo "Treeline is down" | mail -s Treeline you@example.com
set -eu
host="${1:?usage: uptime-check.sh phone.example.com}"
curl -fsS -m 10 "https://$host/api/health" >/dev/null
