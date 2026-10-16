[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$root = Split-Path -Parent $PSScriptRoot
$appRoot = Join-Path $root 'app'
$monitorScript = Join-Path $root 'scripts\processor-monitor.mjs'
$monitorPort = 4322
$sitePort = 4321
$script:startedMonitorPid = $null
$script:currentProcessIds = @{}

function Get-ProcessTable {
    @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue)
}

function Get-ProcessChain {
    param(
        [Parameter(Mandatory)] [int] $ProcessId,
        [Parameter(Mandatory)] [object[]] $Table
    )

    $byId = @{}
    foreach ($item in $Table) {
        $byId[[int] $item.ProcessId] = $item
    }
    $chain = @()
    $current = $byId[$ProcessId]
    while ($null -ne $current -and -not ($chain.ProcessId -contains $current.ProcessId)) {
        $chain += $current
        $parentId = [int] $current.ParentProcessId
        if ($parentId -le 0 -or -not $byId.ContainsKey($parentId)) {
            break
        }
        $current = $byId[$parentId]
    }
    $chain
}

function Get-ListenProcessIds {
    param([Parameter(Mandatory)] [int] $Port)

    @(
        Get-NetTCPConnection -LocalAddress '127.0.0.1' -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique
    )
}

function Get-MonitorProcess {
    $table = Get-ProcessTable
    $ownerIds = @(Get-ListenProcessIds $monitorPort)
    $matches = @(
        $table | Where-Object {
            $ownerIds -contains $_.ProcessId -and
            ([string] $_.CommandLine) -match '(?i)processor-monitor\.mjs'
        }
    )
    if (-not $matches) {
        $matches = @(
            $table | Where-Object {
                ([string] $_.CommandLine) -match '(?i)processor-monitor\.mjs' -and
                ([string] $_.CommandLine).ToLowerInvariant().Contains($root.ToLowerInvariant())
            }
        )
    }
    $matches | Select-Object -First 1
}

function Get-SiteProcessTarget {
    $table = Get-ProcessTable
    $ownerIds = @(Get-ListenProcessIds $sitePort)
    foreach ($ownerId in $ownerIds) {
        $chain = @(Get-ProcessChain -ProcessId ([int] $ownerId) -Table $table)
        $owner = $chain | Select-Object -First 1
        if ($null -eq $owner -or ([string] $owner.CommandLine) -notmatch '(?i)astro') {
            continue
        }
        $hasProjectPath = @($chain | Where-Object {
                ([string] $_.CommandLine).ToLowerInvariant().Contains($appRoot.ToLowerInvariant())
            }).Count -gt 0
        $hasNpmDev = @($chain | Where-Object {
                ([string] $_.CommandLine) -match '(?i)npm-cli\.js.*run dev'
            }).Count -gt 0
        $hasStartScript = @($chain | Where-Object {
                ([string] $_.CommandLine) -match '(?i)start\.bat'
            }).Count -gt 0
        if (-not $hasProjectPath -or (-not $hasNpmDev -and -not $hasStartScript)) {
            continue
        }

        $candidates = @($chain | Where-Object {
                ([string] $_.CommandLine) -match '(?i)npm-cli\.js.*run dev|start\.bat'
            })
        $target = $candidates | Where-Object {
            -not $script:currentProcessIds.ContainsKey([int] $_.ProcessId)
        } | Select-Object -Last 1
        if ($null -eq $target) {
            $target = $owner
        }
        return $target
    }
    $null
}

function Stop-ProcessTree {
    param([Parameter(Mandatory)] [int] $ProcessId)

    if ($ProcessId -le 0) {
        return
    }
    $exists = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction SilentlyContinue
    if ($null -eq $exists) {
        return
    }
    & taskkill.exe /PID $ProcessId /T /F *> $null
}

function Wait-ForPortState {
    param(
        [Parameter(Mandatory)] [int] $Port,
        [Parameter(Mandatory)] [bool] $Listening,
        [int] $Seconds = 15
    )

    $deadline = (Get-Date).AddSeconds($Seconds)
    do {
        $isListening = @(Get-ListenProcessIds $Port).Count -gt 0
        if ($isListening -eq $Listening) {
            return $true
        }
        Start-Sleep -Milliseconds 250
    } while ((Get-Date) -lt $deadline)
    return (@(Get-ListenProcessIds $Port).Count -gt 0) -eq $Listening
}

function Stop-ExistingMonitor {
    $monitor = Get-MonitorProcess
    if ($null -eq $monitor) {
        return
    }
    Write-Host "Stopping existing processor monitor (PID $($monitor.ProcessId))."
    try {
        Invoke-WebRequest -UseBasicParsing -Method Post -Uri "http://127.0.0.1:$monitorPort/api/stop" -Body '{}' -ContentType 'application/json' -TimeoutSec 3 | Out-Null
    } catch {
        Write-Host "The existing monitor did not accept the stop request; terminating its verified process tree."
    }
    Stop-ProcessTree ([int] $monitor.ProcessId)
    if (-not (Wait-ForPortState $monitorPort $false)) {
        throw "The existing processor monitor did not stop on port $monitorPort."
    }
}

function Stop-ExistingSite {
    $site = Get-SiteProcessTarget
    if ($null -eq $site) {
        return
    }
    Write-Host "Stopping existing Astro development server (PID $($site.ProcessId))."
    Stop-ProcessTree ([int] $site.ProcessId)
    if (-not (Wait-ForPortState $sitePort $false)) {
        throw "The existing Astro development server did not stop on port $sitePort."
    }
}

function Wait-ForMonitorReady {
    $deadline = (Get-Date).AddSeconds(10)
    do {
        $monitor = Get-MonitorProcess
        if ($null -ne $monitor -and [int] $monitor.ProcessId -eq $script:startedMonitorPid) {
            try {
                $response = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$monitorPort/" -TimeoutSec 1
                if ($response.StatusCode -eq 200) {
                    return $true
                }
            } catch {
                # The process may still be binding its port.
            }
        }
        Start-Sleep -Milliseconds 250
    } while ((Get-Date) -lt $deadline)
    return $false
}

function Stop-Services {
    try {
        $monitor = Get-MonitorProcess
        if ($null -ne $monitor) {
            try {
                Invoke-WebRequest -UseBasicParsing -Method Post -Uri "http://127.0.0.1:$monitorPort/api/stop" -Body '{}' -ContentType 'application/json' -TimeoutSec 3 | Out-Null
            } catch {
                # The verified process-tree kill below is the fallback during Ctrl+C.
            }
            Stop-ProcessTree ([int] $monitor.ProcessId)
            [void] (Wait-ForPortState $monitorPort $false)
        }
        $site = Get-SiteProcessTarget
        if ($null -ne $site) {
            Stop-ProcessTree ([int] $site.ProcessId)
            [void] (Wait-ForPortState $sitePort $false)
        }
    } catch {
        Write-Warning "Service cleanup was incomplete: $($_.Exception.Message)"
    }
}

function Start-Monitor {
    $node = Get-Command node.exe -ErrorAction Stop
    $monitor = Start-Process -FilePath $node.Source -ArgumentList @($monitorScript) -WorkingDirectory $root -WindowStyle Hidden -PassThru
    $script:startedMonitorPid = [int] $monitor.Id
    if (-not (Wait-ForMonitorReady)) {
        Stop-ProcessTree $script:startedMonitorPid
        throw "The new processor monitor did not become ready on port $monitorPort."
    }
    Write-Host "Processor monitor: http://127.0.0.1:$monitorPort/"
}

$currentTable = Get-ProcessTable
foreach ($current in @(Get-ProcessChain -ProcessId $PID -Table $currentTable)) {
    $script:currentProcessIds[[int] $current.ProcessId] = $true
}

$exitCode = 0
try {
    Stop-ExistingMonitor
    Stop-ExistingSite
    Start-Monitor
    Push-Location $appRoot
    try {
        & npm.cmd run dev -- --host 127.0.0.1
        $exitCode = $LASTEXITCODE
    } finally {
        Pop-Location
    }
} catch {
    Write-Error $_
    $exitCode = 1
} finally {
    Stop-Services
}

exit $exitCode
