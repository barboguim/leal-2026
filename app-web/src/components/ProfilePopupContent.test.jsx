import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import ProfilePopupContent from './ProfilePopupContent';

const p = {
  nm_local: 'Escola Teste', bairro: 'Icarai', ano: 2022, nr_local: '1015',
  total_eleitores: 500, pct_mulheres: 55.2,
};

describe('ProfilePopupContent', () => {
  it('renders the local header and the profile breakdown expanded by default', () => {
    render(<ProfilePopupContent p={p} />);
    expect(screen.getByText('Escola Teste')).toBeInTheDocument();
    expect(screen.getByText('Icarai')).toBeInTheDocument();
    expect(screen.getByText('2022')).toBeInTheDocument();
    const details = screen.getByText('Perfil do eleitorado deste local').closest('details');
    expect(details).toHaveAttribute('open');
  });
});
