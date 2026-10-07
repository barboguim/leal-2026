import { CircleMarker, Popup } from 'react-leaflet';
import PopupContent from './PopupContent';
import { COLORS } from '../lib/constants';
import { getRadius, getHugoIntensityColor } from '../lib/visual';

export default function MarkerLayer({ layerKey, features, maxShare, onSelect }) {
  const useIntensity = layerKey === 'hugo_leal' && Number.isFinite(maxShare) && maxShare > 0;
  return (
    <>
      {features.map(f => {
        const p = f.properties;
        const [lng, lat] = f.geometry.coordinates;
        const fill = useIntensity
          ? getHugoIntensityColor(p.share_pct, maxShare)
          : COLORS[layerKey];
        // Keep the ring in the brand color so the marker reads as "Hugo" even
        // at the lightest fill — otherwise low-share markers vanish.
        const stroke = COLORS[layerKey];
        return (
          <CircleMarker
            key={`${layerKey}-${p.nr_local}-${p.ano ?? 'all'}`}
            center={[lat, lng]}
            radius={getRadius(p.QT_VOTOS, layerKey)}
            pane="markerPane"
            pathOptions={{ fillColor: fill, fillOpacity: 0.85, color: stroke, weight: 1, opacity: 0.8 }}
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
