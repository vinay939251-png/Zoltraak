# Project Run & Operating Instructions

## 1. How to Run the Application
The primary application is a unified Django platform serving both the REST API and the frontend Single Page Application (SPA).

### Quick Start
```powershell
cd backend
python manage.py runserver 127.0.0.1:8000
```
- Open in browser: `http://127.0.0.1:8000/`

### Prerequisites & Database Setup
If setting up fresh or resetting state:
```powershell
cd backend
# 1. Apply migrations
python manage.py migrate

# 2. Seed deterministic demo data
python manage.py seed_data

# 3. Start unified server
python manage.py runserver 127.0.0.1:8000
```

## 2. Service Endpoints
- **Web UI & Collections Dashboard:** `http://127.0.0.1:8000/`
- **System Health Check:** `http://127.0.0.1:8000/api/v1/monitoring/health/`
- **Pipeline & Kafka Telemetry:** `http://127.0.0.1:8000/api/v1/monitoring/pipeline/`
- **Feature Store Drift & Skew (PSI):** `http://127.0.0.1:8000/api/v1/features/monitoring/`
- **ML Training & Calibrated Predict:** `http://127.0.0.1:8000/api/v1/models/train/` & `/predict/`
- **Constrained Workload Optimizer:** `http://127.0.0.1:8000/api/v1/assignments/optimize/`
- **Whisper Signal Extraction:** `http://127.0.0.1:8000/api/v1/contacts/transcribe/`
- **A/B Testing Significance (Z-Test):** `http://127.0.0.1:8000/api/v1/experiments/<id>/significance/`
- **Collections Queue:** `http://127.0.0.1:8000/api/v1/collections/queue/`
- **Copilot Query:** `http://127.0.0.1:8000/api/v1/copilot/query/`
- **Django Admin:** `http://127.0.0.1:8000/admin/`

## 3. Data Platform (Kafka Streaming & Spark Lakehouse)
- **Run Spark Lakehouse Batch Transformation (Raw -> Silver -> Golden):**
  ```powershell
  python manage.py run_spark_pipeline
  ```
- **Stream & Publish Database Events to Kafka Topics:**
  ```powershell
  python manage.py stream_events --publish-seed
  ```
- **Poll & Consume Kafka Events (Consumer Group):**
  ```powershell
  python manage.py stream_events --consume --group-id analytics-group
  ```
- **Run Data Platform Unit & Integration Tests:**
  ```powershell
  python -m unittest discover -s data_platform/tests
  ```

## 4. Demo Roles & Switching
The UI includes a top-navigation role switcher (`POST /api/v1/auth/switch-user/`):
- `collector` (Sarah Jenkins) — Operational collector managing assigned delinquent accounts.
- `lead` (Marcus Vance) — Team lead approving settlements, hardship plans, and reassigning queues.
- `steward` (Elena Rostova) — Data steward reviewing identity match candidates.
- `admin` (System Administrator) — Full platform access, rule editing, model registry management.
- `auditor` (Audit Officer) — Read-only compliance access to immutable append-only audit trail.

## 5. Architecture Note
- The Django server at `backend/config/urls.py` handles API endpoints under `/api/v1/` and serves the frontend SPA static files (`public/index.html`, `public/app.js`, `public/styles.css`).
- `server.js` at project root is a standalone Node fallback/mock server running on port 4173 (`npm start`), but the main full-featured system is the Django unified server on port 8000.
