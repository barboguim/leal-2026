import { describe, it, expect } from 'vitest';
import { interpolateChannel, interpolateColor, getDivergingColor, getRadius, getDeltaRadius, getSequentialColor } from './visual';

describe('interpolateChannel', () => {
  it('interpolates linearly and rounds', () => {
    expect(interpolateChannel(0, 100, 0)).toBe(0);
    expect(interpolateChannel(0, 100, 1)).toBe(100);
    expect(interpolateChannel(0, 100, 0.5)).toBe(50);
  });
});

describe('interpolateColor', () => {
  it('produces an rgb() string between two colors', () => {
    expect(interpolateColor([0, 0, 0], [100, 100, 100], 0.5)).toBe('rgb(50, 50, 50)');
  });
});

describe('getDivergingColor', () => {
  it('trends toward the gain color for positive values', () => {
    const color = getDivergingColor(100, 100);
    expect(color).toBe('rgb(15, 118, 110)');
  });

  it('trends toward the loss color for negative values', () => {
    const color = getDivergingColor(-100, 100);
    expect(color).toBe('rgb(185, 28, 28)');
  });

  it('returns the neutral color at zero', () => {
    expect(getDivergingColor(0, 100)).toBe('rgb(237, 239, 242)');
  });
});

describe('getRadius', () => {
  it('uses a larger multiplier for hugo_leal than other layers', () => {
    expect(getRadius(100, 'hugo_leal')).toBeGreaterThan(getRadius(100, 'felipe_peixoto'));
    expect(getRadius(100, 'hugo_leal')).toBeGreaterThan(getRadius(100, 'psd'));
  });

  it('floors at 4', () => {
    expect(getRadius(0, 'hugo_leal')).toBe(4);
    expect(getRadius(0, 'psd')).toBe(4);
  });
});

describe('getDeltaRadius', () => {
  it('returns 4 for a zero delta', () => {
    expect(getDeltaRadius(0)).toBe(4);
  });

  it('scales with the magnitude of the delta, clamped between 5 and 28', () => {
    expect(getDeltaRadius(1)).toBeGreaterThanOrEqual(5);
    expect(getDeltaRadius(100000)).toBeLessThanOrEqual(28);
  });

  it('treats gains and losses symmetrically', () => {
    expect(getDeltaRadius(50)).toBe(getDeltaRadius(-50));
  });
});

describe('getSequentialColor', () => {
  it('returns a distinct color at 0% vs 100% under the default domain', () => {
    const low = getSequentialColor(0);
    const high = getSequentialColor(100);
    expect(low).not.toBe(high);
  });

  it('treats null/undefined as the min of the domain', () => {
    expect(getSequentialColor(null)).toBe(getSequentialColor(0));
    expect(getSequentialColor(undefined)).toBe(getSequentialColor(0));
  });

  it('clamps values outside the given min/max', () => {
    expect(getSequentialColor(150)).toBe(getSequentialColor(100));
    expect(getSequentialColor(-10)).toBe(getSequentialColor(0));
  });

  it('falls back to a fixed mid-tone when max === min instead of dividing by zero', () => {
    expect(getSequentialColor(55, 55, 55)).toBe(getSequentialColor(50, 0, 100));
  });

  it('normalizes against a data-driven min/max, not a fixed 0-100 domain', () => {
    // Real pct_mulheres data spans ~49.6-62.0 across Niterói. Under a
    // data-driven domain, the low and high ends of that narrow band should
    // map to the full color range (t=0 and t=1) instead of both landing
    // near the middle of a fixed 0-100 scale.
    const min = 49.6;
    const max = 62.0;
    const low = getSequentialColor(min, min, max);
    const high = getSequentialColor(max, min, max);
    expect(low).toBe(getSequentialColor(0, 0, 100)); // t=0
    expect(high).toBe(getSequentialColor(100, 0, 100)); // t=1
    expect(low).not.toBe(high);

    // Under the old fixed 0-100 domain, both values would land close
    // together (t≈0.496 and t≈0.62) — a much smaller color difference than
    // the full-range spread produced by the data-driven domain above.
    const oldLow = getSequentialColor(min); // t ≈ 0.496, default domain
    const oldHigh = getSequentialColor(max); // t ≈ 0.62, default domain
    expect(oldLow).not.toBe(low);
    expect(oldHigh).not.toBe(high);
  });
});
