# Security and data handling

NodeNix is an early local support tool. It is not a malware detector, incident containment system or compliance certificate. Only use the repair actions on machines you are authorized to administer.

## Reporting a vulnerability

Use GitHub private vulnerability reporting when it is enabled for this repository. If it is unavailable, open an issue requesting a private contact channel without posting exploit details, credentials, real support bundles or endpoint identifiers.

## Data boundaries

Local scan/report output contains identifying device and network inventory. Share mode omits selected sections and metadata through a whitelist, recomputes findings, and removes detailed collection errors. Broad device/security details remain; review the result before publishing it.

Diagnostic scans do not invoke repair commands. Connectivity probes are optional. NodeNix makes no cloud API call and includes no telemetry. Antivirus policy is read as evidence and is not automatically changed.

The PowerShell execution-policy option applies to the spawned process and cannot override organization policy. A known folder-write block should be resolved through a writable destination or an approved policy, with endpoint protection left enabled.

## Export protections

Imports are bounded and typed before analysis. Embedded JSON is escaped for its HTML context; collected values are rendered as text. CSV formula-like fields are neutralized. Support ZIPs contain an explicit set of generated files and a hash manifest. The manifest detects accidental alteration; it is not a trusted digital signature.

The public-tree check rejects live JSON scans, mislabeled sample reports and known runtime export files in the publishable tree. It is not a general secret scanner. Review staged changes before pushing.
