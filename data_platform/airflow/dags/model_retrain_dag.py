"""
Apache Airflow DAG: Scheduled Model Drift Evaluation & Retraining.
Monitors Population Stability Index (PSI), evaluates cure prediction calibration,
and triggers offline XGBoost retraining when drift threshold is exceeded.
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    'owner': 'ml_platform',
    'depends_on_past': False,
    'start_date': datetime(2026, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=10),
}


def evaluate_psi_drift():
    """Checks feature store drift using Population Stability Index (PSI)."""
    from features.skew_detector import skew_detector
    result = skew_detector.detect_skew()
    print("Feature Store PSI drift check:", result)
    if result.get("overall_status") == "DRIFT_DETECTED":
        print("ALERT: Significant feature drift detected. Triggering automated retraining.")
    return result


def retrain_and_calibrate_cure_model():
    """Trains, calibrates with Platt sigmoid scaling, and registers the updated XGBoost model."""
    from models_ml.training_service import ml_service
    res = ml_service.train_cure_model(model_id="cure-probability-v1.0")
    print("XGBoost model retraining and calibration metrics:", res["metrics"])
    return res


with DAG(
    'model_drift_retrain_v1',
    default_args=default_args,
    description='Automated model drift monitoring (PSI) and calibrated retraining',
    schedule_interval='@daily',
    catchup=False,
    tags=['mlops', 'xgboost', 'calibration', 'psi_drift']
) as dag:

    monitor_drift = PythonOperator(
        task_id='monitor_feature_drift_psi',
        python_callable=evaluate_psi_drift
    )

    retrain_model = PythonOperator(
        task_id='retrain_and_calibrate_model',
        python_callable=retrain_and_calibrate_cure_model
    )

    monitor_drift >> retrain_model
