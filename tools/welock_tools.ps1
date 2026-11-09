<#
.SYNOPSIS
    WeLock Diagnostic Tools - Interaktives Hauptmenue (Windows PowerShell)
#>
[CmdletBinding()]
param()

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
$env:PYTHONPATH = if ($env:PYTHONPATH) { "$RepoRoot;$env:PYTHONPATH" } else { "$RepoRoot" }

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "          🔐 WeLock BLE & Cloud Diagnose-Werkzeugkasten             " -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "1) BLE-Geraete-Inspektion (ble_probe.py)"
Write-Host "   -> Untersucht ein BLE-Geraet und prueft GATT-Services/Characteristics"
Write-Host ""
Write-Host "2) WeLock Cloud-Login & Geraeteuebersicht (welock_cloud_login.py)"
Write-Host "   -> Prueft Zugangsdaten und listet Schlosscodes & BLE-Namen auf"
Write-Host ""
Write-Host "3) Hybrid Command-Probe (welock_command_probe.py)"
Write-Host "   -> Liest Challenge/Batterie per BLE & holt Cloud-Befehl (KEIN Unlock)"
Write-Host ""
Write-Host "4) Autorisierter Entriegelungstest (welock_unlock_experiment.py)"
Write-Host "   -> Sendet Cloud-Befehl per BLE an das Schloss (ECHTE Entriegelung!)"
Write-Host ""
Write-Host "5) Virtuelle Python-Umgebung erstellen & Bleak installieren"
Write-Host ""
Write-Host "0) Beenden"
Write-Host "======================================================================" -ForegroundColor Cyan

$Choice = Read-Host "Bitte Option waehlen [0-5]"

switch ($Choice) {
    "1" {
        $Addr = Read-Host "Geben Sie die BLE-Adresse ein (z. B. AA:BB:CC:DD:EE:FF)"
        $DoConnect = Read-Host "Verbindung und GATT-Services pruefen? (j/N)"
        if ($DoConnect -match "^[jJyY]$") {
            & "$ScriptDir\run_ble_probe.ps1" --address $Addr --connect
        } else {
            & "$ScriptDir\run_ble_probe.ps1" --address $Addr
        }
    }
    "2" {
        & "$ScriptDir\run_cloud_login.ps1"
    }
    "3" {
        & "$ScriptDir\run_command_probe.ps1"
    }
    "4" {
        & "$ScriptDir\run_unlock_experiment.ps1"
    }
    "5" {
        Write-Host "Erstelle venv unter $RepoRoot\.venv..." -ForegroundColor Yellow
        python -m venv "$RepoRoot\.venv"
        & "$RepoRoot\.venv\Scripts\python.exe" -m pip install --upgrade pip
        & "$RepoRoot\.venv\Scripts\python.exe" -m pip install -r "$ScriptDir\requirements-ble.txt"
        Write-Host "Virtuelle Umgebung erfolgreich eingerichtet!" -ForegroundColor Green
    }
    "0" {
        Write-Host "Auf Wiedersehen!"
        exit 0
    }
    Default {
        Write-Warning "Ungueltige Auswahl."
    }
}
