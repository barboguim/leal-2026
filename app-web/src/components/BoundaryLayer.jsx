import { GeoJSON } from 'react-leaflet';
import { normalizeText, featureName } from '../lib/geo';

export default function BoundaryLayer({ features, selectedName, inactiveColor, opacity, fillOpacity }) {
  const active = normalizeText(selectedName);
  const shown = selectedName === 'all' ? features : features.filter(f => normalizeText(featureName(f)) === active);

  return (
    <GeoJSON
      key={selectedName}
      data={{ type: 'FeatureCollection', features: shown }}
      style={(feature) => ({
        // #1E3A5F matches --color-primary in index.css — a Leaflet path color, can't reference the CSS var directly
        color: normalizeText(featureName(feature)) === active ? '#1E3A5F' : inactiveColor,
        weight: normalizeText(featureName(feature)) === active ? 2 : 1,
        opacity,
        fillOpacity,
      })}
      onEachFeature={(feature, layer) => {
        layer.bindTooltip(featureName(feature), { sticky: true, direction: 'top' });
      }}
    />
  );
}
