import { HEAT_PALETTE } from '../lib/visual';

// Relative heat legend. Each local is colored by its share of the strongest
// local that year — so the strongest local reads as 100 %, half-as-strong is
// 50 %, and so on. Five equal 20-point bins give a natural 0 – 100 % scale.

const CLASS_LABELS = [
  '0 – 20 %',
  '20 – 40 %',
  '40 – 60 %',
  '60 – 80 %',
  '80 – 100 %',
];

export default function IntensityLegend({ year }) {
  return (
    <div className="intensity-legend">
      <div className="section-title">Intensidade dos votos</div>
      <div className="intensity-sub">
        votos de Hugo neste local em relação ao local mais forte{year ? ` em ${year}` : ''}
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
