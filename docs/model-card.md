# Model Card — Local demonstration predictors

## Status
`demo-untrained-v1` is a deterministic development fixture used to exercise recommendation display and governance controls. It is not trained, calibrated, validated, or suitable for customer treatment.

## Intended target
The UI labels the target as “30-day cure demonstration.” A production model must define the eligible starting cohort, prediction timestamp, 30-day observation window, exclusions, label maturity, point-in-time feature join, evaluation split, calibration method, and fairness review before deployment.

## Features
The local registry includes DPD, overdue balance, recent payments, PTP adherence, missed PTP, payment recency, contacts, dispute status, and hardship routing. Protected attributes are excluded.

## Explanations
The local feature contributions are fixture evidence for UI behavior. A production SHAP explanation must be generated from the exact registered model artifact and version used for inference. No causal interpretation is made.
