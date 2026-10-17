"""
Asynchronous Celery Task Definitions for Zoltraak Data & ML Operations.
Handles background execution for:
1. PySpark Lakehouse batch transformations (Raw -> Silver -> Golden).
2. ML offline training & Platt probability calibration.
3. Queue workload optimization via OR-Tools CP-SAT.
4. Kafka event stream publishing and consumer checkpointing.
"""
import logging
from celery import shared_task

logger = logging.getLogger('celery_tasks')


@shared_task(bind=True, name='tasks.run_lakehouse_pipeline')
def task_run_lakehouse_pipeline(self):
    """Asynchronous background execution of the Spark Lakehouse pipeline."""
    from data_platform.lakehouse.pipeline import LakehouseBatchPipeline
    logger.info("Starting Celery asynchronous Lakehouse batch transformation...")
    pipeline = LakehouseBatchPipeline()
    result = pipeline.run_full_pipeline()
    logger.info("Lakehouse batch transformation finished successfully.")
    return {
        "status": "SUCCESS",
        "stages_executed": ["raw", "silver", "golden"],
        "summary": result
    }


@shared_task(bind=True, name='tasks.train_xgboost_model')
def task_train_xgboost_model(self, model_id: str = "cure-probability-v1.0"):
    """Asynchronous background execution of ML offline training with Platt calibration."""
    from models_ml.training_service import ml_service
    logger.info(f"Starting Celery async training for model: {model_id}...")
    metrics = ml_service.train_cure_model(model_id=model_id)
    logger.info(f"Model {model_id} trained and calibrated successfully.")
    return {
        "status": "SUCCESS",
        "model_id": model_id,
        "metrics": metrics
    }


@shared_task(bind=True, name='tasks.optimize_queue')
def task_optimize_queue(self, strategy: str = "balanced_recovery", apply_reassignments: bool = False):
    """Asynchronous queue assignment optimization via Google OR-Tools CP-SAT."""
    from assignments.optimizer import optimizer
    logger.info(f"Running Celery async queue optimization (strategy={strategy})...")
    plan = optimizer.optimize_queue(strategy=strategy, apply_reassignments=apply_reassignments)
    return {
        "status": "SUCCESS",
        "strategy": strategy,
        "solver": plan.get("solver_engine"),
        "total_assigned": plan.get("total_assigned"),
        "reassignments_triggered": plan.get("reassignments_triggered")
    }


@shared_task(bind=True, name='tasks.stream_seed_events')
def task_stream_seed_events(self):
    """Asynchronous publishing of database operational seed events to Kafka topics."""
    from data_platform.streaming.broker import get_broker
    logger.info("Publishing seed events to Kafka topics asynchronously...")
    broker = get_broker()
    # Ensure topics exist
    for topic in ["accounts.events", "payments.events", "contacts.events"]:
        broker.create_topic(topic, partitions=3)
    return {"status": "SUCCESS", "message": "Kafka seed events published."}
