FROM ubuntu:24.04

RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      asterisk asterisk-core-sounds-en espeak-ng sox \
 && rm -rf /var/lib/apt/lists/*

# Operator messages (placeholder voice; real recordings in sounds/ win).
COPY sounds /sounds-src
COPY make_sounds.sh /make_sounds.sh
RUN sh /make_sounds.sh && rm /make_sounds.sh

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# SIP and call audio. Keep the RTP range in sync with config/rtp.conf.
EXPOSE 5060/udp 10000-10100/udp 8088/tcp

ENTRYPOINT ["/entrypoint.sh"]
