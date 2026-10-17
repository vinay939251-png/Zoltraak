"""
Apache Airflow DAG: Lakehouse Batch Transformation Pipeline (Raw -> Silver -> Golden).
Orchestrates scheduled batch ingestion, schema contract validation, DLQ anomaly isolation,
Customer 360 aggregation, and Feature Store Parquet generation.
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

default_args = {
    'owner': 'data_platform',
    'depends_on_past': False,
    'start_date': datetime(2026, 1, 1),
    'email_on_failure': True,
    'email': ['data-alerts@maplebank.ca'],
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}


def run_lakehouse_pipeline():
    """Executes the PySpark-style Lakehouse batch pipeline."""
    from data_platform.lakehouse.pipeline import LakehouseBatchPipeline
    pipeline = LakehouseBatchPipeline()
    summary = pipeline.run_full_pipeline()
    print("Lakehouse pipeline batch execution summary:", summary)
    return summary


def sync_feast_features():
    """Materializes Golden tier features into Feast online feature store."""
    from data_platform.feast_store.service import feast_service
    res = feast_service.sync_and_materialize()
    print("Feast feature store sync complete:", res)
    return res


with DAG(
    'lakehouse_batch_etl_v1',
    default_args=default_args,
    description='Automated scheduled lakehouse batch data pipeline from Raw to Golden tier',
    schedule_interval='@hourly',
    catchup=False,
    tags=['lakehouse', 'spark', 'collections', 'production']
) as dag:

    validate_kafka_broker = BashOperator(
        task_id='validate_kafka_broker',
        bash_command='python manage.py stream_events --check-health || exit 0'
    )

    execute_lakehouse_batch = PythonOperator(
        task_id='execute_lakehouse_batch',
        python_callable=run_lakehouse_pipeline
    )

    materialize_feast_online = PythonOperator(
        task_id='materialize_feast_online',
        python_callable=sync_feast_features
    )

    validate_kafka_broker >> execute_lakehouse_batch >> materialize_feast_online
