#requires -Version 5.1
# Run on Windows before live collection. Parser validation does not execute scripts.
$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
foreach($file in @("$root\collector\Collect-NodeNix.ps1","$root\collector\Repair-NodeNix.ps1","$root\Start-NodeNix.ps1")){
    $tokens=$null; $errors=$null
    $null=[System.Management.Automation.Language.Parser]::ParseFile($file,[ref]$tokens,[ref]$errors)
    if($errors.Count){$errors | Format-List;throw "Parser validation failed: $file"}
    Write-Host "Parsed: $file"
}
& "$root\collector\Repair-NodeNix.ps1" -Action FlushDNS -WhatIf
Write-Host 'Parser and repair dry-run completed. No repair executed.'
