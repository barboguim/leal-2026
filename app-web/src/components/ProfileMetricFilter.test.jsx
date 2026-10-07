import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import ProfileMetricFilter from './ProfileMetricFilter';

describe('ProfileMetricFilter', () => {
  it('shows only map-selectable metrics for the open Genero dimension, not "% Nao informado"', () => {
    render(<ProfileMetricFilter selectedMetricId="mulheres" onChange={() => {}} />);
    expect(screen.getByText('% Mulheres')).toBeInTheDocument();
    expect(screen.getByText('% Homens')).toBeInTheDocument();
    expect(screen.queryByText('% Nao informado')).not.toBeInTheDocument();
  });

  it('still renders all three dimension buttons, including ones whose nao-informado metric is gated out', () => {
    render(<ProfileMetricFilter selectedMetricId="mulheres" onChange={() => {}} />);
    expect(screen.getByText('Genero')).toBeInTheDocument();
    expect(screen.getByText('Faixa etaria')).toBeInTheDocument();
    expect(screen.getByText('Escolaridade')).toBeInTheDocument();
  });
});
