import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { MapContainer } from 'react-leaflet';
import MarkerLayer from './MarkerLayer';

const feature = {
  type: 'Feature',
  geometry: { type: 'Point', coordinates: [-43.0783, -22.9017] },
  properties: { nr_local: '1', ano: 2022, QT_VOTOS: 50, n_secoes: 3, nm_local: 'Escola Teste', bairro: 'Icarai' },
};

describe('MarkerLayer', () => {
  it('renders its CircleMarker in the marker pane (not the overlay pane) so it wins click hit-testing over boundary layers', () => {
    const { container } = render(
      <MapContainer center={[-22.9017, -43.0783]} zoom={13}>
        <MarkerLayer layerKey="hugo_leal" features={[feature]} />
      </MapContainer>
    );

    const markerPane = container.querySelector('.leaflet-marker-pane');
    const overlayPane = container.querySelector('.leaflet-overlay-pane');
    const path = container.querySelector('path');

    expect(path).toBeTruthy();
    expect(markerPane.contains(path)).toBe(true);
    expect(overlayPane.contains(path)).toBe(false);
  });
});
