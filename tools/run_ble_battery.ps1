<#
.SYNOPSIS
    WeLock Battery Reader (Windows PowerShell)
.DESCRIPTION
    Startet ble_battery.py unter Windows, prueft Python und bleak automatisch.
.EXAMPLE
    .\run_ble_battery.ps1 "AA:BB:CC:DD:EE:FF"
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
$env:PYTHONPATH = if ($env:PYTHONPATH) { "$RepoRoot;$ScriptDir;$env:PYTHONPATH" } else { "$RepoRoot;$ScriptDir" }

$PythonBin = $null
if ($env:VIRTUAL_ENV -and (Test-Path "$env:VIRTUAL_ENV\Scripts\python.exe")) {
    $PythonBin = "$env:VIRTUAL_ENV\Scripts\python.exe"
} elseif (Test-Path "$RepoRoot\.venv\Scripts\python.exe") {
    $PythonBin = "$RepoRoot\.venv\Scripts\python.exe"
} elseif (Test-Path "$ScriptDir\.venv\Scripts\python.exe") {
    $PythonBin = "$ScriptDir\.venv\Scripts\python.exe"
} else {
    $PythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $PythonCmd) {
        $PythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
    }
    if ($PythonCmd) {
        $PythonBin = $PythonCmd.Source
    }
}

if (-not $PythonBin) {
    Write-Error "FEHLER: Kein Python-Interpreter gefunden. Bitte installieren Sie Python 3.10+ von https://www.python.org/"
    exit 1
}

$VersionCheck = & $PythonBin -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
if ($LASTEXITCODE -ne 0) {
    Write-Error "FEHLER: Python 3.10 oder neuer erforderlich."
    exit 1
}

$BleakCheck = & $PythonBin -c "import bleak" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "FEHLER: Das Modul 'bleak' fehlt! Bitte installieren mit: pip install -r `"$ScriptDir\requirements-ble.txt`"" -ForegroundColor Red
    exit 1
}

$ScriptFile = Join-Path $ScriptDir "ble_battery.py"
& $PythonBin $ScriptFile @args
exit $LASTEXITCODE
