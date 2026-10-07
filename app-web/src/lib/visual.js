export function interpolateChannel(a, b, t) {
  return Math.round(a + (b - a) * t);
}

export function interpolateColor(start, end, t) {
  return `rgb(${interpolateChannel(start[0], end[0], t)}, ${interpolateChannel(start[1], end[1], t)}, ${interpolateChannel(start[2], end[2], t)})`;
}

export function getDivergingColor(value, maxAbs) {
  const neutral = [237, 239, 242];
  const gain = [15, 118, 110];
  const loss = [185, 28, 28];
  const t = Math.min(1, Math.sqrt(Math.abs(value) / Math.max(maxAbs, 1)));
  return value >= 0 ? interpolateColor(neutral, gain, t) : interpolateColor(neutral, loss, t);
}

export function getRadius(votes, key) {
  if (key === 'hugo_leal') return Math.max(4, Math.sqrt(votes) * 2.5);
  return Math.max(4, Math.sqrt(votes) * 0.8);
}

export function getDeltaRadius(delta) {
  const absDelta = Math.abs(Number(delta) || 0);
  if (absDelta === 0) return 4;
  return Math.max(5, Math.min(28, Math.sqrt(absDelta) * 0.72));
}

export function getSequentialColor(pct, min = 0, max = 100) {
  const light = [238, 242, 255];
  const dark = [49, 46, 129];
  const value = Number.isFinite(Number(pct)) ? Number(pct) : min;
  const t = max === min ? 0.5 : Math.min(1, Math.max(0, (value - min) / (max - min)));
  return interpolateColor(light, dark, t);
}

// Classic 5-class sequential heat palette (ColorBrewer YlOrRd). Chosen over a
// continuous gradient because the user asked for discrete classes — a classed
// map reads more honestly on skewed data (Hugo's share has a long tail) and
// the legend can show explicit break values.
export const HEAT_PALETTE = ['#FFEDA0', '#FEB24C', '#FD8D3C', '#FC4E2A', '#B10026'];

// Quantile breaks: k-1 cut points that split a sorted sample into k classes
// of equal count. Works on skewed distributions (fair visual balance) and
// never produces an empty class, unlike equal-interval. Duplicates in the
// sample can collapse adjacent breaks into the same value — the renderer
// still assigns each point to exactly one class via the strict-less-than
// comparison in getHeatClass.
export function computeQuantileBreaks(values, k = 5) {
  const sorted = values
    .map(Number)
    .filter(v => Number.isFinite(v))
    .sort((a, b) => a - b);
  if (sorted.length === 0) return [];
  const breaks = [];
  for (let i = 1; i < k; i++) {
    const idx = Math.min(sorted.length - 1, Math.floor((sorted.length * i) / k));
    breaks.push(sorted[idx]);
  }
  return breaks;
}

// Returns the class index [0 .. palette.length-1] for a value given k-1 breaks.
export function getHeatClass(value, breaks) {
  const v = Number(value);
  if (!Number.isFinite(v)) return 0;
  for (let i = 0; i < breaks.length; i++) {
    if (v < breaks[i]) return i;
  }
  return breaks.length;
}

export function getHeatColor(value, breaks, palette = HEAT_PALETTE) {
  return palette[getHeatClass(value, breaks)];
}
