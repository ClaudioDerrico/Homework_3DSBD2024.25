from confluent_kafka import Consumer, Producer, KafkaException
import os
from common.database import SessionLocal
from common.models import User
from sqlalchemy import text
import json
import logging

logging.basicConfig(level=logging.CRITICAL)

consumer_config = {
    'bootstrap.servers': os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
    'group.id': 'alert_system_group',
    'auto.offset.reset': 'earliest',
    'enable.auto.commit': False
}

producer_config = {
    'bootstrap.servers': os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
}

consumer = Consumer(consumer_config)
producer = Producer(producer_config)

consumer.subscribe(['to-alert-system'])

def delivery_report(err, msg):
    if err is not None:
        print(f"Errore nell'inviare messaggio a to-notifier: {err}")
    else:
        print(f"Messaggio inviato a to-notifier offset {msg.offset()}")

while True:
    msg = consumer.poll(1.0)
    if msg is None:
        continue
    if msg.error():
            print(f"Consumer error: {msg.error()}")
            continue

    
    if msg.key() and msg.key().decode('utf-8') == 'update':
        print("AlertSystem: ricevuto segnale di update.")
        with SessionLocal() as session:
            
            users = session.query(User).all()
            for user in users:
                if user.ticker:
                  
                    latest_val = session.execute(
                        text('SELECT value FROM financial_data WHERE ticker=:ticker ORDER BY timestamp DESC LIMIT 1'),
                        {"ticker": user.ticker}
                    ).fetchone()

                    if latest_val:
                        value_ticker = latest_val[0]
                        hv = user.high_value
                        lv = user.low_value

                        
                        if hv is not None and value_ticker > hv and user.high_notification_sent==False:
                            alert = {"email": user.email, "ticker": user.ticker, "threshold_value":hv, "condition": "HIGH", "value_ticker": value_ticker}
                            producer.produce('to-notifier', json.dumps(alert).encode('utf-8'), callback=delivery_report)
                            user.high_notification_sent=True

                        if lv is not None and value_ticker < lv and user.low_notification_sent==False:
                            alert = {"email": user.email, "ticker": user.ticker,"threshold_value":lv, "condition": "LOW","value_ticker": value_ticker}
                            producer.produce('to-notifier', json.dumps(alert).encode('utf-8'), callback=delivery_report)
                            user.low_notification_sent=True

            session.commit()
            
            producer.flush()
        consumer.commit()