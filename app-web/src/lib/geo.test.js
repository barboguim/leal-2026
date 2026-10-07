import { describe, it, expect } from 'vitest';
import { pointInRing, pointInGeometry, normalizeText, featureName, passesGeoFilter, annotateFeatureCollection } from './geo';

describe('pointInRing', () => {
  const square = [[0, 0], [0, 10], [10, 10], [10, 0], [0, 0]];

  it('returns true for a point inside the ring', () => {
    expect(pointInRing([5, 5], square)).toBe(true);
  });

  it('returns false for a point outside the ring', () => {
    expect(pointInRing([15, 15], square)).toBe(false);
  });
});

describe('pointInGeometry', () => {
  it('handles a Polygon with an outer ring only', () => {
    const geometry = { type: 'Polygon', coordinates: [[[0, 0], [0, 10], [10, 10], [10, 0], [0, 0]]] };
    expect(pointInGeometry([5, 5], geometry)).toBe(true);
    expect(pointInGeometry([50, 50], geometry)).toBe(false);
  });

  it('excludes points inside a hole (second ring)', () => {
    const geometry = {
      type: 'Polygon',
      coordinates: [
        [[0, 0], [0, 10], [10, 10], [10, 0], [0, 0]],
        [[4, 4], [4, 6], [6, 6], [6, 4], [4, 4]],
      ],
    };
    expect(pointInGeometry([5, 5], geometry)).toBe(false);
    expect(pointInGeometry([1, 1], geometry)).toBe(true);
  });

  it('handles a MultiPolygon by checking each polygon', () => {
    const geometry = {
      type: 'MultiPolygon',
      coordinates: [
        [[[0, 0], [0, 10], [10, 10], [10, 0], [0, 0]]],
        [[[20, 20], [20, 30], [30, 30], [30, 20], [20, 20]]],
      ],
    };
    expect(pointInGeometry([25, 25], geometry)).toBe(true);
    expect(pointInGeometry([50, 50], geometry)).toBe(false);
  });

  it('returns false for missing or unsupported geometry', () => {
    expect(pointInGeometry([1, 1], null)).toBe(false);
    expect(pointInGeometry([1, 1], { type: 'Point', coordinates: [1, 1] })).toBe(false);
  });
});

describe('normalizeText', () => {
  it('strips accents and uppercases', () => {
    expect(normalizeText('Niterói')).toBe('NITEROI');
    expect(normalizeText('  são gonçalo  ')).toBe('SAO GONCALO');
  });

  it('handles null/undefined as empty string', () => {
    expect(normalizeText(null)).toBe('');
    expect(normalizeText(undefined)).toBe('');
  });
});

describe('featureName', () => {
  it('reads the first available name field', () => {
    expect(featureName({ properties: { tx_nome: 'Centro' } })).toBe('Centro');
    expect(featureName({ properties: { si_nome: 'Icarai' } })).toBe('Icarai');
    expect(featureName({ properties: {} })).toBe('');
    expect(featureName({})).toBe('');
  });
});

describe('passesGeoFilter', () => {
  const props = { __region: 'Regiao Oceanica', __bairro_geo: 'Icarai' };

  it('passes everything when both filters are "all"', () => {
    expect(passesGeoFilter(props, 'all', 'all')).toBe(true);
  });

  it('filters by region', () => {
    expect(passesGeoFilter(props, 'Regiao Oceanica', 'all')).toBe(true);
    expect(passesGeoFilter(props, 'Regiao Norte', 'all')).toBe(false);
  });

  it('filters by bairro, falling back to props.bairro when __bairro_geo is absent', () => {
    expect(passesGeoFilter(props, 'all', 'Icarai')).toBe(true);
    expect(passesGeoFilter({ bairro: 'Icarai' }, 'all', 'Icarai')).toBe(true);
    expect(passesGeoFilter({ bairro: 'Centro' }, 'all', 'Icarai')).toBe(false);
  });
});

describe('annotateFeatureCollection', () => {
  const regionFeatures = [{
    properties: { tx_nome: 'Regiao Oceanica' },
    geometry: { type: 'Polygon', coordinates: [[[0, 0], [0, 10], [10, 10], [10, 0], [0, 0]]] },
  }];
  const bairroFeatures = [{
    properties: { tx_nome: 'Icarai' },
    geometry: { type: 'Polygon', coordinates: [[[0, 0], [0, 10], [10, 10], [10, 0], [0, 0]]] },
  }];

  it('tags each feature with __region and __bairro_geo without mutating the input', () => {
    const fc = {
      type: 'FeatureCollection',
      features: [{ type: 'Feature', geometry: { type: 'Point', coordinates: [5, 5] }, properties: { nr_local: '1' } }],
    };
    const result = annotateFeatureCollection(fc, regionFeatures, bairroFeatures);
    expect(result.features[0].properties.__region).toBe('REGIAO OCEANICA');
    expect(result.features[0].properties.__bairro_geo).toBe('ICARAI');
    expect(fc.features[0].properties.__region).toBeUndefined();
  });

  it('returns empty tags for a point outside all boundaries', () => {
    const fc = {
      type: 'FeatureCollection',
      features: [{ type: 'Feature', geometry: { type: 'Point', coordinates: [500, 500] }, properties: {} }],
    };
    const result = annotateFeatureCollection(fc, regionFeatures, bairroFeatures);
    expect(result.features[0].properties.__region).toBe('');
    expect(result.features[0].properties.__bairro_geo).toBe('');
  });

  it('passes through a falsy collection unchanged', () => {
    expect(annotateFeatureCollection(null, regionFeatures, bairroFeatures)).toBeNull();
  });
});
