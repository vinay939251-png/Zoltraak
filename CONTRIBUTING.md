# Contributing locally

Read `Readme.md`, `plan.md`, and `TODO.md` before changing behavior. Keep the demo label and synthetic-data disclaimer visible. Add or update a deterministic test for every service behavior, and record actual commands/results in the README journal. Do not add credentials, real customer data, or claims of production model performance.

Use `npm.cmd test` on the current Windows device because PowerShell script execution blocks `npm.ps1`. Start the app with `node server.js`. Reset state with `powershell -ExecutionPolicy Bypass -File scripts/reset-demo.ps1` only when a clean fixture is needed.
