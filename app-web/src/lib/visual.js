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
