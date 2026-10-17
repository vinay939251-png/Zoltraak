"""
Kafka Producer implementation with schema contract validation and partition hashing.
"""
from dataclasses import dataclass
from typing import Dict, Any, Optional, List

from .contracts import EventContractRegistry, registry, EventContractValidationError
from .broker import KafkaBroker, broker


@dataclass
class RecordMetadata:
    topic: str
    partition: int
    offset: int
    timestamp: int


class KafkaProducer:
    """Enterprise-grade event publisher enforcing schema contracts and key partitioning."""

    TOPIC_ROUTING = {
        "payment.received": "collections.payments",
        "payment.reversed": "collections.payments",
        "promise.created": "collections.promises",
        "promise.updated": "collections.promises",
        "call.completed": "collections.calls",
        "hardship.flagged": "collections.cases",
        "dispute.opened": "collections.cases",
        "identity.match.proposed": "collections.identity",
        "decision.created": "collections.decisions",
        "decision.approved": "collections.decisions",
        "decision.overridden": "collections.decisions",
        "action.completed": "collections.decisions"
    }

    def __init__(self, broker_instance: Optional[KafkaBroker] = None, contract_registry: Optional[EventContractRegistry] = None):
        self.broker = broker_instance or broker
        self.registry = contract_registry or registry

    def resolve_topic(self, event_type: str, explicit_topic: Optional[str] = None) -> str:
        if explicit_topic:
            return explicit_topic
        return self.TOPIC_ROUTING.get(event_type, "collections.events")

    def send(
        self,
        value: Dict[str, Any],
        topic: Optional[str] = None,
        key: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        partition: Optional[int] = None
    ) -> RecordMetadata:
        """
        Validates event against registered contracts and writes to the appropriate topic partition.
        """
        # Validate schema contract
        is_valid, error = self.registry.validate(value)
        if not is_valid:
            raise EventContractValidationError(f"Kafka schema validation failure: {error}")

        event_type = value.get("eventType")
        target_topic = self.resolve_topic(event_type, topic)

        # Derive partition key if not provided (e.g. from accountId or sourceRecordId)
        routing_key = key or value.get("accountId") or value.get("sourceRecordId") or value.get("recommendationId")
        if routing_key is not None:
            routing_key = str(routing_key)

        target_partition = partition
        if target_partition is None:
            target_partition = self.broker.hash_partition(target_topic, routing_key)

        part_log = self.broker.get_partition(target_topic, target_partition)
        record = part_log.append(key=routing_key, value=value, headers=headers)

        return RecordMetadata(
            topic=record.topic,
            partition=record.partition,
            offset=record.offset,
            timestamp=record.timestamp
        )

    def send_batch(self, events: List[Dict[str, Any]], topic: Optional[str] = None) -> List[RecordMetadata]:
        """Publishes a batch of events in atomic order."""
        return [self.send(evt, topic=topic) for evt in events]
