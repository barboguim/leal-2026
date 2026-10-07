import { HEAT_PALETTE } from '../lib/visual';

// Fixed-interval heat legend. Classes are 0-1%, 1-2%, 2-3%, 3-4%, 4%+ — the
// same bins the markers use. Metric is Hugo's share of valid Dep. Fed. votes
// at the local; across cycles 2010-2026 observed max is ~4.7%, so these five
// 1-point bins cover the full range with round, legible edges.

const CLASS_LABELS = [
  '0 – 1 %',
  '1 – 2 %',
  '2 – 3 %',
  '3 – 4 %',
  '4 % ou mais',
];

export default function IntensityLegend({ year }) {
  return (
    <div className="intensity-legend">
      <div className="section-title">Intensidade — % dos votos válidos</div>
      <div className="intensity-sub">
        votos de Hugo sobre o total válido para Deputado Federal no local{year ? ` (${year})` : ''}
      </div>
      <ul className="intensity-classes">
        {HEAT_PALETTE.map((color, i) => (
          <li key={i} className="intensity-class">
            <span className="intensity-swatch" style={{ background: color }} />
            <span className="intensity-range">{CLASS_LABELS[i]}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
