<#
.SYNOPSIS
    WeLock Hybrid Command Probe (Windows PowerShell Wrapper)
.DESCRIPTION
    Liest die BLE-Challenge und den Akkustand aus dem Schloss und fordert bei
    der WeLock Cloud API den 15-Byte-Hex-Befehl an (ohne das Schloss zu entriegeln).
    Leitet alle Parameter transparent und unverändert an welock_command_probe.py weiter.
.EXAMPLE
    .\run_command_probe.ps1
.EXAMPLE
    .\run_command_probe.ps1 -a "AA:BB:CC:DD:EE:FF" -u "user@example.com" -n "C41..."
.EXAMPLE
    .\run_command_probe.ps1 "AA:BB:CC:DD:EE:FF" --show-command
.EXAMPLE
    .\run_command_probe.ps1 --help
#>

$ErrorActionPreference = "Stop"

# 1. Automatisches Erkennen des Projekt- und Tool-Verzeichnisses
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
$env:PYTHONPATH = if ($env:PYTHONPATH) { "$RepoRoot;$ScriptDir;$env:PYTHONPATH" } else { "$RepoRoot;$ScriptDir" }

# 2. Python-Interpreter ermitteln
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

# 3. Mindestversion prüfen (Python >= 3.10)
$VersionCheck = & $PythonBin -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
if ($LASTEXITCODE -ne 0) {
    Write-Error "FEHLER: Python 3.10 oder neuer erforderlich. Gefundener Interpreter: $(& $PythonBin --version)"
    exit 1
}

# 4. Abhängigkeit prüfen (bleak)
$BleakCheck = & $PythonBin -c "import bleak" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "======================================================================" -ForegroundColor Red
    Write-Host "FEHLER: Das erforderliche Python-Paket 'bleak' ist nicht installiert!" -ForegroundColor Red
    Write-Host "======================================================================" -ForegroundColor Red
    Write-Host "Bitte führen Sie folgenden Befehl aus:" -ForegroundColor Yellow
    Write-Host "  pip install -r `"$ScriptDir\requirements-ble.txt`"" -ForegroundColor Cyan
    Write-Host "======================================================================" -ForegroundColor Red
    exit 1
}

# 5. Zielskript ausführen und alle Argumente transparent übergeben
$ScriptFile = Join-Path $ScriptDir "welock_command_probe.py"
& $PythonBin $ScriptFile @args
exit $LASTEXITCODE
