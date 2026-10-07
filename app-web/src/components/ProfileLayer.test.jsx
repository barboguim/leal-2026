import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { MapContainer } from 'react-leaflet';
import ProfileLayer from './ProfileLayer';
import { PROFILE_METRICS } from '../lib/constants';

const feature = (nrLocal, pct) => ({
  type: 'Feature',
  geometry: { type: 'Point', coordinates: [-43.0783, -22.9017] },
  properties: { nr_local: nrLocal, ano: 2022, pct_mulheres: pct, nm_local: 'Escola Teste', bairro: 'Icarai', total_eleitores: 100 },
});

describe('ProfileLayer', () => {
  it('renders one marker per feature for the selected metric', () => {
    const features = [feature('1', 55), feature('2', 40)];
    const { container } = render(
      <MapContainer center={[-22.9017, -43.0783]} zoom={13}>
        <ProfileLayer features={features} metric={PROFILE_METRICS.mulheres} />
      </MapContainer>
    );
    const paths = container.querySelectorAll('.leaflet-marker-pane path');
    expect(paths.length).toBe(2);
  });

  it('skips a feature whose selected metric is null', () => {
    const features = [feature('1', null), feature('2', 40)];
    const { container } = render(
      <MapContainer center={[-22.9017, -43.0783]} zoom={13}>
        <ProfileLayer features={features} metric={PROFILE_METRICS.mulheres} />
      </MapContainer>
    );
    const paths = container.querySelectorAll('.leaflet-marker-pane path');
    expect(paths.length).toBe(1);
  });
});
