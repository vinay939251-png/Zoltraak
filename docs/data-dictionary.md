# Data Dictionary — Local Demo

| Entity | Key fields | Authority / notes |
|---|---|---|
| Customer | `id`, `name`, `email`, `phone`, `identities`, `lineage` | Golden read-model fixture; all values synthetic. |
| Account | `id`, `customerId`, `product`, `balance`, `overdueBalance`, `dpd`, restrictions, features, lineage | Account facts are sourced from synthetic loan/card systems. Monetary values are JSON numbers only for the demo adapter; production migration must use decimal columns. |
| Payment | `id`, `accountId`, `amount`, `status`, `date`, `sourceSystem` | Reconciled/reversed examples are included. |
| Recommendation | `id`, `accountId`, `version`, `status`, `score`, `modelVersion`, `action`, `topFeatures` | Score is deterministic development demonstration, not a calibrated probability. |
| Policy | `id`, `version`, `status`, `effectiveDate`, `chunks` | Policies are visibly demonstration policies and not official institutional documents. |
| Audit | `id`, `type`, `actor`, `entityId`, `timestamp`, `summary` | Append-only through the local application path; sensitive payloads are minimized. |

All source-like records retain `sourceSystem`, `sourceRecordId`, `observedAt`, `ingestedAt`, and `transformationVersion` where applicable. Protected attributes are absent from decision features.
