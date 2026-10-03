# Portfolio lab cases

Use a disposable Windows VM with a snapshot. Capture real before/after reports. The bundled sample is explicitly fictional and must not be described as a completed real investigation.

## Case 1 — DNS troubleshooting

Record normal access first. In a private lab only, introduce an invalid DNS server via Windows settings. Collect with `--connectivity`. Explain why a DNS failure and an ICMP success are evidence, not proof of an unreachable DNS server. Restore the original approved configuration manually; flushing cache does not correct wrong DNS settings. Rescan and verify the actual website. Export a ticket with the action you really performed.

## Case 2 — Printer service

In a VM with a test printer installed, record queue and spooler state. Stop spooler manually only when no important jobs are printing. Scan and inspect findings. Preview RestartSpooler with WhatIf, then execute with confirmation. Scan again and submit a test print. A running service does not prove the printer produced output.

## Case 3 — USB Device Manager error

Use an existing genuine Device Manager error; do not deliberately damage hardware. Record device name/code and collect a local report. Try known-good cable and alternate port, one change at a time. Compare findings and confirm device functionality. Do not claim code 43 identifies a specific faulty component.

## Case 4 — Privacy export

Generate local and share reports from the same scan into separate folders. Demonstrate that account names, hostname, network addresses and software/device inventories are absent from the share ZIP and report. Discuss the tradeoff: reduced detail also means fewer diagnostic findings.

## Interview explanation

“I built NodeNix to connect Windows evidence collection with L1 troubleshooting and ticket documentation. It separates diagnostics from confirmed repair actions, records unavailable checks, and recomputes reports after applying a privacy whitelist. I validate resolution with fresh evidence and the original user symptom.”

Only claim the live Windows scenarios after you have run them and recorded their outcomes.
