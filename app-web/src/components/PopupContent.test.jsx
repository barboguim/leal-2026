import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import PopupContent from './PopupContent';

const hugoProps = {
  nm_local: 'Escola Teste', bairro: 'Icarai', ano: 2022, QT_VOTOS: 50, n_secoes: 3,
  cargo: 'DEPUTADO FEDERAL', total_votos_validos: 1000,
};

describe('PopupContent', () => {
  it('renders Nome, Partido, Cargo pretendido, Votos, and % share for hugo_leal', () => {
    render(<PopupContent p={hugoProps} layerKey="hugo_leal" />);
    expect(screen.getByText('Escola Teste')).toBeInTheDocument();
    expect(screen.getByText('Icarai')).toBeInTheDocument();
    expect(screen.getByText('Hugo Leal')).toBeInTheDocument();
    expect(screen.getByText('DEPUTADO FEDERAL')).toBeInTheDocument();
    expect(screen.getByText('50')).toBeInTheDocument();
    expect(screen.getByText('5,0%')).toBeInTheDocument(); // 50/1000
  });

  it('shows the competitor section for hugo_leal and felipe_peixoto', () => {
    render(<PopupContent p={hugoProps} layerKey="hugo_leal" />);
    expect(screen.getByText('Concorrencia')).toBeInTheDocument();
  });

  it('hides the competitor section for psd and keeps the original field shape (no Cargo pretendido, no % share)', () => {
    const psdProps = { nm_local: 'Escola Teste', bairro: 'Icarai', ano: 2022, QT_VOTOS: 500, n_secoes: 3 };
    render(<PopupContent p={psdProps} layerKey="psd" />);
    expect(screen.queryByText('Concorrencia')).not.toBeInTheDocument();
    expect(screen.queryByText('Cargo pretendido')).not.toBeInTheDocument();
    expect(screen.queryByText('% share')).not.toBeInTheDocument();
  });

  it('shows N/A instead of a vote share when total_votos_validos is missing', () => {
    const propsNoTotal = { ...hugoProps, total_votos_validos: null };
    render(<PopupContent p={propsNoTotal} layerKey="hugo_leal" />);
    expect(screen.getByText('N/A')).toBeInTheDocument();
  });

  it('hides the competitor section in aggregated ("Todos" years) mode, showing a yearly breakdown instead', () => {
    const aggregated = { ...hugoProps, _years: { 2018: 20, 2022: 30 }, QT_VOTOS: 50 };
    render(<PopupContent p={aggregated} layerKey="hugo_leal" />);
    expect(screen.queryByText('Concorrencia')).not.toBeInTheDocument();
    expect(screen.getByText('2018')).toBeInTheDocument();
    expect(screen.getByText('20')).toBeInTheDocument();
    expect(screen.getByText('Total')).toBeInTheDocument();
  });

  it('never shows the demographic profile section in aggregated ("Todos" years) mode, even when stray pct_*/total_eleitores properties are present', () => {
    // aggregateByLocal spreads the first feature's properties onto the
    // aggregated object, so pct_mulheres/total_eleitores can technically be
    // present here — the _years branch must still never render
    // ProfileSection, since profile data has no clean cross-year
    // aggregation semantics.
    const aggregated = { ...hugoProps, _years: { 2018: 20, 2022: 30 }, QT_VOTOS: 50, pct_mulheres: 55.2, total_eleitores: 500 };
    render(<PopupContent p={aggregated} layerKey="hugo_leal" />);
    expect(screen.queryByText('Perfil do eleitorado deste local')).not.toBeInTheDocument();
  });

  it('renders the demographic profile section on hugo_leal, felipe_peixoto, and psd popups alike', () => {
    const withProfile = { ...hugoProps, total_eleitores: 500, pct_mulheres: 55.2 };
    const { rerender } = render(<PopupContent p={withProfile} layerKey="hugo_leal" />);
    expect(screen.getByText('Perfil do eleitorado deste local')).toBeInTheDocument();

    rerender(<PopupContent p={withProfile} layerKey="felipe_peixoto" />);
    expect(screen.getByText('Perfil do eleitorado deste local')).toBeInTheDocument();

    const psdProps = { nm_local: 'Escola Teste', bairro: 'Icarai', ano: 2022, QT_VOTOS: 500, n_secoes: 3, total_eleitores: 500, pct_mulheres: 55.2 };
    rerender(<PopupContent p={psdProps} layerKey="psd" />);
    expect(screen.getByText('Perfil do eleitorado deste local')).toBeInTheDocument();
  });
});
