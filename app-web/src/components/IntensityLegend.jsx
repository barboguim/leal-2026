// Legend for the Hugo marker intensity scale. The scale is "share of Hugo's
// votes at this local as a fraction of his Niteroi total for the year" — so
// 0% means the local contributed nothing, and higher % means more of his base
// lives there. Deliberately a distribution share, not a performance share:
// performance share needs total_votos_validos per local (script 07, not yet
// re-run for 2026).

export default function IntensityLegend({ maxShare, year }) {
  if (!Number.isFinite(maxShare) || maxShare <= 0) return null;
  return (
    <div className="intensity-legend">
      <div className="intensity-legend-title">
        Intensidade — % dos votos de Hugo neste local{year ? ` (${year})` : ''}
      </div>
      <div className="intensity-legend-row">
        <span className="intensity-legend-tick">0%</span>
        <span className="intensity-scale" />
        <span className="intensity-legend-tick">{maxShare.toFixed(1)}%</span>
      </div>
    </div>
  );
}
