import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { mkdir, mkdtemp, readFile, rename, rm, unlink, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import vm from 'node:vm';

const source = await readFile(new URL('../scripts/processor-monitor.mjs', import.meta.url), 'utf8');
const backend = source.slice(source.indexOf('async function applyCooldown'), source.indexOf('function terminateProcessTree'));

test('served dashboard keeps separate Start and Enter controls with valid scripts', () => {
  const page = vm.runInNewContext(`${source.slice(source.indexOf('const dashboardPage ='), source.indexOf('const server ='))}; monitorPage`, { kb: 'test' });
  assert.match(page, /id="start">Start loop</);
  assert.doesNotMatch(page, /Start \/ apply cooldown/);
  assert.match(page, /Press Enter to save and apply/);
  for (const [, attributes, script] of page.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)) {
    new vm.Script(attributes.includes('module') ? script.replace(/^import .*;$/gm, '') : script);
  }
});

test('cooldown persists, reschedules waiting loops, and preserves active or stopped runs', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'monitor-controls-'));
  const settingsPath = 'settings.json';
  const state = { cooldownMs: 900000, running: false, child: null, timer: null };
  let schedules = 0;
  let runs = 0;
  const context = vm.createContext({ root, settingsPath, state, path, process, randomUUID, mkdir, writeFile, rename, unlink,
    addLog() {}, scheduleNext() { schedules++; }, runProcessor() { runs++; } });
  vm.runInContext(backend, context);
  try {
    await context.applyCooldown(120000);
    assert.equal(JSON.parse(await readFile(path.join(root, settingsPath), 'utf8')).cooldownMs, 120000);
    assert.equal(state.running, false);
    assert.equal(runs, 0);
    state.running = true;
    await context.applyCooldown(180000);
    assert.equal(schedules, 1);
    state.child = { pid: 123 };
    await context.applyCooldown(240000);
    assert.equal(schedules, 1);
    assert.equal(state.child.pid, 123);
    await context.start(240000);
    assert.equal(runs, 0);
    for (const invalid of [NaN, Infinity, 0, -1, 86400001]) {
      await assert.rejects(context.applyCooldown(invalid), /between 1 and 1440/);
    }
    assert.equal(state.cooldownMs, 240000);
    context.rename = async () => { throw new Error('write denied'); };
    await assert.rejects(context.applyCooldown(300000), /write denied/);
    assert.equal(state.cooldownMs, 240000, 'failed persistence leaves the applied setting unchanged');
    assert.equal(JSON.parse(await readFile(path.join(root, settingsPath), 'utf8')).cooldownMs, 240000);
    context.rename = rename;
    state.running = false;
    await context.start();
    assert.equal(runs, 0, 'do not restart while the previous child is stopping');
    state.child = null;
    await context.start();
    assert.equal(state.running, true);
    assert.equal(runs, 1);
    assert.equal(state.cooldownMs, 240000);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test('restart loads only a valid saved cooldown', () => {
  const initialization = source.slice(source.indexOf('const state ='), source.indexOf('function addLog'));
  for (const savedCooldownMs of [120000, null, '120000', -1, Infinity, 86400001]) {
    const cooldown = vm.runInNewContext(`${initialization}; state.cooldownMs`, { savedCooldownMs, defaultCooldownMs: 900000 });
    assert.equal(cooldown, savedCooldownMs === 120000 ? 120000 : 900000);
  }
});

test('controls reflect loop and stopping states; Enter applies without starting', async () => {
  const elements = Object.fromEntries(['start', 'stop', 'interval', 'schedule', 'progress-detail'].map(id => [id, { value: '15', reportValidity: () => true }]));
  const document = { getElementById: id => elements[id], querySelector: selector => elements[selector.slice(1)] };
  const calls = [];
  const stopped = { running: false, activeRun: null, cooldownMs: 120000 };
  const context = vm.createContext({ document, time: String, countdown: String, latestState: null,
    api: async (url, options) => { calls.push({ url, body: JSON.parse(options.body) }); return stopped; }, refresh() {} });
  vm.runInContext("const $=id=>document.getElementById(id);function setText(id,value){$(id).textContent=value}", context);
  vm.runInContext(source.slice(source.indexOf('let cooldownInitialized='), source.indexOf('async function refreshSchedule')), context);
  vm.runInContext(source.slice(source.indexOf('async function submitCooldown'), source.indexOf("$('stop').onclick", source.indexOf('async function submitCooldown'))), context);
  context.renderSchedule(stopped);
  assert.equal(elements.interval.value, 2);
  assert.equal(elements.start.disabled, false);
  assert.equal(elements.stop.disabled, true);
  elements.interval.value = '7';
  context.renderSchedule({ ...stopped, running: true });
  assert.equal(elements.interval.value, '7', 'polling preserves unsaved input');
  assert.equal(elements.start.disabled, true);
  assert.equal(elements.stop.disabled, false);
  context.renderSchedule({ ...stopped, activeRun: { startedAt: 'now' } });
  assert.equal(elements.start.disabled, true);
  assert.equal(elements.stop.disabled, false);
  let prevented = false;
  elements.interval.onkeydown({ key: 'Enter', preventDefault() { prevented = true; } });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(prevented, true);
  assert.deepEqual(calls, [{ url: '/api/cooldown', body: { cooldownMinutes: 7 } }]);
  elements.interval.reportValidity = () => false;
  await context.submitCooldown('/api/start');
  assert.equal(calls.length, 1);
});
