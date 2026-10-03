# Contributing

Start with a reproducible support problem and a small change. Use fictional fixtures; do not commit real scans, ticket notes or endpoint screenshots.

## Local setup

Clone/download the repository. Python 3.9+ runs demo/report/tests without pip packages. Windows PowerShell 5.1+ is required for native collection. Node.js is optional for the dashboard logic harness.

```powershell
py -3 -m unittest discover -s tests -v
node tests/test_dashboard.cjs
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tests\Test-Collectors.ps1
py -3 nodenix.py demo --open
py -3 scripts/check_public_tree.py
```

Use `python3` on Linux/macOS. The PowerShell test is a Windows parser/WhatIf check, not a repair execution.

## Design rules

- Collectors return structured section data and distinguish unavailable evidence from an empty result.
- Add a schema validation rule when analysis consumes a newly typed field.
- Findings explain the observation and next step without asserting an unproven root cause.
- New collected fields are excluded from share output until explicitly reviewed and allowlisted.
- Repairs require a bounded action, confirmation, privileges when needed, an audit record and a separate verification step.
- Preserve original input files. Keep generated reports out of source control unless they are checked fictional samples.

Add regression tests for concrete failure modes or diagnostic behavior. Do not require a test that changes the contributor's machine simply to exercise a repair. The hosted Windows job runs a passive collection smoke test and previews repairs with WhatIf.

## Submitting a change

Create a branch, update the relevant docs/changelog, run the applicable checks, and open a pull request. Describe the behavior, validation and any remaining Windows limitation. Keep issue/PR attachments free of identifying support data.
