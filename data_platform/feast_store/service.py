"""
Feast Feature Store Management Service.
Handles:
1. Materialization of Golden lakehouse data into Feast online store (SQLite / Redis).
2. Point-in-time offline feature vector generation.
3. Sub-millisecond online feature retrieval for real-time model inference.
"""
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
from feast import FeatureStore

REPO_PATH = Path(__file__).parent.resolve()
DATA_DIR = REPO_PATH / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


class FeastFeatureService:
    """Manages Feast feature store synchronization and online retrieval."""

    def __init__(self):
        self.repo_path = REPO_PATH
        self.parquet_path = DATA_DIR / "account_cure_features.parquet"
        self._store: Optional[FeatureStore] = None

    def get_store(self) -> FeatureStore:
        if self._store is None:
            self._store = FeatureStore(repo_path=str(self.repo_path))
        return self._store

    def sync_and_materialize(self) -> Dict[str, Any]:
        """
        Extracts current account features from SQLite database, writes Parquet source,
        applies Feast definitions, and materializes into the online store.
        """
        import django
        from accounts.models import Account

        accounts = Account.objects.all().select_related('customer')
        records = []
        now = datetime.now(timezone.utc)

        for a in accounts:
            overdue = float(a.overdue_balance)
            total = float(getattr(a, 'balance', None) or overdue) or 1.0
            ratio = min(overdue / total, 1.0)
            records.append({
                "account_id": a.id,
                "overdue_balance": float(overdue),
                "dpd": int(a.dpd),
                "contact_count_7d": int(a.contact_count_7d),
                "balance_overdue_ratio": float(ratio),
                "has_hardship": bool(a.hardship),
                "has_dispute": bool(a.dispute),
                "event_timestamp": now - timedelta(minutes=5),
                "created_timestamp": now
            })

        df = pd.DataFrame(records)
        df.to_parquet(self.parquet_path, index=False)

        store = self.get_store()
        from .features import account_entity, account_cure_feature_view
        store.apply([account_entity, account_cure_feature_view])

        # Materialize features into online store
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=2)
        store.materialize(start_date=start_time, end_date=end_time)

        return {
            "status": "SUCCESS",
            "materialized_records": len(records),
            "parquet_file": str(self.parquet_path),
            "materialized_at": end_time.isoformat()
        }

    def get_online_account_features(self, account_id: str) -> Dict[str, Any]:
        """Fetches online features directly from Feast for real-time model inference."""
        store = self.get_store()
        feature_refs = [
            "account_cure_features:overdue_balance",
            "account_cure_features:dpd",
            "account_cure_features:contact_count_7d",
            "account_cure_features:balance_overdue_ratio",
            "account_cure_features:has_hardship",
            "account_cure_features:has_dispute",
        ]
        resp = store.get_online_features(
            features=feature_refs,
            entity_rows=[{"account_id": account_id}]
        )
        data = resp.to_dict()
        return {
            "account_id": account_id,
            "overdue_balance": data.get("overdue_balance", [None])[0],
            "dpd": data.get("dpd", [None])[0],
            "contact_count_7d": data.get("contact_count_7d", [None])[0],
            "balance_overdue_ratio": data.get("balance_overdue_ratio", [None])[0],
            "has_hardship": data.get("has_hardship", [None])[0],
            "has_dispute": data.get("has_dispute", [None])[0],
            "source": "Feast Online Feature Store (SQLite/Redis)"
        }


feast_service = FeastFeatureService()
