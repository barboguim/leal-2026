import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import StatsPanel from './StatsPanel';

const data = {
  hugo_leal: { features: [
    { properties: { ano: 2022, nr_local: '10', QT_VOTOS: 40 } },
    { properties: { ano: 2022, nr_local: '20', QT_VOTOS: 60 } },
  ] },
  felipe_peixoto: { features: [] },
  psd: { features: [] },
  vote_deltas: { features: [
    { properties: { pair: '2022-2024', ano_inicio: 2022, ano_fim: 2024, delta_hugo: -10, votos_hugo_inicio: 100, votos_hugo_fim: 90 } },
  ] },
};

const candidateYears2022 = { hugo_leal: 2022, felipe_peixoto: 2022, psd: 2022 };
const candidateYearsAll = { hugo_leal: null, felipe_peixoto: null, psd: null };

describe('StatsPanel', () => {
  it("shows each candidate's own selected-year total and local count", () => {
    render(<StatsPanel data={data} candidateYears={candidateYears2022} selectedRegion="all" selectedBairro="all" selectedPair="2022-2024" selectedDeltaMetric="hugo" deltaEnabled={false} />);
    expect(screen.getByText('Resumo')).toBeInTheDocument();
    expect(screen.getByText('Hugo Leal')).toBeInTheDocument();
    expect(screen.getByText('100')).toBeInTheDocument(); // 40 + 60
    expect(screen.getByText('2')).toBeInTheDocument(); // 2 locais
  });

  it('shows "todos os anos" for a candidate with no year selected', () => {
    render(<StatsPanel data={data} candidateYears={candidateYearsAll} selectedRegion="all" selectedBairro="all" selectedPair="2022-2024" selectedDeltaMetric="hugo" deltaEnabled={false} />);
    expect(screen.getByText(/todos os anos/)).toBeInTheDocument();
  });

  it('shows the delta summary when deltaEnabled is true', () => {
    render(<StatsPanel data={data} candidateYears={candidateYears2022} selectedRegion="all" selectedBairro="all" selectedPair="2022-2024" selectedDeltaMetric="hugo" deltaEnabled />);
    expect(screen.getByText('Delta Hugo (2022-2024)')).toBeInTheDocument();
    expect(screen.getByText('-10')).toBeInTheDocument();
  });

  it('omits the delta summary when deltaEnabled is false', () => {
    render(<StatsPanel data={data} candidateYears={candidateYears2022} selectedRegion="all" selectedBairro="all" selectedPair="2022-2024" selectedDeltaMetric="hugo" deltaEnabled={false} />);
    expect(screen.queryByText(/Delta Hugo/)).not.toBeInTheDocument();
  });

  it('excludes null (N/A) deltas from Ganhos/Perdas instead of coercing to 0', () => {
    const dataWithNull = {
      ...data,
      vote_deltas: { features: [
        { properties: { pair: '2022-2024', ano_inicio: 2022, ano_fim: 2024, delta_hugo: null, votos_hugo_inicio: 100, votos_hugo_fim: null } },
        { properties: { pair: '2022-2024', ano_inicio: 2022, ano_fim: 2024, delta_hugo: -30, votos_hugo_inicio: 200, votos_hugo_fim: 170 } },
      ] },
    };
    render(<StatsPanel data={dataWithNull} candidateYears={candidateYears2022} selectedRegion="all" selectedBairro="all" selectedPair="2022-2024" selectedDeltaMetric="hugo" deltaEnabled />);
    // Only the second row (-30) should count toward Perdas.
    expect(screen.getByText('30')).toBeInTheDocument();
    // Inicio must exclude the null row's votos_hugo_inicio (100): 200, not 100+200=300.
    expect(screen.getByText('200')).toBeInTheDocument();
    expect(screen.queryByText('300')).not.toBeInTheDocument();
  });

  it('shows an N/A reason instead of a row of zeros when every feature gates to null', () => {
    const dataAllGated = {
      ...data,
      vote_deltas: { features: [
        { properties: { pair: '2020-2024', ano_inicio: 2020, ano_fim: 2024, delta_hugo: null, votos_hugo_inicio: null, votos_hugo_fim: null, candidacy_status_hugo: 'nao_concorreu' } },
        { properties: { pair: '2020-2024', ano_inicio: 2020, ano_fim: 2024, delta_hugo: null, votos_hugo_inicio: null, votos_hugo_fim: null, candidacy_status_hugo: 'nao_concorreu' } },
      ] },
    };
    render(<StatsPanel data={dataAllGated} candidateYears={{ hugo_leal: 2020, felipe_peixoto: 2020, psd: 2020 }} selectedRegion="all" selectedBairro="all" selectedPair="2020-2024" selectedDeltaMetric="hugo" deltaEnabled />);
    expect(screen.getByText(/N\/A \(nao concorreu\)/)).toBeInTheDocument();
    // no misleading zeros row
    expect(screen.queryByText('Inicio')).not.toBeInTheDocument();
    expect(screen.queryByText('Saldo')).not.toBeInTheDocument();
  });
});
