import { HEAT_PALETTE } from '../lib/visual';

// Classed heat legend. Breaks reflect the actual Hugo-share distribution
// across 2010-2026: p50 ~1.1 %, p75 ~2 %, max between 4 % and 10 %. Tight
// bins at the low end (where most locais live) and an open-ended top bin
// so a single standout year doesn't rescale everyone else.

const CLASS_LABELS = [
  'até 0,5 %',
  '0,5 – 1 %',
  '1 – 2 %',
  '2 – 3 %',
  '3 % ou mais',
];

export default function IntensityLegend({ year }) {
  return (
    <div className="intensity-legend">
      <div className="section-title">Intensidade — % dos votos de Hugo</div>
      <div className="intensity-sub">
        parcela do total de votos de Hugo em Niterói{year ? ` (${year})` : ''}
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
