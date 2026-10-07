import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import PsdBreakdownSection from './PsdBreakdownSection';

describe('PsdBreakdownSection', () => {
  it('renders candidate count and up to 3 ranked entries with cargo and share', () => {
    render(<PsdBreakdownSection props={{
      psd_candidate_count: 3,
      psd_top1_nome: 'FULANO', psd_top1_cargo: 'PREFEITO', psd_top1_votos: 900, psd_top1_share: 45.0,
      psd_top2_nome: 'BELTRANO', psd_top2_cargo: 'VEREADOR', psd_top2_votos: 200, psd_top2_share: 12.5,
    }} />);
    expect(screen.getByText('Composicao PSD')).toBeInTheDocument();
    expect(screen.getByText(/3 candidatos/)).toBeInTheDocument();
    expect(screen.getByText(/FULANO \(PREFEITO\) — 900 — 45% do PSD no cargo/)).toBeInTheDocument();
    expect(screen.getByText(/BELTRANO \(VEREADOR\) — 200 — 12,5% do PSD no cargo/)).toBeInTheDocument();
  });

  it('renders the psd_total_por_cargo breakdown when present', () => {
    render(<PsdBreakdownSection props={{
      psd_candidate_count: 2,
      psd_top1_nome: 'FULANO', psd_top1_cargo: 'PREFEITO', psd_top1_votos: 900, psd_top1_share: 100,
      psd_total_por_cargo: JSON.stringify({ PREFEITO: 900, VEREADOR: 250 }),
    }} />);
    expect(screen.getByText('PREFEITO')).toBeInTheDocument();
    expect(screen.getByText('900 votos')).toBeInTheDocument();
    expect(screen.getByText('VEREADOR')).toBeInTheDocument();
    expect(screen.getByText('250 votos')).toBeInTheDocument();
  });

  it('renders no total-por-cargo rows when the field is absent', () => {
    render(<PsdBreakdownSection props={{
      psd_candidate_count: 1,
      psd_top1_nome: 'FULANO', psd_top1_cargo: 'PREFEITO', psd_top1_votos: 900, psd_top1_share: 100,
    }} />);
    expect(screen.queryByText('Total PSD por cargo')).not.toBeInTheDocument();
  });

  it('shows "Sem dados" when no breakdown fields are present', () => {
    render(<PsdBreakdownSection props={{}} />);
    expect(screen.getByText('Sem dados')).toBeInTheDocument();
  });

  it('is collapsed by default (a native <details> element)', () => {
    render(<PsdBreakdownSection props={{ psd_candidate_count: 1, psd_top1_nome: 'X', psd_top1_cargo: 'VEREADOR', psd_top1_votos: 10, psd_top1_share: 1 }} />);
    const details = screen.getByText('Composicao PSD').closest('details');
    expect(details).not.toHaveAttribute('open');
  });
});
