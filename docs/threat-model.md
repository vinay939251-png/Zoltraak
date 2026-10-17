# Threat model

| Threat | Control in local demo | Production follow-up |
|---|---|---|
| Unauthorized account access | Assigned-account filtering in server services | Django auth, object permissions, row-level DB controls |
| Prompt injection in notes/policies | Evidence treated as data; only server rules authorize | Retrieval isolation, content scanning, provider policy controls |
| SQL injection or mutation | Read-only query validator and approved view list | SQLGlot AST validation plus DB read-only role and timeouts |
| Protected-attribute inference | Server refusal and exclusion from features | Formal fairness/legal review and sensitive-field minimization |
| DNC bypass | Deterministic fail-closed rule | Versioned institution policy and pre-execution recheck |
| Duplicate payment/action | Event IDs and recommendation transition checks | Transactional outbox/idempotency keys |
| Fabricated model/policy claims | Explicit demo/untrained labels and citations | Artifact registry, calibration evidence, policy approval workflow |
