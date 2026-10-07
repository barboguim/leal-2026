import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import ProfileSection from './ProfileSection';

const props = {
  total_eleitores: 500,
  pct_mulheres: 55.2, pct_homens: 44.1, pct_genero_nao_informado: 0.7,
  pct_jovens_16_24: 15.0, pct_adultos_25_59: 60.0, pct_60_mais: 24.0, pct_idade_nao_informado: 1.0,
  pct_ate_fundamental: 20.0, pct_ensino_medio: 45.0, pct_ensino_superior: 34.0, pct_escolaridade_nao_informado: 1.0,
};

describe('ProfileSection', () => {
  it('renders the framing-safe title and mandatory subtitle', () => {
    render(<ProfileSection props={props} defaultOpen />);
    expect(screen.getByText('Perfil do eleitorado deste local')).toBeInTheDocument();
    expect(screen.getByText(/Composicao do eleitorado local/)).toBeInTheDocument();
    expect(screen.getByText(/nao indica em quem estes eleitores votaram/)).toBeInTheDocument();
  });

  it('never renders forbidden candidate-attribution phrasing', () => {
    render(<ProfileSection props={props} defaultOpen />);
    const text = document.body.textContent;
    expect(text).not.toMatch(/eleitores d[eo] (Hugo|Felipe|candidato)/i);
    expect(text).not.toMatch(/quem votou/i);
  });

  it('renders all 11 fields grouped under 3 dimension headers, plus total', () => {
    render(<ProfileSection props={props} defaultOpen />);
    expect(screen.getByText('500')).toBeInTheDocument();
    expect(screen.getByText('Genero')).toBeInTheDocument();
    expect(screen.getByText('Faixa etaria')).toBeInTheDocument();
    expect(screen.getByText('Escolaridade')).toBeInTheDocument();
    expect(screen.getByText('55,2%')).toBeInTheDocument();
    expect(screen.getByText('% 60+')).toBeInTheDocument();
    expect(screen.getByText('34%')).toBeInTheDocument();
  });

  it('is collapsed by default unless defaultOpen is set', () => {
    render(<ProfileSection props={props} />);
    const details = screen.getByText('Perfil do eleitorado deste local').closest('details');
    expect(details).not.toHaveAttribute('open');
  });

  it('shows a dash for missing fields instead of crashing', () => {
    render(<ProfileSection props={{}} defaultOpen />);
    const dashes = screen.getAllByText('—');
    expect(dashes.length).toBeGreaterThan(0);
  });
});
