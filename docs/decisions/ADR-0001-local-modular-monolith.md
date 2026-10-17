# ADR-0001: Local modular monolith first

**Status:** Accepted for local development

## Context
The requirements call for a Django/PostgreSQL modular monolith, but the selected plain-local device currently lacks Python and container runtimes. The workspace is empty apart from requirements/reference files.

## Decision
Implement a runnable Node.js standard-library modular monolith with explicit service boundaries and stable `/api/v1/` contracts. Keep persistence behind an adapter and label all unavailable production integrations. Do not fabricate live infrastructure or model performance.

## Consequences
This enables a complete, testable local vertical slice immediately. It is not a substitute for a production Django/PostgreSQL deployment; migration work remains documented and isolated.
