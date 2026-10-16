import assert from 'node:assert/strict';
import test from 'node:test';
import { prepareBucketHistory, renderBucketChart } from '../scripts/monitor-history.mjs';

const day = 24 * 60 * 60 * 1000;
const now = Date.parse('2026-10-12T10:00:00Z');
const item = { id: 'accepted', label: 'Accepted concept proposals' };
const entry = (days, count) => ({ at: new Date(now - days * day).toISOString(), stages: {}, decisions: { accepted: count } });

test('flat observed counts render a horizontal line, not just a point', () => {
  const html = renderBucketChart('decisions', item, [entry(6, 1200), entry(1, 1200)], now);
  assert.match(html, /d="M 151\.4 101\.0 H 548\.6 V 101\.0"/);
  assert.match(html, /2 observations/);
  assert.match(html, /No observations before/);
  assert.match(html, /last 7 days/);
});

test('uneven times use elapsed time and step changes, with visible small differences', () => {
  const html = renderBucketChart('decisions', item, [entry(7, 1200), entry(6, 1201), entry(0, 1202)], now);
  assert.match(html, /d="M 72\.0 [\d.]+ H 151\.4 V [\d.]+ H 628\.0 V [\d.]+"/);
  assert.ok(html.includes(`>${Number(1199).toLocaleString()}<`));
  assert.doesNotMatch(html, /No observations before/);
});

test('a single observation does not fabricate a week of historical counts', () => {
  const html = renderBucketChart('decisions', item, [entry(0, 1200)], now);
  assert.match(html, /Only one observation; collecting history/);
  assert.doesNotMatch(html, /d="M [^"]+ H /);
  assert.equal(renderBucketChart('decisions', item, [], now), '');
});

test('restart preparation merges saved and actual manifest observations chronologically', () => {
  const summary = count => ({ states: { complete: 3 }, candidates: { accepted: count } });
  const saved = { entries: [entry(0, 14), entry(9, 9), entry(8, 10), entry(1, 12)] };
  const latest = { started_at: entry(2, 0).at, inventory_before: summary(11), finished_at: entry(1, 0).at, inventory_after: summary(12) };
  const inventory = { generated_at: entry(0, 0).at, summary: summary(14) };
  const result = prepareBucketHistory(saved, latest, inventory, now);
  assert.deepEqual(result.map(value => value.decisions.accepted), [10, 11, 12, 14]);
  assert.deepEqual(prepareBucketHistory({ entries: result }, latest, inventory, now), result);
});

test('new observations are read on refresh and future dates are excluded', () => {
  const first = prepareBucketHistory({ entries: [entry(1, 12), entry(-1, 99)] }, null, null, now);
  const refreshed = prepareBucketHistory({ entries: [...first, entry(0, 13)] }, null, null, now);
  assert.deepEqual(refreshed.map(value => value.decisions.accepted), [12, 13]);
});
