import logging
import json
import base64
import pandas as pd
from kafka import KafkaConsumer, KafkaProducer
import joblib

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Consumer")

# Настройки Kafka
KAFKA_TOPIC = "network_logs"
ALERTS_TOPIC = "alerts"
consumer = KafkaConsumer(
    KAFKA_TOPIC,
    bootstrap_servers=['kafka:9093'],
    auto_offset_reset='earliest',
    group_id='consumer-group',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)
producer = KafkaProducer(
    bootstrap_servers=['kafka:9093'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Загрузка моделей и предобработчиков
try:
    rf_model = joblib.load("models/rf_model_new.pkl")
    dt_model = joblib.load("models/dt_model_new.pkl")
    encoder = joblib.load("models/encoder_new.pkl")
    scaler = joblib.load("models/scaler_new.pkl")
    feature_order = joblib.load("models/feature_order_new.pkl")
    logger.info("Модели и предобработчики успешно загружены")
    logger.info(f"Ожидаемые признаки модели (feature_order): {feature_order}")
except Exception as e:
    logger.error(f"Ошибка загрузки моделей: {e}")
    raise

def transform_log_to_features(log):
    payload_bytes = base64.b64decode(log["payload"])
    features = {
        "duration": 0,
        "protocol_type": "tcp" if log["protocol"] == 6 else "udp" if log["protocol"] == 17 else "icmp",
        "service": ("http" if log["dst_port"] == 80 else "https" if log["dst_port"] == 443 else 
                    "dns" if log["dst_port"] == 53 else "kafka" if log["dst_port"] == 9092 else "unknown"),
        "flag": "SF",
        "src_bytes": len(payload_bytes),
        "dst_bytes": 0,
        "land": 0,
        "wrong_fragment": 0,
        "urgent": 0,
        "hot": 0,
        "num_failed_logins": 0,
        "logged_in": 0,
        "num_compromised": 0,
        "root_shell": 0,
        "su_attempted": 0,
        "num_root": 0,
        "num_file_creations": 0,
        "num_shells": 0,
        "num_access_files": 0,
        "num_outbound_cmds": 0,
        "is_host_login": 0,
        "is_guest_login": 0,
        "count": 1,
        "srv_count": 1,
        "serror_rate": 0.0,
        "srv_serror_rate": 0.0,
        "rerror_rate": 0.0,
        "srv_rerror_rate": 0.0,
        "same_srv_rate": 1.0,
        "diff_srv_rate": 0.0,
        "srv_diff_host_rate": 0.0,
        "dst_host_count": 1,
        "dst_host_srv_count": 1,
        "dst_host_same_srv_rate": 1.0,
        "dst_host_diff_srv_rate": 0.0,
        "dst_host_same_src_port_rate": 1.0,
        "dst_host_srv_diff_host_rate": 0.0,
        "dst_host_serror_rate": 0.0,
        "dst_host_srv_serror_rate": 0.0,
        "dst_host_rerror_rate": 0.0,
        "dst_host_srv_rerror_rate": 0.0,
    }
    return pd.DataFrame([features])

def preprocess_features(df):
    cat_cols = ["protocol_type", "service", "flag"]
    num_cols = [col for col in df.columns if col not in cat_cols]
    
    # Кодирование категориальных признаков
    encoded = pd.DataFrame(encoder.transform(df[cat_cols]), columns=encoder.get_feature_names_out(cat_cols))
    
    # Масштабирование числовых признаков
    scaled_num = scaler.transform(df[num_cols])
    df_num = pd.DataFrame(scaled_num, columns=num_cols)
    
    # Объединение всех признаков
    final_data = pd.concat([df_num, encoded], axis=1)
    
    # Ограничение признаков до feature_order
    for col in feature_order:
        if col not in final_data.columns:
            final_data[col] = 0
    final_data = final_data[feature_order]
    
    logger.info(f"Количество признаков после обработки: {final_data.shape[1]}")
    if final_data.shape[1] != len(feature_order):
        raise ValueError(f"После обработки {final_data.shape[1]} признаков, ожидается {len(feature_order)}")
    return final_data

def main():
    logger.info("Запущен consumer")
    for message in consumer:
        try:
            log = message.value
            logger.info(f"Получен лог: {log}")
            
            # Преобразование и предобработка
            raw_features = transform_log_to_features(log)
            processed_features = preprocess_features(raw_features)
            
            # Предсказание
            rf_proba = rf_model.predict_proba(processed_features.values)[:, 1][0]
            dt_proba = dt_model.predict_proba(processed_features.values)[:, 1][0]
            avg_proba = (rf_proba + dt_proba) / 2
            attack_status = "ATTACK DETECTED" if avg_proba > 0.5 else "NORMAL"
            
            # Отправка результата
            alert = {
                "timestamp": log["timestamp"],
                "attack_status": attack_status,
                "rf_prediction": 1 if rf_proba > 0.5 else 0,
                "dt_prediction": 1 if dt_proba > 0.5 else 0,
                "src_ip": log["src_ip"],
                "dst_ip": log["dst_ip"],
                "src_port": log["src_port"],
                "dst_port": log["dst_port"],
                "protocol": log["protocol"]
            }
            producer.send(ALERTS_TOPIC, value=alert)
            producer.flush()
            logger.info(f"Отправлено оповещение: {alert}")
            
        except Exception as e:
            logger.error(f"Ошибка в обработке сообщения: {e}")
            raise

if __name__ == "__main__":
    main()