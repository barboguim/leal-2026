import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MapContainer } from 'react-leaflet';
import PotentialLayer from './PotentialLayer';

const feature = (nrLocal, rank) => ({
  type: 'Feature',
  geometry: { type: 'Point', coordinates: [-43.0783, -22.9017] },
  properties: { nr_local: nrLocal, ano: 2022, rank, pct_share: 0.3, nm_local: 'Escola Teste', bairro: 'Icarai' },
});

describe('PotentialLayer', () => {
  it('renders one marker per feature', () => {
    const features = [feature('1', 1), feature('2', 2)];
    const { container } = render(
      <MapContainer center={[-22.9017, -43.0783]} zoom={13}>
        <PotentialLayer features={features} />
      </MapContainer>
    );
    const paths = container.querySelectorAll('.leaflet-marker-pane path');
    expect(paths.length).toBe(2);
  });

  it('renders no markers for an empty feature list', () => {
    const { container } = render(
      <MapContainer center={[-22.9017, -43.0783]} zoom={13}>
        <PotentialLayer features={[]} />
      </MapContainer>
    );
    const paths = container.querySelectorAll('.leaflet-marker-pane path');
    expect(paths.length).toBe(0);
  });

  it("labels each marker with its rank number, permanently visible on the map", () => {
    const features = [feature('1', 1), feature('2', 7)];
    render(
      <MapContainer center={[-22.9017, -43.0783]} zoom={13}>
        <PotentialLayer features={features} />
      </MapContainer>
    );
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('7')).toBeInTheDocument();
  });
});

describe('PotentialPopupContent framing', () => {
  it('never implies predicted or probable voters', async () => {
    const PotentialPopupContent = (await import('./PotentialPopupContent')).default;
    render(<PotentialPopupContent p={{ nr_local: '1', nm_local: 'Escola Teste', bairro: 'Icarai', rank: 1, pct_share: 0.3 }} />);
    const text = screen.getByText(/similaridade/i).closest('div').textContent;
    expect(text).not.toMatch(/eleitores? d[eo] Hugo|provave|potencial eleitor/i);
  });

  it('shows which fields drive the rank when maior_semelhanca is present', async () => {
    const PotentialPopupContent = (await import('./PotentialPopupContent')).default;
    render(<PotentialPopupContent p={{ nr_local: '1', nm_local: 'Escola Teste', bairro: 'Icarai', rank: 1, pct_share: 0.3, maior_semelhanca: '% Mulheres, % Ensino Superior' }} />);
    expect(screen.getByText('Maior semelhanca em')).toBeInTheDocument();
    expect(screen.getByText('% Mulheres, % Ensino Superior')).toBeInTheDocument();
  });

  it('omits the row when maior_semelhanca is absent, instead of showing blank', async () => {
    const PotentialPopupContent = (await import('./PotentialPopupContent')).default;
    render(<PotentialPopupContent p={{ nr_local: '1', nm_local: 'Escola Teste', bairro: 'Icarai', rank: 1, pct_share: 0.3 }} />);
    expect(screen.queryByText('Maior semelhanca em')).not.toBeInTheDocument();
  });
});
