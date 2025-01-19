FROM python:3.9-slim
WORKDIR /app
COPY alert_system/alert_system.py . 
COPY common/ common/
RUN pip install sqlalchemy psycopg2-binary confluent-kafka
ENV DATABASE_URL=postgresql://Hw1:123ciao@database:5432/Hw1DB
CMD ["python", "alert_system.py"]
