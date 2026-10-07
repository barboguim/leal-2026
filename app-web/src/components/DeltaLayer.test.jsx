import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { MapContainer } from 'react-leaflet';
import DeltaLayer from './DeltaLayer';
import { DELTA_METRICS } from '../lib/constants';

const feature = {
  type: 'Feature',
  geometry: { type: 'Point', coordinates: [-43.0783, -22.9017] },
  properties: { nr_local: '1', pair: '2022-2024', delta_hugo: 12, nm_local: 'Escola Teste', bairro: 'Icarai' },
};

describe('DeltaLayer', () => {
  it('renders its CircleMarker in the marker pane (not the overlay pane) so it wins click hit-testing over boundary layers', () => {
    const { container } = render(
      <MapContainer center={[-22.9017, -43.0783]} zoom={13}>
        <DeltaLayer features={[feature]} metric={DELTA_METRICS.hugo} selectedDeltaMetric="hugo" data={{}} />
      </MapContainer>
    );

    const markerPane = container.querySelector('.leaflet-marker-pane');
    const overlayPane = container.querySelector('.leaflet-overlay-pane');
    const path = container.querySelector('path');

    expect(path).toBeTruthy();
    expect(markerPane.contains(path)).toBe(true);
    expect(overlayPane.contains(path)).toBe(false);
  });

  it('skips rendering a marker for a feature whose selected metric is null (N/A)', () => {
    const features = [
      { type: 'Feature', geometry: { type: 'Point', coordinates: [-43.08, -22.90] }, properties: { nr_local: '1', pair: '2022-2024', delta_hugo: null } },
      { type: 'Feature', geometry: { type: 'Point', coordinates: [-43.07, -22.91] }, properties: { nr_local: '2', pair: '2022-2024', delta_hugo: -10 } },
    ];
    const { container } = render(
      <MapContainer center={[-22.9017, -43.0783]} zoom={13}>
        <DeltaLayer features={features} metric={DELTA_METRICS.hugo} selectedDeltaMetric="hugo" data={{}} />
      </MapContainer>
    );
    const paths = container.querySelectorAll('.leaflet-marker-pane path');
    expect(paths.length).toBe(1);
  });
});
