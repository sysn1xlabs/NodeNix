#requires -Version 5.1
[CmdletBinding(SupportsShouldProcess=$true,ConfirmImpact='High')]
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('FlushDNS','RestartSpooler','SFC','DISMCheck')][string]$Action,
    [string]$AuditPath=(Join-Path ([IO.Path]::GetTempPath()) 'NodeNix\repairs.jsonl')
)
$ErrorActionPreference='Stop'
if($env:OS -ne 'Windows_NT'){throw 'Windows required.'}
$descriptions=@{
    FlushDNS='Flush the DNS resolver cache'
    RestartSpooler='Restart Print Spooler; active printing may be interrupted'
    SFC='Run SFC /scannow; protected system files may be repaired'
    DISMCheck='Run DISM /Online /Cleanup-Image /CheckHealth (diagnostic only)'
}
if($PSCmdlet.ShouldProcess($env:COMPUTERNAME,$descriptions[$Action])) {
    $principal=New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    if(-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){
        throw 'Open PowerShell as Administrator for this action.'
    }
    $record=@{
        time=[DateTime]::UtcNow.ToString('o');action=$Action;status='started'
        verification='Not verified. Run a fresh NodeNix scan.'
    }
    $full=$ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($AuditPath)
    try {
        $null=[IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($full))
        $record | ConvertTo-Json -Compress | Add-Content -LiteralPath $full -Encoding UTF8 -ErrorAction Stop
    } catch {
        throw "Repair was not started: audit log '$full' is not writable. $($_.Exception.Message)"
    }
    $actionError=$null
    try {
        switch($Action){
            FlushDNS { Clear-DnsClientCache }
            RestartSpooler {
                Restart-Service Spooler
                (Get-Service Spooler).WaitForStatus('Running',[TimeSpan]::FromSeconds(20))
            }
            SFC {
                & "$env:SystemRoot\System32\sfc.exe" /scannow
                if($LASTEXITCODE -ne 0){throw "SFC exit code $LASTEXITCODE; inspect CBS.log."}
            }
            DISMCheck {
                & "$env:SystemRoot\System32\dism.exe" /Online /Cleanup-Image /CheckHealth
                if($LASTEXITCODE -ne 0){throw "DISM exit code $LASTEXITCODE"}
            }
        }
        $record.status='command_completed'
    } catch {
        $record.status='failed'
        $record.error=$_.Exception.Message
        $actionError=$_
    } finally {
        $record.time=[DateTime]::UtcNow.ToString('o')
        try { $record | ConvertTo-Json -Compress | Add-Content -LiteralPath $full -Encoding UTF8 -ErrorAction Stop }
        catch { Write-Warning "The command was attempted, but its final audit record could not be written to '$full'. $($_.Exception.Message)" }
    }
    if($null -ne $actionError){throw $actionError}
    Write-Host "Command completed. Audit: $full"
    Write-Host 'Rescan and verify the reported issue before resolving the ticket.'
}
