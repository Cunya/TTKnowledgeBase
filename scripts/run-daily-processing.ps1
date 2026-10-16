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

$Lock = $null
try {
    $Lock = [System.IO.File]::Open($LockPath, [System.IO.FileMode]::OpenOrCreate, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
    $Lock.SetLength(0)
    $owner = [System.Text.Encoding]::UTF8.GetBytes("pid=$PID`nstarted=$([DateTimeOffset]::Now.ToString('o'))")
    $Lock.Write($owner, 0, $owner.Length)
    $Lock.Flush()
} catch [System.IO.IOException] {
    Write-Output "Daily processing already running for $Kb; exiting."
    exit 10
}

$started = [DateTimeOffset]::Now
$status = "completed"
$exitCode = 0
try {
    $args = @("scripts/run-cp.py", "--kb", $Kb)
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
        command = "$Python scripts/run-cp.py --kb $Kb"
    } | ConvertTo-Json | Set-Content -LiteralPath $ManifestPath -Encoding utf8
    if ($Lock) { $Lock.Dispose() }
    Remove-Item -LiteralPath $LockPath -Force -ErrorAction SilentlyContinue
}
exit $exitCode
