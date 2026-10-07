import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import CompetitorSection from './CompetitorSection';

describe('CompetitorSection', () => {
  it('renders up to 3 ranked rows with name, party, and votes', () => {
    render(<CompetitorSection title="Concorrencia" props={{
      top1_nome: 'FULANO', top1_partido: 'PSD', top1_votos: 100,
      top2_nome: 'BELTRANO', top2_partido: 'PT', top2_votos: 80,
    }} />);
    expect(screen.getByText('Concorrencia')).toBeInTheDocument();
    expect(screen.getByText(/FULANO \(PSD\) — 100/)).toBeInTheDocument();
    expect(screen.getByText(/BELTRANO \(PT\) — 80/)).toBeInTheDocument();
  });

  it('shows "Sem dados" when no competitor fields are present', () => {
    render(<CompetitorSection title="Concorrencia" props={{}} />);
    expect(screen.getByText('Sem dados')).toBeInTheDocument();
  });

  it('is collapsed by default (a native <details> element)', () => {
    render(<CompetitorSection title="Concorrencia" props={{ top1_nome: 'FULANO', top1_partido: 'PSD', top1_votos: 1 }} />);
    const details = screen.getByText('Concorrencia').closest('details');
    expect(details).not.toHaveAttribute('open');
  });
});
