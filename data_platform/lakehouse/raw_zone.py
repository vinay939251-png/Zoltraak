"""
Lakehouse Raw Zone Ingestion Engine.
Preserves immutable source system payloads with ingestion timestamps, provenance, and hashes.
"""
import uuid
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

from .. import LAKEHOUSE_ROOT
from .dataframe import spark, SparkDataFrame


class RawZoneManager:
    """Manages raw ingestion into the lakehouse, preserving original payloads and audit provenance."""

    def __init__(self, lakehouse_root: Optional[Path] = None):
        self.root = (lakehouse_root or LAKEHOUSE_ROOT) / "raw"
        self.root.mkdir(parents=True, exist_ok=True)

    def ingest_records(
        self,
        source_system: str,
        records: List[Dict[str, Any]],
        partition_date: Optional[str] = None
    ) -> SparkDataFrame:
        """
        Wraps incoming source payloads with immutable audit provenance metadata.
        """
        dt_str = partition_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        now_iso = datetime.now(timezone.utc).isoformat()

        enriched_records = []
        for r in records:
            raw_serialized = json.dumps(r, sort_keys=True)
            checksum = hashlib.sha256(raw_serialized.encode("utf-8")).hexdigest()
            raw_id = f"raw-{uuid.uuid4().hex[:12]}"
            source_rec_id = r.get("id") or r.get("sourceRecordId") or r.get("accountId") or raw_id

            enriched_records.append({
                "_raw_id": raw_id,
                "_source_system": source_system,
                "_source_record_id": str(source_rec_id),
                "_ingested_at": now_iso,
                "_payload_checksum": checksum,
                "payload": r
            })

        df = spark.createDataFrame(enriched_records)
        target_dir = self.root / f"source_system={source_system}" / f"dt={dt_str}"
        df.write.mode("append").format("jsonl").save(target_dir)

        return df

    def read_raw(self, source_system: Optional[str] = None) -> SparkDataFrame:
        """Reads raw records for a specific source system or across all systems."""
        path = self.root / f"source_system={source_system}" if source_system else self.root
        return spark.read.format("jsonl").load(path)
