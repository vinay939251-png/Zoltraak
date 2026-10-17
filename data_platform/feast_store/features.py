"""
Feast Feature Definitions for Zoltraak Collections Platform.
Defines Entities, Batch Feature Views, and Field schemas adhering to Section 9:
1. Account Entity & Account Delinquency Feature View.
2. Customer Entity & Customer 360 Feature View.
3. Source Parquet file references mapped to Golden Lakehouse tier.
"""
from datetime import timedelta
from pathlib import Path
from feast import (
    Entity,
    FeatureView,
    Field,
    FileSource,
)
from feast.types import Float32, Int64, String, Bool

CURRENT_DIR = Path(__file__).parent.resolve()
DATA_DIR = CURRENT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 1. Entities
account_entity = Entity(
    name="account_id",
    join_keys=["account_id"],
    description="Primary account identifier across loan servicing and cards."
)

customer_entity = Entity(
    name="customer_id",
    join_keys=["customer_id"],
    description="Unified Golden Customer 360 identifier."
)

# 2. File Sources (pointing to Golden Lakehouse features)
account_features_source = FileSource(
    name="account_cure_features_source",
    path=str(DATA_DIR / "account_cure_features.parquet"),
    timestamp_field="event_timestamp",
    created_timestamp_column="created_timestamp",
)

# 3. Account Delinquency & Cure Feature View
account_cure_feature_view = FeatureView(
    name="account_cure_features",
    entities=[account_entity],
    ttl=timedelta(days=30),
    schema=[
        Field(name="overdue_balance", dtype=Float32, description="Current delinquent balance amount"),
        Field(name="dpd", dtype=Int64, description="Days Past Due"),
        Field(name="contact_count_7d", dtype=Int64, description="Outbound contacts within rolling 7 days"),
        Field(name="balance_overdue_ratio", dtype=Float32, description="Overdue balance over total balance"),
        Field(name="has_hardship", dtype=Bool, description="Customer enrolled in hardship relief"),
        Field(name="has_dispute", dtype=Bool, description="Formal account dispute active"),
    ],
    online=True,
    source=account_features_source,
    tags={"team": "collections_ml", "tier": "golden"},
)
