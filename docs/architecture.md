# Architecture

## Current local architecture
A standard-library Node.js modular monolith serves both the REST API and the static frontend. The server keeps a deterministic synthetic state in `data/demo.json`; writes use a temp-file replacement to avoid partially written state. The API is versioned under `/api/v1/` and includes demo metadata on every response.

```text
Browser UI
   | fetch /api/v1/*
Node HTTP server
   |-- auth + role/object checks
   |-- customer/account services
   |-- copilot classification + evidence services
   |-- deterministic decision rules
   |-- recommendation/approval service
   |-- audit service
   '-- JSON persistence adapter (local substitute)
Synthetic demo state + provenance
```

## Domain boundaries
- **customers/accounts:** Golden Customer 360 read model and authorized records.
- **identity:** source identities, match evidence, review transitions, crosswalk history.
- **copilot:** intent routing, facts, policy chunks, evidence/citation validation, refusals.
- **features/models:** feature snapshots, freshness, development-only predictions.
- **decisioning:** deterministic rules, recommendation cards, state machine, simulated execution.
- **operations:** dashboard aggregation, monitoring, experiments, audit exploration.

## Migration boundary
The JSON adapter is deliberately isolated. A future Django/PostgreSQL implementation can replace it with models and transactions while retaining endpoint schemas and service-level tests. Kafka, Spark, Airflow, Redis, vector search, Splink, and model runtimes are represented as explicit adapter statuses rather than silently emulated as live infrastructure.

## Data lifecycle
Source-like fixtures retain `sourceSystem`, `sourceRecordId`, `observedAt`, `ingestedAt`, `transformationVersion`, and `dataQuality`. Demo records are already in a golden read-model shape; the ingestion status page calls out that raw/silver processing is a local substitute until the optional dataset adapter is enabled.
