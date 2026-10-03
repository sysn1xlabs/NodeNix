# Validation record — 2026-10-03 — v0.1.2

## Completed locally

- **33 Python regression tests passed.** They cover diagnostic behavior, unavailable evidence, ICMP/event-provider interpretation, privacy filtering, HTML/CSV escaping, bundle integrity, imported data types, invalid JSON, nonfinite/oversized numbers, source overwrite prevention, output access failures, collection timeout/policy errors, missing scan output, browser fallback, staged generation, coverage changes and publication guards.
- The dependency-free JavaScript DOM harness passed console initialization, navigation, finding search, unavailable evidence, workflow selection, resolved-ticket verification guard and download handlers. This tests logic, not layout rendering.
- CLI demo and share reports were generated. Release packaging checks the selected source files, ZIP integrity and produces a SHA-256 checksum.
- The README, troubleshooting history, release notes, contribution docs, issue/PR templates and CI configuration are included.

## Owner-reported Windows result

During initial testing, PowerShell policy blocked the collector. A process-only launch allowed collection to start; writing in the extracted Downloads folder then failed. The owner reported the collector and report working after both destinations were changed to `%TEMP%`.

This is evidence that the workflow worked at that destination. It does not prove Defender caused the earlier write block, independently validate every collected section, or validate the newest 0.1.2 wrapper and repair changes.

## Configured but not yet confirmed on GitHub

The workflow runs Python tests on Windows/Linux with Python 3.9/3.13, dashboard logic, public-source checks, PowerShell parser/WhatIf checks and one passive Windows collector smoke test. Review the actual Actions result after publication; the build environment cannot execute that hosted run.

## Remaining limitations

- No native Windows collector or repair execution was performed in this Linux build environment.
- PowerShell parser validation must run on Windows or a PowerShell runtime. The configured Windows job performs it.
- Real-browser appearance, narrow layout, accessibility interactions and print output still require visual review.
- Repair execution requires a disposable lab and real post-action symptom verification. The parser/WhatIf check does not perform repairs.
- This is an early source release, not a signed executable or a production certification.

## Reproduce the checks

```powershell
py -3 -m unittest discover -s tests -v
node tests/test_dashboard.cjs
py -3 scripts/check_public_tree.py
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tests\Test-Collectors.ps1
py -3 nodenix.py scan --open
```

Use a different `--out` folder for each investigation. Check section statuses and keep actual endpoint evidence private.
