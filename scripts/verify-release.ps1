[CmdletBinding()]
param(
    [string]$Kb = "table-tennis"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$ruff = Join-Path $repoRoot ".venv\Scripts\ruff.exe"
if (-not (Test-Path -LiteralPath $python)) { throw "Project Python runtime was not found: $python" }
if (-not (Test-Path -LiteralPath $ruff)) { throw "Project Ruff executable was not found: $ruff" }

$runtimeProcesses = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -match "processor-monitor\.mjs|run-cp\.py"
}
if ($runtimeProcesses) {
    $ids = ($runtimeProcesses | ForEach-Object ProcessId) -join ", "
    throw "Processor monitor or cp runtime is active (PIDs: $ids). Stop it before release verification."
}

function Invoke-Checked {
    param(
        [Parameter(Mandatory)] [string]$Label,
        [Parameter(Mandatory)] [string]$Executable,
        [Parameter(Mandatory)] [string[]]$Arguments
    )
    Write-Host "`n== $Label ==" -ForegroundColor Cyan
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE"
    }
}

$env:PYTHONUTF8 = "1"
Invoke-Checked "Validate reviewed corpus" $python @("-m", "processors.cli", "validate", "--kb", $Kb)
Invoke-Checked "Publish sanitized corpus" $python @("-m", "processors.cli", "publish", "--kb", $Kb)
Invoke-Checked "Validate published artifacts" $python @("-m", "processors.cli", "validate-published", "--kb", $Kb)
Invoke-Checked "Run tests" $python @("-m", "pytest")
Invoke-Checked "Run Ruff" $ruff @("check", ".")

Push-Location (Join-Path $repoRoot "app")
try {
    Invoke-Checked "Build Astro site" "npm.cmd" @("run", "build")
}
finally {
    Pop-Location
}

Write-Host "`nRelease verification passed for $Kb." -ForegroundColor Green
