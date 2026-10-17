# Agentic Collections Copilot — Local Implementation Plan

## Delivery mode
Plain local development in this workspace. No Manus-managed services, publishing, or synchronization will be configured.

## Current baseline
The workspace began with the master requirements README and three reference files, but no application source, package manifest, migrations, or tests. The linked Hugging Face dataset is synthetic, 4.66 GB total, and contains a release ZIP plus optional voice samples; it will be treated as an optional ingestion source rather than required for the local demo.

## Implementation approach
Build a runnable local modular monolith around a Node.js standard-library HTTP server and a browser client first, because Python/Django and container runtimes are not installed on the device. The domain boundaries mirror the requested architecture so the implementation can later be migrated to Django/PostgreSQL without changing the contracts:

- `server.js`: HTTP API, authorization, deterministic seed/reset, business services, audit persistence.
- `data/demo.json`: synthetic operational state and provenance.
- `public/`: accessible enterprise operations UI for dashboard, queue, Customer 360, copilot, recommendation review, identity review, monitoring, policy library, audit, and experiments.
- `docs/`: architecture, security, API and migration notes.
- `tests/`: Node test coverage for core rules and API behavior.

## Design direction
Three possible styles were considered: **Evidence Ledger** (0.06), **Control Room Editorial** (0.08), and **Quiet Signal** (0.05). The selected direction is **Evidence Ledger**.

- **Design movement:** editorial financial-operations tooling with ledger-like surfaces and restrained data visualization.
- **Core principles:** evidence first; calm hierarchy; explicit status; reversible human control.
- **Color philosophy:** warm paper neutrals for the workspace, ink/navy for authority, teal for verified data, amber for review, red only for blocking restrictions.
- **Layout paradigm:** persistent left rail plus asymmetric workbench, with detail panels that open beside operational lists instead of forcing a centered dashboard.
- **Signature elements:** provenance chips, rule-result rows, and a vertical decision timeline.
- **Interaction philosophy:** every consequential action exposes why, who can act, what will be recorded, and whether it is simulated.
- **Animation:** short opacity/translate transitions only; reduced-motion safe.
- **Typography:** system sans for operational density with serif-like display accents avoided in dense tables; strong numeric tabular figures.
- **Brand essence:** an evidence-grounded collections decision workspace for authorized teams; precise, governed, accountable.
- **Brand voice:** “See the evidence before you act.” / “Blocked by policy is a useful answer.”
- **Wordmark:** a small stacked ledger mark beside “Maple / Collections Copilot”.
- **Signature color:** deep blue-black `#102a43` with teal `#0f766e` as verified-signal accent.

## Milestones
1. Foundation: local server, deterministic demo data, health/readiness, routes, audit, role checks.
2. Vertical slice: dashboard → queue → Customer 360 → copilot factual/policy answers → recommendation eligibility → simulated approval → audit.
3. Steward/monitoring/evaluation surfaces and expanded automated tests.
4. Optional dataset adapter and infrastructure manifests, clearly labeled as adapters/substitutes until their runtimes are configured.

## Important honesty constraints
The local implementation will label all records as synthetic/demo data. Predictive scores are deterministic development demonstrations, not trained or calibrated production models. External Kafka, Spark, Airflow, PostgreSQL, Redis, Splink, pgvector, XGBoost/LightGBM, SHAP, Feast, OR-Tools, Whisper, and LLM services will only be marked live after actual dependencies are configured and verified.
