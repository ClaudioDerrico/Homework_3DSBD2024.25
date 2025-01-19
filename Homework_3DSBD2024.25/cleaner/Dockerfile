FROM python:3.9-slim

WORKDIR /app

COPY cleaner/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY cleaner/ .

COPY common/ ./common

ENV PYTHONUNBUFFERED=1

CMD ["python", "cleaner.py"]