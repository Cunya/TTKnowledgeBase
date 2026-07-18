param(
    [string]$Kb = "table-tennis",
    [string]$Python = "",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $Python) { $Python = Join-Path $Repo ".venv\Scripts\python.exe" }
$RunDir = Join-Path $Repo "data\manifests\$Kb"
$LockPath = Join-Path $RunDir "daily-processing.lock"
$ManifestPath = Join-Path $RunDir "daily-processing.latest.json"
New-Item -ItemType Directory -Force -Path $RunDir | Out-Null

try {
    $Lock = [System.IO.File]::Open($LockPath, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
} catch [System.IO.IOException] {
    Write-Output "Daily processing already running for $Kb; exiting."
    exit 10
}

$started = [DateTimeOffset]::Now
$status = "completed"
$exitCode = 0
try {
    $args = @("-m", "processors.cli", "process-pending", "--kb", $Kb)
    if ($DryRun) {
        Write-Output "Dry run: would execute $Python $($args -join ' ')"
    } else {
        & $Python @args
        $exitCode = $LASTEXITCODE
        if ($exitCode -ne 0) { $status = "failed" }
    }
} catch {
    $status = "failed"
    $exitCode = 1
    Write-Error $_
} finally {
    $finished = [DateTimeOffset]::Now
    [ordered]@{
        knowledge_base = $Kb
        started_at = $started.ToString("o")
        finished_at = $finished.ToString("o")
        status = if ($DryRun) { "dry_run" } else { $status }
        exit_code = $exitCode
        command = "$Python -m processors.cli process-pending --kb $Kb"
    } | ConvertTo-Json | Set-Content -LiteralPath $ManifestPath -Encoding utf8
    if ($Lock) { $Lock.Dispose() }
    Remove-Item -LiteralPath $LockPath -Force -ErrorAction SilentlyContinue
}
exit $exitCode
