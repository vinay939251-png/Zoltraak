# Data platform adapters

The local server uses deterministic fixture records as a development substitute for raw/silver/golden processing. This boundary is intentional: source-like metadata is retained, but the 4.66 GB Hugging Face release is not silently downloaded or loaded.

## Raw
Preserve source payload, source system, source record ID, event ID, occurrence time, ingestion time, and validation result.

## Silver
Normalize allowed identifiers and timestamps, standardize currency, reject malformed records, deduplicate by event ID, and record a dead-letter reason.

## Golden
Link authorized records to Golden Customer IDs, preserve effective/recorded time, and expose field-level lineage.

## Optional integrations
Kafka, Spark, Airflow, PostgreSQL, Redis, OpenMetadata, and the Hugging Face release require explicit local configuration. Their availability must be reported by `/api/v1/monitoring` and never replaced with a fake production-looking result.
