# API Reference — Agentic Collections Copilot (v1)

The platform exposes versioned RESTful JSON endpoints under `/api/v1/`.
All responses adhere to standard envelope semantics:
- Successful operations return structured data with timestamp, status, and role metadata.
- Error operations return `{ "error": { "code": string, "message": string, "details": object } }`.
- Mutating endpoints enforce audit-logging, authorization checks, and idempotency guarantees.

---

## 1. Authentication & Session Identity
| Method | Path | Description | Access Scope |
|---|---|---|---|
| `GET` | `/api/v1/auth/me/` | Current user profile, active role, and assigned permissions | Authenticated |
| `POST` | `/api/v1/auth/switch-user/` | Switch active role/persona for demo & testing (`collector`, `lead`, `steward`, `admin`, `auditor`) | Demo context |
| `GET` | `/api/v1/users/` | Directory of operational users and assigned collector agents | Authenticated |

---

## 2. Customer 360 & Golden Identity
| Method | Path | Description | Access Scope |
|---|---|---|---|
| `GET` | `/api/v1/customers/` | List customer records with search, filter, and pagination | All roles |
| `GET` | `/api/v1/customers/<id>/` | Single customer details with source provenance | All roles |
| `GET` | `/api/v1/customers/<id>/360/` | Unified 360 view: linked accounts, payment history, contact logs, active PTPs, hardship status | Object-scoped |

---

## 3. Financial Accounts & Policy Eligibility
| Method | Path | Description | Access Scope |
|---|---|---|---|
| `GET` | `/api/v1/accounts/` | List financial accounts (loans, cards, mortgages) with balances, DPD, and hardship flags | All roles |
| `GET` | `/api/v1/accounts/<id>/` | Detailed account state, interest rates, arrears breakdown | Object-scoped |
| `GET` | `/api/v1/accounts/<id>/eligibility/` | Live rule evaluation: contact caps, DNC, hardship, dispute status, settlement eligibility | Collector, Lead |

---

## 4. Collections Dashboard & Operational Queue
| Method | Path | Description | Access Scope |
|---|---|---|---|
| `GET` | `/api/v1/collections/dashboard/` | High-level portfolio aggregates: total exposure, delinquent volume, kept PTP rate, queue depth | Collector, Lead, Admin |
| `GET` | `/api/v1/collections/queue/` | Prioritized agent work queue with filtering by tier, DPD band, hardship, and eligibility | Collector, Lead |

---

## 5. Payments & Ingestion (Idempotent)
| Method | Path | Description | Access Scope |
|---|---|---|---|
| `GET` | `/api/v1/payments/` | Query payment ledger records with status (`POSTED`, `PENDING`, `REVERSED`) | All roles |
| `POST` | `/api/v1/payments/` | Ingest payment event with strict `event_id` idempotency checking and balance recalculation | Ingestion, System |

---

## 6. Promises to Pay (PTP)
| Method | Path | Description | Access Scope |
|---|---|---|---|
| `GET` | `/api/v1/promises/` | List PTP records filtered by account, status (`KEPT`, `PENDING`, `BROKEN`) | Collector, Lead |
| `POST` | `/api/v1/promises/` | Record new commitment with amount, promised date, and payment channel | Collector |

---

## 7. Customer Contacts & Call Transcripts
| Method | Path | Description | Access Scope |
|---|---|---|---|
| `GET` | `/api/v1/contacts/` | List customer outreach attempts (phone, SMS, email, letter) with outcome | All roles |
| `POST` | `/api/v1/contacts/` | Record new contact event with timestamp and compliance checks | Collector |
| `GET` | `/api/v1/contacts/transcripts/` | Call interaction transcripts with sentiment, speaker turns, and entity tags | Collector, Lead, Auditor |

---

## 8. Identity Resolution & Entity Stewardship (Splink)
| Method | Path | Description | Access Scope |
|---|---|---|---|
| `GET` | `/api/v1/identity/candidates/` | Probabilistic match pairs awaiting steward verification | Data Steward, Admin |
| `POST` | `/api/v1/identity/candidates/<id>/action/` | Approve, reject, or defer identity merge candidates | Data Steward, Admin |
| `GET` | `/api/v1/identity/merges/` | History of unified identities and crosswalk mappings | Data Steward, Admin |
| `POST` | `/api/v1/identity/merges/<id>/unmerge/` | Reversibly unmerge composite golden records back to constituent sources | Data Steward, Admin |

---

## 9. AI Copilot (Google Gemini 3.8 Flash + RAG)
| Method | Path | Description | Access Scope |
|---|---|---|---|
| `POST` | `/api/v1/copilot/query/` | Grounded AI query answering with citation of retrieved policy chunks, read-only SQL execution provenance, and Section 8 refusal guards | All authenticated users |
| `POST` | `/api/v1/copilot/feedback/` | Submit collector feedback (thumbs up/down, corrections) for alignment evaluation | All authenticated users |

### Copilot Refusal Guardrails
- **Protected Attribute Non-Inference**: Requests asking to infer or condition collections actions on gender, ethnicity, religion, marital status, or nationality are hard-refused with standard code `GOVERNANCE_REFUSAL`.
- **SQL Mutation Prevention**: Data modification queries (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`) or non-whitelisted database tables are blocked.

---

## 10. Policy Library & Compliance Retrieval
| Method | Path | Description | Access Scope |
|---|---|---|---|
| `GET` | `/api/v1/policies/` | Active collection policy documents, jurisdiction rules, and contact cap rules | All roles |
| `GET` | `/api/v1/policies/search/` | Semantic/lexical RAG chunk search across policy repository | All roles |

---

## 11. Feature Store & Lineage Monitoring
| Method | Path | Description | Access Scope |
|---|---|---|---|
| `GET` | `/api/v1/features/definitions/` | Feature metadata registry: data types, entity keys, freshness SLAs, source lineage | Lead, Data Steward, Admin |
| `GET` | `/api/v1/features/monitoring/` | Population Stability Index (PSI) drift monitoring, offline/online skew, missingness | Lead, Admin |

---

## 12. ML Model Registry & Explanations
| Method | Path | Description | Access Scope |
|---|---|---|---|
| `GET` | `/api/v1/models/` | Registered ML models (Cure Probability, PTP Propensity) and performance metrics | Lead, Data Scientist, Admin |
| `POST` | `/api/v1/models/train/` | Trigger offline training & calibration using Scikit-Learn / XGBoost on feature store | Data Scientist, Admin |
| `POST` | `/api/v1/models/predict/` | Generate calibrated Honor Score (0-100) with local SHAP attribution explanations | Collector, Lead |
| `GET` | `/api/v1/predictions/` | Real-time and batch model scores with top SHAP feature attribution weights | Collector, Lead |

---

## 13. Decisioning & Rules Engine
| Method | Path | Description | Access Scope |
|---|---|---|---|
| `GET` | `/api/v1/recommendations/` | Generated Next Best Action cards with rationale, eligible settlement tiers, and confidence | Collector, Lead |
| `GET` | `/api/v1/rules/` | Configured deterministic business policy rules | Lead, Admin |
| `POST` | `/api/v1/rules/evaluate/` | Test deterministic rule evaluation against an account or hypothetical scenario | Collector, Lead |

---

## 14. Workload Assignments & Capacity
| Method | Path | Description | Access Scope |
|---|---|---|---|
| `GET` | `/api/v1/assignments/` | Current queue assignments across collectors | Lead, Admin |
| `POST` | `/api/v1/assignments/reassign/` | Reassign accounts between collectors or adjust capacity weights | Lead, Admin |
| `POST` | `/api/v1/assignments/optimize/` | Constrained work-allocation optimizer matching capacity, skills, and DNC constraints | Lead, Admin |
| `GET` | `/api/v1/assignments/agents/` | Agent status, current active accounts, and skill specialization tags | Lead, Admin |

---

## 15. Approvals & Human-in-the-Loop Governance
| Method | Path | Description | Access Scope |
|---|---|---|---|
| `GET` | `/api/v1/approvals/` | Pending high-impact actions (settlement > $5,000, legal escalation, hardship plans) | Lead, Admin |
| `POST` | `/api/v1/approvals/<id>/transition/` | Approve, reject, or escalate with pre-execution safety revalidation | Lead, Admin |

---

## 16. Audit Log, Experiments & Infrastructure Monitoring
| Method | Path | Description | Access Scope |
|---|---|---|---|
| `GET` | `/api/v1/audit/` | Immutable append-only audit trail with actor, action, timestamp, and before/after state diffs | Auditor, Admin |
| `GET` | `/api/v1/experiments/` | A/B testing cohorts, champion/challenger allocation, recovery rates | Lead, Data Scientist, Admin |
| `GET` | `/api/v1/experiments/<id>/significance/` | Two-proportion Z-test hypothesis testing, 95% CI, and statistical power maturity | Lead, Data Scientist, Admin |
| `GET` | `/api/v1/monitoring/health/` | Service liveness, component statuses, and Kafka broker telemetry | Public |
| `GET` | `/api/v1/monitoring/pipeline/` | Ingestion pipeline latency, batch processing lag, and Kafka topic posture | Admin |
| `POST` | `/api/v1/monitoring/pipeline/` | Trigger on-demand PySpark Lakehouse batch pipeline (Raw -> Silver -> Golden) | Admin |
| `GET` | `/api/v1/monitoring/quality/` | Data quality check metrics, schema validation failure counts | Admin |
| `POST` | `/api/v1/contacts/transcribe/` | Whisper conversational signal extraction (PTP, Hardship, Dispute indicators) | Collector, Lead |

