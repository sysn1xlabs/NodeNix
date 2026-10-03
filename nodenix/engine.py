"""Evidence-based triage. No finding is a definitive root-cause claim."""
from collections import Counter

def data(scan, name, default=None):
    section = scan.get('sections', {}).get(name, {})
    return section.get('data', default) if section.get('status') == 'ok' else default

def rows(value):
    return value if isinstance(value, list) else ([] if value is None else [value])

def analyze(scan):
    findings = []
    def add(code, severity, category, title, evidence, next_step):
        findings.append(dict(code=code, severity=severity, category=category, title=title, evidence=evidence, next_step=next_step))
    system = data(scan, 'system', {}) or {}
    memory = system.get('memory_percent')
    if isinstance(memory, (float, int)) and memory >= 85:
        add('MEMORY_HIGH','warning','System','High memory utilization',f'{memory}% used at collection time.','Review top memory consumers and reproduce the slowdown; one sample does not establish a trend.')
    uptime = system.get('uptime_days')
    if isinstance(uptime, (int, float)) and not isinstance(uptime, bool) and uptime >= 14:
        add('UPTIME_LONG','info','System','Extended uptime',f"{system['uptime_days']} days since boot.",'Consider an agreed restart if troubleshooting requires it; uptime alone is not a fault.')
    for disk in rows(data(scan, 'storage')):
        used = disk.get('used_percent')
        if isinstance(used, (float, int)) and used >= 85:
            add('DISK_SPACE','critical' if used >= 95 else 'warning','Storage',f"Low free space on {disk.get('drive','drive')}",f"{used}% used; {disk.get('free_gb','unknown')} GB free.",'Review large files and approved cleanup options. Do not delete user data without approval.')
    for disk in rows(data(scan, 'physical_disks')):
        health = disk.get('HealthStatus')
        if health not in (None, 0, 'Healthy'):
            add('DISK_HEALTH','warning','Storage','Storage health requires review',str(health),'Back up important data and confirm with manufacturer diagnostics. This is not a full SMART assessment.')
    for dev in rows((data(scan,'hardware',{}) or {}).get('devices')):
        add('DEVICE_ERROR','warning','Hardware',f"Device error: {dev.get('Name','Unknown device')}",f"Device Manager code {dev.get('ConfigManagerErrorCode')}",'Check cable, port, power and driver evidence. Code 43 does not identify the failing component.')
    probe = data(scan,'connectivity',{}) or {}
    if probe.get('tested'):
        if probe.get('dns') is False:
            add('DNS_FAILED','warning','Network','DNS probe failed','www.microsoft.com could not be resolved during this scan.','Inspect configured DNS, VPN and resolver reachability; flush the cache only if appropriate, then retest.')
        if probe.get('https') is False:
            add('HTTPS_FAILED','warning','Network','HTTPS probe failed','HEAD request to www.microsoft.com did not succeed.','Check proxy, captive portal, TLS inspection, DNS and site availability. A single target failure does not prove an Internet outage.')
        if probe.get('gateway') is False or probe.get('internet_icmp') is False:
            add('ICMP_FAILED','info','Network','ICMP probe did not receive a reply','Gateway or Internet ICMP test failed.','ICMP may be filtered. Correlate with DNS and HTTPS before concluding connectivity is broken.')
    updates = data(scan,'updates',{}) or {}
    if updates.get('reboot_pending') is True:
        add('REBOOT_PENDING','warning','Windows','Restart indication detected','One or more pending-reboot registry indicators are present.','Arrange a restart, then rescan. These indicators do not measure update compliance.')
    defender = data(scan,'defender',{}) or {}
    if defender.get('RealTimeProtectionEnabled') is False:
        add('DEFENDER_REALTIME','warning','Security','Defender real-time protection inactive','Defender reports RealTimeProtectionEnabled = false.','Confirm whether an approved third-party antivirus manages protection before changing policy.')
    if isinstance(defender.get('AntivirusSignatureAge'),(int,float)) and defender['AntivirusSignatureAge'] > 7:
        add('DEFENDER_SIGNATURES','warning','Security','Defender signatures need review',f"Signature age: {defender['AntivirusSignatureAge']} days.",'Check approved signature update source and effective antivirus policy.')
    for profile in rows(data(scan,'firewall')):
        if profile.get('Enabled') in (False, 0, 'False'):
            add('FIREWALL_DISABLED','warning','Security',f"Firewall disabled: {profile.get('Name')}",'Profile is configured as disabled; it may not be the active profile.','Review effective network profile and organizational policy.')
    for volume in rows(data(scan,'bitlocker')):
        if volume.get('ProtectionStatus') in ('Off', 0):
            add('BITLOCKER_OFF','info','Security',f"BitLocker protection off: {volume.get('MountPoint')}",f"Volume status: {volume.get('VolumeStatus')}",'Check encryption requirements and recovery-key handling before enabling protection.')
    if (data(scan,'secure_boot',{}) or {}).get('enabled') is False:
        add('SECURE_BOOT_OFF','info','Security','Secure Boot disabled','UEFI query returned false.','Review hardware support and boot configuration before making firmware changes.')
    printers = data(scan,'printers',{}) or {}
    if printers.get('spooler') == 'Stopped' and rows(printers.get('printers')):
        add('SPOOLER_STOPPED','warning','Printers','Print Spooler stopped','Installed printers exist and spooler is stopped.','Check service events. If approved, restart spooler and submit a test page from the affected application.')
    for p in rows(printers.get('printers')):
        if p.get('WorkOffline') is True:
            add('PRINTER_OFFLINE','warning','Printers',f"Printer marked offline: {p.get('Name')}",'WorkOffline flag is set.','Inspect queue, port, cable and printer state. This flag alone does not prove a network fault.')
    counts = Counter((e.get('ProviderName'),e.get('Id')) for e in rows((data(scan,'events',{}) or {}).get('events')))
    for (provider, event_id), count in counts.items():
        if (provider == 'Microsoft-Windows-Kernel-Power' and event_id == 41):
            add('UNEXPECTED_SHUTDOWN','warning','Events','Unexpected shutdown events',f'{count} Kernel-Power 41 event(s) in the collected window.','Correlate crash dumps and adjacent events. Event 41 records an unclean shutdown; it does not prove a PSU failure.')
        elif provider in ('disk','Disk') and event_id in (7,51,153):
            add('STORAGE_EVENT','warning','Events','Storage-related events',f'{provider} {event_id}: {count} occurrence(s).','Check storage health, cabling and backups; escalate recurrent errors.')
    return sorted(findings, key=lambda f: {'critical':0,'warning':1,'info':2}[f['severity']])

WORKFLOWS = {
 'No Internet': {'sections':['network','connectivity'], 'steps':['Inspect adapter addresses, gateway and DNS; check for APIPA (169.254.x.x).','Compare gateway ICMP, DNS and HTTPS probes; an ICMP failure alone is inconclusive.','Check VPN, proxy and captive portal. Use approved network settings.','Apply an approved action, then run another scan with connectivity probes.','Verify access to the user’s actual service before marking resolved.']},
 'Slow computer': {'sections':['system','storage','processes','startup','events'], 'steps':['Reproduce and record when the slowdown occurs.','Review memory, free storage and top working sets. CPU seconds are cumulative, not instantaneous utilization.','Review startup entries and events; do not disable services blindly.','Agree any cleanup or restart with the user.','Repeat the same workload and compare before/after evidence.']},
 'Printer problem': {'sections':['printers','services','events'], 'steps':['Confirm affected printer, application, port and whether all users are affected.','Inspect offline flag, queue and Print Spooler.','Check power, cable or network port and driver compatibility.','Restart spooler only with approval; this can interrupt printing.','Submit a test page and verify output from the user’s application.']},
 'Windows Update': {'sections':['updates','services','events','storage'], 'steps':['Check available space and reboot indications.','Review Windows Update and BITS service states; trigger-start services may normally be stopped.','Review Settings update history; hotfix inventory is not complete update history.','Use DISMCheck for triage or SFC when repair is justified.','Reboot if agreed, retry the update and capture its actual outcome.']},
 'USB / driver error': {'sections':['hardware','drivers','events'], 'steps':['Record the exact device and Device Manager error code.','Test known-good cable and another port, one variable at a time.','Check manufacturer drivers and related events.','Do not assume code 43 means a software fault.','Reconnect and rescan; verify the intended device operation.']},
 'Security triage': {'sections':['defender','firewall','bitlocker','accounts','connections','startup'], 'steps':['Confirm effective antivirus and organizational policy.','Review unexpected administrator memberships and established connections in context.','This release does not identify malware or establish compromise.','Preserve evidence and escalate to the security team if suspicious.','Avoid killing processes or deleting evidence as an automatic fix.']},
}
