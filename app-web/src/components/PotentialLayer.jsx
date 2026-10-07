import { CircleMarker, Popup, Tooltip } from 'react-leaflet';
import PotentialPopupContent from './PotentialPopupContent';
import { COLORS } from '../lib/constants';

export default function PotentialLayer({ features }) {
  return (
    <>
      {features.map(f => {
        const p = f.properties;
        const [lng, lat] = f.geometry.coordinates;
        return (
          <CircleMarker
            key={`potential-${p.nr_local}`}
            center={[lat, lng]}
            radius={8}
            pane="markerPane"
            pathOptions={{ fillColor: COLORS.potentialAccent, fillOpacity: 0.75, color: '#5B6472', weight: 1, opacity: 0.95 }}
            eventHandlers={{
              mouseover: (e) => e.target.setStyle({ fillOpacity: 0.95, weight: 2 }),
              mouseout: (e) => e.target.setStyle({ fillOpacity: 0.75, weight: 1 }),
            }}
          >
            <Tooltip permanent direction="center" className="potential-rank-label">{p.rank}</Tooltip>
            <Popup>
              <PotentialPopupContent p={p} />
            </Popup>
          </CircleMarker>
        );
      })}
    </>
  );
}
