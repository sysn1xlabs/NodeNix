#requires -Version 5.1
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$OutputPath, [switch]$Connectivity, [ValidateRange(1,168)][int]$EventHours=24)
$ErrorActionPreference='Stop'
if ($env:OS -ne 'Windows_NT') { throw 'NodeNix live collection requires Windows.' }
$sections=[ordered]@{}
$arraySections=@('storage','physical_disks','network','services','processes','firewall','bitlocker','accounts','software','startup','connections','drivers')
# Resolve relative paths through PowerShell's current filesystem location.
$full=$ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputPath)
$parent=[IO.Path]::GetDirectoryName($full)
$probe=Join-Path $parent ([guid]::NewGuid().ToString()+'.nodenix-write-check')
try {
    $null=[IO.Directory]::CreateDirectory($parent)
    [IO.File]::WriteAllText($probe,'NodeNix write check')
    [IO.File]::Delete($probe)
} catch {
    throw "NodeNix cannot write to '$parent'. Collection has not started. Choose a writable folder such as `$env:TEMP. $($_.Exception.Message)"
}
function Collect([string]$Name,[scriptblock]$Body) {
    Write-Host "Collecting $Name..."
    try {
        $data=& $Body
        if($script:arraySections -contains $Name){
            if($null -eq $data){$data=@()}else{$data=@($data)}
        }
        elseif($null -eq $data){throw 'The Windows provider returned no data.'}
        $script:sections[$Name]=@{status='ok';data=$data}
    }
    catch { $script:sections[$Name]=@{status='unavailable';data=$null;error=$_.Exception.Message} }
}
Collect 'system' {
    $os=Get-CimInstance Win32_OperatingSystem
    $cs=Get-CimInstance Win32_ComputerSystem
    $bios=Get-CimInstance Win32_BIOS
    @{hostname=$env:COMPUTERNAME;user=$env:USERNAME;os=$os.Caption;build=$os.BuildNumber;manufacturer=$cs.Manufacturer;model=$cs.Model;serial=$bios.SerialNumber;bios=$bios.SMBIOSBIOSVersion;domain=$cs.Domain;domain_joined=$cs.PartOfDomain;uptime_days=[math]::Round(((Get-Date)-$os.LastBootUpTime).TotalDays,1);memory_percent=[math]::Round(100*(1-$os.FreePhysicalMemory/$os.TotalVisibleMemorySize),1);ram_gb=[math]::Round($cs.TotalPhysicalMemory/1GB,1)}
}
Collect 'hardware' {
    @{cpu=@(Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors,LoadPercentage);gpu=@(Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion);battery=@(Get-CimInstance Win32_Battery | Select-Object Name,BatteryStatus,EstimatedChargeRemaining);devices=@(Get-CimInstance Win32_PnPEntity -Filter 'ConfigManagerErrorCode <> 0' | Select-Object Name,PNPDeviceID,ConfigManagerErrorCode)}
}
Collect 'storage' {
    @(Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | ForEach-Object { @{drive=$_.DeviceID;size_gb=[math]::Round($_.Size/1GB,1);free_gb=[math]::Round($_.FreeSpace/1GB,1);used_percent=$(if($_.Size -gt 0){[math]::Round(100*(1-$_.FreeSpace/$_.Size),1)}else{$null});filesystem=$_.FileSystem} })
}
Collect 'physical_disks' { @(Get-PhysicalDisk | Select-Object FriendlyName,MediaType,BusType,HealthStatus,OperationalStatus,Size) }
Collect 'network' {
    @(Get-CimInstance Win32_NetworkAdapterConfiguration -Filter 'IPEnabled=True' | ForEach-Object { @{adapter=$_.Description;addresses=@($_.IPAddress);gateway=@($_.DefaultIPGateway);dns=@($_.DNSServerSearchOrder);dhcp=$_.DHCPEnabled;mac=$_.MACAddress} })
}
Collect 'connectivity' {
    if(-not $Connectivity) { @{tested=$false;reason='Opt in with -Connectivity to send ICMP, DNS and HTTPS probes.'} }
    else {
        $cfg=Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway } | Select-Object -First 1
        $gateway=$null
        if($cfg) { $gateway=Test-Connection -ComputerName $cfg.IPv4DefaultGateway.NextHop -Count 1 -Quiet -ErrorAction SilentlyContinue }
        $ip=Test-Connection -ComputerName '1.1.1.1' -Count 1 -Quiet -ErrorAction SilentlyContinue
        $dns=$false; $https=$false
        try { $null=Resolve-DnsName 'www.microsoft.com' -DnsOnly; $dns=$true } catch {}
        try { $r=Invoke-WebRequest 'https://www.microsoft.com' -Method Head -UseBasicParsing -TimeoutSec 10; $https=($r.StatusCode -ge 200 -and $r.StatusCode -lt 400) } catch {}
        @{tested=$true;gateway=$gateway;internet_icmp=[bool]$ip;dns=$dns;https=$https;target='www.microsoft.com'}
    }
}
Collect 'services' { @(Get-CimInstance Win32_Service | Select-Object Name,DisplayName,State,StartMode) }
Collect 'processes' { @(Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 30 @{n='name';e={$_.ProcessName}},Id,@{n='memory_mb';e={[math]::Round($_.WorkingSet64/1MB,1)}},@{n='cpu_seconds';e={$_.CPU}}) }
Collect 'printers' {
    @{printers=@(Get-CimInstance Win32_Printer | Select-Object Name,Default,WorkOffline,PrinterStatus,PortName,DriverName);jobs=@(Get-CimInstance Win32_PrintJob | Select-Object Name,JobId,Status,TotalPages);spooler=(Get-Service Spooler).Status.ToString()}
}
Collect 'events' {
    $rows=@()
    foreach($log in @('System','Application')) {
        try { $rows+=@(Get-WinEvent -FilterHashtable @{LogName=$log;Level=1,2,3;StartTime=(Get-Date).AddHours(-$EventHours)} -MaxEvents 200 | Select-Object @{n='log';e={$log}},Id,ProviderName,LevelDisplayName,@{n='time';e={$_.TimeCreated.ToUniversalTime().ToString('o')}}) }
        catch { if($_.FullyQualifiedErrorId -notlike 'NoMatchingEventsFound*'){throw} }
    }
    @{hours=$EventHours;limit_per_log=200;events=$rows}
}
Collect 'updates' {
    @{hotfixes=@(Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 20 HotFixID,Description,@{n='installed';e={if($_.InstalledOn){$_.InstalledOn.ToString('o')}}});reboot_pending=((Test-Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending') -or (Test-Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired') -or ($null -ne (Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager' -Name PendingFileRenameOperations -ErrorAction SilentlyContinue)))}
}
Collect 'defender' { Get-MpComputerStatus | Select-Object AntivirusEnabled,RealTimeProtectionEnabled,AntivirusSignatureAge,AMServiceEnabled }
Collect 'firewall' { @(Get-NetFirewallProfile | Select-Object Name,Enabled) }
Collect 'bitlocker' { @(Get-BitLockerVolume | Select-Object MountPoint,@{n='ProtectionStatus';e={$_.ProtectionStatus.ToString()}},@{n='VolumeStatus';e={$_.VolumeStatus.ToString()}}) }
Collect 'secure_boot' { @{enabled=Confirm-SecureBootUEFI} }
Collect 'tpm' { Get-Tpm | Select-Object TpmPresent,TpmReady }
Collect 'accounts' { @(Get-LocalGroupMember -SID 'S-1-5-32-544' | Select-Object Name,ObjectClass,PrincipalSource) }
Collect 'software' {
    @(Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*','HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*','HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*' -ErrorAction SilentlyContinue | Where-Object DisplayName | Select-Object DisplayName,DisplayVersion,Publisher | Sort-Object DisplayName -Unique)
}
Collect 'startup' { @(Get-CimInstance Win32_StartupCommand | Select-Object Name,Location) }
Collect 'connections' { @(Get-NetTCPConnection -State Established | Select-Object LocalAddress,LocalPort,RemoteAddress,RemotePort,OwningProcess) }
Collect 'drivers' { @(Get-CimInstance Win32_PnPSignedDriver | Select-Object DeviceName,DriverVersion,DriverProviderName,IsSigned) }
$principal=New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$result=@{schema_version=1;version='0.1.2';mode='live';generated_at=[DateTime]::UtcNow.ToString('o');elevated=$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator);sections=$sections}
try {
    $null=New-Item -ItemType Directory -Path $parent -Force -ErrorAction Stop
    if(-not (Test-Path -LiteralPath $parent -PathType Container)){throw "Directory was not created: $parent"}
    $json=$result | ConvertTo-Json -Depth 12
    Set-Content -LiteralPath $full -Value $json -Encoding UTF8 -ErrorAction Stop
    if(-not (Test-Path -LiteralPath $full -PathType Leaf)){throw "Output file was not created: $full"}
} catch {
    throw "NodeNix could not write '$full'. Choose a writable folder (for example `$env:TEMP\NodeNix-Scan.json). $($_.Exception.Message)"
}
Write-Host "Saved $full"
