# Security posture

This repository is a synthetic local demonstration, not a production financial system. Never place real personal, financial, authentication, or policy data in the fixture. Do not commit `.env` files or provider keys. Report security issues privately to the project owner rather than publishing sensitive evidence.

Before production use, replace the local JSON adapter with transactional PostgreSQL/Django services, add real authentication/session controls, rate limiting, encrypted secret storage, redacted structured logging, retention enforcement, dependency scanning, independent authorization checks, and formal model/policy governance.
