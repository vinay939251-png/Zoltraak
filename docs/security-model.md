# Security Model

## Roles
The demo supports `collections_agent`, `team_lead`, `hardship_specialist`, `data_steward`, and `administrator`. Role checks execute on the server; the UI is not a security boundary. Object access is limited by assigned account IDs for agents.

## Protected behavior
- Protected attributes are excluded from decision features and copilot responses.
- DNC, contact caps, open disputes, hardship routing, and missing mandatory data fail closed.
- Mutating copilot requests, multi-statement SQL, unauthorized resources, and prompt-injection-like instructions are rejected.
- Approval references the exact recommendation version and re-evaluates eligibility.
- Simulated execution is idempotent by recommendation/action key.
- Audit events are append-only through the application API; there is no ordinary delete/edit endpoint.

## Synthetic data
All names, identifiers, balances, and policy documents are fictional. The UI and API expose `environment: DEMO` and `simulation: true`. No real communication or collection side effect is available.

## Future production controls
A production migration must add Django authentication/session handling, PostgreSQL permissions/transactions, rate limiting, encrypted secret management, structured redacted logs, CSRF protections, retention controls, and independent infrastructure credentials. The current local server is a development demonstration, not a production financial system.
