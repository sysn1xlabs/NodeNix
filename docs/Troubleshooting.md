# Troubleshooting NodeNix

## Scripts are disabled / UnauthorizedAccess

**Observed:** the initial release's `py -3 nodenix.py scan --open` failed because its child PowerShell process could not load the collector under the effective execution policy.

**Fix:** v0.1.1 and later launch the collector with `-ExecutionPolicy Bypass` for that process only. It does not edit CurrentUser/LocalMachine policy or bypass organization Group Policy.

If the latest version is still blocked:

```powershell
Get-ExecutionPolicy -List
```

If MachinePolicy or UserPolicy is set, follow the managed device's approved policy. On a personal machine, the direct launch used during troubleshooting was:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\collector\Collect-NodeNix.ps1 -OutputPath "$env:TEMP\NodeNix-Scan.json"
```

Optional `.ps1` launchers can themselves be blocked before Python runs. Use `py -3 nodenix.py scan --open`, or launch the helper explicitly with the process option:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Start-NodeNix.ps1 -Mode Scan
```

## Could not find part of the path / folder write blocked

**Observed:** writing a scan beneath the extracted Downloads folder failed. Writing both the collector JSON and the report under `%TEMP%` succeeded on the same machine.

The owner suspected Defender. Controlled folder access is one possible cause, but these results alone do not distinguish it from other access or path restrictions. Check **Windows Security → Virus & threat protection → Protection history** for a matching blocked write. Keep Defender enabled.

**Fix:** default reports use the OS temporary directory. Both the Python launcher and collector check destination access before collection; the collector also checks that its final file exists. Pick a writable location explicitly when needed:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\collector\Collect-NodeNix.ps1 -OutputPath "$env:TEMP\NodeNix-Scan.json"
py -3 nodenix.py report "$env:TEMP\NodeNix-Scan.json" --profile local --out "$env:TEMP\NodeNix-Report" --open
```

The second command preserves local detail. For a share profile, select a different destination. Temporary reports can be cleaned by Windows; copy or export evidence to an approved durable location when retaining it.

## A collection section is unavailable

Open Evidence and select that section. Permissions, unsupported firmware, unavailable Windows modules, a stopped provider or absent data can cause this. The other collectors continue. An unavailable result is not pass or fail.

If appropriate, rerun from Administrator PowerShell into a different output folder. NodeNix does not elevate itself. Collection shows a coverage count; comparisons report sections whose status changed.

## Collector timeout

The default limit is 300 seconds. NodeNix stops the child process and does not generate a report from a timed-out collection. If a provider needs longer:

```powershell
py -3 nodenix.py scan --scan-timeout 600
```

Investigate repeated stalls rather than continuously increasing the timeout.

## Imported scan is rejected

NodeNix expects UTF-8 JSON with `schema_version: 1`, mode demo/live and typed section records. It rejects oversized files, nonfinite numbers and malformed nested data before analysis. Use the original collector export rather than hand-editing types or importing another tool's schema.

## Output would overwrite the input scan

Use a different `--out` folder. This protects the source evidence when converting a local scan to a reduced share profile.

## Browser did not open

The exports may have completed successfully. Open the printed `Report.html` path manually. An HTML viewer that disables JavaScript will not run the console; use a local browser.

## Repair audit log is blocked

Repair scripts use the temp directory for the audit log by default. Choose a writable `-AuditPath` if needed. A failed initial audit write prevents the repair from starting; a failed final audit write produces a warning and does not conceal an action that was attempted. Review the command output and verify the actual user symptom.

## Capturing a bug report

Record the release version, Python/PowerShell versions, command, section statuses and sanitized error text. `--debug` can expose local paths. Remove identifiers before posting publicly. Real support bundles should remain private even when they appear relevant to a bug.

References:

- [Microsoft: PowerShell execution policies](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_execution_policies)
- [Microsoft: Controlled folder access](https://learn.microsoft.com/en-us/defender-endpoint/controlled-folders)
