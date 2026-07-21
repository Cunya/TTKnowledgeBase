import http from 'node:http';
import { execFile, spawn } from 'node:child_process';
import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const port = Number(process.env.PROCESSOR_MONITOR_PORT || 4322);
const kb = process.env.PROCESSOR_MONITOR_KB || 'table-tennis';
const python = path.join(root, '.venv', 'Scripts', 'python.exe');
const defaultIntervalMs = 15 * 60 * 1000;

const state = {
  running: false,
  intervalMs: defaultIntervalMs,
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
  const collect = (chunk) => {
    output += chunk.toString();
    output = output.slice(-12000);
    if (state.activeRun) state.activeRun.output = output;
  };
  child.stdout.on('data', collect);
  child.stderr.on('data', collect);
  child.on('close', (code, signal) => {
    const failed = Boolean(signal) || code !== 0;
    if (failed) state.retryCount += 1; else state.retryCount = 0;
    state.lastRun = {
      startedAt: state.activeRun?.startedAt,
      finishedAt: new Date().toISOString(),
      durationMs: Date.now() - started,
      code,
      signal,
      outcome: failed ? 'failed' : 'completed',
      retryCount: state.retryCount,
      reason: failed ? (signal ? `terminated by ${signal}` : `run-cp exited ${code}`) : null,
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
  state.nextRunAt = new Date(Date.now() + state.intervalMs).toISOString();
  state.timer = setTimeout(runProcessor, state.intervalMs);
}

function start(intervalMs) {
  state.intervalMs = Math.max(60_000, Math.min(24 * 60 * 60 * 1000, intervalMs || defaultIntervalMs));
  if (state.running) return;
  state.running = true;
  state.startedAt = new Date().toISOString();
  addLog(`Loop started; interval ${Math.round(state.intervalMs / 60000)} minutes.`);
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

async function readProcessList() {
  if (process.platform !== 'win32') return [];
  return new Promise((resolve) => {
    execFile('powershell.exe', ['-NoProfile', '-Command',
      "Get-Process python,node -ErrorAction SilentlyContinue | Select-Object Id,ProcessName,CPU,WorkingSet64,StartTime | ConvertTo-Json -Compress"],
      { windowsHide: true, timeout: 4000 }, (error, stdout) => {
        if (error || !stdout.trim()) return resolve([]);
        try {
          const value = JSON.parse(stdout);
          resolve((Array.isArray(value) ? value : [value]).map((item) => ({
            pid: item.Id, name: item.ProcessName, cpuSeconds: item.CPU || 0,
            memoryBytes: item.WorkingSet64 || 0, startedAt: item.StartTime || null,
          })));
        } catch { resolve([]); }
      });
  });
}

function explainStage(name) {
  const explanations = {
    'process-pending before acquisition': 'Triage cached candidates and preserve review decisions before new video work.',
    'ingest selected batch': 'Download metadata and timed captions for the configured video queue.',
    'ingest discovered batch': 'Download metadata and captions for the next unseen, policy-eligible videos.',
    'process-pending after extraction': 'Turn extracted proposals into accepted, deferred, or rejected review-queue decisions.',
    'build review queue': 'Rebuild the deterministic editorial queue while preserving existing review actions.',
    'refresh summaries': 'Write evidence summaries for reviewed concepts that need them.',
    'publish reviewed corpus': 'Validate and copy reviewed, browser-safe data into the local static site.',
  };
  if (name?.startsWith('extract cached ')) return 'Use an existing local transcript to create its private concept candidates; no video download is needed.';
  if (name?.startsWith('extract ')) return 'Use the newly cached transcript to create private, source-grounded concept candidates.';
  if (name?.startsWith('discover ')) return 'Refresh one configured channel or playlist catalog; discovery alone does not ingest videos.';
  return explanations[name] || 'Run the current controlled pipeline stage.';
}

function currentStage(output) {
  const matches = [...(output || '').matchAll(/^=== (.+) ===$/gm)];
  const name = matches.at(-1)?.[1] || null;
  return name ? { name, explanation: explainStage(name) } : null;
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
  return { percent, label: name, detail: explainStage(name) };
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

async function snapshot() {
  const [budget, progress, daily, cp, processes] = await Promise.all([
    readJson(`data/manifests/${kb}/llm-budget.json`),
    readJson(`app/src/data/generated/${kb}-progress.json`),
    readJson(`data/manifests/${kb}/daily-processing.latest.json`),
    readJson(`data/manifests/${kb}/cp.latest.json`),
    readProcessList(),
  ]);
  const day = budget?.days?.[new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Helsinki' }).format(new Date())];
  const used = day?.actual_tokens || 0;
  const extraction = day?.tasks?.extraction || {};
  const totals = progress?.totals || progress || {};
  return {
    kb,
    running: state.running,
    activeRun: state.activeRun,
    currentStage: currentStage(state.activeRun?.output),
    runProgress: runProgress(state.activeRun?.output),
    processes,
    lastRun: state.lastRun,
    startedAt: state.startedAt,
    nextRunAt: state.nextRunAt,
    intervalMs: state.intervalMs,
    retryCount: state.retryCount,
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
    } : null,
    latest: cp || daily,
    log: state.log,
  };
}

const page = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Processor monitor</title><style>
:root{font-family:system-ui,sans-serif;color:#17211b;background:#f4f1e9}body{max-width:1100px;margin:0 auto;padding:40px 24px}h1{font-family:Georgia,serif;font-size:48px;font-weight:500;margin:8px 0 12px}.eyebrow{font:11px monospace;letter-spacing:.12em;text-transform:uppercase;color:#2e7d54}.intro{max-width:720px;color:#5d655e;line-height:1.6}.controls,.cards{display:grid;gap:16px;margin:28px 0}.controls{grid-template-columns:auto auto 180px 1fr;align-items:end}.controls label{display:grid;gap:6px;font:11px monospace;text-transform:uppercase}.controls input{padding:10px;border:1px solid #bac5bb;background:white}button{padding:11px 18px;border:1px solid #22613f;background:#22613f;color:white;cursor:pointer}button.stop{background:transparent;color:#b3462f;border-color:#b3462f}.cards{grid-template-columns:repeat(4,1fr)}.card{padding:16px;border-top:2px solid #1e6845;background:white}.card b{display:block;font:24px Georgia,serif;margin-top:8px}.card small{color:#6d756e}.status{padding:14px 16px;border-left:4px solid #22613f;background:white;margin:20px 0}.status.warn{border-color:#b3462f}pre{white-space:pre-wrap;max-height:280px;overflow:auto;padding:16px;background:#17211b;color:#d9e8db;font:12px monospace;line-height:1.5}.meta{color:#6d756e;font:12px monospace}@media(max-width:700px){.controls,.cards{grid-template-columns:1fr 1fr}.controls label:last-child{grid-column:1/-1}}
</style></head><body><div class="eyebrow">Local operator tool</div><h1>Processor monitor</h1><p class="intro">Cache-first processing for <b>${kb}</b>. Start or stop the loop; each tick runs the full controlled cp cycle and never overlaps another run.</p><section class="controls"><button id="start">Start loop</button><button class="stop" id="stop">Stop loop</button><button class="stop" id="reset">Reset budget</button><label>Interval (minutes)<input id="interval" type="number" min="1" max="1440" value="15"></label><span class="meta" id="updated">Waiting for status…</span></section><div id="status" class="status">Loading…</div><section class="cards"><div class="card"><small>Daily LLM usage</small><b id="daily">—</b></div><div class="card"><small>Extraction usage</small><b id="extract">—</b></div><div class="card"><small>Deferred candidates</small><b id="deferred">—</b></div><div class="card"><small>Corpus</small><b id="corpus">—</b></div></section><h2>Latest run</h2><pre id="latest">—</pre><h2>Monitor log</h2><pre id="log">—</pre><script>
const $=id=>document.getElementById(id);const fmt=n=>n==null?'—':Number(n).toLocaleString();const time=s=>s?new Date(s).toLocaleString():'—';
async function api(url,options){const r=await fetch(url,options);return r.json()}
async function refresh(){const s=await api('/api/status');$('status').textContent=s.running?(s.activeRun?'Running now · started '+time(s.activeRun.startedAt):'Loop active · next run '+time(s.nextRunAt)):'Stopped';$('status').className='status '+(s.lastRun&&s.lastRun.code?'warn':'');const b=s.budget||{};$('daily').textContent=fmt(b.used)+' / '+fmt(b.dailyLimit);$('extract').textContent=fmt(b.extractionUsed)+' / '+fmt(b.extractionLimit);$('deferred').textContent=fmt(b.deferred);const p=s.progress||{};$('corpus').textContent=fmt(p.concepts)+' concepts · '+fmt(p.videos)+' videos';if(s.lastRun){const {output,...summary}=s.lastRun;$('latest').textContent=JSON.stringify(summary,null,2)+'\\n\\n'+(output||'')}else{$('latest').textContent='No run completed yet.'}$('log').textContent=(s.log||[]).join('\\n')||'No monitor events yet.';$('updated').textContent='Updated '+new Date().toLocaleTimeString()}
$('start').onclick=async()=>{await api('/api/start',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({minutes:Number($('interval').value)})});refresh()};$('stop').onclick=async()=>{await api('/api/stop',{method:'POST'});refresh()};$('reset').onclick=async()=>{if(confirm("Reset today's local LLM budget counters? This does not change configured limits.")){await api('/api/reset-budget',{method:'POST'});refresh()}};refresh();setInterval(refresh,5000);
</script></body></html>`;

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
async function refreshCurrentOutput(){const response=await fetch('/api/status');const state=await response.json();const active=state.activeRun;currentOutput.textContent=active?.output||'No active run.';const current=state.currentStage;stage.innerHTML=current?'<strong>'+current.name+'</strong><p>'+current.explanation+'</p>':'<strong>Waiting for a run</strong><p>No pipeline stage is active. The monitor will start the next cycle at the scheduled time.</p>';document.querySelector('#live-processes').innerHTML=(state.processes||[]).map(p=>'<tr><td>'+p.name+'</td><td>'+p.pid+'</td><td>'+Number(p.cpuSeconds||0).toFixed(1)+' s</td><td>'+fmtBytes(p.memoryBytes)+'</td><td>'+fmtTime(p.startedAt)+'</td></tr>').join('')||'<tr><td colspan="5" class="muted">No Python or Node processes found.</td></tr>'}
refreshCurrentOutput();setInterval(refreshCurrentOutput,5000);
async function refreshProgress(){const state=await (await fetch('/api/status')).json();const run=state.runProgress||{percent:0,label:'Waiting for a run',detail:'The next cycle has not started.'};document.querySelector('#live-percent').textContent=run.percent+'%';document.querySelector('#live-bar').style.width=run.percent+'%';document.querySelector('#live-progress-detail').textContent=run.label+' · '+run.detail}
refreshProgress();setInterval(refreshProgress,5000);
</script>`;

const dashboardPage = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Processor monitor</title><style>
:root{color-scheme:light;--ink:#17211b;--muted:#617066;--soft:#f4f1e9;--panel:#fffdf7;--line:#d6ddcf;--accent:#22613f;--accent-2:#2f6f8e;--warn:#b3462f;--console:#101713;--console-text:#d9e8db;font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:var(--ink);background:var(--soft)}*{box-sizing:border-box}body{margin:0;min-height:100vh;padding:24px clamp(20px,3vw,56px) 36px}.shell{width:100%;display:grid;gap:18px}.topbar{display:grid;grid-template-columns:minmax(320px,1fr) auto;gap:20px;align-items:end}.eyebrow{font:11px/1.2 ui-monospace,SFMono-Regular,Consolas,monospace;letter-spacing:.12em;text-transform:uppercase;color:#2e7d54}h1{font:500 clamp(34px,4vw,56px)/1.02 Georgia,serif;margin:7px 0 8px}h2{font:700 15px/1.2 system-ui,sans-serif;margin:0}.intro{max-width:900px;color:var(--muted);line-height:1.55;margin:0}.controls{display:flex;gap:10px;align-items:end;justify-content:flex-end;flex-wrap:wrap}.controls label{display:grid;gap:5px;font:10px/1.2 ui-monospace,SFMono-Regular,Consolas,monospace;text-transform:uppercase;color:var(--muted)}.controls input{width:120px;padding:9px 10px;border:1px solid var(--line);background:white;color:var(--ink)}button{min-height:38px;padding:9px 14px;border:1px solid var(--accent);background:var(--accent);color:white;cursor:pointer;font-weight:650}button.secondary{background:white;color:var(--accent)}button.danger{background:white;color:var(--warn);border-color:var(--warn)}.progress-panel{padding:18px 20px;background:var(--panel);border:1px solid var(--line)}.progress-head,.section-head{display:flex;justify-content:space-between;align-items:baseline;gap:16px}.status-pill{display:inline-flex;align-items:center;gap:8px;padding:6px 10px;border-radius:999px;background:#e5eee3;color:#1d5b3b;font-weight:700;font-size:13px}.status-pill.warn{background:#f7e3dc;color:var(--warn)}.dot{width:9px;height:9px;border-radius:50%;background:currentColor}.progress-title{font-size:16px;font-weight:750;margin-top:8px}.progress-percent{font:650 28px/1 Georgia,serif}.bar{height:16px;margin:14px 0 10px;background:#dce5dc;border-radius:999px;overflow:hidden}.bar-fill{height:100%;width:0%;background:linear-gradient(90deg,var(--accent),var(--accent-2));transition:width .35s ease}.meta{color:var(--muted);font:12px/1.45 ui-monospace,SFMono-Regular,Consolas,monospace}.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.metric{padding:14px 15px;background:var(--panel);border:1px solid var(--line)}.metric small{display:block;color:var(--muted);font-size:12px}.metric b{display:block;margin-top:7px;font:650 23px/1.1 Georgia,serif}.metric span{display:block;margin-top:5px;color:var(--muted);font-size:12px}.main-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(310px,360px);gap:18px;align-items:start}.panel{background:var(--panel);border:1px solid var(--line);min-width:0}.panel.pad{padding:16px}.stage{display:grid;grid-template-columns:minmax(180px,.7fr) 1fr;gap:16px;padding:16px 18px;background:#e7eee3;border-bottom:1px solid var(--line)}.stage strong{font:650 22px/1.2 Georgia,serif}.stage p{margin:0;color:#46564a;line-height:1.5}.output{height:clamp(430px,58vh,760px);white-space:pre-wrap;overflow:auto;margin:0;padding:16px 18px;background:var(--console);color:var(--console-text);font:12px/1.52 ui-monospace,SFMono-Regular,Consolas,monospace}.side-stack{display:grid;gap:14px}.process-list{display:grid;gap:8px;max-height:190px;overflow:auto}.process-row{display:grid;grid-template-columns:1fr auto;gap:8px;padding:9px 10px;background:white;border:1px solid #e3e8df}.process-name{font-weight:750}.process-sub{color:var(--muted);font:11px/1.35 ui-monospace,SFMono-Regular,Consolas,monospace}.log,.latest{overflow:auto;white-space:pre-wrap;margin:0;padding:12px;background:#fbfaf5;border:1px solid #e3e8df;color:#435045;font:11px/1.45 ui-monospace,SFMono-Regular,Consolas,monospace}.log{max-height:190px}.latest{max-height:270px}.footer-panels{display:grid;grid-template-columns:1fr 1fr;gap:18px}.muted{color:var(--muted)}@media(max-width:1050px){.topbar,.main-grid,.footer-panels{grid-template-columns:1fr}.controls{justify-content:flex-start}.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.output{height:460px}}@media(max-width:620px){body{padding:18px 14px}.metrics{grid-template-columns:1fr}.stage{grid-template-columns:1fr}.controls{display:grid;grid-template-columns:1fr 1fr}.controls label{grid-column:1/-1}.controls input{width:100%}}
</style></head><body><main class="shell"><header class="topbar"><div><div class="eyebrow">Local operator tool</div><h1>Processor monitor</h1><p class="intro">Cache-first processing for <b>${kb}</b>. Each tick runs the controlled cp cycle, keeps the run non-overlapping, and reports enough context to tell whether it is working, waiting, or blocked.</p></div><section class="controls"><button id="start">Start loop</button><button class="danger" id="stop">Stop loop</button><button class="secondary" id="reset">Reset budget</button><label>Interval (minutes)<input id="interval" type="number" min="1" max="1440" value="15"></label></section></header><section class="progress-panel"><div class="progress-head"><div><span id="status-pill" class="status-pill"><span class="dot"></span><span id="status-text">Loading</span></span><div class="progress-title" id="progress-label">Preparing the cycle</div></div><div class="progress-percent" id="progress-percent">0%</div></div><div class="bar"><div class="bar-fill" id="progress-bar"></div></div><div class="meta" id="progress-detail">Waiting for status...</div></section><section class="metrics"><div class="metric"><small>Daily LLM usage</small><b id="daily">-</b><span id="daily-sub">local budget</span></div><div class="metric"><small>Extraction usage</small><b id="extract">-</b><span id="extract-sub">candidate generation</span></div><div class="metric"><small>Deferred candidates</small><b id="deferred">-</b><span>waiting on review or stronger evidence</span></div><div class="metric"><small>Published corpus</small><b id="corpus">-</b><span id="corpus-sub">latest publish snapshot</span></div></section><section class="main-grid"><article class="panel"><div class="stage" id="stage"><strong>Waiting for a run</strong><p>No pipeline stage is active yet.</p></div><pre class="output" id="current-output">No active run.</pre></article><aside class="side-stack"><section class="panel pad"><div class="section-head"><h2>Run State</h2><span class="meta" id="updated">-</span></div><p class="meta" id="schedule">Loading...</p><p class="meta" id="last-outcome">No completed run yet.</p></section><section class="panel pad"><div class="section-head"><h2>Resources</h2><span class="meta">python/node</span></div><div class="process-list" id="processes"><div class="muted">Loading...</div></div></section><section class="panel pad"><div class="section-head"><h2>Monitor Log</h2><span class="meta">latest events</span></div><pre class="log" id="log">-</pre></section></aside></section><section class="footer-panels"><section class="panel pad"><div class="section-head"><h2>Latest Completed Run</h2><span class="meta">summary</span></div><pre class="latest" id="latest">No run completed yet.</pre></section><section class="panel pad"><div class="section-head"><h2>Latest Manifest</h2><span class="meta">cp.latest</span></div><pre class="latest" id="manifest">No manifest loaded.</pre></section></section></main><script>
const $=id=>document.getElementById(id);
const fmt=n=>n==null?'-':Number(n).toLocaleString();
const pct=(used,limit)=>limit?Math.round((Number(used||0)/Number(limit))*1000)/10:0;
const time=s=>{if(!s)return '-';const match=String(s).match(/^\\/Date\\((\\d+)\\)\\/$/);const value=match?Number(match[1]):s;const date=new Date(value);return Number.isNaN(date.getTime())?String(s):date.toLocaleString()};
const bytes=n=>n==null?'-':(Number(n)/1024/1024).toFixed(0)+' MB';
async function api(url,options){const r=await fetch(url,options);if(!r.ok)throw new Error(await r.text());return r.json()}
function setText(id,value){$(id).textContent=value}
function runStatus(state){if(state.activeRun)return ['Running now','warn'];if(state.running)return ['Loop active',''];return ['Stopped','warn']}
function renderProcesses(items){const rows=(items||[]).filter(p=>Number(p.memoryBytes||0)>1024*1024).sort((a,b)=>Number(b.memoryBytes||0)-Number(a.memoryBytes||0)).slice(0,8);$('processes').innerHTML=rows.map(p=>'<div class="process-row"><div><div class="process-name">'+p.name+' <span class="muted">#'+p.pid+'</span></div><div class="process-sub">CPU '+Number(p.cpuSeconds||0).toFixed(1)+' s - started '+time(p.startedAt)+'</div></div><div class="process-sub">'+bytes(p.memoryBytes)+'</div></div>').join('')||'<div class="muted">No relevant Python or Node processes found.</div>'}
function renderLatest(lastRun){if(!lastRun){setText('latest','No run completed yet.');return}const {output,...summary}=lastRun;setText('latest',JSON.stringify(summary,null,2)+'\\n\\n'+(output||''))}
async function refresh(){try{const state=await api('/api/status');const [label,mode]=runStatus(state);$('status-pill').className='status-pill '+mode;setText('status-text',label);const run=state.runProgress||{percent:0,label:'Waiting for a run',detail:'The next cycle has not started.'};setText('progress-percent',run.percent+'%');$('progress-bar').style.width=run.percent+'%';setText('progress-label',run.label||'Waiting for a run');setText('progress-detail',run.detail||'No run detail yet.');const b=state.budget||{};setText('daily',fmt(b.used)+' / '+fmt(b.dailyLimit));setText('daily-sub',pct(b.used,b.dailyLimit)+'% used today');setText('extract',fmt(b.extractionUsed)+' / '+fmt(b.extractionLimit));setText('extract-sub',pct(b.extractionUsed,b.extractionLimit)+'% extraction budget');setText('deferred',fmt(b.deferred));const p=state.progress||{};setText('corpus',fmt(p.concepts)+' concepts');setText('corpus-sub',fmt(p.videos)+' videos - '+fmt(p.evidence)+' evidence items');const current=state.currentStage;$('stage').innerHTML=current?'<strong>'+current.name+'</strong><p>'+current.explanation+'</p>':'<strong>Waiting for a run</strong><p>No pipeline stage is active. The next scheduled cycle will start automatically while the loop is active.</p>';setText('current-output',state.activeRun?.output||'No active run.');setText('schedule',state.running?(state.activeRun?'Started '+time(state.activeRun.startedAt):'Next run '+time(state.nextRunAt)):'Loop is stopped.');setText('last-outcome',state.lastRun?'Last run '+state.lastRun.outcome+' at '+time(state.lastRun.finishedAt)+(state.lastRun.reason?' - '+state.lastRun.reason:''):'No completed run yet.');renderProcesses(state.processes);renderLatest(state.lastRun);setText('manifest',state.latest?JSON.stringify(state.latest,null,2):'No manifest loaded.');setText('log',(state.log||[]).join('\\n')||'No monitor events yet.');setText('updated','Updated '+new Date().toLocaleTimeString())}catch(error){$('status-pill').className='status-pill warn';setText('status-text','Status error');setText('progress-detail',error.message)}}
$('start').onclick=async()=>{await api('/api/start',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({minutes:Number($('interval').value)})});refresh()};
$('stop').onclick=async()=>{await api('/api/stop',{method:'POST'});refresh()};
$('reset').onclick=async()=>{if(confirm("Reset today's local LLM budget counters? This does not change configured limits.")){await api('/api/reset-budget',{method:'POST'});refresh()}};
refresh();setInterval(refresh,5000);
</script></body></html>`;

const server = http.createServer(async (request, response) => {
  const url = new URL(request.url, `http://${request.headers.host}`);
  response.setHeader('cache-control', 'no-store');
  response.setHeader('access-control-allow-origin', 'http://127.0.0.1:4321');
  response.setHeader('access-control-allow-headers', 'content-type');
  if (url.pathname === '/') { response.writeHead(200, { 'content-type': 'text/html; charset=utf-8' }); response.end(dashboardPage); return; }
  if (url.pathname === '/api/status') { response.writeHead(200, { 'content-type': 'application/json' }); response.end(JSON.stringify(await snapshot())); return; }
  if (url.pathname === '/api/start' && request.method === 'POST') {
    let body=''; for await (const chunk of request) body += chunk; const input=JSON.parse(body||'{}'); start(Number(input.minutes)*60*1000); response.writeHead(200, {'content-type':'application/json'}); response.end(JSON.stringify(await snapshot())); return;
  }
  if (url.pathname === '/api/stop' && request.method === 'POST') { stop(); response.writeHead(200, {'content-type':'application/json'}); response.end(JSON.stringify(await snapshot())); return; }
  if (url.pathname === '/api/reset-budget' && request.method === 'POST') {
    try { await resetBudget(); response.writeHead(200, {'content-type':'application/json'}); response.end(JSON.stringify(await snapshot())); }
    catch (error) { response.writeHead(500, {'content-type':'application/json'}); response.end(JSON.stringify({ error: error.message })); }
    return;
  }
  if (url.pathname === '/api/review-tasks' && request.method === 'GET') {
    response.writeHead(200, {'content-type':'application/json'}); response.end(JSON.stringify(await readReviewTasks())); return;
  }
  if (url.pathname === '/api/review-tasks' && request.method === 'POST') {
    try { let body=''; for await (const chunk of request) body += chunk; const input=JSON.parse(body||'{}'); if(!input.videoId || !input.note?.trim()) throw new Error('A video and note are required.'); const data=await readReviewTasks(); const task={id:`review-${Date.now()}-${Math.random().toString(36).slice(2,7)}`,createdAt:new Date().toISOString(),updatedAt:new Date().toISOString(),status:'open',type:input.type||'concept',videoId:input.videoId,conceptId:input.conceptId||null,startMs:Number(input.startMs||0),endMs:Number(input.endMs||0),note:input.note.trim(),resolution:null}; data.tasks=[task,...(data.tasks||[])]; await writeReviewTasks(data); response.writeHead(201,{'content-type':'application/json'}); response.end(JSON.stringify(task)); }
    catch(error) { response.writeHead(400,{'content-type':'application/json'}); response.end(JSON.stringify({error:error.message})); }
    return;
  }
  if (url.pathname.startsWith('/api/review-tasks/') && request.method === 'PATCH') {
    try { let body=''; for await (const chunk of request) body += chunk; const task=await updateReviewTask(url.pathname.split('/').pop(),JSON.parse(body||'{}')); response.writeHead(200,{'content-type':'application/json'}); response.end(JSON.stringify(task)); }
    catch(error) { response.writeHead(400,{'content-type':'application/json'}); response.end(JSON.stringify({error:error.message})); }
    return;
  }
  response.writeHead(404); response.end('Not found');
});

server.listen(port, '127.0.0.1', () => console.log(`Processor monitor: http://127.0.0.1:${port}/`));
process.on('SIGINT', () => { stop(); server.close(() => process.exit(0)); });
process.on('SIGTERM', () => { stop(); server.close(() => process.exit(0)); });
