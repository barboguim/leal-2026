import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import GeoFilter from './GeoFilter';

const baseProps = {
  regions: ['Regiao Oceanica', 'Regiao Norte'],
  bairros: ['Icarai', 'Centro'],
  selectedRegion: 'all',
  selectedBairro: 'all',
  onRegionChange: () => {},
  onBairroChange: () => {},
  showRegionBoundaries: true,
  showBairroBoundaries: false,
  onToggleRegionBoundaries: () => {},
  onToggleBairroBoundaries: () => {},
  disabled: false,
};

describe('GeoFilter', () => {
  it('lists all region and bairro options plus an "all" default', () => {
    render(<GeoFilter {...baseProps} />);
    expect(screen.getByText('Todas as regioes')).toBeInTheDocument();
    expect(screen.getByText('Regiao Oceanica')).toBeInTheDocument();
    expect(screen.getByText('Icarai')).toBeInTheDocument();
  });

  it('fires onRegionChange/onBairroChange when a select changes', () => {
    const onRegionChange = vi.fn();
    render(<GeoFilter {...baseProps} onRegionChange={onRegionChange} />);
    fireEvent.change(screen.getByDisplayValue('Todas as regioes'), { target: { value: 'Regiao Norte' } });
    expect(onRegionChange).toHaveBeenCalledWith('Regiao Norte');
  });

  it('reflects the boundary-toggle checkbox state', () => {
    render(<GeoFilter {...baseProps} />);
    expect(screen.getByText('Mostrar limites das regioes').previousSibling).toBeChecked();
    expect(screen.getByText('Mostrar limites dos bairros').previousSibling).not.toBeChecked();
  });

  it('disables both selects when disabled is true', () => {
    render(<GeoFilter {...baseProps} disabled />);
    expect(screen.getByDisplayValue('Todas as regioes')).toBeDisabled();
  });
});
