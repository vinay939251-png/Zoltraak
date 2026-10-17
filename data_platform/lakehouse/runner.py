"""
Lakehouse Batch Pipeline Runner (Spark Job Simulator).
Executes the full Raw -> Silver -> Golden lakehouse transformation lifecycle.
"""
import time
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

from .. import REPO_ROOT, LAKEHOUSE_ROOT
from .raw_zone import RawZoneManager
from .silver_zone import SilverZoneManager
from .golden_zone import GoldenZoneManager


class LakehousePipelineRunner:
    """Orchestrates end-to-end lakehouse batch jobs, tracking execution telemetry."""

    def __init__(self, lakehouse_root: Optional[Path] = None):
        self.root = lakehouse_root or LAKEHOUSE_ROOT
        self.manifest_dir = self.root / "manifests"
        self.manifest_dir.mkdir(parents=True, exist_ok=True)

        self.raw_mgr = RawZoneManager(self.root)
        self.silver_mgr = SilverZoneManager(self.root)
        self.golden_mgr = GoldenZoneManager(self.root)

    def load_source_fixtures(self) -> Dict[str, list]:
        """Loads source system accounts and customers from data/seed.json."""
        seed_path = REPO_ROOT / "data" / "seed.json"
        if not seed_path.exists():
            return {"loan-servicing": [], "credit-card": []}

        with open(seed_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        accounts = data.get("accounts", [])
        loan_records = []
        card_records = []

        for a in accounts:
            product = a.get("product", "LOAN").upper()
            if "CARD" in product:
                card_records.append(a)
            else:
                loan_records.append(a)

        return {
            "loan-servicing": loan_records,
            "credit-card": card_records
        }

    def run_pipeline(self, partition_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes the three-tier lakehouse batch transformation pipeline.
        """
        start_time = time.time()
        dt_str = partition_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # 1. RAW INGESTION
        fixtures = self.load_source_fixtures()
        total_raw_records = 0
        raw_dfs = []

        for source_sys, recs in fixtures.items():
            if recs:
                df = self.raw_mgr.ingest_records(source_sys, recs, partition_date=dt_str)
                raw_dfs.append(df)
                total_raw_records += df.count()

        # Combine raw
        raw_all = self.raw_mgr.read_raw()

        # 2. SILVER CLEANSING & DLQ
        clean_silver, dlq_silver = self.silver_mgr.process_raw_accounts(raw_all, partition_date=dt_str)

        # 3. GOLDEN AGGREGATION & FEATURE STORE
        c360_df = self.golden_mgr.build_golden_customer_360(clean_silver, partition_date=dt_str)
        feat_df = self.golden_mgr.build_feature_store(clean_silver, feature_version="v2.1", partition_date=dt_str)

        duration_ms = int((time.time() - start_time) * 1000)

        manifest = {
            "job_id": f"spark-job-{int(time.time())}",
            "job_name": "CollectionsLakehouseBatchTransform",
            "status": "COMPLETED",
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "partition_date": dt_str,
            "duration_ms": duration_ms,
            "zones": {
                "raw": {
                    "records_ingested": total_raw_records,
                    "sources": list(fixtures.keys())
                },
                "silver": {
                    "cleansed_records": clean_silver.count(),
                    "dlq_records": dlq_silver.count()
                },
                "golden": {
                    "customer_360_records": c360_df.count(),
                    "features_derived": feat_df.count()
                }
            }
        }

        # Persist manifest
        manifest_file = self.manifest_dir / f"manifest_{int(time.time())}.json"
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        latest_file = self.manifest_dir / "latest_manifest.json"
        with open(latest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        return manifest


pipeline_runner = LakehousePipelineRunner()
