# Runs a local subset of the CI checks (the HA job needs Home Assistant and Python 3.14).
# Usage: powershell -File scripts\check.ps1      (from any folder; uses .venv if there is one)
$ErrorActionPreference = "Continue"
Set-Location (Join-Path $PSScriptRoot "..")

$venv = ".venv\Scripts\python.exe"
$py = if (Test-Path $venv) { $venv } else { "python" }
$failed = @()

function Invoke-Step([string]$Name, [string[]]$Arguments) {
    Write-Host ""
    Write-Host "== $Name"
    & $py @Arguments
    if ($LASTEXITCODE -ne 0) { $script:failed += $Name }
}

function Test-Module([string]$Module) {
    & $py -m $Module --help *> $null
    return ($LASTEXITCODE -eq 0)
}

Invoke-Step "ruff" @("-m", "ruff", "check", "custom_components/", "tools/", "tests/", "tests_ha/")
Invoke-Step "black" @("-m", "black", "--check", "custom_components/", "tools/", "tests/", "tests_ha/")
if (Test-Module "xenon") {
    Invoke-Step "xenon (complexity)" @("-m", "xenon", "--max-absolute", "B", "--max-modules", "A", "--max-average", "A", "custom_components")
} else {
    Write-Host ""; Write-Host "== xenon: not installed (pip install xenon), skipped; the CI runs it"
}
& $py -c "import homeassistant" *> $null
$haInstalled = ($LASTEXITCODE -eq 0)
if ((Test-Module "mypy") -and $haInstalled) {
    Invoke-Step "mypy" @("-m", "mypy", "custom_components/welock")
} else {
    Write-Host ""; Write-Host "== mypy: needs mypy and Home Assistant (its types) in this environment, skipped; the CI runs it"
}
Invoke-Step "pytest (unit tests, -m not live)" @("-m", "pytest", "-m", "not live")

Write-Host ""
Write-Host "NOTE: tests_ha/ (the integration inside a real Home Assistant core, job 'ha-tests') needs"
Write-Host "      Python 3.14 and pytest-homeassistant-custom-component. It runs in the CI or in WSL/Linux:"
Write-Host "      pip install -r requirements_test.txt && pytest -c tests_ha/pytest.ini tests_ha"

if ($failed.Count -gt 0) {
    Write-Host ""
    Write-Host "FAILED: $($failed -join ', ')"
    exit 1
}
Write-Host ""
Write-Host "All local checks passed."
