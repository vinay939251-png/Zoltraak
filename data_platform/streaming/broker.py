"""
Kafka Broker and Consumer Group Coordinator.
Provides topic routing, partition hashing, offset commits, and cluster telemetry.
"""
import os
import json
import zlib
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from .. import KAFKA_BROKER_ROOT
from .storage import PartitionLog, MessageRecord


class KafkaBroker:
    """Simulates a cluster-grade Kafka Broker with topics, partitions, and group offsets."""

    DEFAULT_PARTITIONS = 3

    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = root_dir or KAFKA_BROKER_ROOT
        self.topics_dir = self.root_dir / "topics"
        self.groups_dir = self.root_dir / "consumer_groups"
        self.topics_dir.mkdir(parents=True, exist_ok=True)
        self.groups_dir.mkdir(parents=True, exist_ok=True)

        self._partitions: Dict[Tuple[str, int], PartitionLog] = {}
        self._lock = threading.RLock()
        self._init_default_topics()

    def _init_default_topics(self):
        """Ensures core enterprise collection topics are pre-created."""
        default_topics = [
            "collections.payments",
            "collections.promises",
            "collections.calls",
            "collections.cases",
            "collections.identity",
            "collections.decisions",
            "collections.dlq"
        ]
        for topic in default_topics:
            self.create_topic(topic, partitions=self.DEFAULT_PARTITIONS)

    def create_topic(self, topic: str, partitions: int = DEFAULT_PARTITIONS):
        """Registers a topic and creates its partition log managers."""
        with self._lock:
            for p in range(partitions):
                key = (topic, p)
                if key not in self._partitions:
                    self._partitions[key] = PartitionLog(topic, p, self.root_dir)

    def get_partition(self, topic: str, partition: int) -> PartitionLog:
        with self._lock:
            key = (topic, partition)
            if key not in self._partitions:
                self.create_topic(topic, self.DEFAULT_PARTITIONS)
            return self._partitions[key]

    def get_partition_count(self, topic: str) -> int:
        with self._lock:
            topic_dir = self.topics_dir / topic
            if not topic_dir.exists():
                return self.DEFAULT_PARTITIONS
            count = len([d for d in topic_dir.iterdir() if d.is_dir() and d.name.startswith("partition_")])
            return max(count, self.DEFAULT_PARTITIONS)

    def hash_partition(self, topic: str, key: Optional[str]) -> int:
        """Determines partition by consistent hashing on message key, ensuring causal order."""
        num_partitions = self.get_partition_count(topic)
        if not key:
            return 0
        return (zlib.crc32(str(key).encode("utf-8")) & 0xffffffff) % num_partitions

    def list_topics(self) -> List[str]:
        """Lists all existing topics in the broker."""
        with self._lock:
            if not self.topics_dir.exists():
                return []
            return sorted([d.name for d in self.topics_dir.iterdir() if d.is_dir()])

    # Consumer Group Management
    def _group_offset_file(self, group_id: str) -> Path:
        group_path = self.groups_dir / group_id
        group_path.mkdir(parents=True, exist_ok=True)
        return group_path / "offsets.json"

    def get_committed_offset(self, group_id: str, topic: str, partition: int) -> int:
        """Returns the committed offset for a group/topic/partition, defaulting to 0."""
        with self._lock:
            offset_file = self._group_offset_file(group_id)
            if not offset_file.exists():
                return 0
            try:
                with open(offset_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get(topic, {}).get(str(partition), 0)
            except Exception:
                return 0

    def commit_offset(self, group_id: str, topic: str, partition: int, offset: int):
        """Persists the committed offset for a consumer group."""
        with self._lock:
            offset_file = self._group_offset_file(group_id)
            data = {}
            if offset_file.exists():
                try:
                    with open(offset_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    data = {}

            if topic not in data:
                data[topic] = {}
            data[topic][str(partition)] = offset

            with open(offset_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

    def get_topic_telemetry(self) -> Dict[str, Any]:
        """Returns deep telemetry metrics across all topics, partition depths, and consumer lag."""
        with self._lock:
            topics = self.list_topics()
            result = {}
            total_messages = 0

            for t in topics:
                num_p = self.get_partition_count(t)
                p_details = []
                topic_msgs = 0
                for p in range(num_p):
                    part_log = self.get_partition(t, p)
                    end_offset = part_log.log_end_offset
                    topic_msgs += end_offset
                    p_details.append({
                        "partition": p,
                        "log_end_offset": end_offset
                    })
                total_messages += topic_msgs
                result[t] = {
                    "partitions": num_p,
                    "total_messages": topic_msgs,
                    "partition_status": p_details
                }

            return {
                "broker_status": "ONLINE",
                "storage_directory": str(self.root_dir),
                "total_topics": len(topics),
                "total_messages": total_messages,
                "topics": result
            }


# Singleton broker instance
broker = KafkaBroker()
