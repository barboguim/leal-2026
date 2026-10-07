import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import App from './App';

function point(nrLocal, ano, votos) {
  return {
    type: 'Feature',
    geometry: { type: 'Point', coordinates: [-43.0783, -22.9017] },
    properties: { nr_local: nrLocal, ano, QT_VOTOS: votos, n_secoes: 1, nm_local: 'Escola Teste', bairro: 'Icarai' },
  };
}

describe('App', () => {
  afterEach(() => {
    delete window.DATA;
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('shows each candidate\'s own selected-year total, then that candidate\'s own aggregated total for "Todos" — independent of the other candidates', () => {
    window.DATA = {
      hugo_leal: {
        type: 'FeatureCollection',
        features: [point('1', 2018, 100), point('1', 2022, 150)],
      },
      felipe_peixoto: {
        type: 'FeatureCollection',
        features: [point('1', 2018, 60), point('1', 2022, 90)],
      },
    };
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ type: 'FeatureCollection', features: [] }),
    })));

    render(<App />);

    const hugoRow = screen.getByText('Hugo Leal', { selector: '.cand-name' }).closest('details');
    // Default year (2022) is selected: only that year's votes are counted.
    expect(within(hugoRow).getByText('150')).toBeInTheDocument();

    // Switching Hugo's own "Todos" chip aggregates across years for Hugo
    // only -- must be the summed total (250), not zero.
    fireEvent.click(within(hugoRow).getByText('Todos'));
    expect(within(hugoRow).getByText('250')).toBeInTheDocument();

    // Felipe's own year selection is untouched by Hugo's change.
    const felipeRow = screen.getByText('Felipe Peixoto', { selector: '.cand-name' }).closest('details');
    expect(within(felipeRow).getByText('90')).toBeInTheDocument();
  });

  it('only lets one candidate compare years at a time', () => {
    window.DATA = {
      hugo_leal: { type: 'FeatureCollection', features: [point('1', 2018, 100), point('1', 2022, 150)] },
      felipe_peixoto: { type: 'FeatureCollection', features: [point('1', 2018, 60), point('1', 2022, 90)] },
      vote_deltas: {
        type: 'FeatureCollection',
        features: [
          { type: 'Feature', geometry: { type: 'Point', coordinates: [-43.0783, -22.9017] }, properties: { nr_local: '1', pair: '2018-2022', ano_inicio: 2018, ano_fim: 2022, tipo_par: 'Geral -> Geral', delta_hugo: 50, delta_felipe: 30, votos_hugo_inicio: 100, votos_hugo_fim: 150, votos_felipe_inicio: 60, votos_felipe_fim: 90 } },
        ],
      },
    };
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ type: 'FeatureCollection', features: [] }),
    })));

    render(<App />);

    const hugoRow = screen.getByText('Hugo Leal', { selector: '.cand-name' }).closest('details');
    const felipeRow = screen.getByText('Felipe Peixoto', { selector: '.cand-name' }).closest('details');

    // Hugo compares by default.
    expect(within(hugoRow).getByText('2018-2022')).toHaveClass('active');

    // Turning Felipe's comparison on switches the active candidate off Hugo.
    const felipeCompareToggle = within(felipeRow.querySelector('.delta-toggle-row')).getByRole('checkbox');
    fireEvent.click(felipeCompareToggle);
    expect(within(felipeRow).getByText('2018-2022')).toHaveClass('active');
    expect(within(hugoRow).queryByText('2018-2022')).not.toBeInTheDocument();
  });

  it('keeps "comparing" and "visible" in sync: hiding the active candidate turns its comparison off', () => {
    window.DATA = {
      hugo_leal: { type: 'FeatureCollection', features: [point('1', 2018, 100), point('1', 2022, 150)] },
      vote_deltas: {
        type: 'FeatureCollection',
        features: [
          { type: 'Feature', geometry: { type: 'Point', coordinates: [-43.0783, -22.9017] }, properties: { nr_local: '1', pair: '2018-2022', ano_inicio: 2018, ano_fim: 2022, tipo_par: 'Geral -> Geral', delta_hugo: 50, votos_hugo_inicio: 100, votos_hugo_fim: 150 } },
        ],
      },
    };
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ type: 'FeatureCollection', features: [] }),
    })));

    render(<App />);

    const hugoRow = screen.getByText('Hugo Leal', { selector: '.cand-name' }).closest('details');
    // Hugo compares by default.
    expect(within(hugoRow).getByText('2018-2022')).toHaveClass('active');

    // Hiding Hugo (unchecking his own visibility box) turns his comparison off too.
    fireEvent.click(within(hugoRow).getAllByRole('checkbox')[0]);
    expect(within(hugoRow).queryByText('2018-2022')).not.toBeInTheDocument();
  });

  it('keeps "comparing" and "visible" in sync: turning comparison on for a hidden candidate makes it visible', () => {
    window.DATA = {
      hugo_leal: { type: 'FeatureCollection', features: [] },
      psd: { type: 'FeatureCollection', features: [point('1', 2018, 40), point('1', 2022, 60)] },
      vote_deltas: {
        type: 'FeatureCollection',
        features: [
          { type: 'Feature', geometry: { type: 'Point', coordinates: [-43.0783, -22.9017] }, properties: { nr_local: '1', pair: '2018-2022', ano_inicio: 2018, ano_fim: 2022, tipo_par: 'Geral -> Geral', delta_psd: 20, votos_psd_inicio: 40, votos_psd_fim: 60 } },
        ],
      },
    };
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ type: 'FeatureCollection', features: [] }),
    })));

    render(<App />);

    const psdRow = screen.getByText('PSD (total)', { selector: '.cand-name' }).closest('details');
    // PSD starts hidden (unchecked) by default.
    expect(within(psdRow).getAllByRole('checkbox')[0]).not.toBeChecked();

    // Turning PSD's comparison on also makes it visible.
    const psdCompareToggle = within(psdRow.querySelector('.delta-toggle-row')).getByRole('checkbox');
    fireEvent.click(psdCompareToggle);
    expect(within(psdRow).getAllByRole('checkbox')[0]).toBeChecked();
  });
});
