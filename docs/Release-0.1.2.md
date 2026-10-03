# NodeNix v0.1.2

NodeNix is a local Windows diagnostics and IT support toolkit with an offline console, guided investigation, privacy profiles and confirmed repair commands.

## Included

- Structured Windows evidence across 21 independently handled sections.
- System, hardware, storage, network, Windows, printer and security evidence.
- Six guided support procedures, editable ticket notes and KB drafts.
- Offline HTML, JSON/CSV support bundle and SHA-256 manifest.
- Local/share profiles with findings recomputed after filtering.
- Separately confirmed DNS flush, spooler restart, SFC and DISM health-state check.

## Fixes and error handling

- PowerShell process-only execution-policy option for the live collector.
- Default output under the working OS temp folder, addressing the observed Downloads write failure.
- Destination preflight and final-file checks; writable audit logging before repairs start.
- Typed/bounded imports, nested-record validation and nonfinite-number rejection.
- Readable policy/provider/permission errors, bounded collection timeout and debug mode.
- Source-scan overwrite protection, staged generation and coverage-aware comparison.
- Public-source guard, contribution/issue templates and configured Windows/Linux CI.

## Validation

The local build passed 33 Python regression tests and the dashboard DOM logic harness. The owner reported the direct Windows collector and report working after using %TEMP%. Hosted Windows CI is configured but its result must be checked after publication. Repair execution and real-browser layout remain outside the completed local validation.

## Start

Extract the full source ZIP and run `py -3 nodenix.py scan --open` on Windows, or open the fictional `samples/DemoReport/Report.html` directly. Reports default to `%TEMP%\NodeNix\scan`.

Temporary files may be cleaned by Windows. Real local support bundles contain identifying evidence and should stay private. AD administration, remote/fleet management and advanced malware triage are not implemented in this release.
