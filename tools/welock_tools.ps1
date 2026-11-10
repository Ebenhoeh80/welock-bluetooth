<#
.SYNOPSIS
    WeLock Diagnostic Tools - Interaktives Hauptmenue (Windows PowerShell)
.DESCRIPTION
    Startet das interaktive Hauptmenü zur Auswahl und Ausführung aller WeLock-Tools.
.EXAMPLE
    .\welock_tools.ps1
.EXAMPLE
    .\welock_tools.ps1 1
#>

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
$env:PYTHONPATH = if ($env:PYTHONPATH) { "$RepoRoot;$ScriptDir;$env:PYTHONPATH" } else { "$RepoRoot;$ScriptDir" }

# Python-Interpreter ermitteln
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

# Falls Argumente übergeben wurden (z. B. Option 0-7), direkt an welock_tools.py übergeben
if ($args.Count -gt 0) {
    $ScriptFile = Join-Path $ScriptDir "welock_tools.py"
    & $PythonBin $ScriptFile @args
    exit $LASTEXITCODE
}

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "          🔐 WeLock BLE & Cloud Diagnose-Werkzeugkasten             " -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "1) BLE-Gerätesuche & WeLock-Erkennung (run_ble_scan.ps1)"
Write-Host "   -> Sucht Geräte in Reichweite und hebt WeLock-Zylinder hervor"
Write-Host ""
Write-Host "2) Akkustand & Challenge per BLE auslesen (run_ble_battery.ps1)"
Write-Host "   -> Liest Batteriestand in % und Challenge-Faktor direkt aus"
Write-Host ""
Write-Host "3) BLE-Geräte-Inspektion (run_ble_probe.ps1)"
Write-Host "   -> Untersucht ein BLE-Gerät und prüft GATT-Services/Characteristics"
Write-Host ""
Write-Host "4) WeLock Cloud-Login & Geräteübersicht (run_cloud_login.ps1)"
Write-Host "   -> Prüft Zugangsdaten und listet Schlosscodes & BLE-Namen auf"
Write-Host ""
Write-Host "5) Hybrid Command-Probe (run_command_probe.ps1)"
Write-Host "   -> Liest Challenge/Batterie per BLE & holt Cloud-Befehl (KEIN Unlock)"
Write-Host ""
Write-Host "6) Autorisierter Entriegelungstest (run_unlock.ps1)"
Write-Host "   -> Sendet Cloud-Befehl per BLE an das Schloss (ECHTE Entriegelung!)"
Write-Host ""
Write-Host "7) System- & Abhängigkeitsprüfung (dependency_check.py)"
Write-Host ""
Write-Host "8) Virtuelle Python-Umgebung erstellen & Bleak installieren"
Write-Host ""
Write-Host "0) Beenden"
Write-Host "======================================================================" -ForegroundColor Cyan

$Choice = Read-Host "Bitte Option wählen [0-8]"

switch ($Choice) {
    "1" {
        $OnlyWelock = Read-Host "Nur WeLock-Schlösser anzeigen? (j/N)"
        if ($OnlyWelock -match "^[jJyY]$") {
            & "$ScriptDir\run_ble_scan.ps1" --welock-only
        } else {
            & "$ScriptDir\run_ble_scan.ps1"
        }
    }
    "2" {
        $Addr = Read-Host "Geben Sie die BLE-Adresse ein (z. B. AA:BB:CC:DD:EE:FF)"
        & "$ScriptDir\run_ble_battery.ps1" $Addr
    }
    "3" {
        $Addr = Read-Host "Geben Sie die BLE-Adresse ein (z. B. AA:BB:CC:DD:EE:FF)"
        $DoConnect = Read-Host "Verbindung und GATT-Services prüfen? (j/N)"
        if ($DoConnect -match "^[jJyY]$") {
            & "$ScriptDir\run_ble_probe.ps1" --address $Addr --connect
        } else {
            & "$ScriptDir\run_ble_probe.ps1" --address $Addr
        }
    }
    "4" {
        & "$ScriptDir\run_cloud_login.ps1"
    }
    "5" {
        & "$ScriptDir\run_command_probe.ps1"
    }
    "6" {
        & "$ScriptDir\run_unlock.ps1"
    }
    "7" {
        & $PythonBin "$ScriptDir\dependency_check.py"
    }
    "8" {
        Write-Host "Erstelle venv unter $RepoRoot\.venv..." -ForegroundColor Yellow
        & $PythonBin -m venv "$RepoRoot\.venv"
        & "$RepoRoot\.venv\Scripts\python.exe" -m pip install --upgrade pip
        & "$RepoRoot\.venv\Scripts\python.exe" -m pip install -r "$ScriptDir\requirements-ble.txt"
        Write-Host "Virtuelle Umgebung erfolgreich eingerichtet!" -ForegroundColor Green
    }
    "0" {
        Write-Host "Auf Wiedersehen!"
        exit 0
    }
    Default {
        Write-Warning "Ungültige Auswahl."
    }
}
