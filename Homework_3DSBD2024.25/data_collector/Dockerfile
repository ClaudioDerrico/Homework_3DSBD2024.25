FROM python:3.9-slim

WORKDIR /app

COPY data_collector/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir prometheus_client

COPY data_collector/ .

COPY common/ ./common

ENV PYTHONUNBUFFERED=1

RUN pip install confluent-kafka

CMD ["python", "collector.py"]
