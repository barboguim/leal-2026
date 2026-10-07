import { CircleMarker, Popup } from 'react-leaflet';
import DeltaPopupContent from './DeltaPopupContent';
import { getDivergingColor, getDeltaRadius } from '../lib/visual';
import { findYearLocalFeature } from '../lib/findFeature';

export default function DeltaLayer({ features, metric, selectedDeltaMetric, data }) {
  const gatedFeatures = features.filter(f => f.properties[metric.field] !== null && f.properties[metric.field] !== undefined);
  const maxAbs = Math.max(1, ...gatedFeatures.map(f => Math.abs(Number(f.properties[metric.field]))));

  return (
    <>
      {gatedFeatures.map(f => {
        const p = f.properties;
        const [lng, lat] = f.geometry.coordinates;
        const delta = Number(p[metric.field]) || 0;
        const color = getDivergingColor(delta, maxAbs);

        return (
          <CircleMarker
            key={`delta-${p.nr_local}-${p.pair}`}
            center={[lat, lng]}
            radius={getDeltaRadius(delta)}
            pane="markerPane"
            // stroke stays a fixed neutral (matches --color-text-muted) so low-magnitude
            // markers (near-white fill) stay visible against the light basemap
            pathOptions={{ fillColor: color, fillOpacity: 0.78, color: '#5B6472', weight: delta === 0 ? 1 : 2, opacity: 0.95 }}
            eventHandlers={{
              mouseover: (e) => e.target.setStyle({ fillOpacity: 0.95, weight: 3 }),
              mouseout: (e) => e.target.setStyle({ fillOpacity: 0.78, weight: delta === 0 ? 1 : 2 }),
            }}
          >
            <Popup>
              <DeltaPopupContent
                p={p}
                metric={metric}
                color={color}
                selectedDeltaMetric={selectedDeltaMetric}
                findYearLocalFeature={(layerKey, ano, nrLocal) => findYearLocalFeature(data, layerKey, ano, nrLocal)}
              />
            </Popup>
          </CircleMarker>
        );
      })}
    </>
  );
}
