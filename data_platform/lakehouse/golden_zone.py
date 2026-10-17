"""
Lakehouse Golden Zone Aggregation Engine.
Produces the Golden Customer 360 unified view and Feature Store tables with full data lineage.
"""
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

import pandas as pd
from .. import LAKEHOUSE_ROOT
from .dataframe import spark, SparkDataFrame


class GoldenZoneManager:
    """Builds authorized Golden Customer 360 read models and feature store tables."""

    def __init__(self, lakehouse_root: Optional[Path] = None):
        self.root = (lakehouse_root or LAKEHOUSE_ROOT) / "golden"
        self.c360_root = self.root / "customer_360"
        self.features_root = self.root / "feature_store"
        self.c360_root.mkdir(parents=True, exist_ok=True)
        self.features_root.mkdir(parents=True, exist_ok=True)

    def build_golden_customer_360(
        self,
        silver_accounts: SparkDataFrame,
        partition_date: Optional[str] = None
    ) -> SparkDataFrame:
        """
        Aggregates multi-product accounts into a unified Golden Customer 360 entity.
        """
        dt_str = partition_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        now_iso = datetime.now(timezone.utc).isoformat()
        records = silver_accounts.collect()

        if not records:
            return spark.createDataFrame([])

        customer_map: Dict[str, Dict[str, Any]] = {}

        for r in records:
            cid = r.get("customer_id")
            if cid not in customer_map:
                customer_map[cid] = {
                    "golden_customer_id": cid,
                    "account_count": 0,
                    "total_overdue_balance": 0.0,
                    "max_dpd": 0,
                    "contact_count_7d": 0,
                    "has_dnc": False,
                    "has_hardship": False,
                    "has_dispute": False,
                    "linked_source_systems": set(),
                    "accounts_list": [],
                    "_effective_at": now_iso
                }

            c = customer_map[cid]
            c["account_count"] += 1
            c["total_overdue_balance"] = round(c["total_overdue_balance"] + float(r.get("overdue_balance", 0.0)), 2)
            c["max_dpd"] = max(c["max_dpd"], int(r.get("dpd", 0)))
            c["contact_count_7d"] = max(c["contact_count_7d"], int(r.get("contact_count_7d", 0)))
            c["has_dnc"] = c["has_dnc"] or bool(r.get("dnc", False))
            c["has_hardship"] = c["has_hardship"] or bool(r.get("hardship", False))
            c["has_dispute"] = c["has_dispute"] or bool(r.get("dispute", False))
            if r.get("_source_system"):
                c["linked_source_systems"].add(r.get("_source_system"))
            c["accounts_list"].append(r.get("account_id"))

        # Format lists and sets
        c360_records = []
        for c in customer_map.values():
            c360_records.append({
                "golden_customer_id": c["golden_customer_id"],
                "account_count": c["account_count"],
                "total_overdue_balance": c["total_overdue_balance"],
                "max_dpd": c["max_dpd"],
                "contact_count_7d": c["contact_count_7d"],
                "dnc_active": c["has_dnc"],
                "hardship_active": c["has_hardship"],
                "dispute_active": c["has_dispute"],
                "source_systems": list(c["linked_source_systems"]),
                "account_ids": c["accounts_list"],
                "last_observed_at": c["_effective_at"]
            })

        c360_df = spark.createDataFrame(c360_records)
        target_path = self.c360_root / f"dt={dt_str}"
        c360_df.write.mode("overwrite").format("jsonl").save(target_path)
        return c360_df

    def build_feature_store(
        self,
        silver_accounts: SparkDataFrame,
        feature_version: str = "v1.2",
        partition_date: Optional[str] = None
    ) -> SparkDataFrame:
        """
        Derives deterministic ML features for collection outcome prediction and rule evaluation.
        """
        dt_str = partition_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        now_iso = datetime.now(timezone.utc).isoformat()
        records = silver_accounts.collect()

        feature_records = []
        for r in records:
            overdue = float(r.get("overdue_balance", 0.0))
            total = float(r.get("total_balance", overdue)) or 1.0
            ratio = round(min(overdue / total, 1.0), 4)

            feature_records.append({
                "account_id": r.get("account_id"),
                "customer_id": r.get("customer_id"),
                "feature_version": feature_version,
                "overdue_balance": overdue,
                "total_balance": total,
                "balance_overdue_ratio": ratio,
                "dpd": int(r.get("dpd", 0)),
                "contact_count_7d": int(r.get("contact_count_7d", 0)),
                "dnc_flag": int(bool(r.get("dnc", False))),
                "hardship_flag": int(bool(r.get("hardship", False))),
                "dispute_flag": int(bool(r.get("dispute", False))),
                "calculated_at": now_iso
            })

        feat_df = spark.createDataFrame(feature_records)
        target_path = self.features_root / f"dt={dt_str}"
        feat_df.write.mode("overwrite").format("jsonl").save(target_path)
        return feat_df

    def read_customer_360(self) -> SparkDataFrame:
        return spark.read.format("jsonl").load(self.c360_root)

    def read_feature_store(self) -> SparkDataFrame:
        return spark.read.format("jsonl").load(self.features_root)
