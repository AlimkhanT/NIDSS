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
        logging.FileHandler("consumer.log"),  # Логи в файл
        logging.StreamHandler()  # Логи в консоль
    ]
)
logger = logging.getLogger(__name__)

# Настройки Kafka
BOOTSTRAP_SERVERS = 'kafka:9093'
TOPIC = 'test-topic'
GROUP_ID = 'webapp-group'

# Глобальные флаги и данные
producer_running = False
consumer_messages = []
consumer_lock = threading.Lock()

# Функция для ожидания Kafka
def wait_for_kafka():
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            producer = KafkaProducer(
                bootstrap_servers=BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            producer.close()
            logger.info("Successfully connected to Kafka")
            return True
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}/{max_attempts} - Failed to connect to Kafka: {e}")
            time.sleep(2)
    logger.error("Failed to connect to Kafka after maximum attempts")
    return False

# Создаём продюсера
def create_producer():
    try:
        return KafkaProducer(
            bootstrap_servers=BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
    except Exception as e:
        logger.error(f"Error creating producer: {e}")
        raise

# Функция для генерации тестовых транзакций
def produce_transactions():
    global producer_running
    producer = create_producer()
    i = 0
    while producer_running:
        transaction = {
            'transaction_id': i,
            'user_id': f'user_{i % 3}',
            'amount': round(i * 10.5, 2),
            'timestamp': int(time.time())
        }
        producer.send(TOPIC, transaction)
        logger.info(f"Sent transaction: {transaction}")
        i += 1
        time.sleep(1)
    producer.close()

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

# Простая "модель" для обработки транзакций
def predict_suspicious(transaction):
    amount = transaction['amount']
    is_suspicious = amount > 100
    return "Suspicious" if is_suspicious else "Normal"

# Функция для потребителя
def consume_transactions():
    consumer = create_consumer()
    for message in consumer:
        transaction = message.value
        status = predict_suspicious(transaction)
        result = {
            'transaction_id': transaction['transaction_id'],
            'user_id': transaction['user_id'],
            'amount': transaction['amount'],
            'status': status,
            'timestamp': transaction['timestamp']
        }
        with consumer_lock:
            consumer_messages.append(result)
        logger.info(f"Processed transaction: {result}")

# Главная страница
@app.route('/')
def index():
    return render_template('index.html')

# Эндпоинт для отправки транзакции через форму
@app.route('/send_transaction', methods=['POST'])
def send_transaction():
    try:
        transaction_id = int(request.form['transaction_id'])
        user_id = request.form['user_id']
        amount = float(request.form['amount'])
        
        transaction = {
            'transaction_id': transaction_id,
            'user_id': user_id,
            'amount': amount,
            'timestamp': int(time.time())
        }
        
        producer = create_producer()
        producer.send(TOPIC, transaction)
        producer.flush()
        producer.close()
        
        logger.info(f"Transaction sent via form: {transaction}")
        return {'status': 'success', 'message': 'Transaction sent successfully!'}
    except Exception as e:
        logger.error(f"Error sending transaction: {e}")
        return {'status': 'error', 'message': str(e)}, 500

# Эндпоинт для управления продюсером
@app.route('/toggle_producer', methods=['POST'])
def toggle_producer():
    global producer_running
    if not producer_running:
        producer_running = True
        threading.Thread(target=produce_transactions, daemon=True).start()
        logger.info("Producer started")
        return {'status': 'success', 'message': 'Producer started'}
    else:
        producer_running = False
        logger.info("Producer stopped")
        return {'status': 'success', 'message': 'Producer stopped'}

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