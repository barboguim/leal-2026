import { describe, it, expect } from 'vitest';
import { aggregateByLocal } from './aggregate';

describe('aggregateByLocal', () => {
  it('sums votes across years for the same local', () => {
    const features = [
      { type: 'Feature', geometry: { type: 'Point', coordinates: [1, 2] }, properties: { nr_local: '10', ano: 2018, QT_VOTOS: 100, n_secoes: 5 } },
      { type: 'Feature', geometry: { type: 'Point', coordinates: [1, 2] }, properties: { nr_local: '10', ano: 2022, QT_VOTOS: 150, n_secoes: 6 } },
    ];
    const result = aggregateByLocal(features);
    expect(result).toHaveLength(1);
    expect(result[0].properties.QT_VOTOS).toBe(250);
    expect(result[0].properties.n_secoes).toBe(6);
    expect(result[0].properties._years).toEqual({ 2018: 100, 2022: 150 });
    expect(result[0].geometry).toEqual(features[0].geometry);
  });

  it('keeps different locals separate', () => {
    const features = [
      { type: 'Feature', geometry: { type: 'Point', coordinates: [1, 2] }, properties: { nr_local: '10', ano: 2022, QT_VOTOS: 100, n_secoes: 5 } },
      { type: 'Feature', geometry: { type: 'Point', coordinates: [3, 4] }, properties: { nr_local: '20', ano: 2022, QT_VOTOS: 200, n_secoes: 3 } },
    ];
    expect(aggregateByLocal(features)).toHaveLength(2);
  });

  it('returns an empty array for no features', () => {
    expect(aggregateByLocal([])).toEqual([]);
  });
});
