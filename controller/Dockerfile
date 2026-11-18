FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY treeline treeline
COPY run_controller.py backup.py make_vapid.py ./
COPY tests tests

CMD ["python", "-u", "run_controller.py"]
