import http from 'node:http';
import { randomUUID } from 'node:crypto';
import { execFile, spawn } from 'node:child_process';
import { mkdir, readFile, rename, unlink, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { prepareBucketHistory } from './monitor-history.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const port = Number(process.env.PROCESSOR_MONITOR_PORT || 4322);
const kb = process.env.PROCESSOR_MONITOR_KB || 'table-tennis';
const python = path.join(root, '.venv', 'Scripts', 'python.exe');
const defaultCooldownMs = 15 * 60 * 1000;
const bucketHistoryPath = `data/manifests/${kb}/bucket-history.json`;
const settingsPath = `data/manifests/${kb}/local-monitor-settings.json`;
const savedCooldownMs = (await readJson(settingsPath))?.cooldownMs;

const state = {
  running: false,
  cooldownMs: Number.isFinite(savedCooldownMs) && savedCooldownMs >= 60_000 && savedCooldownMs <= 86_400_000
    ? savedCooldownMs : defaultCooldownMs,
  startedAt: null,
  nextRunAt: null,
  activeRun: null,
  lastRun: null,
  log: [],
  child: null,
  timer: null,
  retryCount: 0,
};

function addLog(message) {
  state.log.push(`${new Date().toISOString()} ${message}`);
  state.log = state.log.slice(-80);
}

function summarizeProcessorLogLine(line) {
  const text = String(line || '').trim();
  if (!text) return null;
  const numbered = text.match(/^Stage (\d+)\/(\d+):\s*(.+)$/);
  if (numbered) return `Stage ${numbered[1]}/${numbered[2]}: ${numbered[3]}`;
  const stage = text.match(/^=== (.+) ===$/);
  if (stage) return `Stage started: ${explainStage(stage[1])}`;
  if (text.startsWith('[stage] No new output yet;')) return `Stage update: ${text.slice(8).trim()}`;
  if (text.startsWith('[stage] Finished:')) return `Stage finished: ${text.replace(/^\[stage\]\s+Finished:\s*/, '')}`;
  if (text.startsWith('[adjudication]') && text.includes('checkpoint')) {
    return `Candidate proposal decision checkpoint: ${text.replace(/^\[adjudication\]\s*/, '')}`;
  }
  if (text.startsWith('[adjudication]') && text.includes('finished with')) {
    return `Candidate proposal decision: ${text.replace(/^\[adjudication\]\s*/, '')}`;
  }
  return null;
}

function summarizeProcessorFailure(output) {
  const lines = String(output || '').split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  const validationIndex = lines.findIndex((line) => line.includes('ValueError: Publish validation failed:'));
  if (validationIndex >= 0) {
    const details = lines.slice(validationIndex + 1).filter((line) => line.startsWith('- ')).slice(0, 3);
    return `Processor failure: publish validation failed${details.length ? `: ${details.join('; ')}` : '.'}`;
  }
  const stopped = [...lines].reverse().find((line) => line.startsWith('cp stopped safely:'));
  if (stopped) return `Processor failure: ${stopped}`;
  const stageFailed = [...lines].reverse().find((line) => line.startsWith('[stage] Finished:') && line.includes('(stage failed'));
  return stageFailed ? `Processor failure: ${stageFailed.slice(8).trim()}` : null;
}

async function readRequestBody(request) {
  let body = '';
  for await (const chunk of request) {
    body += chunk;
    if (body.length > 100_000) throw new Error('Request is too large.');
  }
  return body;
}

function runProcessor() {
  if (state.child) {
    addLog('Skipped tick: a processor run is already active.');
    return;
  }
  const started = Date.now();
  state.activeRun = { startedAt: new Date(started).toISOString(), command: `run-cp.py --kb ${kb}` };
  addLog(`Starting full cp cycle for ${kb}.`);
  const child = spawn(python, ['scripts/run-cp.py', '--kb', kb], {
    cwd: root,
    env: { ...process.env, PYTHONUTF8: '1' },
    windowsHide: true,
  });
  state.child = child;
  let output = '';
  let pendingLogLine = '';
  const collect = (chunk) => {
    const text = chunk.toString();
    output += text;
    output = output.slice(-12000);
    if (state.activeRun) state.activeRun.output = output;
    pendingLogLine += text;
    const lines = pendingLogLine.split(/\r?\n/);
    pendingLogLine = lines.pop() || '';
    for (const line of lines) {
      const summary = summarizeProcessorLogLine(line);
      if (summary) addLog(summary);
    }
  };
  child.stdout.on('data', collect);
  child.stderr.on('data', collect);
  child.on('close', async (code, signal) => {
    const finalSummary = summarizeProcessorLogLine(pendingLogLine);
    if (finalSummary) addLog(finalSummary);
    const failed = Boolean(signal) || code !== 0;
    if (failed) await markInterruptedManifest(child.pid, code, signal);
    if (failed) state.retryCount += 1; else state.retryCount = 0;
    const failureSummary = failed ? summarizeProcessorFailure(output) : null;
    if (failureSummary) addLog(failureSummary);
    state.lastRun = {
      startedAt: state.activeRun?.startedAt,
      finishedAt: new Date().toISOString(),
      durationMs: Date.now() - started,
      code,
      signal,
      outcome: failed ? 'failed' : 'completed',
      retryCount: state.retryCount,
      reason: failed ? (failureSummary || (signal ? `terminated by ${signal}` : `run-cp exited ${code}`)) : null,
      output: output.trim(),
    };
    addLog(failed ? `Processor failed: ${signal || `exit ${code}`}; consecutive failures ${state.retryCount}.` : 'Processor completed successfully; retry counter reset.');
    state.child = null;
    state.activeRun = null;
    if (state.running) scheduleNext();
  });
  child.on('error', (error) => addLog(`Processor error: ${error.message}`));
}

function scheduleNext() {
  clearTimeout(state.timer);
  state.nextRunAt = new Date(Date.now() + state.cooldownMs).toISOString();
  state.timer = setTimeout(runProcessor, state.cooldownMs);
}

async function applyCooldown(cooldownMs = state.cooldownMs) {
  if (!Number.isFinite(cooldownMs) || cooldownMs < 60_000 || cooldownMs > 86_400_000) {
    throw new Error('Cooldown must be between 1 and 1440 minutes.');
  }
  const destination = path.join(root, settingsPath);
  const temporaryPath = `${destination}.${process.pid}.${randomUUID()}.tmp`;
  await mkdir(path.dirname(destination), { recursive: true });
  try {
    await writeFile(temporaryPath, `${JSON.stringify({ cooldownMs })}\n`, 'utf8');
    await rename(temporaryPath, destination);
  } catch (error) {
    await unlink(temporaryPath).catch(() => {});
    throw error;
  }
  const previousCooldownMs = state.cooldownMs;
  state.cooldownMs = cooldownMs;
  if (state.running) {
    if (state.child) {
      if (state.cooldownMs !== previousCooldownMs) {
        addLog(`Cooldown changed to ${Math.round(state.cooldownMs / 60000)} minutes; it will apply after the active cycle finishes.`);
      }
      return;
    }
    if (state.cooldownMs !== previousCooldownMs || !state.timer) {
      scheduleNext();
      addLog(`Cooldown changed to ${Math.round(state.cooldownMs / 60000)} minutes; next cycle rescheduled for ${state.nextRunAt}.`);
    }
    return;
  }
}

async function start(cooldownMs) {
  await applyCooldown(cooldownMs);
  if (state.running || state.child) return;
  state.running = true;
  state.startedAt = new Date().toISOString();
  addLog(`Loop started; cooldown between runs ${Math.round(state.cooldownMs / 60000)} minutes.`);
  runProcessor();
}

function terminateProcessTree(child) {
  if (!child) return;
  if (process.platform !== 'win32') {
    child.kill('SIGTERM');
    return;
  }
  execFile('taskkill.exe', ['/PID', String(child.pid), '/T', '/F'], { windowsHide: true, timeout: 10000 }, (error) => {
    if (error && !child.killed) {
      addLog(`Process-tree termination fallback: ${error.message}`);
      child.kill('SIGTERM');
    }
  });
}

async function markInterruptedManifest(childPid, code, signal) {
  const manifestPath = path.join(root, `data/manifests/${kb}/cp.latest.json`);
  const manifest = await readJson(`data/manifests/${kb}/cp.latest.json`);
  if (!manifest || manifest.status !== 'running' || Number(manifest.pid) !== Number(childPid)) return;
  const updated = {
    ...manifest,
    status: 'stopped',
    exit_class: 'interrupted',
    error: `Processor terminated by monitor${signal ? ` (${signal})` : ` (exit ${code})`}.`,
    finished_at: new Date().toISOString(),
  };
  const temporaryPath = `${manifestPath}.${process.pid}.tmp`;
  try {
    await writeFile(temporaryPath, `${JSON.stringify(updated, null, 2)}\n`, 'utf8');
    await rename(temporaryPath, manifestPath);
  } catch (error) {
    await unlink(temporaryPath).catch(() => {});
    addLog(`Could not mark interrupted cp manifest: ${error.message}`);
  }
}

function stop() {
  state.running = false;
  clearTimeout(state.timer);
  state.timer = null;
  state.nextRunAt = null;
  if (state.child) {
    addLog('Stop requested; terminating the active processor run.');
    terminateProcessTree(state.child);
  } else {
    addLog('Loop stopped.');
  }
}

async function readJson(relativePath) {
  try {
    return JSON.parse(await readFile(path.join(root, relativePath), 'utf8'));
  } catch {
    return null;
  }
}

async function reconcileStaleManifest() {
  const manifestPath = path.join(root, `data/manifests/${kb}/cp.latest.json`);
  const manifest = await readJson(`data/manifests/${kb}/cp.latest.json`);
  const pid = Number(manifest?.pid);
  if (manifest?.status !== 'running' || !Number.isInteger(pid) || pid <= 0) return;
  // ponytail: PID liveness is sufficient here; the per-KB run lock prevents a live replacement run.
  try {
    process.kill(pid, 0);
    return;
  } catch (error) {
    if (!['ESRCH', 'EINVAL'].includes(error.code)) return;
  }
  const updated = {
    ...manifest,
    status: 'stopped',
    exit_class: 'interrupted',
    error: `Processor process ${pid} is no longer running; monitor recovered the stale running manifest.`,
    finished_at: new Date().toISOString(),
  };
  const temporaryPath = `${manifestPath}.${process.pid}.tmp`;
  try {
    await writeFile(temporaryPath, `${JSON.stringify(updated, null, 2)}\n`, 'utf8');
    await rename(temporaryPath, manifestPath);
    addLog(`Recovered stale cp manifest for process ${pid} as interrupted.`);
  } catch (error) {
    await unlink(temporaryPath).catch(() => {});
    addLog(`Could not recover stale cp manifest: ${error.message}`);
  }
}

function runHumanReview(args, input = null) {
  return new Promise((resolve, reject) => {
    const child = spawn(python, ['-m', 'processors.human_review', ...args], {
      cwd: root,
      env: { ...process.env, PYTHONUTF8: '1' },
      windowsHide: true,
      stdio: ['pipe', 'pipe', 'pipe'],
    });
    let stdout = '';
    let stderr = '';
    const timer = setTimeout(() => {
      terminateProcessTree(child);
      reject(new Error('Human-review command timed out.'));
    }, 30_000);
    child.stdout.on('data', (chunk) => { stdout = (stdout + chunk.toString()).slice(-2_000_000); });
    child.stderr.on('data', (chunk) => { stderr = (stderr + chunk.toString()).slice(-20_000); });
    child.on('error', (error) => { clearTimeout(timer); reject(error); });
    child.on('close', (code) => {
      clearTimeout(timer);
      let result;
      try { result = JSON.parse(stdout.trim() || '{}'); }
      catch { reject(new Error(stderr.trim() || 'Human-review command returned invalid JSON.')); return; }
      if (code !== 0 || result.error) reject(new Error(result.error || stderr.trim() || `Human-review command exited ${code}.`));
      else resolve(result);
    });
    if (input) child.stdin.end(JSON.stringify(input)); else child.stdin.end();
  });
}

async function readProcessSnapshot() {
  if (process.platform !== 'win32') return { processes: [], resources: null };
  const powerShellRoot = root.replaceAll("'", "''");
  const powerShellScript = `
    $projectRoot = '${powerShellRoot}'.ToLowerInvariant();
    $monitorProcessId = ${process.pid};
    $allProcesses = @(Get-CimInstance Win32_Process -ErrorAction Stop);
    $projectIds = New-Object 'System.Collections.Generic.HashSet[int]';
    [void]$projectIds.Add($monitorProcessId);
    foreach ($item in $allProcesses) {
      $processId = [int]$item.ProcessId;
      if ($processId -eq $PID) { continue }
      $commandLine = ([string]$item.CommandLine).ToLowerInvariant();
      $executablePath = ([string]$item.ExecutablePath).ToLowerInvariant();
      if ($commandLine.Contains($projectRoot) -or $executablePath.StartsWith($projectRoot)) {
        [void]$projectIds.Add($processId);
      }
    }
    do {
      $changed = $false;
      foreach ($item in $allProcesses) {
        $processId = [int]$item.ProcessId;
        if ($processId -eq $PID -or $projectIds.Contains($processId)) { continue }
        if ($projectIds.Contains([int]$item.ParentProcessId)) {
          [void]$projectIds.Add($processId);
          $changed = $true;
        }
      }
    } while ($changed);
    $ids = @($projectIds);
    $performanceById = @{};
    foreach ($item in @(Get-CimInstance Win32_PerfFormattedData_PerfProc_Process -ErrorAction SilentlyContinue)) {
      $performanceById[[int]$item.IDProcess] = [double]$item.PercentProcessorTime;
    }
    $processes = @(
      foreach ($item in @(Get-Process -Id $ids -ErrorAction SilentlyContinue)) {
        [pscustomobject]@{
          Id = $item.Id;
          ProcessName = $item.ProcessName;
          CpuSeconds = if ($null -ne $item.CPU) { [double]$item.CPU } else { 0 };
          CpuPercent = if ($performanceById.ContainsKey([int]$item.Id)) { $performanceById[[int]$item.Id] } else { 0 };
          WorkingSet64 = [double]$item.WorkingSet64;
          StartTime = $item.StartTime;
        }
      }
    );
    $cpuPercent = [double](($processes | Measure-Object -Property CpuPercent -Sum).Sum);
    $memoryBytes = [double](($processes | Measure-Object -Property WorkingSet64 -Sum).Sum);
    [pscustomobject]@{
      resources = [pscustomobject]@{ cpuPercent = $cpuPercent; memoryBytes = $memoryBytes };
      processes = $processes;
    } | ConvertTo-Json -Compress -Depth 4;
  `;
  return new Promise((resolve) => {
    execFile('powershell.exe', ['-NoProfile', '-Command', powerShellScript],
      { windowsHide: true, timeout: 4000 }, (error, stdout) => {
        if (error || !stdout.trim()) return resolve({ processes: [], resources: null });
        try {
          const snapshot = JSON.parse(stdout);
          const items = Array.isArray(snapshot.processes) ? snapshot.processes : snapshot.processes ? [snapshot.processes] : [];
          resolve({
            resources: snapshot.resources || null,
            processes: items.map((item) => ({
              pid: item.Id, name: item.ProcessName, cpuSeconds: item.CpuSeconds || 0,
              cpuPercent: item.CpuPercent || 0,
              memoryBytes: item.WorkingSet64 || 0, startedAt: item.StartTime || null,
            })),
          });
        } catch { resolve({ processes: [], resources: null }); }
      });
  });
}

function explainStage(name) {
  const explanations = {
    'small fair retry batch for unclear candidates': 'Review unclear candidate proposals against their transcript evidence; each decision is bounded and retryable.',
    'process-pending before acquisition': 'Triage cached candidates and preserve review decisions before new video work.',
    'ingest selected batch': 'Download metadata and timed captions for the configured video queue.',
    'ingest discovered batch': 'Download metadata and captions for the next unseen, policy-eligible videos.',
    'process-pending after extraction': 'Turn extracted proposals into accepted, waiting, or rejected review-queue decisions.',
    'build review queue': 'Rebuild the deterministic editorial queue while preserving existing review actions.',
    'refresh summaries': 'Write evidence summaries for reviewed concepts that need them.',
    'publish reviewed corpus': 'Validate and copy reviewed, browser-safe data into the local static site.',
  };
  if (name?.startsWith('extract cached ')) return 'Use an existing local transcript to create its private concept candidates; no video download is needed.';
  if (name?.startsWith('extract ')) return 'Use the newly cached transcript to create private, source-grounded concept candidates.';
  if (name?.startsWith('discover ')) return 'Refresh one configured channel or playlist catalog; discovery alone does not ingest videos.';
  return explanations[name] || 'Run the current controlled pipeline stage.';
}

function stageMeta(output, stageStart) {
  const scoped = stageStart == null ? String(output || '') : String(output || '').slice(stageStart);
  const match = [...scoped.matchAll(/^Stage (\d+)\/(\d+):/gm)].at(-1);
  if (!match) return null;
  const index = Number(match[1]);
  const total = Number(match[2]);
  return Number.isInteger(index) && Number.isInteger(total) && total >= index && index > 0
    ? { index, total }
    : null;
}

function latestAdjudicationProgress(output, stageStart) {
  const matches = [...(output || '').matchAll(/^\[adjudication\]\s+(\d+)\/(\d+)\b.*$/gm)];
  const match = matches.at(-1);
  if (!match || (stageStart != null && match.index < stageStart)) return null;
  const completed = Number(match[1]);
  const total = Number(match[2]);
  if (!Number.isInteger(completed) || !Number.isInteger(total) || total < 1 || completed < 1 || completed > total) return null;
  const selectedPool = match[0].match(/\bselected-video pool\s+(\d+)\/(\d+)\s+remaining\b/)
    || match[0].match(/\bretry backlog\s+(\d+)\/(\d+)\s+remaining\b/);
  const fullBacklog = match[0].match(/\bfull (?:adjudication|retry) backlog:?\s+(\d+)\/(\d+)\b/);
  const batch = match[0].match(/\(batch\s+(\d+)\/(\d+)\)/);
  const backlogRemaining = Number(selectedPool?.[1] ?? (batch && Number(match[2]) - Number(match[1])));
  const backlogTotal = Number(selectedPool?.[2] ?? (batch && Number(match[2])));
  return {
    completed,
    total,
    remaining: total - completed,
    ...(batch ? { batchCompleted: Number(batch[1]), batchTotal: Number(batch[2]) } : {}),
    ...(selectedPool ? { selectedPoolRemaining: Number(selectedPool[1]), selectedPoolTotal: Number(selectedPool[2]) } : {}),
    ...(fullBacklog ? { fullBacklogRemaining: Number(fullBacklog[1]), fullBacklogTotal: Number(fullBacklog[2]) } : {}),
    ...(Number.isInteger(backlogRemaining) && Number.isInteger(backlogTotal) && backlogTotal >= 1 && backlogRemaining >= 0 && backlogRemaining <= backlogTotal
      ? { backlogRemaining, backlogTotal }
      : {}),
  };
}

function currentStage(output) {
  const matches = [...(output || '').matchAll(/^=== (.+) ===$/gm)];
  const current = matches.at(-1);
  const name = current?.[1] || null;
  const meta = stageMeta(output, current?.index);
  const adjudication = latestAdjudicationProgress(output, current?.index);
  const remaining = adjudication?.backlogRemaining ?? adjudication?.remaining;
  const full = adjudication?.fullBacklogTotal != null
    ? `Full adjudication backlog ${adjudication.fullBacklogRemaining}/${adjudication.fullBacklogTotal}; `
    : '';
  return name ? {
    name,
    stageLabel: meta ? `Stage ${meta.index}/${meta.total} · ${name}` : name,
    stageIndex: meta?.index,
    stageTotal: meta?.total,
    explanation: adjudication ? `${full}${remaining} candidates remaining in this pass. ${explainStage(name)}` : explainStage(name),
  } : null;
}

function runProgress(output) {
  const text = output || '';
  const stages = [...text.matchAll(/^=== (.+) ===$/gm)].map((match) => match[1]);
  if (!stages.length) return { percent: 0, label: 'Preparing the cycle', detail: 'Starting the controlled cp workflow.' };
  const name = stages.at(-1);
  const weights = {
    'process-pending before acquisition': 10,
    'process-pending after extraction': 10,
    'build review queue': 5,
    'refresh summaries': 5,
    'publish reviewed corpus': 5,
  };
  const completedWeight = stages.slice(0, -1).reduce((sum, item) => sum + (weights[item] || (item.startsWith('extract') ? 4 : item.startsWith('discover') ? 3 : item.startsWith('ingest') ? 12 : 1)), 0);
  const currentWeight = weights[name] || (name.startsWith('extract') ? 4 : name.startsWith('discover') ? 3 : name.startsWith('ingest') ? 12 : 1);
  const percent = Math.min(99, Math.round((completedWeight + currentWeight * 0.5) / 100 * 100));
  const stageStart = [...text.matchAll(/^=== (.+) ===$/gm)].at(-1)?.index;
  const meta = stageMeta(text, stageStart);
  const prefix = meta ? `Stage ${meta.index}/${meta.total} · ` : '';
  const adjudication = latestAdjudicationProgress(text, stageStart);
  if (adjudication) {
    const hasBacklog = adjudication.backlogTotal != null;
    const hasFullBacklog = adjudication.fullBacklogTotal != null;
    const batchCompleted = adjudication.batchCompleted ?? adjudication.completed;
    const batchTotal = adjudication.batchTotal ?? adjudication.total;
    return {
      percent,
      label: prefix + (hasFullBacklog
        ? `Adjudication backlog · ${adjudication.fullBacklogTotal - adjudication.fullBacklogRemaining}/${adjudication.fullBacklogTotal}`
        : hasBacklog
        ? `Adjudication pass · ${adjudication.backlogTotal - adjudication.backlogRemaining}/${adjudication.backlogTotal}`
        : `Adjudication batch · ${adjudication.completed}/${adjudication.total}`),
      detail: hasFullBacklog
        ? `Full adjudication backlog ${adjudication.fullBacklogRemaining}/${adjudication.fullBacklogTotal} · ${adjudication.remaining} remaining in this pass · current batch ${batchCompleted}/${batchTotal} · ${explainStage(name)}`
        : hasBacklog
        ? `${adjudication.backlogRemaining} candidates remaining in the selected video pool · current batch ${batchCompleted}/${batchTotal} · ${explainStage(name)}`
        : `${adjudication.remaining} remaining in the current batch · ${explainStage(name)}`,
      ...adjudication,
      ...(meta ? { stageIndex: meta.index, stageTotal: meta.total } : {}),
    };
  }
  return { percent, label: prefix + name, detail: explainStage(name), ...(meta ? { stageIndex: meta.index, stageTotal: meta.total } : {}) };
}

async function readReviewTasks() {
  return (await readJson(`data/manifests/${kb}/review-tasks.json`)) || { version: 1, tasks: [] };
}

async function writeReviewTasks(data) {
  await writeFile(path.join(root, `data/manifests/${kb}/review-tasks.json`), `${JSON.stringify(data, null, 2)}\n`, 'utf8');
}

async function updateReviewTask(id, input) {
  const data = await readReviewTasks();
  const task = (data.tasks || []).find((item) => item.id === id);
  if (!task) throw new Error('Review task not found.');
  task.status = input.status === 'resolved' ? 'resolved' : 'open';
  task.updatedAt = new Date().toISOString();
  task.resolution = input.resolution?.trim() || null;
  await writeReviewTasks(data);
  return task;
}

async function resetBudget() {
  const relativePath = `data/manifests/${kb}/llm-budget.json`;
  const filePath = path.join(root, relativePath);
  const ledger = JSON.parse(await readFile(filePath, 'utf8'));
  const dayKey = new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Helsinki' }).format(new Date());
  const day = ledger.days?.[dayKey];
  if (!day) throw new Error(`No budget ledger exists for ${dayKey}.`);
  day.reserved_tokens = 0;
  day.actual_tokens = 0;
  for (const task of Object.values(day.tasks || {})) {
    task.reserved_tokens = 0;
    task.actual_tokens = 0;
    task.calls = 0;
    task.deferred = 0;
  }
  await writeFile(filePath, `${JSON.stringify(ledger, null, 2)}\n`, 'utf8');
  addLog(`Reset local LLM budget counters for ${dayKey}.`);
}

function routeLockout(retryState) {
  const deadlines = Object.values(retryState?.items || {})
    .filter((item) => item.blocked === true && item.next_retry_at)
    .map((item) => new Date(item.next_retry_at).getTime())
    .filter((value) => Number.isFinite(value) && value > Date.now());
  if (!deadlines.length) return null;
  const until = new Date(Math.max(...deadlines));
  return { until: until.toISOString(), remainingMs: until.getTime() - Date.now() };
}

async function snapshot() {
  await reconcileStaleManifest();
  const [budget, progress, daily, cp, processSnapshot, retries, inventory, history] = await Promise.all([
    readJson(`data/manifests/${kb}/llm-budget.json`),
    readJson(`app/src/data/generated/${kb}-progress.json`),
    readJson(`data/manifests/${kb}/daily-processing.latest.json`),
    readJson(`data/manifests/${kb}/cp.latest.json`),
    readProcessSnapshot(),
    readJson(`data/manifests/${kb}/ingest-retries.json`),
    readJson(`data/manifests/${kb}/inventory-ledger.json`),
    readJson(bucketHistoryPath),
  ]);
  const day = budget?.days?.[new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Helsinki' }).format(new Date())];
  const used = day?.actual_tokens || 0;
  const extraction = day?.tasks?.extraction || {};
  const totals = progress?.totals || progress || {};
  const inventorySummary = inventory?.summary || {};
  const inventoryStates = inventorySummary.states || {};
  const candidateStates = inventorySummary.candidates || {};
  const activeStage = currentStage(state.activeRun?.output);
  const activeProgress = runProgress(state.activeRun?.output);
  const processBuckets = {
    stages: [
      { id: 'acquisition', label: 'Acquisition', count: inventoryStates.needs_acquisition || 0, unit: 'videos', description: 'Eligible videos still needing transcript acquisition.' },
      { id: 'extraction', label: 'Extraction', count: inventoryStates.needs_extraction || 0, unit: 'videos', description: 'Normalized videos still needing candidate extraction.' },
      { id: 'adjudication', label: 'Adjudication', count: inventoryStates.needs_adjudication || 0, unit: 'videos', description: 'Videos with pending, deferred, or unincorporated decisions.' },
      { id: 'complete', label: 'Complete', count: inventoryStates.complete || 0, unit: 'videos', description: 'Eligible videos with incorporated final decisions.' },
      { id: 'excluded', label: 'Excluded', count: inventoryStates.excluded || 0, unit: 'videos', description: 'Videos excluded by availability or source-caption policy.' },
      { id: 'retry_wait', label: 'Retry wait', count: inventoryStates.retry_wait || 0, unit: 'videos', description: 'Videos waiting for an acquisition retry window.' },
    ],
    decisions: [
      { id: 'pending', label: 'Pending concept proposals', count: candidateStates.pending || 0, unit: 'concept proposals', description: 'Extracted concept proposals not yet given a final decision.' },
      { id: 'deferred', label: 'Deferred concept proposals', count: candidateStates.deferred || 0, unit: 'concept proposals', description: 'Concept proposals waiting for another automated evidence check.' },
      { id: 'accepted', label: 'Accepted concept proposals', count: candidateStates.accepted || 0, unit: 'concept proposals', description: 'Concept proposals accepted and linked to reviewed evidence.' },
      { id: 'rejected', label: 'Rejected concept proposals', count: candidateStates.rejected || 0, unit: 'concept proposals', description: 'Concept proposals rejected by semantic validation.' },
      { id: 'human_review', label: 'Human-advice concept proposals', count: candidateStates.human_review || 0, unit: 'concept proposals', description: 'Concept proposals with optional human advice or override.' },
    ],
    inventoryTotal: inventorySummary.inventory || 0,
    candidateTotal: candidateStates.total || 0,
  };
  return {
    kb,
    running: state.running,
    activeRun: state.activeRun,
    currentStage: activeStage,
    runProgress: activeProgress,
    processBuckets,
    bucketHistory: prepareBucketHistory(history, cp, inventory),
    processes: processSnapshot.processes,
    resources: processSnapshot.resources,
    lastRun: state.lastRun,
    startedAt: state.startedAt,
    nextRunAt: state.nextRunAt,
    cooldownMs: state.cooldownMs,
    retryCount: state.retryCount,
    routeLockout: routeLockout(retries),
    budget: budget ? {
      used,
      dailyLimit: 30_000_000,
      extractionUsed: extraction.actual_tokens || 0,
      extractionLimit: 24_000_000,
      deferred: extraction.deferred || 0,
    } : null,
    progress: progress ? {
      concepts: totals.concepts,
      videos: totals.published_videos ?? totals.videos,
      evidence: totals.evidence,
      generatedAt: progress.generated_at || progress.generatedAt,
      publicSnapshot: progress.public_snapshot || null,
      quarantinedHistory: progress.quarantined_history || null,
      lastSuccessfulPublishAt: progress.last_successful_publish_at || progress.generated_at || null,
    } : null,
    inventory: inventory?.summary || null,
    latest: cp || daily,
    log: state.log,
  };
}

const page = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Processor monitor</title><style>
:root{font-family:system-ui,sans-serif;color:#17211b;background:#f4f1e9}body{max-width:1100px;margin:0 auto;padding:40px 24px}h1{font-family:Georgia,serif;font-size:48px;font-weight:500;margin:8px 0 12px}.eyebrow{font:11px monospace;letter-spacing:.12em;text-transform:uppercase;color:#2e7d54}.intro{max-width:720px;color:#5d655e;line-height:1.6}.controls,.cards{display:grid;gap:16px;margin:28px 0}.controls{grid-template-columns:auto auto 180px 1fr;align-items:end}.controls label{display:grid;gap:6px;font:11px monospace;text-transform:uppercase}.controls input{padding:10px;border:1px solid #bac5bb;background:white}button{padding:11px 18px;border:1px solid #22613f;background:#22613f;color:white;cursor:pointer}button.stop{background:transparent;color:#b3462f;border-color:#b3462f}.cards{grid-template-columns:repeat(4,1fr)}.card{padding:16px;border-top:2px solid #1e6845;background:white}.card b{display:block;font:24px Georgia,serif;margin-top:8px}.card small{color:#6d756e}.status{padding:14px 16px;border-left:4px solid #22613f;background:white;margin:20px 0}.status.warn{border-color:#b3462f}pre{white-space:pre-wrap;max-height:280px;overflow:auto;padding:16px;background:#17211b;color:#d9e8db;font:12px monospace;line-height:1.5}.meta{color:#6d756e;font:12px monospace}@media(max-width:700px){.controls,.cards{grid-template-columns:1fr 1fr}.controls label:last-child{grid-column:1/-1}}
</style></head><body><div class="eyebrow">Local operator tool</div><h1>Processor monitor</h1><p class="intro">Cache-first processing for <b>${kb}</b>. Start or stop the loop; each tick runs the full controlled cp cycle and never overlaps another run.</p><section class="controls"><button id="start">Start loop</button><button class="stop" id="stop">Stop loop</button><button class="stop" id="reset">Reset budget</button><label>Interval (minutes)<input id="interval" type="number" min="1" max="1440" value="15"></label><span class="meta" id="updated">Waiting for status…</span></section><div id="status" class="status">Loading…</div><section class="cards"><div class="card"><small>Daily LLM usage</small><b id="daily">—</b></div><div class="card"><small>Extraction usage</small><b id="extract">—</b></div><div class="card"><small>Concept proposals awaiting decision</small><b id="deferred">—</b></div><div class="card"><small>Corpus</small><b id="corpus">—</b></div></section><h2>Latest run</h2><pre id="latest">—</pre><h2>Monitor log</h2><pre id="log">—</pre><script>
const $=id=>document.getElementById(id);const fmt=n=>n==null?'—':Number(n).toLocaleString();const time=s=>s?new Date(s).toLocaleString():'—';
async function api(url,options){const r=await fetch(url,options);return r.json()}
async function refresh(){const s=await api('/api/status');$('status').textContent=s.running?(s.activeRun?'Running now · started '+time(s.activeRun.startedAt):'Loop active · next run '+time(s.nextRunAt)):'Stopped';$('status').className='status '+(s.lastRun&&s.lastRun.code?'warn':'');const b=s.budget||{};$('daily').textContent=fmt(b.used)+' / '+fmt(b.dailyLimit);$('extract').textContent=fmt(b.extractionUsed)+' / '+fmt(b.extractionLimit);$('deferred').textContent=fmt(b.deferred);const p=s.progress||{};$('corpus').textContent=fmt(p.concepts)+' concepts · '+fmt(p.videos)+' videos';if(s.lastRun){const {output,...summary}=s.lastRun;$('latest').textContent=JSON.stringify(summary,null,2)+'\\n\\n'+(output||'')}else{$('latest').textContent='No run completed yet.'}$('log').textContent=(s.log||[]).join('\\n')||'No monitor events yet.';$('updated').textContent='Updated '+new Date().toLocaleTimeString()}
$('start').onclick=async()=>{await api('/api/start',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({minutes:Number($('interval').value)})});refresh()};$('stop').onclick=async()=>{await api('/api/stop',{method:'POST'});refresh()};$('reset').onclick=async()=>{if(confirm("Reset today's local LLM budget counters? This does not change configured limits.")){await api('/api/reset-budget',{method:'POST'});refresh()}};refresh();setInterval(refresh,5000);
</script></body></html>`.replaceAll('Interval (minutes)', 'Cooldown between runs (minutes)').replaceAll('Start loop', 'Start / apply cooldown');

const liveOutputScript = `<script>
document.body.style.width='100%';document.body.style.maxWidth='none';document.body.style.boxSizing='border-box';document.body.style.margin='0';document.body.style.padding='32px clamp(24px,4vw,72px)';
const style=document.createElement('style');style.textContent='.stage{display:grid;grid-template-columns:1fr 2fr;gap:20px;padding:18px;background:#e2eadf;border:1px solid #bbccb9;margin:20px 0}.stage strong{font:20px Georgia,serif}.stage p{margin:0;color:#4e5e51;line-height:1.5}.section-head{display:flex;justify-content:space-between;align-items:baseline}.processes{width:100%;border-collapse:collapse;background:white;font:13px monospace}.processes th,.processes td{text-align:left;padding:10px 12px;border-bottom:1px solid #e1e5df}.processes th{color:#637067;font-size:11px;text-transform:uppercase}.muted{color:#748078}';document.head.appendChild(style);
const stage=document.createElement('section');stage.id='live-stage';stage.className='stage';stage.innerHTML='<strong>Waiting for a run</strong><p>Loading current pipeline activity…</p>';
const progress=document.createElement('section');progress.innerHTML='<div style="display:flex;justify-content:space-between;align-items:baseline"><h2 style="margin-bottom:8px">Whole-cycle progress</h2><strong id="live-percent">0%</strong></div><div style="height:14px;background:#d7dfd7;border-radius:99px;overflow:hidden"><div id="live-bar" style="height:100%;width:0%;background:#22613f;transition:width .4s ease"></div></div><p id="live-progress-detail" class="meta">Preparing the cycle</p>';
document.body.insertBefore(progress,document.querySelector('.controls'));
const currentHeading=document.createElement('h2');currentHeading.textContent='Current run output';
const currentOutput=document.createElement('pre');currentOutput.id='current-output';currentOutput.textContent='No active run.';
const processHeading=document.createElement('div');processHeading.className='section-head';processHeading.innerHTML='<h2>Running processes</h2><span class="meta">Windows snapshot</span>';
const processTable=document.createElement('table');processTable.className='processes';processTable.innerHTML='<thead><tr><th>Process</th><th>PID</th><th>CPU time</th><th>Memory</th><th>Started</th></tr></thead><tbody id="live-processes"></tbody>';
processTable.style.fontSize='11px';processTable.style.maxHeight='180px';processTable.style.display='block';processTable.style.overflowY='auto';processHeading.style.marginTop='22px';
const latestHeading=document.querySelector('h2');latestHeading.parentNode.insertBefore(stage,latestHeading);latestHeading.parentNode.insertBefore(currentHeading,latestHeading);latestHeading.parentNode.insertBefore(currentOutput,latestHeading);latestHeading.parentNode.insertBefore(processHeading,latestHeading);latestHeading.parentNode.insertBefore(processTable,latestHeading);
const fmtTime=s=>s?new Date(s).toLocaleString():'—';const fmtBytes=n=>n==null?'—':(Number(n)/1024/1024).toFixed(0)+' MB';
async function refreshCurrentOutput(){const response=await fetch('/api/status');const state=await response.json();const active=state.activeRun;currentOutput.textContent=active?.output||'No active run.';const current=state.currentStage;stage.innerHTML=current?'<strong>'+(current.stageLabel||current.name)+'</strong><p>'+current.explanation+'</p>':'<strong>Waiting for a run</strong><p>No pipeline stage is active. The monitor will start the next cycle at the scheduled time.</p>';document.querySelector('#live-processes').innerHTML=(state.processes||[]).map(p=>'<tr><td>'+p.name+'</td><td>'+p.pid+'</td><td>'+Number(p.cpuSeconds||0).toFixed(1)+' s</td><td>'+fmtBytes(p.memoryBytes)+'</td><td>'+fmtTime(p.startedAt)+'</td></tr>').join('')||'<tr><td colspan="5" class="muted">No Python or Node processes found.</td></tr>'}
refreshCurrentOutput();setInterval(refreshCurrentOutput,5000);
const lockoutMetric=document.createElement('div');lockoutMetric.className='metric';lockoutMetric.innerHTML='<small>Route lockout</small><b id="route-lockout">-</b><span id="route-lockout-sub">YouTube transcript access</span>';document.querySelector('.metrics')?.appendChild(lockoutMetric);
async function refreshRouteLockout(){const state=await (await fetch('/api/status')).json();const lock=state.routeLockout;const value=document.querySelector('#route-lockout');const detail=document.querySelector('#route-lockout-sub');if(!value||!detail)return;if(lock){value.textContent=fmtTime(lock.until);detail.textContent='blocked until '+new Date(lock.until).toLocaleString();}else{value.textContent='None';detail.textContent='no active route-wide block';}}
refreshRouteLockout();setInterval(refreshRouteLockout,5000);
async function refreshProgress(){const state=await (await fetch('/api/status')).json();const run=state.runProgress||{percent:0,label:'Waiting for a run',detail:'The next cycle has not started.'};document.querySelector('#live-percent').textContent=run.percent+'%';document.querySelector('#live-bar').style.width=run.percent+'%';document.querySelector('#live-progress-detail').textContent=run.label+' · '+run.detail}
refreshProgress();setInterval(refreshProgress,5000);
</script>`;

const dashboardPage = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Processor monitor</title><style>
:root{color-scheme:light;--ink:#17211b;--muted:#617066;--soft:#f4f1e9;--panel:#fffdf7;--line:#d6ddcf;--accent:#22613f;--accent-2:#2f6f8e;--warn:#b3462f;--console:#101713;--console-text:#d9e8db;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:var(--ink);background:var(--soft)}*{box-sizing:border-box}body{margin:0;min-height:100vh;padding:24px clamp(20px,3vw,56px) 36px}.shell{width:100%;display:grid;gap:18px}.topbar{display:grid;grid-template-columns:minmax(320px,1fr) auto;gap:20px;align-items:end}.eyebrow{font:11px/1.2 ui-monospace,SFMono-Regular,Consolas,monospace;letter-spacing:.12em;text-transform:uppercase;color:#2e7d54}h1{font:500 clamp(34px,4vw,56px)/1.02 Georgia,serif;margin:7px 0 8px}h2{font:700 15px/1.2 system-ui,sans-serif;margin:0}.intro{max-width:900px;color:var(--muted);line-height:1.55;margin:0}.controls{display:flex;gap:10px;align-items:end;justify-content:flex-end;flex-wrap:wrap}.controls label{display:grid;gap:5px;font:10px/1.2 ui-monospace,SFMono-Regular,Consolas,monospace;text-transform:uppercase;color:var(--muted)}.controls input{width:120px;padding:9px 10px;border:1px solid var(--line);background:white;color:var(--ink)}button{min-height:38px;padding:9px 14px;border:1px solid var(--accent);background:var(--accent);color:white;cursor:pointer;font-weight:650}button:disabled{opacity:.45;cursor:not-allowed}button.secondary{background:white;color:var(--accent)}button.danger{background:white;color:var(--warn);border-color:var(--warn)}.progress-panel{padding:18px 20px;background:var(--panel);border:1px solid var(--line)}.progress-head,.section-head{display:flex;justify-content:space-between;align-items:baseline;gap:16px}.status-pill{display:inline-flex;align-items:center;gap:8px;padding:6px 10px;border-radius:999px;background:#e5eee3;color:#1d5b3b;font-weight:700;font-size:13px}.status-pill.warn{background:#f7e3dc;color:var(--warn)}.dot{width:9px;height:9px;border-radius:50%;background:currentColor}.progress-title{font-size:16px;font-weight:750;margin-top:8px}.progress-percent{font:650 28px/1 Georgia,serif}.bar{height:16px;margin:14px 0 10px;background:#dce5dc;border-radius:999px;overflow:hidden}.bar-fill{height:100%;width:0%;background:linear-gradient(90deg,var(--accent),var(--accent-2));transition:width .35s ease}.meta{color:var(--muted);font:12px/1.45 ui-monospace,SFMono-Regular,Consolas,monospace}.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.metric{padding:14px 15px;background:var(--panel);border:1px solid var(--line)}.metric small{display:block;color:var(--muted);font-size:12px}.metric b{display:block;margin-top:7px;font:650 23px/1.1 Georgia,serif}.metric span{display:block;margin-top:5px;color:var(--muted);font-size:12px}.main-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;align-items:stretch}.panel{background:var(--panel);border:1px solid var(--line);min-width:0}.panel.pad{padding:16px}.stage{display:grid;grid-template-columns:minmax(180px,.7fr) 1fr;gap:16px;padding:16px 18px;background:#e7eee3;border-bottom:1px solid var(--line)}.stage strong{font:650 22px/1.2 Georgia,serif}.stage p{margin:0;color:#46564a;line-height:1.5}.main-grid>article.panel{display:flex;flex-direction:column}.main-grid>article.panel>.stage{flex-shrink:0}.output{flex:1;height:0;min-height:430px;white-space:pre-wrap;overflow:auto;margin:0;padding:16px 18px;background:var(--console);color:var(--console-text);font:12px/1.52 ui-monospace,SFMono-Regular,Consolas,monospace}.side-stack{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));grid-template-rows:158px minmax(320px,1fr);gap:14px;min-width:0}.side-stack>.panel{height:100%;min-height:0}.route-lockout-panel{overflow:auto}.resources-panel,.monitor-log-panel{display:flex;min-height:0;overflow:hidden;flex-direction:column}.resources-panel .process-list{flex:1;min-height:0;max-height:none}.monitor-log-panel .log{flex:1;min-height:0;max-height:none}.process-list{display:grid;gap:8px;max-height:190px;overflow:auto}.process-row{display:grid;grid-template-columns:1fr auto;gap:8px;padding:9px 10px;background:white;border:1px solid #e3e8df}.process-name{font-weight:750}.process-sub{color:var(--muted);font:11px/1.35 ui-monospace,SFMono-Regular,Consolas,monospace}.log,.latest{overflow:auto;white-space:pre-wrap;margin:0;padding:12px;background:#fbfaf5;border:1px solid #e3e8df;color:#435045;font:11px/1.45 ui-monospace,SFMono-Regular,Consolas,monospace}.log{max-height:190px}.latest{max-height:270px}.footer-panels{display:grid;grid-template-columns:1fr 1fr;gap:18px}.muted{color:var(--muted)}@media(max-width:1050px){.topbar,.main-grid,.footer-panels{grid-template-columns:1fr}.controls{justify-content:flex-start}.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.output{height:460px}}@media(max-width:700px){.side-stack{grid-template-columns:1fr;grid-template-rows:158px 158px minmax(320px,auto) minmax(260px,auto)}.resources-panel,.monitor-log-panel{min-height:320px}}@media(max-width:620px){body{padding:18px 14px}.metrics{grid-template-columns:1fr}.stage{grid-template-columns:1fr}.controls{display:grid;grid-template-columns:1fr 1fr}.controls label{grid-column:1/-1}.controls input{width:100%}}
</style></head><body><main class="shell"><header class="topbar"><div><div class="eyebrow">Local operator tool</div><h1>Processor monitor</h1><p class="intro">Cache-first processing for <b>${kb}</b>. Each tick runs the controlled cp cycle, keeps the run non-overlapping, and reports enough context to tell whether it is working, waiting, or blocked.</p></div><section class="controls"><button id="start">Start loop</button><button class="danger" id="stop">Stop loop</button><button class="secondary" id="reset">Reset budget</button><label>Interval (minutes)<input id="interval" type="number" min="1" max="1440" value="15" title="Press Enter to save and apply the cooldown"></label></section></header><section class="progress-panel"><div class="progress-head"><div><span id="status-pill" class="status-pill"><span class="dot"></span><span id="status-text">Loading</span></span><div class="progress-title" id="progress-label">Preparing the cycle</div></div><div class="progress-percent" id="progress-percent">0%</div></div><div class="bar"><div class="bar-fill" id="progress-bar"></div></div><div class="meta" id="progress-detail">Waiting for status...</div></section><section class="metrics"><div class="metric"><small>Daily LLM usage</small><b id="daily">-</b><span id="daily-sub">local budget</span></div><div class="metric"><small>Extraction usage</small><b id="extract">-</b><span id="extract-sub">candidate generation</span></div><div class="metric"><small>Concept proposals awaiting decision</small><b id="deferred">-</b><span>ready for another automatic check</span></div><div class="metric"><small>Published corpus</small><b id="corpus">-</b><span id="corpus-sub">latest publish snapshot</span></div><div class="metric"><small>Inventory completion</small><b id="inventory-complete">-</b><span id="inventory-sub">private completion ledger</span></div></section><section class="main-grid"><article class="panel"><div class="stage" id="stage"><strong>Waiting for a run</strong><p>No pipeline stage is active yet.</p></div><pre class="output" id="current-output">No active run.</pre></article><aside class="side-stack"><section class="panel pad run-state-panel"><div class="section-head"><h2>Run State</h2><span class="meta" id="updated">-</span></div><p class="meta" id="schedule">Loading...</p><p class="meta" id="last-outcome">No completed run yet.</p></section><section class="panel pad resources-panel"><div class="section-head"><h2>Resources</h2><span class="meta">python/node</span></div><div class="process-list" id="processes"><div class="muted">Loading...</div></div></section><section class="panel pad monitor-log-panel"><div class="section-head"><h2>Monitor Log</h2><span class="meta">latest events</span></div><pre class="log" id="log">-</pre></section></aside></section><section class="footer-panels"><section class="panel pad"><div class="section-head"><h2>Latest Completed Run</h2><span class="meta">summary</span></div><pre class="latest" id="latest">No run completed yet.</pre></section><section class="panel pad"><div class="section-head"><h2>Latest Manifest</h2><span class="meta">cp.latest</span></div><pre class="latest" id="manifest">No manifest loaded.</pre></section></section></main><script>
const $=id=>document.getElementById(id);
const cooldownLabel=document.querySelector('#interval')?.parentElement;if(cooldownLabel?.firstChild)cooldownLabel.firstChild.textContent='Cooldown between runs (minutes)';
const fmt=n=>n==null?'-':Number(n).toLocaleString();
const pct=(used,limit)=>limit?Math.round((Number(used||0)/Number(limit))*1000)/10:0;
const time=s=>{if(!s)return '-';const match=String(s).match(/^\\/Date\\((\\d+)\\)\\/$/);const value=match?Number(match[1]):s;const date=new Date(value);return Number.isNaN(date.getTime())?String(s):date.toLocaleString()};
const bytes=n=>n==null?'-':(Number(n)/1024/1024).toFixed(0)+' MB';
async function api(url,options){const r=await fetch(url,options);if(!r.ok)throw new Error(await r.text());return r.json()}
function setText(id,value){$(id).textContent=value}
function runStatus(state){if(state.activeRun)return ['Running now','warn'];if(state.running)return ['Loop active',''];return ['Stopped','warn']}
let latestState=null;
function countdown(iso){const remaining=Math.max(0,new Date(iso).getTime()-Date.now());const seconds=Math.ceil(remaining/1000);const hours=Math.floor(seconds/3600);const minutes=Math.floor((seconds%3600)/60);const secs=seconds%60;return hours?hours+'h '+String(minutes).padStart(2,'0')+'m '+String(secs).padStart(2,'0')+'s':minutes?minutes+'m '+String(secs).padStart(2,'0')+'s':secs+'s'}
let cooldownInitialized=false;
function renderSchedule(state){$('start').disabled=Boolean(state.running||state.activeRun);$('stop').disabled=!state.running&&!state.activeRun;if(!cooldownInitialized){$('interval').value=state.cooldownMs/60000;cooldownInitialized=true}const target=document.querySelector('#schedule');if(!target)return;if(!state?.running){target.textContent='Loop is stopped.';return}if(state.activeRun){target.textContent='Process running · started '+time(state.activeRun.startedAt);return}if(!state.nextRunAt){target.textContent='Loop active · next process start pending';return}target.textContent='Next process start in '+countdown(state.nextRunAt)+' · '+time(state.nextRunAt)}
async function refreshSchedule(){try{const state=await api('/api/status');latestState=state;renderSchedule(state)}catch(error){} }
function renderProcesses(items){const rows=(items||[]).filter(p=>Number(p.memoryBytes||0)>1024*1024).sort((a,b)=>Number(b.memoryBytes||0)-Number(a.memoryBytes||0)).slice(0,8);$('processes').innerHTML=rows.map(p=>'<div class="process-row"><div><div class="process-name">'+p.name+' <span class="muted">#'+p.pid+'</span></div><div class="process-sub">CPU '+Number(p.cpuSeconds||0).toFixed(1)+' s - started '+time(p.startedAt)+'</div></div><div class="process-sub">'+bytes(p.memoryBytes)+'</div></div>').join('')||'<div class="muted">No relevant Python or Node processes found.</div>'}
function renderLatest(lastRun){if(!lastRun){setText('latest','No run completed yet.');return}const {output,...summary}=lastRun;setText('latest',JSON.stringify(summary,null,2)+'\\n\\n'+(output||''))}
async function refresh(){try{const state=await api('/api/status');const [label,mode]=runStatus(state);$('status-pill').className='status-pill '+mode;setText('status-text',label);const run=state.runProgress||{percent:0,label:'Waiting for a run',detail:'The next cycle has not started.'};setText('progress-percent',run.percent+'%');$('progress-bar').style.width=run.percent+'%';setText('progress-label',run.label||'Waiting for a run');setText('progress-detail',run.detail||'No run detail yet.');const b=state.budget||{};setText('daily',fmt(b.used)+' / '+fmt(b.dailyLimit));setText('daily-sub',pct(b.used,b.dailyLimit)+'% used today');setText('extract',fmt(b.extractionUsed)+' / '+fmt(b.extractionLimit));setText('extract-sub',pct(b.extractionUsed,b.extractionLimit)+'% extraction budget');const inv=state.inventory||{};setText('deferred',fmt(inv.candidates?.deferred ?? b.deferred));setText('inventory-complete',fmt(inv.eligible_complete)+' / '+fmt(inv.inventory));setText('inventory-sub',fmt(inv.automated_work_remaining)+' automated · '+fmt(inv.human_review_videos)+' human · '+fmt(inv.excluded)+' excluded');const p=state.progress||{};const history=p.quarantinedHistory||{};setText('corpus',fmt(p.concepts)+' concepts');setText('corpus-sub',fmt(p.videos)+' videos · '+fmt(p.evidence)+' moments · '+fmt(history.concepts||0)+' quarantined concepts · published '+time(p.lastSuccessfulPublishAt));const current=state.currentStage;$('stage').innerHTML=current?'<strong>'+(current.stageLabel||current.name)+'</strong><p>'+current.explanation+'</p>':'<strong>Waiting for a run</strong><p>No pipeline stage is active. The next scheduled cycle will start automatically while the loop is active.</p>';setText('current-output',state.activeRun?.output||'No active run.');setText('schedule',state.running?(state.activeRun?'Started '+time(state.activeRun.startedAt):'Next run '+time(state.nextRunAt)):'Loop is stopped.');setText('last-outcome',state.lastRun?'Last run '+state.lastRun.outcome+' at '+time(state.lastRun.finishedAt)+(state.lastRun.reason?' - '+state.lastRun.reason:''):'No completed run yet.');renderProcesses(state.processes);renderLatest(state.lastRun);setText('manifest',state.latest?JSON.stringify(state.latest,null,2):'No manifest loaded.');setText('log',(state.log||[]).join('\\n')||'No monitor events yet.');setText('updated','Updated '+new Date().toLocaleTimeString())}catch(error){$('status-pill').className='status-pill warn';setText('status-text','Status error');setText('progress-detail',error.message)}}
async function submitCooldown(url){if(!$('interval').reportValidity())return;$('start').disabled=true;try{const state=await api(url,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({cooldownMinutes:Number($('interval').value)})});latestState=state;renderSchedule(state);refresh()}catch(error){setText('progress-detail',error.message);if(latestState)renderSchedule(latestState)}}
$('start').disabled=true;$('stop').disabled=true;
$('start').onclick=()=>submitCooldown('/api/start');
$('interval').onkeydown=event=>{if(event.key==='Enter'){event.preventDefault();submitCooldown('/api/cooldown')}};
$('stop').onclick=async()=>{await api('/api/stop',{method:'POST'});refresh()};
$('reset').onclick=async()=>{if(confirm("Reset today's local LLM budget counters? This does not change configured limits.")){await api('/api/reset-budget',{method:'POST'});refresh()}};
refresh();refreshSchedule();setInterval(refresh,5000);setInterval(refreshSchedule,1000);
</script></body></html>`.replaceAll('Interval (minutes)', 'Cooldown between runs (minutes)').replace('</style>', '.run-state-panel{height:158px;display:grid;grid-template-rows:auto minmax(0,1fr) minmax(0,1fr);overflow:hidden}.run-state-panel .section-head{min-width:0}.run-state-panel #updated{min-width:116px;text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}.run-state-panel #schedule,.run-state-panel #last-outcome{min-height:0;max-height:none;margin:10px 0 0;overflow:auto;line-height:1.45;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}</style>');

const completionDashboardPage = dashboardPage
  .replaceAll('Inventory completion', 'Fully processed eligible')
  .replace(
    "setText('inventory-complete',fmt(inv.eligible_complete)+' / '+fmt(inv.inventory));setText('inventory-sub',fmt(inv.automated_work_remaining)+' automated · '+fmt(inv.human_review_videos)+' human · '+fmt(inv.excluded)+' excluded');",
    "setText('inventory-complete',fmt(inv.eligible_complete)+' / '+fmt(inv.eligible_total ?? Number(inv.inventory||0)-Number(inv.excluded||0)));setText('inventory-sub',fmt(inv.automation_triaged)+' Codex-complete · '+fmt(inv.automated_work_remaining)+' automated work remaining');",
  )
  .replace(
    '</style>',
    '.bucket-panel{padding:18px 20px;background:var(--panel);border:1px solid var(--line)}.bucket-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:14px}.bucket-subhead{margin-top:18px;color:var(--muted);font:11px ui-monospace,SFMono-Regular,Consolas,monospace;text-transform:uppercase;letter-spacing:.08em}.bucket{padding:12px 14px;background:#f7faf5;border:1px solid var(--line)}.bucket-head{display:flex;justify-content:space-between;align-items:baseline;gap:10px}.bucket-head span{color:var(--muted);font-size:12px}.bucket-head strong{font:650 22px/1 Georgia,serif}.bucket-track{height:9px;margin:10px 0 8px;background:#dce5dc;border-radius:999px;overflow:hidden}.bucket-fill{height:100%;width:0;border-radius:inherit;transition:width .45s ease;background:var(--accent)}.bucket-fill.acquisition{background:var(--accent-2)}.bucket-fill.extraction{background:#7a5ea8}.bucket-fill.adjudication{background:#b07b32}.bucket-fill.complete{background:#2f7a4d}.bucket-fill.excluded,.bucket-fill.retry_wait{background:#7c8580}.bucket small{display:block;color:var(--muted);font-size:11px;line-height:1.35}.bucket-current{margin-top:16px;padding:12px 14px;background:#e7eee3;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;gap:16px;align-items:baseline}.bucket-current strong{font:650 18px/1.2 Georgia,serif}.bucket-current span{color:#46564a;font-size:12px;text-align:right}.bucket-queue .bucket{background:#fbfaf5}@media(max-width:900px){.bucket-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:620px){.bucket-grid{grid-template-columns:1fr}.bucket-current{display:block}.bucket-current span{display:block;margin-top:6px;text-align:left}}</style>',
  )
  .replace(
    '</style>',
    '.bucket-history{display:grid;gap:8px;margin-top:12px;max-height:320px;overflow:auto}.bucket-history-row{padding:10px 12px;background:#fbfaf5;border:1px solid #e3e8df;color:#526156;font:11px/1.4 ui-monospace,SFMono-Regular,Consolas,monospace}.bucket-history-head{display:flex;justify-content:space-between;gap:12px;margin-bottom:5px;color:var(--muted)}.bucket-history-head strong{color:var(--ink);font-weight:700}.bucket-history-row>div:not(.bucket-history-head){overflow-wrap:anywhere}.bucket-history-label{color:var(--muted)}</style>',
  )
  .replace(
    '</style>',
    '.bucket-history-graphs{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:12px}.bucket-chart{min-width:0;padding:12px;background:#fbfaf5;border:1px solid #e3e8df}.bucket-chart-title{font-weight:700;font-size:14px}.bucket-chart-group{display:block;margin-top:3px;color:var(--muted);font:10px ui-monospace,SFMono-Regular,Consolas,monospace;text-transform:uppercase;letter-spacing:.06em}.bucket-chart svg{display:block;width:100%;height:190px;margin-top:8px;overflow:visible}.bucket-chart-empty{height:190px;display:grid;place-items:center;color:var(--muted);font-size:12px}.bucket-legend{display:flex;flex-wrap:wrap;gap:6px 10px;margin-top:8px;color:var(--muted);font:14px/1.4 ui-monospace,SFMono-Regular,Consolas,monospace}.bucket-legend strong{font-size:18px;color:var(--ink)}.bucket-legend i{display:inline-block;width:8px;height:8px;margin-right:4px;border-radius:50%}.bucket-chart-note{margin-top:5px;color:var(--muted);font:10px ui-monospace,SFMono-Regular,Consolas,monospace}.bucket-chart .chart-grid{stroke:#dfe6df;stroke-width:1}.bucket-chart .chart-axis-label{fill:#435045;font:18px ui-monospace,SFMono-Regular,Consolas,monospace}.bucket-chart .chart-line{fill:none;stroke-width:2.5;stroke-linecap:round;stroke-linejoin:round}.bucket-chart .chart-point{stroke:#fbfaf5;stroke-width:2}@media(max-width:900px){.bucket-history-graphs{grid-template-columns:1fr}}</style>',
  )
  .replace(
    '<section class="main-grid">',
    '<section class="bucket-panel" aria-labelledby="bucket-title"><div class="section-head"><h2 id="bucket-title">Live process buckets</h2><span class="meta" id="bucket-updated">inventory snapshot</span></div><div id="process-buckets" class="bucket-grid" aria-live="polite"></div><div class="bucket-subhead">Concept-proposal decision buckets</div><div id="decision-buckets" class="bucket-grid bucket-queue" aria-live="polite"></div><div id="bucket-current" class="bucket-current" aria-live="polite"><strong>Waiting for a run</strong><span>No active stage.</span></div><div class="bucket-subhead">Bucket history · last 7 days</div><div id="bucket-history-graphs" class="bucket-history-graphs" aria-live="polite"><div class="bucket-chart-empty">No bucket changes recorded yet.</div></div><div id="bucket-history" class="bucket-history" aria-live="polite"><div class="muted">No bucket changes recorded yet.</div></div></section><section class="main-grid">',
  );

const monitorPage = completionDashboardPage.replace('</body></html>', `<script type="module">
import { renderBucketChart } from '/monitor-history.mjs';
const bucketFormat=n=>Number(n||0).toLocaleString();
function renderBucketGroup(id,items,total){const root=document.querySelector('#'+id);if(!root)return;const denominator=Math.max(1,Number(total||0));root.innerHTML=(items||[]).map(item=>{const count=Number(item.count||0);const width=Math.min(100,Math.round(count/denominator*100));return '<article class="bucket"><div class="bucket-head"><span>'+item.label+'</span><strong>'+bucketFormat(count)+' '+item.unit+'</strong></div><div class="bucket-track" role="progressbar" aria-label="'+item.label+' '+item.unit+'" aria-valuenow="'+count+'" aria-valuemin="0" aria-valuemax="'+denominator+'"><div class="bucket-fill '+item.id+'" style="width:'+width+'%"></div></div><small>'+item.description+'</small></article>'}).join('')||'<div class="muted">Inventory bucket data unavailable.</div>'}
function renderBucketHistory(state){const root=document.querySelector('#bucket-history');if(!root)return;const buckets=state.processBuckets||{};const history=(state.bucketHistory||[]).slice().reverse();const graphRoot=document.querySelector('#bucket-history-graphs');if(graphRoot){const graphHistory=history.slice().reverse();const groups=[['stages',buckets.stages||[]],['decisions',buckets.decisions||[]]];const charts=groups.flatMap(([group,items])=>items.map(item=>renderBucketChart(group,item,graphHistory)));graphRoot.innerHTML=charts.length?charts.join(''):'<div class="bucket-chart-empty">No bucket changes recorded yet.</div>'}const values=(group,items)=>items.map(item=>item.label+' '+bucketFormat(group?.[item.id]??0)+' '+item.unit).join(' · ');root.innerHTML=history.length?history.map(entry=>'<article class="bucket-history-row"><div class="bucket-history-head"><strong>'+time(entry.at)+'</strong><span>snapshot</span></div><div><span class="bucket-history-label">Inventory:</span> '+values(entry.stages,buckets.stages||[])+'</div><div><span class="bucket-history-label">Decisions:</span> '+values(entry.decisions,buckets.decisions||[])+'</div></article>').join(''):'<div class="muted">No bucket changes recorded yet.</div>'}
function renderBuckets(state){const buckets=state.processBuckets||{};renderBucketGroup('process-buckets',buckets.stages,buckets.inventoryTotal);renderBucketGroup('decision-buckets',buckets.decisions,buckets.candidateTotal);renderBucketHistory(state);const current=document.querySelector('#bucket-current');if(current){const stage=state.currentStage;const progress=state.runProgress;current.innerHTML=stage?'<strong>Active: '+(stage.stageLabel||stage.name)+' ('+(progress?.percent||0)+'%)</strong><span>'+stage.explanation+'</span>':'<strong>Waiting for a run</strong><span>Next cycle has not started.</span>'}const updated=document.querySelector('#bucket-updated');if(updated)updated.textContent='Updated '+new Date().toLocaleTimeString()}
async function refreshBuckets(){try{renderBuckets(await api('/api/status'))}catch(error){const current=document.querySelector('#bucket-current');if(current)current.innerHTML='<strong>Bucket status unavailable</strong><span>'+error.message+'</span>'}}
refreshBuckets();setInterval(refreshBuckets,5000);
const routeLockoutMetric=document.createElement('section');routeLockoutMetric.className='panel pad route-lockout-panel';routeLockoutMetric.innerHTML='<div class="section-head"><h2>Route lockout</h2><span class="meta">YouTube transcript access</span></div><p class="meta" id="route-lockout-status">Checking blocked retry windows...</p>';document.querySelector('.side-stack')?.prepend(routeLockoutMetric);
async function refreshRouteLockout(){const state=await (await fetch('/api/status')).json();const lock=state.routeLockout;const target=document.querySelector('#route-lockout-status');if(!target)return;if(lock){target.textContent='Blocked until '+new Date(lock.until).toLocaleString()+' (route-wide IP cooldown).';}else{target.textContent='No active route-wide block.';}}refreshRouteLockout();setInterval(refreshRouteLockout,5000);
const resourcePanel=document.querySelector('#processes')?.closest('.panel');
if(resourcePanel){
  const resourceStyle=document.createElement('style');resourceStyle.textContent='.resource-summary{margin:12px 0 14px;padding:12px;background:#f7faf5;border:1px solid #e1e8df;border-radius:10px}.resource-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.resource-stat{min-width:0}.resource-stat-head{display:flex;justify-content:space-between;align-items:baseline;gap:8px;color:#526156;font:11px ui-monospace,SFMono-Regular,Consolas,monospace}.resource-stat-head strong{font:700 20px Georgia,serif;color:#17211b}.resource-track{height:8px;margin-top:8px;background:#dce5dc;border-radius:999px;overflow:hidden}.resource-track i{display:block;height:100%;width:0;background:linear-gradient(90deg,#22613f,#2f6f8e);border-radius:inherit;transition:width .45s ease}.resource-track.memory i{background:linear-gradient(90deg,#2f6f8e,#7a5ea8)}.resource-spark{height:32px;margin-top:7px;display:flex;align-items:end;gap:3px}.resource-spark span{flex:1;min-width:2px;height:4%;background:#b8cdbb;border-radius:2px 2px 0 0}.resource-spark.memory span{background:#c1b7d6}.resource-meta{margin:10px 0 0;color:#718078;font:11px/1.4 ui-monospace,SFMono-Regular,Consolas,monospace}.resource-list-heading{display:flex;justify-content:space-between;align-items:baseline;margin:8px 0 6px;color:#68766d;font:10px ui-monospace,SFMono-Regular,Consolas,monospace;text-transform:uppercase;letter-spacing:.08em}@media(max-width:620px){.resource-grid{grid-template-columns:1fr}}';document.head.append(resourceStyle);
  const summary=document.createElement('div');summary.className='resource-summary';summary.innerHTML='<div class="resource-grid"><article class="resource-stat"><div class="resource-stat-head"><span>Project CPU</span><strong id="resource-cpu-value">-</strong></div><div class="resource-spark" id="resource-cpu-spark" aria-label="Recent project CPU load"></div></article><article class="resource-stat"><div class="resource-stat-head"><span>Project memory</span><strong id="resource-memory-value">-</strong></div><div class="resource-spark memory" id="resource-memory-spark" aria-label="Recent project memory use"></div></article></div><p class="resource-meta" id="resource-meta">Waiting for project process snapshot...</p>';resourcePanel.querySelector('.section-head')?.after(summary);
  resourcePanel.querySelector('.section-head .meta').textContent='this repository only';
  const listHeading=document.createElement('div');listHeading.className='resource-list-heading';listHeading.innerHTML='<span>Project process details</span><span id="resource-process-count">Waiting...</span>';document.querySelector('#processes')?.before(listHeading);
}
const resourceHistory={cpu:[],memory:[]};
const resourceBytes=value=>{const bytes=Number(value)||0;if(bytes<1024*1024)return Math.round(bytes/1024)+' KB';return (bytes/1024/1024/1024).toFixed(1)+' GB'};
function renderResourceSpark(id,values){const target=document.querySelector('#'+id);if(!target)return;const peak=Math.max(1,...values);target.innerHTML=values.map(value=>'<span style="height:'+Math.max(4,Math.round(value/peak*100))+'%"></span>').join('')}
function renderResources(resources,processes){const meta=document.querySelector('#resource-meta');if(!meta)return;if(!resources){meta.textContent='Project process snapshot unavailable.';return}const cpu=Math.max(0,Number(resources.cpuPercent)||0);const memory=Math.max(0,Number(resources.memoryBytes)||0);resourceHistory.cpu=[...resourceHistory.cpu,cpu].slice(-24);resourceHistory.memory=[...resourceHistory.memory,memory].slice(-24);document.querySelector('#resource-cpu-value').textContent=cpu.toFixed(0)+'%';document.querySelector('#resource-memory-value').textContent=resourceBytes(memory);renderResourceSpark('resource-cpu-spark',resourceHistory.cpu);renderResourceSpark('resource-memory-spark',resourceHistory.memory);document.querySelector('#resource-process-count').textContent=(processes||[]).length+' tracked';meta.textContent=(processes||[]).length+' repository processes · '+resourceBytes(memory)+' working set · '+new Date().toLocaleTimeString()}
async function refreshResources(){try{const state=await (await fetch('/api/status')).json();renderResources(state.resources,state.processes)}catch(error){const meta=document.querySelector('#resource-meta');if(meta)meta.textContent='Resource snapshot error: '+error.message}}
refreshResources();setInterval(refreshResources,5000);
</script></body></html>`);

const server = http.createServer(async (request, response) => {
  const url = new URL(request.url, `http://${request.headers.host}`);
  response.setHeader('cache-control', 'no-store');
  response.setHeader('access-control-allow-origin', 'http://127.0.0.1:4321');
  response.setHeader('access-control-allow-headers', 'content-type');
  response.setHeader('access-control-allow-methods', 'GET, POST, PATCH, OPTIONS');
  if (request.method === 'OPTIONS') { response.writeHead(204); response.end(); return; }
  if (url.pathname === '/') { response.writeHead(200, { 'content-type': 'text/html; charset=utf-8' }); response.end(monitorPage); return; }
  if (url.pathname === '/monitor-history.mjs') {
    response.writeHead(200, { 'content-type': 'text/javascript; charset=utf-8' });
    response.end(await readFile(path.join(root, 'scripts', 'monitor-history.mjs'), 'utf8'));
    return;
  }
  if (url.pathname === '/api/status') { response.writeHead(200, { 'content-type': 'application/json' }); response.end(JSON.stringify(await snapshot())); return; }
  if (['/api/start', '/api/cooldown'].includes(url.pathname) && request.method === 'POST') {
    try {
      const input = JSON.parse(await readRequestBody(request) || '{}');
      const cooldownMinutes = input.cooldownMinutes ?? input.minutes ?? state.cooldownMs / 60000;
      const action = url.pathname === '/api/start' ? start : applyCooldown;
      await action(Number(cooldownMinutes) * 60 * 1000);
      response.writeHead(200, {'content-type':'application/json'});
      response.end(JSON.stringify(await snapshot()));
    } catch (error) {
      response.writeHead(400, {'content-type':'application/json'});
      response.end(JSON.stringify({error: error.message}));
    }
    return;
  }
  if (url.pathname === '/api/stop' && request.method === 'POST') { stop(); response.writeHead(200, {'content-type':'application/json'}); response.end(JSON.stringify(await snapshot())); return; }
  if (url.pathname === '/api/reset-budget' && request.method === 'POST') {
    try { await resetBudget(); response.writeHead(200, {'content-type':'application/json'}); response.end(JSON.stringify(await snapshot())); }
    catch (error) { response.writeHead(500, {'content-type':'application/json'}); response.end(JSON.stringify({ error: error.message })); }
    return;
  }
  if (url.pathname === '/api/human-review' && request.method === 'GET') {
    try {
      const limit = Math.min(5, Math.max(1, Number(url.searchParams.get('limit') || 5)));
      const offset = Math.max(0, Number(url.searchParams.get('offset') || 0));
      const result = await runHumanReview(['list', '--kb', kb, '--limit', String(limit), '--offset', String(offset)]);
      response.writeHead(200, {'content-type':'application/json'}); response.end(JSON.stringify(result));
    } catch (error) {
      response.writeHead(500, {'content-type':'application/json'}); response.end(JSON.stringify({error:error.message}));
    }
    return;
  }
  if (url.pathname === '/api/human-review/decision' && request.method === 'POST') {
    if (state.running || state.child) {
      response.writeHead(409, {'content-type':'application/json'});
      response.end(JSON.stringify({error:'Pause the processor loop and wait for the active cycle to finish before saving an optional advisory or override.'}));
      return;
    }
    try {
      const result = await runHumanReview(['decide', '--kb', kb], JSON.parse(await readRequestBody(request) || '{}'));
      response.writeHead(200, {'content-type':'application/json'}); response.end(JSON.stringify(result));
    } catch (error) {
      response.writeHead(400, {'content-type':'application/json'}); response.end(JSON.stringify({error:error.message}));
    }
    return;
  }
  if (url.pathname === '/api/review-tasks' && request.method === 'GET') {
    response.writeHead(200, {'content-type':'application/json'}); response.end(JSON.stringify(await readReviewTasks())); return;
  }
  if (url.pathname === '/api/review-tasks' && request.method === 'POST') {
    try { const input=JSON.parse(await readRequestBody(request)||'{}'); if(!input.videoId || !input.note?.trim()) throw new Error('A video and note are required.'); const data=await readReviewTasks(); const task={id:`review-${Date.now()}-${Math.random().toString(36).slice(2,7)}`,createdAt:new Date().toISOString(),updatedAt:new Date().toISOString(),status:'open',type:input.type||'concept',videoId:input.videoId,conceptId:input.conceptId||null,startMs:Number(input.startMs||0),endMs:Number(input.endMs||0),note:input.note.trim(),resolution:null}; data.tasks=[task,...(data.tasks||[])]; await writeReviewTasks(data); response.writeHead(201,{'content-type':'application/json'}); response.end(JSON.stringify(task)); }
    catch(error) { response.writeHead(400,{'content-type':'application/json'}); response.end(JSON.stringify({error:error.message})); }
    return;
  }
  if (url.pathname.startsWith('/api/review-tasks/') && request.method === 'PATCH') {
    try { const task=await updateReviewTask(url.pathname.split('/').pop(),JSON.parse(await readRequestBody(request)||'{}')); response.writeHead(200,{'content-type':'application/json'}); response.end(JSON.stringify(task)); }
    catch(error) { response.writeHead(400,{'content-type':'application/json'}); response.end(JSON.stringify({error:error.message})); }
    return;
  }
  response.writeHead(404); response.end('Not found');
});

server.listen(port, '127.0.0.1', () => console.log(`Processor monitor: http://127.0.0.1:${port}/`));
process.on('SIGINT', () => { stop(); server.close(() => process.exit(0)); });
process.on('SIGTERM', () => { stop(); server.close(() => process.exit(0)); });
