#requires -Version 5.1
[CmdletBinding()]
param([ValidateSet('Demo','Scan')][string]$Mode='Demo',[switch]$Connectivity,[switch]$Share)
$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
$launcher=Get-Command py.exe -ErrorAction SilentlyContinue
$arguments=@()
if($launcher){$arguments+= '-3'}else{$launcher=Get-Command python.exe -ErrorAction SilentlyContinue}
if(-not $launcher){throw 'Install Python 3.9+ from python.org, then restart PowerShell. See README.md.'}
$arguments+=@('nodenix.py',$Mode.ToLower(), '--open')
if($Mode -eq 'Scan' -and $Connectivity){$arguments+='--connectivity'}
if($Share){$arguments+=@('--profile','share')}
& $launcher.Source @arguments
if($LASTEXITCODE -ne 0){throw 'NodeNix did not complete. Review the error above.'}
