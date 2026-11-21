# The dev Asterisk: the same artifact production runs (asterisk/build/artifact.lock), not Ubuntu's package.
# `./dev up` finds or builds the artifact, checks it against artifact.lock, and puts it in asterisk/runtime/ for this COPY.
FROM ubuntu:24.04

ARG ASTERISK_ID
ARG ASTERISK_SHA256
ENV ASTERISK_ID=${ASTERISK_ID}

# The runtime libraries the artifact needs, plus what renders the operator messages.
COPY runtime-deps.txt /tmp/runtime-deps.txt
RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends espeak-ng sox $(grep -vE '^[[:space:]]*(#|$)' /tmp/runtime-deps.txt) \
 && rm -rf /var/lib/apt/lists/* /tmp/runtime-deps.txt

# The artifact unpacks at / into /opt/asterisk/<id>; the build is only trusted if it is the one artifact.lock names.
COPY runtime/asterisk-${ASTERISK_ID}.tar.gz /tmp/asterisk.tar.gz
RUN test -n "${ASTERISK_ID}" && echo "${ASTERISK_SHA256}  /tmp/asterisk.tar.gz" | sha256sum -c - \
 && tar -xzf /tmp/asterisk.tar.gz -C / \
 && rm /tmp/asterisk.tar.gz \
 && useradd --system --uid 1500 --user-group --no-create-home --shell /usr/sbin/nologin asterisk \
 && ln -s /usr/share/asterisk/sounds /opt/asterisk/${ASTERISK_ID}/share/asterisk/sounds

# Operator messages (placeholder voice; real recordings in sounds/ win).
COPY sounds /sounds-src
COPY make_sounds.sh /make_sounds.sh
RUN mkdir -p /usr/share/asterisk/sounds/en && sh /make_sounds.sh && rm /make_sounds.sh

COPY dev/asterisk.conf /asterisk.conf.in
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# SIP and call audio. Keep the RTP range in sync with config/rtp.conf.
EXPOSE 5060/udp 10000-10100/udp 8088/tcp

ENTRYPOINT ["/entrypoint.sh"]
