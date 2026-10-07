import { describe, it, expect } from 'vitest';
import { findYearLocalFeature } from './findFeature';

const data = {
  hugo_leal: {
    features: [
      { properties: { ano: 2022, nr_local: '10' } },
      { properties: { ano: 2018, nr_local: '10' } },
    ],
  },
};

describe('findYearLocalFeature', () => {
  it('finds the matching feature by year and local, coercing nr_local to string', () => {
    const result = findYearLocalFeature(data, 'hugo_leal', 2022, 10);
    expect(result).toBe(data.hugo_leal.features[0]);
  });

  it('returns null when the layer does not exist', () => {
    expect(findYearLocalFeature(data, 'nonexistent', 2022, '10')).toBeNull();
  });

  it('returns null when no feature matches', () => {
    expect(findYearLocalFeature(data, 'hugo_leal', 1999, '10')).toBeNull();
  });
});
