# Changelog

## 0.1.2 — 2026-10-03

- Split CLI, schema validation, analysis, privacy and reporting into focused modules.
- Added nested input checks, finite-number validation and readable runtime failures.
- Added output preflight, collector timeout, missing-output detection and browser fallback.
- Refused report exports that would overwrite the source scan.
- Staged exports before publication and exposed coverage changes in scan comparison.
- Normalized empty/singleton PowerShell inventories and marked missing object data unavailable.
- Moved repair audit defaults to the temp folder and checked audit access before any action.
- Added a GitHub README, troubleshooting history, release notes, contribution/security docs,
  issue/PR templates, source publication checks, packaging script and configured CI.


## 0.1.1 — 2026-10-03
- Default report output moved to the user temporary directory to work around protected Downloads folders.
- The live collector launches PowerShell with a process-only execution-policy override; saved policy is unchanged.
- Export now verifies its target folder and reports write failures clearly.


## 0.1.0 — 2026-10-03
- PowerShell Windows collection across 21 independently handled sections.
- Explainable triage rules and six guided troubleshooting workflows.
- Offline responsive HTML dashboard, evidence explorer, ticket and KB exports.
- Local/share profiles, support ZIP, section CSV exports and SHA-256 manifest.
- Four separately confirmed PowerShell actions with WhatIf and audit records.
- Fictional demo snapshot and reports; Python regression tests.
