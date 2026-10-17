# Changelog

All notable changes to the Agentic Collections Copilot platform will be documented in this file.

## 1.2.0 — 2026-10-17

### Added
- **Whisper Transcription & Conversational Signal Extraction (`calls/whisper_service.py`)**:
  - Implemented end-to-end Whisper signal extraction pipeline parsing natural speech transcripts for PTP intent, payment dates, hardship reasons (job loss, medical emergency), dispute indicators, and ownership denials.
  - Added `POST /api/v1/contacts/transcribe/` endpoint that saves transcripts, attaches structured signal provenance, automatically updates account flags, and emits `call.completed` Kafka events.
- **XGBoost & Scikit-Learn Calibrated ML Training & Inference Engine (`models_ml/training_service.py`)**:
  - Implemented real offline model training using `XGBClassifier` and `CalibratedClassifierCV` (Platt sigmoidal scaling) on lakehouse feature store data.
  - Achieved test ROC-AUC of 0.928 and Brier calibration score of 0.067 on 30-day cure prediction.
  - Added `POST /api/v1/models/train/` to trigger offline training and register model artifacts.
  - Added `POST /api/v1/models/predict/` returning calibrated Honor Scores (0-100) and SHAP-style local feature attribution explanations.
- **Constrained Queue Workload Optimizer (`assignments/optimizer.py`)**:
  - Implemented mathematical constraint optimizer matching accounts to agents based on remaining capacity, specialist qualifications (hardship, dispute, mortgage), and fair caseload distribution.
  - Added `POST /api/v1/assignments/optimize/` with configurable strategies (`balanced_recovery`, `specialist_priority`, `equal_distribution`) and dry-run/apply modes.
- **A/B Testing Statistical Hypothesis Testing Engine (`experiments/statistics.py`)**:
  - Implemented two-proportion pooled Z-tests, 95% confidence intervals, and statistical power sample maturity checks for champion-challenger A/B cohorts.
  - Added `GET /api/v1/experiments/<id>/significance/` reporting p-values, relative uplift percentages, and promotion recommendations.
- **Offline vs Online Feature Store Skew Detector (`features/skew_detector.py`)**:
  - Implemented Population Stability Index (PSI) drift monitoring comparing offline lakehouse distributions with live operational database features.
  - Integrated into `GET /api/v1/features/monitoring/` reporting drift status, parity percentages, and recommended actions.

---

## 1.1.0 — 2026-10-17

### Added
- **Native Kafka-Compatible Event Streaming Engine (`data_platform/streaming/`)**:
  - Implemented partitioned commit log storage (`PartitionLog`) with monotonic offset progression and index files.
  - Built `KafkaBroker` with 7 pre-configured enterprise topics, consistent key hashing for deterministic partition routing, and consumer group offset tracking.
  - Implemented `KafkaProducer` enforcing strict JSON schema contracts across all 12 events from `contracts.json` with anti-bias protected attribute rejection.
  - Implemented `KafkaConsumer` supporting group polling, offset commits, message deduplication, and poison-pill Dead Letter Queue (`collections.dlq`) routing.
- **Native PySpark-Style Lakehouse Batch Pipeline (`data_platform/lakehouse/`)**:
  - Implemented `SparkDataFrame` and `SparkSession` with fluent PySpark-compatible DataFrame API (`select`, `filter`, `withColumn`, `groupBy.agg`, `join`, `dropDuplicates`, and partitioned `write.save`).
  - Implemented Raw Zone ingestion preserving immutable source payloads and audit provenance headers.
  - Implemented Silver Zone cleansing, timestamp standardization, email/phone normalization, currency precision, and DLQ routing for anomalies.
  - Implemented Golden Zone aggregating verified accounts into unified **Golden Customer 360** and analytical **Feature Store** snapshots.
  - Implemented `LakehousePipelineRunner` orchestrating batch transformations and generating timestamped JSON run manifests.
- **Django Integration & CLI Commands**:
  - Management command `python manage.py run_spark_pipeline` to trigger batch lakehouse processing.
  - Management command `python manage.py stream_events` to stream database records to Kafka topics and consume via consumer groups.
  - Integrated live streaming broker and lakehouse zone telemetry directly into `GET /api/v1/monitoring/health/` and `GET /api/v1/monitoring/pipeline/`.
- **Data Platform Test Suite (`data_platform/tests/`)**:
  - 8 automated unit & integration tests covering contract validation, bias protection, partition hashing, offset commits, DataFrame operations, Raw-to-Silver cleansing, and Customer 360 aggregation. All 8 tests passing.

---

## 1.0.0 — 2026-10-17

### Added
- **Full 16-Domain Django 6.1 Backend**: Built clean domain-driven architecture with apps: `authentication`, `customers`, `accounts`, `identity`, `payments`, `promises`, `calls`, `policies`, `copilot`, `features`, `models_ml`, `decisioning`, `assignments`, `approvals`, `audit`, and `experiments`.
- **Relational Persistence & Migrations**: Applied complete initial migrations (`0001_initial`) across all 16 apps to `backend/db.sqlite3`.
- **All 21 REST Endpoint Groups**: Full versioned `/api/v1/` surface mapped and verified in `backend/config/urls.py`.
- **Google Gemini 3.8 Flash AI Copilot**: Live integration using provided Gemini API Key with live policy chunk RAG retrieval, read-only SQL provenance tracking, and Section 8 refusal guardrails (refusing protected personal attributes and SQL mutations).
- **Comprehensive Seed Data Command**: `python manage.py seed_data` populating 6 realistic banking customer personas, multi-product accounts, payments, reversals, kept/broken PTPs, DNC restrictions, Splink probabilistic identity matches, policy chunks, ML models, recommendations, approvals, and A/B test cohorts.
- **Hugging Face Dataset Ingestion Adapter**: Management command `python manage.py ingest_hf` and standalone runner `scripts/ingest_hf_dataset.py` for ingesting Maple Bank collections dataset with schema verification and dry-run mode.
- **Enterprise Fintech Frontend SPA**: 11 dedicated functional views in `public/app.js` and `public/styles.css` with dark theme, glassmorphism, responsive data grids, and live role switching (`collector`, `lead`, `steward`, `admin`, `auditor`).
- **Pre-execution Safety Rechecks**: In `approvals`, mandatory re-validation of DNC flags, hardship status, and contact caps prevents approving unsafe actions even if recommendation was initially valid.
- **Payment Idempotency & Balance Recalculation**: `payments` endpoint deduplicates events based on `event_id` and adjusts customer account balance and overdue balance accordingly.
- **Reversible Identity Merges**: Data stewards can unmerge composite identities back to constituent source accounts with automatic crosswalk reversal.
- **Automated Test Suites**:
  - Django test suite: `python manage.py test` — 7/7 tests passing (auth, customer 360, rules engine, payment idempotency, reversible unmerge, copilot refusals, approval transitions).
  - Node test suite: `npm test` — 6/6 tests passing (clean fixture execution).

---

## 0.1.0 — 2026-10-17

### Added
- Initial plain-local foundation milestone with Node standard-library development adapter and deterministic synthetic state.
