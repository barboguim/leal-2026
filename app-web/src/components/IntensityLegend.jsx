import { HEAT_PALETTE } from '../lib/visual';

// Classed heat-map legend. Each row = one class with its lower bound and the
// swatch color. The upper bound of the last class is maxShare; between-class
// edges come from the quantile breaks. Format: "0.00% – 0.08%" style ranges.

function fmt(pct) {
  if (!Number.isFinite(pct)) return '—';
  return `${pct.toFixed(pct >= 1 ? 1 : 2)}%`;
}

export default function IntensityLegend({ breaks, maxShare, year }) {
  if (!breaks || breaks.length === 0) return null;
  // Build bin edges: [0, b1, b2, b3, b4, maxShare]
  const edges = [0, ...breaks, Math.max(maxShare, breaks[breaks.length - 1])];
  return (
    <div className="intensity-legend">
      <div className="section-title">Intensidade % dos votos</div>
      <div className="intensity-sub">
        quintis sobre os votos de Hugo em {year ?? 'cada ano'}
      </div>
      <ul className="intensity-classes">
        {HEAT_PALETTE.map((color, i) => {
          const lo = edges[i];
          const hi = edges[i + 1];
          return (
            <li key={i} className="intensity-class">
              <span className="intensity-swatch" style={{ background: color }} />
              <span className="intensity-range">{fmt(lo)} – {fmt(hi)}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
