FROM python:3.9-slim
WORKDIR /app
COPY common/ common/
COPY alert_notifier_system/notifier.py .
COPY alert_notifier_system/alert_notifier_system.py .
RUN pip install confluent-kafka
RUN pip install --no-cache-dir prometheus_client
CMD ["python", "alert_notifier_system.py"]