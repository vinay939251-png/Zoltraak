"""
Lakehouse Silver Zone Cleansing and Normalization Engine.
Performs schema validation, standardization, deduplication, and dead-letter queue routing.
"""
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import pandas as pd
from .. import LAKEHOUSE_ROOT
from .dataframe import spark, SparkDataFrame


class SilverZoneManager:
    """Cleanses raw payloads into canonical normalized schemas, routing anomalies to DLQ."""

    def __init__(self, lakehouse_root: Optional[Path] = None):
        self.root = (lakehouse_root or LAKEHOUSE_ROOT) / "silver"
        self.dlq_root = self.root / "dlq"
        self.root.mkdir(parents=True, exist_ok=True)
        self.dlq_root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def normalize_phone(phone: Optional[str]) -> Optional[str]:
        if not phone:
            return None
        cleaned = re.sub(r"[^\d+]", "", str(phone))
        return cleaned

    @staticmethod
    def normalize_email(email: Optional[str]) -> Optional[str]:
        if not email:
            return None
        return str(email).strip().lower()

    @staticmethod
    def normalize_currency(val: Any) -> float:
        try:
            return round(float(val), 2)
        except (ValueError, TypeError):
            return 0.0

    def process_raw_accounts(self, raw_df: SparkDataFrame, partition_date: Optional[str] = None) -> Tuple[SparkDataFrame, SparkDataFrame]:
        """
        Transforms raw account/customer payloads into silver canonical schema.
        Splits output into (clean_silver_df, dlq_failures_df).
        """
        dt_str = partition_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        now_iso = datetime.now(timezone.utc).isoformat()
        records = raw_df.collect()

        clean_records = []
        dlq_records = []

        seen_keys = set()

        for r in records:
            payload = r.get("payload") or {}
            src = r.get("_source_system", "unknown")
            rec_id = r.get("_source_record_id")

            # Deduplication key
            dedup_key = (src, str(rec_id))
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)

            # Data Quality Validations
            acct_id = payload.get("id") or payload.get("accountId") or payload.get("sourceRecordId")
            status = payload.get("status", "ACTIVE").upper()

            if not acct_id:
                dlq_records.append({
                    "_raw_id": r.get("_raw_id"),
                    "_source_system": src,
                    "_failure_reason": "MISSING_PRIMARY_IDENTIFIER",
                    "_rejected_at": now_iso,
                    "payload": payload
                })
                continue

            overdue_balance = self.normalize_currency(payload.get("overdueBalance", payload.get("balance", 0.0)))
            total_balance = self.normalize_currency(payload.get("totalBalance", overdue_balance))
            dpd = int(payload.get("dpd", payload.get("daysPastDue", 0)))
            contact_count = int(payload.get("contactCount7d", payload.get("contact_count_7d", 0)))

            clean_records.append({
                "account_id": str(acct_id),
                "customer_id": str(payload.get("customerId", payload.get("customer_id", f"cust-{acct_id}"))),
                "product_type": payload.get("product", payload.get("product_type", "LOAN")).upper(),
                "status": status,
                "overdue_balance": overdue_balance,
                "total_balance": total_balance,
                "dpd": max(dpd, 0),
                "contact_count_7d": max(contact_count, 0),
                "dnc": bool(payload.get("dnc", False)),
                "hardship": bool(payload.get("hardship", False)),
                "dispute": bool(payload.get("dispute", False)),
                "_source_system": src,
                "_source_record_id": str(rec_id),
                "_cleansed_at": now_iso
            })

        clean_df = spark.createDataFrame(clean_records)
        dlq_df = spark.createDataFrame(dlq_records)

        # Write clean records
        if clean_df.count() > 0:
            target_clean = self.root / "dataset=accounts" / f"dt={dt_str}"
            clean_df.write.mode("append").format("jsonl").save(target_clean)

        # Write DLQ records
        if dlq_df.count() > 0:
            target_dlq = self.dlq_root / f"dt={dt_str}"
            dlq_df.write.mode("append").format("jsonl").save(target_dlq)

        return clean_df, dlq_df

    def read_silver(self, dataset: str) -> SparkDataFrame:
        """Reads silver cleansed records for a specific dataset."""
        path = self.root / f"dataset={dataset}"
        return spark.read.format("jsonl").load(path)
