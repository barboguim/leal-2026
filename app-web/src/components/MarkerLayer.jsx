import { CircleMarker, Popup } from 'react-leaflet';
import PopupContent from './PopupContent';
import { COLORS } from '../lib/constants';
import { getRadius } from '../lib/visual';

export default function MarkerLayer({ layerKey, features, onSelect }) {
  return (
    <>
      {features.map(f => {
        const p = f.properties;
        const [lng, lat] = f.geometry.coordinates;
        return (
          <CircleMarker
            key={`${layerKey}-${p.nr_local}-${p.ano ?? 'all'}`}
            center={[lat, lng]}
            radius={getRadius(p.QT_VOTOS, layerKey)}
            pane="markerPane"
            pathOptions={{ fillColor: COLORS[layerKey], fillOpacity: 0.55, color: COLORS[layerKey], weight: 1, opacity: 0.8 }}
            eventHandlers={{
              mouseover: (e) => e.target.setStyle({ fillOpacity: 0.85, weight: 2 }),
              mouseout: (e) => e.target.setStyle({ fillOpacity: 0.55, weight: 1 }),
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
