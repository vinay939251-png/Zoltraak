"""
Data Platform package initialization.
Provides Kafka-compatible event streaming and PySpark-compatible lakehouse batch processing.
"""
from pathlib import Path

DATA_PLATFORM_DIR = Path(__file__).resolve().parent
REPO_ROOT = DATA_PLATFORM_DIR.parent
LAKEHOUSE_ROOT = REPO_ROOT / "data" / "lakehouse"
KAFKA_BROKER_ROOT = REPO_ROOT / ".work" / "kafka_broker"

__version__ = "1.0.0"
