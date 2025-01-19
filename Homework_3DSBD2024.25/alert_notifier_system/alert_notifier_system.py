from confluent_kafka import Consumer, KafkaException
import os
import json
from notifier import send_email

import prometheus_client
from prometheus_client import Counter, start_http_server
import socket
HOSTNAME = socket.gethostname()
SERVICE_LABEL = "alert_notifier_system"  # servizio che stiamo monitorando


NUM_EMAIL_COUNTER = Counter(
    'num_email_total',
    'Numero di email inviate agli utenti',
    ['service', 'node']
)


consumer_config = {
    'bootstrap.servers': os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
    'group.id': 'alert_notifier_group',
    'auto.offset.reset': 'earliest',
    'enable.auto.commit': True
}

consumer = Consumer(consumer_config)
consumer.subscribe(['to-notifier'])


try:
    start_http_server(8002)
    print("Prometheus metrics disponibili su porta 8002")
    while True:

        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            print(f"E' stato rilevato un errore dal consumatore: {msg.error()}")
            continue

        data = json.loads(msg.value().decode('utf-8'))
        email = data['email']
        ticker = data['ticker']
        ThresholdValue = data['threshold_value']
        ChoosenThreshold = data['condition']
        value_ticker_registered = data['value_ticker']

        NUM_EMAIL_COUNTER.labels(service=SERVICE_LABEL, node=HOSTNAME).inc()
        print(f"Incrementato num_email_total: {NUM_EMAIL_COUNTER.labels(service=SERVICE_LABEL, node=HOSTNAME)._value.get()}")
        send_email(email, ticker, ThresholdValue, ChoosenThreshold, value_ticker_registered)
except KeyboardInterrupt:
    print("Processo interrotto dall'utente")
finally:
    consumer.close()