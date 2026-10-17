"""
Kafka-compatible event streaming package.
Provides topic management, partitioned commit logs, consumer groups, and schema-validated producers/consumers.
"""
from .contracts import EventContractRegistry, registry, EventContractValidationError
from .storage import PartitionLog, MessageRecord
from .broker import KafkaBroker, broker
from .producer import KafkaProducer
from .consumer import KafkaConsumer

__all__ = [
    "EventContractRegistry",
    "registry",
    "EventContractValidationError",
    "PartitionLog",
    "MessageRecord",
    "KafkaBroker",
    "broker",
    "KafkaProducer",
    "KafkaConsumer",
]
