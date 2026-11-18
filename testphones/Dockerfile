FROM ubuntu:24.04

RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      baresip-core python3 tzdata \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /tests
COPY run_scenarios.py .

ENTRYPOINT ["python3", "-u", "run_scenarios.py"]
