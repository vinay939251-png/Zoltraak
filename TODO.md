# Implementation TODO

## Foundation and Runtime
- [x] Start the app with a documented local command (`python manage.py runserver 8000`) and expose `/api/v1/monitoring/health/`.
- [x] Implement complete 16-domain-app Django 6.1 backend with SQLite (substitute for PostgreSQL without Docker).
- [x] Apply database migrations for all 16 domain apps (`authentication` through `promises`).
- [x] Provide deterministic seed command (`python manage.py seed_data`) populating 6 realistic banking customer personas, accounts, payments, PTPs, DNC, Splink identity matches, RAG policies, ML models, and A/B cohorts.
- [x] Provide optional Hugging Face Maple Bank dataset ingestion adapter (`python manage.py ingest_hf` and `scripts/ingest_hf_dataset.py`).
- [x] Keep environment configuration in `.env` and `.env.example`; securely integrate Google Gemini 3.8 Flash via API key.

## Core Domain and Customer 360 (Layer 1)
- [x] Represent golden customers, source identities, accounts, payments, promises, contacts, transcripts, hardship, disputes, and audit events in relational models.
- [x] Expose authorized customer 360 endpoint (`/api/v1/customers/<id>/360/`) with current balance, delinquency band, contact history, and machine-extracted metadata.
- [x] Enforce idempotent payment ingestion keyed by `event_id` with transaction reversal tracking.
- [x] Reconcile balances and overdue balances upon payment recording.

## Identity Resolution & Stewardship (Section 10)
- [x] Implement normalized exact matching with composite keys.
- [x] Implement Splink-compatible probabilistic candidate matching with match probability scores and feature match vectors.
- [x] Provide steward review queue (`/api/v1/identity/candidates/`) with approve, reject, and defer workflows.
- [x] Implement reversible crosswalk merges and unmerge capabilities (`/api/v1/identity/merges/<id>/unmerge/`) with downstream state reconciliation.

## AI Copilot & Evidence-Grounded RAG (Layer 2)
- [x] Integrate Google Gemini 3.8 Flash via `copilot/service.py` with fallback and request timeout protection.
- [x] Grounded answering with live RAG policy chunk citations (`RETRIEVED_CHUNKS` metadata).
- [x] Read-only SQL query execution with provenance tracking against safe database views.
- [x] Implement mandatory Section 8 governance refusal rules (hard refusal on protected personal attributes: gender, ethnicity, religion, marital status, nationality).
- [x] Implement SQL mutation guards (blocking INSERT, UPDATE, DELETE, DROP, ALTER, and system catalog access).

## Features, Models, and Decisioning (Layer 3)
- [x] Define versioned feature registry (`/api/v1/features/definitions/`) with freshness SLAs, entity keys, and lineage.
- [x] Implement live offline vs online feature store skew detector (`features/skew_detector.py`) with Population Stability Index (PSI) drift monitoring (`/api/v1/features/monitoring/`).
- [x] Train and calibrate ML models with XGBoost & Scikit-Learn (`models_ml/training_service.py`), achieving 0.928 ROC-AUC and 0.067 Brier score on cure prediction.
- [x] Expose calibrated Honor Score (0-100) and real local SHAP attribution explanations (`/api/v1/models/predict/` and `/api/v1/models/train/`).
- [x] Evaluate deterministic business rules (DNC restrictions, contact-caps, hardship status, dispute holds, data staleness) independent of model scores; rules fail-closed.
- [x] Generate evidence-backed Next Best Action recommendation cards with rationale and confidence metrics.

## Approvals, Optimization & Outreach (Layer 4)
- [x] Implement human-in-the-loop approval state transitions (`PENDING_REVIEW` → `APPROVED`, `REJECTED`, `ESCALATED`).
- [x] Enforce mandatory pre-execution safety revalidation on approval actions (re-verifying DNC, hardship, and contact caps before transition).
- [x] Implement Constrained Queue Workload Optimizer (`assignments/optimizer.py`, `/api/v1/assignments/optimize/`) matching collector capacity, specialist skills, and DNC rules.
- [x] Implement Whisper-compatible conversational signal extraction adapter (`calls/whisper_service.py`, `/api/v1/contacts/transcribe/`) extracting PTP, Hardship, Dispute, and Ownership Denial signals.
- [x] Implement rigorous A/B Testing Statistical Hypothesis Engine (`experiments/statistics.py`, `/api/v1/experiments/<id>/significance/`) with two-proportion Z-tests, 95% CIs, and power maturity.

## Data Platform: Kafka Event Streaming & Spark Lakehouse (Layer 5)
- [x] Implement Python partitioned commit log engine (`data_platform/streaming/`) with Kafka-compatible producer, consumer, and topic coordinator.
- [x] Enforce strict JSON schema validation for all 12 event contracts from `data-platform/events/contracts.json` with bias attribute protection.
- [x] Implement PySpark-style DataFrame API (`data_platform/lakehouse/dataframe.py`) supporting fluent transformations, schema enforcement, and partition saves.
- [x] Build Raw $\rightarrow$ Silver $\rightarrow$ Golden lakehouse stages with cleansing, deduplication, DLQ anomaly routing, Golden Customer 360, and Feature Store generation.
- [x] Provide Django management commands (`python manage.py run_spark_pipeline` and `python manage.py stream_events`).
- [x] Wire live telemetry from the Kafka broker and Spark lakehouse into `/api/v1/monitoring/health/` and `/api/v1/monitoring/pipeline/`.
- [x] Full data platform test suite (`data_platform/tests/`) — 8/8 tests passing.

## Operations, Frontend & Evaluation
- [x] Modern financial technology SPA frontend with 11 responsive views (`Dashboard`, `Collections Queue`, `Customer 360`, `Recommendations & Approvals`, `Identity Stewardship`, `Copilot AI`, `Policy Library`, `Feature Store & Models`, `Workload & Queueing`, `A/B Experiments`, `Audit Trail`).
- [x] Live role-switcher (`collector`, `lead`, `steward`, `admin`, `auditor`) for instant persona demonstration.
- [x] Operational monitoring endpoints for service health, pipeline latency, and data quality metrics.
- [x] A/B experiment monitoring with recovery rate metrics, sample sizes, and maturity indicators.
- [x] Full Django test suite (`python manage.py test`) — 7/7 tests passing with zero failures.
- [x] Node.js test suite (`npm test`) — 6/6 tests passing with zero failures.

## Documentation
- [x] Maintain comprehensive developer journal in `Readme.md` documenting architecture, migrations, Gemini 3.8 Flash integration, and test results.
- [x] Complete architecture (`docs/architecture.md`), security model (`docs/security-model.md`), and updated API reference (`docs/api-reference.md`).
- [x] Provide exact startup instructions and verification report.
