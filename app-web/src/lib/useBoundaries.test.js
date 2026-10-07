import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useBoundaries } from './useBoundaries';

describe('useBoundaries', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('populates regionFeatures and bairroFeatures on successful fetch', async () => {
    const regionFC = { features: [{ properties: { tx_nome: 'Regiao Oceanica' } }] };
    const bairroFC = { features: [{ properties: { tx_nome: 'Icarai' } }] };
    let call = 0;
    vi.stubGlobal('fetch', vi.fn(() => {
      call += 1;
      const body = call === 1 ? regionFC : bairroFC;
      return Promise.resolve({ ok: true, json: () => Promise.resolve(body) });
    }));

    const { result } = renderHook(() => useBoundaries());

    await waitFor(() => expect(result.current.regionFeatures).toHaveLength(1));
    expect(result.current.bairroFeatures).toHaveLength(1);
    expect(result.current.error).toBeNull();
  });

  it('sets an error and leaves features empty when the fetch fails', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({ ok: false, status: 500 })));
    vi.spyOn(console, 'warn').mockImplementation(() => {});

    const { result } = renderHook(() => useBoundaries());

    await waitFor(() => expect(result.current.error).not.toBeNull());
    expect(result.current.regionFeatures).toEqual([]);
    expect(result.current.bairroFeatures).toEqual([]);
    expect(console.warn).toHaveBeenCalled();
  });
});
