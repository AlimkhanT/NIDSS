from flask import Flask, render_template, Response, request
from kafka import KafkaProducer, KafkaConsumer
import json
import threading
import time
import logging
import os

app = Flask(__name__)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("consumer.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Настройки Kafka
BOOTSTRAP_SERVERS = 'kafka:9093'
TOPIC = 'alerts'  # Топик, куда consumer-1 отправляет результаты
GROUP_ID = 'webapp-group'

# Глобальные флаги и данные
consumer_messages = []
consumer_lock = threading.Lock()

# Функция для ожидания Kafka
def wait_for_kafka():
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            consumer = KafkaConsumer(
                TOPIC,
                bootstrap_servers=BOOTSTRAP_SERVERS,
                group_id=GROUP_ID,
                auto_offset_reset='latest',
                value_deserializer=lambda x: json.loads(x.decode('utf-8'))
            )
            consumer.close()
            logger.info("Successfully connected to Kafka")
            return True
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}/{max_attempts} - Failed to connect to Kafka: {e}")
            time.sleep(2)
    logger.error("Failed to connect to Kafka after maximum attempts")
    return False

# Создаём потребителя
def create_consumer():
    try:
        return KafkaConsumer(
            TOPIC,
            bootstrap_servers=BOOTSTRAP_SERVERS,
            group_id=GROUP_ID,
            auto_offset_reset='latest',
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
    except Exception as e:
        logger.error(f"Error creating consumer: {e}")
        raise

# Функция для потребителя
def consume_transactions():
    consumer = create_consumer()
    for message in consumer:
        result = message.value
        with consumer_lock:
            consumer_messages.append(result)
        logger.info(f"Processed alert: {result}")

# Главная страница
@app.route('/')
def index():
    return render_template('index.html')

# Эндпоинт для получения сообщений в реальном времени через SSE
@app.route('/stream')
def stream():
    def generate():
        last_index = 0
        while True:
            with consumer_lock:
                if last_index < len(consumer_messages):
                    for i in range(last_index, len(consumer_messages)):
                        yield f"data: {json.dumps(consumer_messages[i])}\n\n"
                    last_index = len(consumer_messages)
            time.sleep(0.5)
    return Response(generate(), mimetype='text/event-stream')

# Запускаем приложение
if __name__ == '__main__':
    logger.info("Starting Flask application...")
    if wait_for_kafka():
        threading.Thread(target=consume_transactions, daemon=True).start()
        app.run(host='0.0.0.0', port=5000, debug=False)
    else:
        logger.error("Application failed to start due to Kafka connection issues")
        exit(1)