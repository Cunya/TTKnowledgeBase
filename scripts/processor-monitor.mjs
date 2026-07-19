import http from 'node:http';
import { spawn } from 'node:child_process';
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
    state.lastRun = {
      startedAt: state.activeRun?.startedAt,
      finishedAt: new Date().toISOString(),
      durationMs: Date.now() - started,
      code,
      signal,
      output: output.trim(),
    };
    addLog(`Processor finished with ${signal || `exit ${code}`}.`);
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

function stop() {
  state.running = false;
  clearTimeout(state.timer);
  state.timer = null;
  state.nextRunAt = null;
  if (state.child) {
    addLog('Stop requested; terminating the active processor run.');
    state.child.kill();
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
  const [budget, progress, daily, cp] = await Promise.all([
    readJson(`data/manifests/${kb}/llm-budget.json`),
    readJson(`app/src/data/generated/${kb}-progress.json`),
    readJson(`data/manifests/${kb}/daily-processing.latest.json`),
    readJson(`data/manifests/${kb}/cp.latest.json`),
  ]);
  const day = budget?.days?.[new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Helsinki' }).format(new Date())];
  const used = day?.actual_tokens || 0;
  const extraction = day?.tasks?.extraction || {};
  const totals = progress?.totals || progress || {};
  return {
    kb,
    running: state.running,
    activeRun: state.activeRun,
    lastRun: state.lastRun,
    startedAt: state.startedAt,
    nextRunAt: state.nextRunAt,
    intervalMs: state.intervalMs,
    budget: budget ? {
      used,
      dailyLimit: 1_500_000,
      extractionUsed: extraction.actual_tokens || 0,
      extractionLimit: 1_200_000,
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
const currentHeading=document.createElement('h2');currentHeading.textContent='Current run output';
const currentOutput=document.createElement('pre');currentOutput.id='current-output';currentOutput.textContent='No active run.';
const latestHeading=document.querySelector('h2');latestHeading.parentNode.insertBefore(currentHeading,latestHeading);latestHeading.parentNode.insertBefore(currentOutput,latestHeading);
async function refreshCurrentOutput(){const response=await fetch('/api/status');const state=await response.json();currentOutput.textContent=state.activeRun?.output||'No active run.'}
refreshCurrentOutput();setInterval(refreshCurrentOutput,5000);
</script>`;

const server = http.createServer(async (request, response) => {
  const url = new URL(request.url, `http://${request.headers.host}`);
  response.setHeader('cache-control', 'no-store');
  if (url.pathname === '/') { response.writeHead(200, { 'content-type': 'text/html; charset=utf-8' }); response.end(page.replace('</body>', `${liveOutputScript}</body>`)); return; }
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
  response.writeHead(404); response.end('Not found');
});

server.listen(port, '127.0.0.1', () => console.log(`Processor monitor: http://127.0.0.1:${port}/`));
process.on('SIGINT', () => { stop(); server.close(() => process.exit(0)); });
process.on('SIGTERM', () => { stop(); server.close(() => process.exit(0)); });
