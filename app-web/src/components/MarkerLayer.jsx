import { CircleMarker, Popup } from 'react-leaflet';
import PopupContent from './PopupContent';
import { getHeatColor } from '../lib/visual';

// Fixed-size markers, colored by heat class. Size encoding was dropped per
// design: a dot's job here is to carry the heat color, not to double-encode
// vote volume (which the share already captures through the color).
const MARKER_RADIUS = 6;

export default function MarkerLayer({ layerKey, features, breaks, onSelect }) {
  const useIntensity = layerKey === 'hugo_leal' && Array.isArray(breaks) && breaks.length > 0;
  return (
    <>
      {features.map(f => {
        const p = f.properties;
        const [lng, lat] = f.geometry.coordinates;
        const fill = useIntensity ? getHeatColor(p.intensity_pct, breaks) : '#8B4A9C';
        return (
          <CircleMarker
            key={`${layerKey}-${p.nr_local}-${p.ano ?? 'all'}`}
            center={[lat, lng]}
            radius={MARKER_RADIUS}
            pane="markerPane"
            pathOptions={{ fillColor: fill, fillOpacity: 0.9, color: '#5B6472', weight: 1, opacity: 0.8 }}
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
