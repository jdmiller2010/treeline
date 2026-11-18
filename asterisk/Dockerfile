FROM ubuntu:24.04

RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      asterisk asterisk-core-sounds-en \
 && rm -rf /var/lib/apt/lists/*

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# SIP and call audio. Keep the RTP range in sync with config/rtp.conf.
EXPOSE 5060/udp 10000-10100/udp 8088/tcp

ENTRYPOINT ["/entrypoint.sh"]
