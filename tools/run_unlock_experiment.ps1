<#
.SYNOPSIS
    WeLock Unlock Experiment Runner (Windows PowerShell)
.DESCRIPTION
    Startet welock_unlock_experiment.py unter Windows, prueft Python und Bleak
    und setzt den PYTHONPATH korrekt auf das Repository-Root.
.EXAMPLE
    .\run_unlock_experiment.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

# 1. Automatisches Erkennen des Projekt- und Tool-Verzeichnisses
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir

# 2. PYTHONPATH auf das Repository-Root setzen
$env:PYTHONPATH = if ($env:PYTHONPATH) { "$RepoRoot;$env:PYTHONPATH" } else { "$RepoRoot" }

# 3. Python-Interpreter ermitteln
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

# 4. Mindestversion pruefen (Python >= 3.10)
$VersionCheck = & $PythonBin -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
if ($LASTEXITCODE -ne 0) {
    Write-Error "FEHLER: Python 3.10 oder neuer erforderlich. Gefunden: $(& $PythonBin --version)"
    exit 1
}

# 5. Abhaengigkeit pruefen (bleak)
$BleakCheck = & $PythonBin -c "import bleak" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "======================================================================" -ForegroundColor Red
    Write-Host "FEHLER: Das erforderliche Python-Paket 'bleak' ist nicht installiert!" -ForegroundColor Red
    Write-Host "======================================================================" -ForegroundColor Red
    Write-Host "Bitte fuehren Sie folgenden Befehl aus:" -ForegroundColor Yellow
    Write-Host "  pip install -r `"$ScriptDir\requirements-ble.txt`"" -ForegroundColor Cyan
    Write-Host "Oder in einer virtuellen Umgebung:" -ForegroundColor Yellow
    Write-Host "  python -m venv .venv; .venv\Scripts\Activate.ps1; pip install -r tools\requirements-ble.txt" -ForegroundColor Cyan
    Write-Host "======================================================================" -ForegroundColor Red
    exit 1
}

# 6. Ausfuehren mit allen uebergebenen Parametern
$ScriptFile = Join-Path $ScriptDir "welock_unlock_experiment.py"
& $PythonBin $ScriptFile @args
exit $LASTEXITCODE
