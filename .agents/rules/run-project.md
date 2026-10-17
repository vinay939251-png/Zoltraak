---
trigger: always_on
description: Instructions on how to run and start the Agentic Collections Copilot platform.
---

# Project Run Instructions

Whenever the user asks to run, start, or test the application:

1. **Working Directory:** `backend`
2. **Command:**
   ```powershell
   python manage.py runserver 127.0.0.1:8000
   ```
3. **URL:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
4. **Setup Commands (if database needs reset or fresh setup):**
   - Migrations: `python manage.py migrate`
   - Seeding: `python manage.py seed_data`
5. **Note:** The Django server serves both the REST API under `/api/v1/` and the SPA frontend from `public/`.
