import { describe, it, expect, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useMapData } from './useMapData';

describe('useMapData', () => {
  afterEach(() => {
    delete window.DATA;
  });

  it('returns window.DATA when present', () => {
    window.DATA = { hugo_leal: { type: 'FeatureCollection', features: [] } };
    const { result } = renderHook(() => useMapData());
    expect(result.current).toBe(window.DATA);
  });

  it('returns null when window.DATA is missing', () => {
    delete window.DATA;
    const { result } = renderHook(() => useMapData());
    expect(result.current).toBeNull();
  });

  it('reflects the real generated data.js shape', async () => {
    const raw = await import('../../public/data.js?raw');
    // eslint-disable-next-line no-eval
    window.DATA = undefined;
    (0, eval)(raw.default.replace('const DATA', 'window.DATA'));
    const { result } = renderHook(() => useMapData());
    expect(result.current).toHaveProperty('hugo_leal.features');
    expect(result.current).toHaveProperty('felipe_peixoto.features');
    const sample = result.current.hugo_leal.features[0].properties;
    expect(sample).toHaveProperty('ano');
    expect(sample).toHaveProperty('nr_local');
    expect(sample).toHaveProperty('QT_VOTOS');
  });
});
