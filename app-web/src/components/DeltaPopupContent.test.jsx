import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import DeltaPopupContent from './DeltaPopupContent';

const p = {
  nm_local: 'Escola Teste', bairro: 'Icarai', pair: '2022-2024', nr_local: '10',
  ano_inicio: 2022, ano_fim: 2024, tipo_par: 'Federal -> Municipal',
  delta_hugo: -10, delta_felipe: 20, delta_psd: 5,
  votos_hugo_inicio: 50, votos_hugo_fim: 40,
  votos_felipe_inicio: 30, votos_felipe_fim: 50,
  votos_psd_inicio: 100, votos_psd_fim: 105,
  secoes_inicio: 3, secoes_fim: 4, secao_churn: 0.1,
};
const metric = { label: 'Hugo', field: 'delta_hugo' };
const noopFind = () => null;

describe('DeltaPopupContent', () => {
  it('renders the local name and delta fields', () => {
    render(<DeltaPopupContent p={p} metric={metric} color="#fff" selectedDeltaMetric="hugo" findYearLocalFeature={noopFind} />);
    expect(screen.getByText('Escola Teste')).toBeInTheDocument();
    expect(screen.getByText('Delta Hugo')).toBeInTheDocument();
    expect(screen.getByText('-10')).toBeInTheDocument();
  });

  it('shows two competitor sections (start and end year) for the hugo metric', () => {
    render(<DeltaPopupContent p={p} metric={metric} color="#fff" selectedDeltaMetric="hugo" findYearLocalFeature={noopFind} />);
    expect(screen.getByText('Concorrencia 2022')).toBeInTheDocument();
    expect(screen.getByText('Concorrencia 2024')).toBeInTheDocument();
  });

  it('shows no competitor sections for the psd metric', () => {
    render(<DeltaPopupContent p={p} metric={{ label: 'PSD', field: 'delta_psd' }} color="#fff" selectedDeltaMetric="psd" findYearLocalFeature={noopFind} />);
    expect(screen.queryByText(/Concorrencia/)).not.toBeInTheDocument();
  });

  it('renders N/A with the candidacy_status reason when a candidate delta is null', () => {
    const pWithNull = { ...p, delta_felipe: null, candidacy_status_felipe: 'nao_concorreu', votos_felipe_inicio: null, votos_felipe_fim: null };
    render(<DeltaPopupContent p={pWithNull} metric={metric} color="#fff" selectedDeltaMetric="hugo" findYearLocalFeature={noopFind} />);
    expect(screen.getByText(/N\/A/)).toBeInTheDocument();
    expect(screen.queryByText(/undefined -> undefined/)).not.toBeInTheDocument();
  });

  it('renders N/A for the primary metric row when the selected metric itself is gated out', () => {
    const pWithNull = { ...p, delta_hugo: null, candidacy_status_hugo: 'tipo_incompativel' };
    render(<DeltaPopupContent p={pWithNull} metric={metric} color="#fff" selectedDeltaMetric="hugo" findYearLocalFeature={noopFind} />);
    // Both the "Delta Hugo" row (primaryValue) and the "Hugo" candidate row read
    // candidacy_status_hugo, so both render N/A here. Assert exactly 2: this still
    // discriminates a primaryValue-only regression (which would leave just 1 match)
    // from correct behavior.
    expect(screen.getAllByText(/N\/A/).length).toBe(2);
  });

  it('flags cargo diferente on the candidate row when the compared years had different cargos', () => {
    const pCargoDiff = { ...p, cargo_diferente_felipe: true };
    render(<DeltaPopupContent p={pCargoDiff} metric={metric} color="#fff" selectedDeltaMetric="hugo" findYearLocalFeature={noopFind} />);
    expect(screen.getByText(/cargo diferente/)).toBeInTheDocument();
  });

  it('does not show cargo diferente when cargos matched or the field is absent', () => {
    render(<DeltaPopupContent p={p} metric={metric} color="#fff" selectedDeltaMetric="hugo" findYearLocalFeature={noopFind} />);
    expect(screen.queryByText(/cargo diferente/)).not.toBeInTheDocument();
  });
});
