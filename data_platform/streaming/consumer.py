"""
Kafka Consumer implementation supporting consumer groups, offset commits, and DLQ routing.
"""
from typing import Dict, Any, List, Optional, Set

from .broker import KafkaBroker, broker
from .storage import MessageRecord


class KafkaConsumer:
    """Group-aware Kafka consumer with partition offset tracking and dead-letter queue routing."""

    def __init__(
        self,
        group_id: str,
        topics: Optional[List[str]] = None,
        broker_instance: Optional[KafkaBroker] = None,
        auto_offset_reset: str = "earliest",
        enable_auto_commit: bool = True
    ):
        self.group_id = group_id
        self.broker = broker_instance or broker
        self.auto_offset_reset = auto_offset_reset
        self.enable_auto_commit = enable_auto_commit
        self.topics: List[str] = topics or []
        # In-memory cursor: (topic, partition) -> current_offset
        self._current_offsets: Dict[tuple, int] = {}
        self._processed_event_ids: Set[str] = set()

        if self.topics:
            self._init_offsets()

    def subscribe(self, topics: List[str]):
        """Subscribes this consumer to a list of topics."""
        self.topics = topics
        self._init_offsets()

    def _init_offsets(self):
        for topic in self.topics:
            num_p = self.broker.get_partition_count(topic)
            for p in range(num_p):
                committed = self.broker.get_committed_offset(self.group_id, topic, p)
                self._current_offsets[(topic, p)] = committed

    def poll(self, max_records: int = 50) -> List[MessageRecord]:
        """
        Polls assigned topic partitions for newly available records starting from the current offset.
        """
        records: List[MessageRecord] = []
        if not self.topics:
            return records

        for topic in self.topics:
            num_p = self.broker.get_partition_count(topic)
            for p in range(num_p):
                cursor = self._current_offsets.get((topic, p), 0)
                part_log = self.broker.get_partition(topic, p)
                batch = part_log.read(start_offset=cursor, max_messages=max_records - len(records))

                for r in batch:
                    records.append(r)
                    self._current_offsets[(topic, p)] = r.offset + 1
                    if len(records) >= max_records:
                        break

                if len(records) >= max_records:
                    break
            if len(records) >= max_records:
                break

        if self.enable_auto_commit and records:
            self.commit()

        return records

    def commit(self):
        """Persists the current offset positions to the broker coordinator."""
        for (topic, p), offset in self._current_offsets.items():
            self.broker.commit_offset(self.group_id, topic, p, offset)

    def seek(self, topic: str, partition: int, offset: int):
        """Allows seeking/replaying from a specific offset."""
        self._current_offsets[(topic, partition)] = offset
        self.commit()

    def is_duplicate(self, record: MessageRecord) -> bool:
        """Idempotency check based on eventId in payload."""
        event_id = record.value.get("eventId")
        if not event_id:
            return False
        if event_id in self._processed_event_ids:
            return True
        self._processed_event_ids.add(event_id)
        return False

    def send_to_dlq(self, record: MessageRecord, reason: str):
        """Routes malformed or unprocessable messages to the Dead Letter Queue."""
        dlq_partition = self.broker.get_partition("collections.dlq", 0)
        dlq_payload = {
            "original_topic": record.topic,
            "original_partition": record.partition,
            "original_offset": record.offset,
            "error_reason": reason,
            "failed_record": record.to_dict()
        }
        dlq_partition.append(key=record.key, value=dlq_payload, headers={"status": "DLQ_POISON_PILL"})
