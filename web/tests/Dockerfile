# Browser tests that need the Docker stack (real Asterisk, real WebRTC).
#   docker compose run --rm webtests                 # tablet softphone calls
#   docker compose run --rm webtests smoke.py        # the parent app
#   docker compose run --rm webtests phone_ui.py     # the softphone's screen
FROM mcr.microsoft.com/playwright/python:v1.55.0-noble
RUN pip install --no-cache-dir --break-system-packages playwright==1.55.0
WORKDIR /t
COPY *.py ./
ENTRYPOINT ["python", "-u"]
CMD ["phone_calls.py"]
