import { CircleMarker, Popup } from 'react-leaflet';
import ProfilePopupContent from './ProfilePopupContent';
import { getSequentialColor } from '../lib/visual';

export default function ProfileLayer({ features, metric }) {
  const values = features
    .map(f => f.properties[metric.field])
    .filter(v => v !== null && v !== undefined)
    .map(Number);
  const min = values.length ? Math.min(...values) : 0;
  const max = values.length ? Math.max(...values) : 100;

  return (
    <>
      {features.map(f => {
        const p = f.properties;
        const [lng, lat] = f.geometry.coordinates;
        const pct = p[metric.field];
        if (pct === null || pct === undefined) return null;
        const color = getSequentialColor(pct, min, max);

        return (
          <CircleMarker
            key={`profile-${p.nr_local}-${p.ano}`}
            center={[lat, lng]}
            radius={6}
            pane="markerPane"
            // stroke stays a fixed neutral (matches --color-text-muted) so low-concentration
            // markers (near-white fill) stay visible against the light basemap
            pathOptions={{ fillColor: color, fillOpacity: 0.78, color: '#5B6472', weight: 1, opacity: 0.95 }}
            eventHandlers={{
              mouseover: (e) => e.target.setStyle({ fillOpacity: 0.95, weight: 2 }),
              mouseout: (e) => e.target.setStyle({ fillOpacity: 0.78, weight: 1 }),
            }}
          >
            <Popup>
              <ProfilePopupContent p={p} />
            </Popup>
          </CircleMarker>
        );
      })}
    </>
  );
}
