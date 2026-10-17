"""
Partitioned commit log storage engine.
Implements append-only, sequentially indexed log files per topic partition.
"""
import os
import json
import time
import threading
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional, Iterator

from .. import KAFKA_BROKER_ROOT


@dataclass
class MessageRecord:
    offset: int
    timestamp: int  # epoch milliseconds
    key: Optional[str]
    value: Dict[str, Any]
    headers: Dict[str, str]
    partition: int
    topic: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MessageRecord":
        return cls(**data)


class PartitionLog:
    """Manages append-only commit logs and index files for a single partition."""

    def __init__(self, topic: str, partition: int, base_dir: Optional[Path] = None):
        self.topic = topic
        self.partition = partition
        self.base_dir = (base_dir or KAFKA_BROKER_ROOT) / "topics" / topic / f"partition_{partition}"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.base_dir / "00000000000000000000.log"
        self.index_file = self.base_dir / "00000000000000000000.index"
        self._lock = threading.RLock()
        self._next_offset = self._recover_next_offset()

    def _recover_next_offset(self) -> int:
        """Inspects existing log to discover the current log end offset."""
        if not self.log_file.exists():
            return 0
        last_offset = -1
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        record = json.loads(line)
                        last_offset = max(last_offset, record.get("offset", -1))
        except Exception:
            pass
        return last_offset + 1

    @property
    def log_end_offset(self) -> int:
        """Offset of the next message that will be appended."""
        with self._lock:
            return self._next_offset

    def append(self, key: Optional[str], value: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> MessageRecord:
        """Appends a new message record to the partition commit log atomically."""
        with self._lock:
            offset = self._next_offset
            timestamp = int(time.time() * 1000)
            record = MessageRecord(
                offset=offset,
                timestamp=timestamp,
                key=key,
                value=value,
                headers=headers or {},
                partition=self.partition,
                topic=self.topic
            )
            raw_line = json.dumps(record.to_dict()) + "\n"
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(raw_line)
                f.flush()

            # Record in index (offset -> byte position estimate)
            with open(self.index_file, "a", encoding="utf-8") as f:
                f.write(f"{offset}:{timestamp}\n")
                f.flush()

            self._next_offset += 1
            return record

    def read(self, start_offset: int = 0, max_messages: int = 100) -> List[MessageRecord]:
        """Reads messages starting from start_offset up to max_messages."""
        with self._lock:
            if not self.log_file.exists():
                return []
            records = []
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if data.get("offset", -1) >= start_offset:
                            records.append(MessageRecord.from_dict(data))
                            if len(records) >= max_messages:
                                break
                    except Exception:
                        continue
            return records

    def purge(self):
        """Purges partition log for testing/reset."""
        with self._lock:
            if self.log_file.exists():
                os.remove(self.log_file)
            if self.index_file.exists():
                os.remove(self.index_file)
            self._next_offset = 0
