import pandas as pd
import numpy as np
import logging
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.utils import resample
from sklearn.metrics import f1_score
import joblib

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FEATURES = [
    'duration', 'protocol_type', 'service', 'flag', 'src_bytes', 'dst_bytes', 
    'land', 'wrong_fragment', 'urgent', 'hot', 'num_failed_logins', 'logged_in',
    'num_compromised', 'root_shell', 'su_attempted', 'num_root', 'num_file_creations',
    'num_shells', 'num_access_files', 'num_outbound_cmds', 'is_host_login', 
    'is_guest_login', 'count', 'srv_count', 'serror_rate', 'srv_serror_rate',
    'rerror_rate', 'srv_rerror_rate', 'same_srv_rate', 'diff_srv_rate',
    'srv_diff_host_rate', 'dst_host_count', 'dst_host_srv_count',
    'dst_host_same_srv_rate', 'dst_host_diff_srv_rate', 'dst_host_same_src_port_rate',
    'dst_host_srv_diff_host_rate', 'dst_host_serror_rate', 'dst_host_srv_serror_rate',
    'dst_host_rerror_rate', 'dst_host_srv_rerror_rate'
]

def preprocess(data, is_train=True, keep_label=True):
    cat_cols = ["protocol_type", "service", "flag"]
    num_cols = [col for col in FEATURES if col not in cat_cols]
    
    label = data["label"].copy() if keep_label and "label" in data.columns else None
    
    if is_train:
        encoder = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
        encoded = pd.DataFrame(encoder.fit_transform(data[cat_cols]))
        encoded.columns = encoder.get_feature_names_out(cat_cols)
        joblib.dump(encoder, "encoder.pkl")
    else:
        encoder = joblib.load("encoder.pkl")
        try:
            encoded = pd.DataFrame(encoder.transform(data[cat_cols]))
            encoded.columns = encoder.get_feature_names_out(cat_cols)
        except ValueError as e:
            logger.error(f"Ошибка кодирования: {str(e)}")
            encoded = pd.DataFrame(0, index=range(len(data)), 
                                 columns=encoder.get_feature_names_out(cat_cols))
    
    data = data.drop(columns=cat_cols + ["difficulty"], errors='ignore')
    if not keep_label and "label" in data.columns:
        data = data.drop(columns=["label"])
    
    if is_train:
        scaler = StandardScaler()
        data[num_cols] = scaler.fit_transform(data[num_cols])
        joblib.dump(scaler, "scaler.pkl")
        feature_order = num_cols + list(encoded.columns)
        joblib.dump(feature_order, "feature_order.pkl")
    else:
        scaler = joblib.load("scaler.pkl")
        feature_order = joblib.load("feature_order.pkl")
        for col in num_cols:
            if col not in data.columns:
                data[col] = 0
        data[num_cols] = scaler.transform(data[num_cols])
    
    final_data = pd.concat([data[num_cols], encoded], axis=1)
    
    if not is_train:
        for col in feature_order:
            if col not in final_data.columns:
                final_data[col] = 0
    
    final_data = final_data[feature_order]
    
    if label is not None:
        final_data["label"] = label
        
    return final_data

def main():
    # Загрузка данных
    logger.info("Загрузка KDDCup датасета...")
    data = pd.read_csv("kddcup.data_10_percent_corrected", names=[
        "duration", "protocol_type", "service", "flag", "src_bytes", "dst_bytes", 
        "land", "wrong_fragment", "urgent", "hot", "num_failed_logins", "logged_in",
        "num_compromised", "root_shell", "su_attempted", "num_root", "num_file_creations",
        "num_shells", "num_access_files", "num_outbound_cmds", "is_host_login", 
        "is_guest_login", "count", "srv_count", "serror_rate", "srv_serror_rate",
        "rerror_rate", "srv_rerror_rate", "same_srv_rate", "diff_srv_rate",
        "srv_diff_host_rate", "dst_host_count", "dst_host_srv_count",
        "dst_host_same_srv_rate", "dst_host_diff_srv_rate", "dst_host_same_src_port_rate",
        "dst_host_srv_diff_host_rate", "dst_host_serror_rate", "dst_host_srv_serror_rate",
        "dst_host_rerror_rate", "dst_host_srv_rerror_rate", "label"
    ])

    # Заполнение пропущенных значений
    data = data.fillna(0)

    # Проверка категориальных признаков
    logger.info(f"Уникальные значения protocol_type: {data['protocol_type'].unique()}")
    logger.info(f"Уникальные значения service: {data['service'].unique()}")
    logger.info(f"Уникальные значения flag: {data['flag'].unique()}")

    # Преобразование меток
    data["label"] = data["label"].apply(lambda x: 0 if x == "normal." else 1)

    # Балансировка классов
    normal = data[data["label"] == 0]
    attack = data[data["label"] == 1]
    logger.info(f"До балансировки: Нормальных={len(normal)}, Атак={len(attack)}")
    attack_downsampled = resample(attack, replace=False, n_samples=len(normal), random_state=42)
    balanced_data = pd.concat([normal, attack_downsampled])
    logger.info(f"После балансировки: Нормальных={len(normal)}, Атак={len(attack_downsampled)}")

    # Предобработка
    X = balanced_data.drop(columns=["label"])
    y = balanced_data["label"]
    X_processed = preprocess(X, is_train=True, keep_label=False)

    # Проверка диапазонов признаков
    logger.info(f"Диапазон duration в обучающих данных: {X_processed['duration'].min()} - {X_processed['duration'].max()}")
    logger.info(f"Диапазон src_bytes в обучающих данных: {X_processed['src_bytes'].min()} - {X_processed['src_bytes'].max()}")
    logger.info(f"Диапазон dst_bytes в обучающих данных: {X_processed['dst_bytes'].min()} - {X_processed['dst_bytes'].max()}")

    # Разделение данных
    X_train, X_test, y_train, y_test = train_test_split(X_processed, y, test_size=0.2, random_state=42)

    # Обучение моделей
    logger.info("Обучение моделей...")
    rf_model = RandomForestClassifier(class_weight="balanced", random_state=42)
    dt_model = DecisionTreeClassifier(class_weight="balanced", max_depth=10, min_samples_split=10, random_state=42)

    rf_model.fit(X_train, y_train)
    dt_model.fit(X_train, y_train)

    # Сохранение моделей
    joblib.dump(rf_model, "rf_model.pkl")
    joblib.dump(dt_model, "dt_model.pkl")

    # Оценка моделей
    logger.info(f"RandomForest accuracy: {rf_model.score(X_test, y_test)}")
    logger.info(f"DecisionTree accuracy: {dt_model.score(X_test, y_test)}")
    logger.info(f"RandomForest F1-score: {f1_score(y_test, rf_model.predict(X_test))}")
    logger.info(f"DecisionTree F1-score: {f1_score(y_test, dt_model.predict(X_test))}")

    # Кросс-валидация
    rf_scores = cross_val_score(rf_model, X_processed, y, cv=5, scoring='f1')
    dt_scores = cross_val_score(dt_model, X_processed, y, cv=5, scoring='f1')
    logger.info(f"RandomForest F1-score (cross-validation): {rf_scores.mean()}")
    logger.info(f"DecisionTree F1-score (cross-validation): {dt_scores.mean()}")

if __name__ == "__main__":
    main()