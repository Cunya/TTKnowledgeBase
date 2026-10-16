const weekMs = 7 * 24 * 60 * 60 * 1000;
const stageNames = { acquisition: 'needs_acquisition', extraction: 'needs_extraction', adjudication: 'needs_adjudication', complete: 'complete', excluded: 'excluded', retry_wait: 'retry_wait' };
const decisionNames = ['pending', 'deferred', 'accepted', 'rejected', 'human_review'];
const colors = { acquisition: '#2f6f8e', extraction: '#7a5ea8', adjudication: '#b07b32', complete: '#2f7a4d', excluded: '#7c8580', retry_wait: '#9aa39d', pending: '#22613f', deferred: '#b3462f', accepted: '#2f7a4d', rejected: '#7a5ea8', human_review: '#8a6f3d' };

function observation(at, summary) {
  return {
    at,
    stages: Object.fromEntries(Object.entries(stageNames).map(([id, state]) => [id, summary.states?.[state] ?? 0])),
    decisions: Object.fromEntries(decisionNames.map(id => [id, summary.candidates?.[id] ?? 0])),
  };
}

export function prepareBucketHistory(saved, latest, inventory, now = Date.now()) {
  const savedEntries = Array.isArray(saved) ? saved : saved?.entries;
  const entries = Array.isArray(savedEntries) ? [...savedEntries] : [];
  if (latest?.started_at && latest.inventory_before) entries.push(observation(latest.started_at, latest.inventory_before));
  if (latest?.finished_at && latest.inventory_after) entries.push(observation(latest.finished_at, latest.inventory_after));
  if (inventory?.generated_at && inventory.summary) entries.push(observation(inventory.generated_at, inventory.summary));
  const byTime = new Map();
  for (const entry of entries) {
    const at = Date.parse(entry?.at);
    if (!Number.isFinite(at) || at > now || !entry.stages || !entry.decisions) continue;
    const counts = (value, names) => Object.fromEntries(names
      .filter(id => Number.isFinite(value?.[id]) && value[id] >= 0)
      .map(id => [id, value[id]]));
    byTime.set(at, {
      at: new Date(at).toISOString(),
      stages: counts(entry.stages, Object.keys(stageNames)),
      decisions: counts(entry.decisions, decisionNames),
    });
  }
  const ordered = [...byTime.values()].sort((a, b) => Date.parse(a.at) - Date.parse(b.at));
  const cutoff = now - weekMs;
  const anchor = ordered.filter(entry => Date.parse(entry.at) < cutoff).at(-1);
  return [...(anchor ? [anchor] : []), ...ordered.filter(entry => Date.parse(entry.at) >= cutoff)];
}

export function renderBucketChart(group, item, history, now = Date.now()) {
  const points = (history || []).filter(entry => Number.isFinite(entry[group]?.[item.id]));
  if (!points.length) return '';
  const width = 640, height = 220, left = 72, right = 12, top = 18, bottom = 36;
  const plotWidth = width - left - right, plotHeight = height - top - bottom;
  const cutoff = now - weekMs;
  const values = points.map(entry => entry[group][item.id]);
  const padding = Math.max(1, Math.ceil((Math.max(...values) - Math.min(...values)) * 0.15));
  const lower = Math.max(0, Math.min(...values) - padding);
  const upper = Math.max(...values) + padding;
  const x = at => left + Math.max(0, Math.min(1, (Date.parse(at) - cutoff) / weekMs)) * plotWidth;
  const y = value => top + plotHeight - (value - lower) / (upper - lower) * plotHeight;
  const format = value => Number(value).toLocaleString();
  const time = at => new Date(at).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  const ticks = [...new Set([lower, Math.round((lower + upper) / 2), upper])];
  const grid = ticks.map(value => `<line class="chart-grid" x1="${left}" y1="${y(value)}" x2="${width - right}" y2="${y(value)}"></line><text class="chart-axis-label" x="${left - 8}" y="${y(value) + 3}" text-anchor="end">${format(value)}</text>`).join('');
  const path = points.map((entry, index) => index === 0
    ? `M ${x(entry.at).toFixed(1)} ${y(values[index]).toFixed(1)}`
    : `H ${x(entry.at).toFixed(1)} V ${y(values[index]).toFixed(1)}`).join(' ');
  const last = points.at(-1);
  const color = colors[item.id] || '#22613f';
  const groupLabel = group === 'stages' ? 'Inventory videos' : 'Concept-proposal decisions';
  const coverage = Date.parse(points[0].at) > cutoff ? `No observations before ${time(points[0].at)}. ` : '';
  const note = points.length === 1 ? 'Only one observation; collecting history.' : 'Lines hold the last recorded count between observations.';
  const labels = [0, 0.5, 1].map((fraction, index) => `<text class="chart-axis-label" x="${left + fraction * plotWidth}" y="${height - 8}" text-anchor="${['start', 'middle', 'end'][index]}">${time(cutoff + fraction * weekMs)}</text>`).join('');
  return `<section class="bucket-chart"><div class="bucket-chart-title">${item.label}</div><span class="bucket-chart-group">${groupLabel} · last 7 days</span><svg role="img" aria-label="${item.label} seven-day history graph" viewBox="0 0 ${width} ${height}"><title>${item.label} history</title>${grid}<path class="chart-line" stroke="${color}" d="${path}"></path><circle class="chart-point" fill="${color}" cx="${x(last.at).toFixed(1)}" cy="${y(values.at(-1)).toFixed(1)}" r="3.5"></circle>${labels}</svg><div class="bucket-legend"><span><i style="background:${color}"></i><strong>${format(values.at(-1))}</strong> last observed</span></div><div class="bucket-chart-note">${points.length} observations · ${coverage}${note} Last observed ${time(last.at)}.</div></section>`;
}
