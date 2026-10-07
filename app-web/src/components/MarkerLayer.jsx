import { CircleMarker, Popup } from 'react-leaflet';
import PopupContent from './PopupContent';
import { getHeatColor } from '../lib/visual';

// Fixed-size markers, colored by heat class. Zero-vote locais render as
// smaller hollow circles — same roster, no Hugo signal — so the user sees
// the full set of polling places and the Hugo-free ones read as 'quiet'.
const MARKER_RADIUS = 6;
const ZERO_MARKER_RADIUS = 3;

export default function MarkerLayer({ layerKey, features, breaks, onSelect }) {
  const useIntensity = layerKey === 'hugo_leal' && Array.isArray(breaks) && breaks.length > 0;
  return (
    <>
      {features.map(f => {
        const p = f.properties;
        const [lng, lat] = f.geometry.coordinates;
        const isZero = Boolean(p.is_zero);
        const fill = isZero ? '#ffffff' : (useIntensity ? getHeatColor(p.intensity_pct, breaks) : '#8B4A9C');
        const stroke = isZero ? '#a59f97' : '#5B6472';
        const radius = isZero ? ZERO_MARKER_RADIUS : MARKER_RADIUS;
        return (
          <CircleMarker
            key={`${layerKey}-${p.nr_local}-${p.ano ?? 'all'}${isZero ? '-z' : ''}`}
            center={[lat, lng]}
            radius={radius}
            pane="markerPane"
            pathOptions={{
              fillColor: fill,
              fillOpacity: isZero ? 0.4 : 0.9,
              color: stroke,
              weight: 1,
              opacity: isZero ? 0.6 : 0.8,
            }}
            eventHandlers={{
              mouseover: (e) => e.target.setStyle({ weight: 2 }),
              mouseout: (e) => e.target.setStyle({ weight: 1 }),
              click: () => onSelect?.(p, f.geometry.coordinates),
            }}
          >
            <Popup>
              <PopupContent p={p} layerKey={layerKey} />
            </Popup>
          </CircleMarker>
        );
      })}
    </>
  );
}
