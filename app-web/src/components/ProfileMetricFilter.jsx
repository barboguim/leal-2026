import { useState } from 'react';
import { PROFILE_DIMENSIONS } from '../lib/constants';

export default function ProfileMetricFilter({ selectedMetricId, onChange }) {
  const activeDimension = PROFILE_DIMENSIONS.find(d =>
    d.metrics.some(m => m.id === selectedMetricId)
  ) || PROFILE_DIMENSIONS[0];
  const [openDimensionId, setOpenDimensionId] = useState(activeDimension.id);
  const openDimension = PROFILE_DIMENSIONS.find(d => d.id === openDimensionId) || PROFILE_DIMENSIONS[0];

  return (
    <div>
      <div className="year-bar">
        {PROFILE_DIMENSIONS.map(d => (
          <button
            key={d.id}
            className={'year-btn' + (d.id === openDimensionId ? ' active' : '')}
            onClick={() => setOpenDimensionId(d.id)}
          >
            {d.label}
          </button>
        ))}
      </div>
      <div className="year-bar">
        {openDimension.metrics.filter(m => m.mapMetric !== false).map(m => (
          <button
            key={m.id}
            className={'year-btn' + (m.id === selectedMetricId ? ' active' : '')}
            onClick={() => onChange(m.id)}
          >
            {m.label}
          </button>
        ))}
      </div>
    </div>
  );
}
