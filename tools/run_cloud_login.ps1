<#
.SYNOPSIS
    WeLock Cloud Login Runner (Windows PowerShell Wrapper)
.DESCRIPTION
    Startet welock_cloud_login.py unter Windows zur Prüfung von WeLock-Konten
    und zum Abruf registrierter Schlösser (deviceNumber, BLE-Namen).
    Leitet alle Parameter transparent und unverändert an welock_cloud_login.py weiter.
.EXAMPLE
    .\run_cloud_login.ps1
.EXAMPLE
    .\run_cloud_login.ps1 -u "user@example.com" -l
.EXAMPLE
    .\run_cloud_login.ps1 -u "user@example.com" -l --json
.EXAMPLE
    .\run_cloud_login.ps1 --help
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

# 4. Zielskript ausführen und alle Argumente transparent übergeben (benötigt kein bleak)
$ScriptFile = Join-Path $ScriptDir "welock_cloud_login.py"
& $PythonBin $ScriptFile @args
exit $LASTEXITCODE
