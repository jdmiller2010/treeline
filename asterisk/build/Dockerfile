# The toolchain image for the Asterisk build (asterisk/build/README.md). Built with the values in sources.lock:
#   docker build --build-arg BASE_IMAGE=... --build-arg APT_SNAPSHOT=... -f asterisk/build/Dockerfile asterisk/build
# It has network access while it is built (packages), and nothing in it runs third-party code except the packages'
# own install scripts. The Asterisk build itself runs later in `docker run --network none` (build.sh).
ARG BASE_IMAGE
FROM ${BASE_IMAGE}
ARG APT_SNAPSHOT
ENV DEBIAN_FRONTEND=noninteractive
COPY build-deps.txt /tmp/build-deps.txt
# The base image has no CA certificates, so the first install comes from its own archive (apt checks the signatures);
# every other package then comes from the Ubuntu archive as it was at APT_SNAPSHOT.
RUN test -n "${APT_SNAPSHOT}" \
 && apt-get update -qq && apt-get install -y -qq --no-install-recommends ca-certificates \
 && rm -f /etc/apt/sources.list.d/ubuntu.sources \
 && printf 'Types: deb\nURIs: https://snapshot.ubuntu.com/ubuntu/%s\nSuites: noble noble-updates noble-security\nComponents: main universe\nSigned-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg\n' "${APT_SNAPSHOT}" > /etc/apt/sources.list.d/snapshot.sources \
 && apt-get update -qq \
 && xargs -a /tmp/build-deps.txt apt-get install -y -qq --no-install-recommends \
 && rm -rf /var/lib/apt/lists/* /tmp/build-deps.txt \
 && useradd --uid 2000 --create-home --shell /bin/sh build
