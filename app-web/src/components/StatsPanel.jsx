import { BASE_KEYS, COLORS, LABELS, DELTA_METRICS } from '../lib/constants';
import { electionType, electionPairLabel, formatSigned, STATUS_LABELS } from '../lib/format';
import { passesGeoFilter } from '../lib/geo';

export default function StatsPanel({ data, candidateYears, selectedRegion, selectedBairro, selectedPair, selectedDeltaMetric, deltaEnabled }) {
  const regionLabel = selectedRegion === 'all' ? 'todas as regioes' : selectedRegion;
  const bairroLabel = selectedBairro === 'all' ? 'todos os bairros' : selectedBairro;

  const baseSections = BASE_KEYS.map(key => {
    const fc = data[key];
    if (!fc) return null;
    const year = candidateYears[key];
    const feats = (year ? fc.features.filter(f => f.properties.ano === year) : fc.features)
      .filter(f => passesGeoFilter(f.properties, selectedRegion, selectedBairro));
    if (feats.length === 0) return null;
    const total = feats.reduce((s, f) => s + f.properties.QT_VOTOS, 0);
    const nLocais = new Set(feats.map(f => f.properties.nr_local)).size;
    return { key, total, nLocais, year };
  }).filter(Boolean);

  let deltaSection = null;
  let deltaNaSection = null;
  if (data.vote_deltas && selectedPair && deltaEnabled) {
    const metric = DELTA_METRICS[selectedDeltaMetric];
    const feats = data.vote_deltas.features
      .filter(f => f.properties.pair === selectedPair)
      .filter(f => passesGeoFilter(f.properties, selectedRegion, selectedBairro));
    const gated = feats.filter(f => f.properties[metric.field] !== null && f.properties[metric.field] !== undefined);
    if (gated.length === 0 && feats.length > 0) {
      // Candidate didn't run (or party didn't exist, or type mismatch) for
      // this pair — every feature gates to null, so show why instead of a
      // row of misleading zeros.
      const status = feats[0].properties[`candidacy_status_${selectedDeltaMetric}`];
      deltaNaSection = { metric, reason: STATUS_LABELS[status] || 'sem dados' };
    } else if (gated.length > 0) {
      const startTotal = gated.reduce((s, f) => s + (Number(f.properties[`votos_${selectedDeltaMetric}_inicio`]) || 0), 0);
      const endTotal = gated.reduce((s, f) => s + (Number(f.properties[`votos_${selectedDeltaMetric}_fim`]) || 0), 0);
      const total = gated.reduce((s, f) => s + Number(f.properties[metric.field]), 0);
      const gained = gated.reduce((s, f) => s + Math.max(Number(f.properties[metric.field]), 0), 0);
      const lost = gated.reduce((s, f) => s + Math.max(-Number(f.properties[metric.field]), 0), 0);
      deltaSection = {
        metric, startTotal, endTotal, total, gained, lost,
        anoInicio: feats[0]?.properties.ano_inicio || 0,
        anoFim: feats[0]?.properties.ano_fim || 0,
      };
    }
  }

  return (
    <div id="stats">
      <div style={{ fontWeight: 600, marginBottom: 6 }}>Resumo</div>
      {(selectedRegion !== 'all' || selectedBairro !== 'all') && (
        <div style={{ color: 'var(--color-text-muted)', marginBottom: 6 }}>{regionLabel} / {bairroLabel}</div>
      )}
      {baseSections.map(({ key, total, nLocais, year }) => (
        <div key={key}>
          <div style={{ marginTop: 4 }}>
            <span style={{ color: COLORS[key] }}>{LABELS[key]}</span>
            <span style={{ color: 'var(--color-text-muted)' }}> · {year ? `${year} (${electionType(year)})` : 'todos os anos'}</span>
          </div>
          <div className="popup-row"><span className="popup-label">Votos</span><span className="stat-val">{total.toLocaleString('pt-BR')}</span></div>
          <div className="popup-row"><span className="popup-label">Locais</span><span className="stat-val">{nLocais}</span></div>
        </div>
      ))}
      {deltaSection && (
        <>
          <div style={{ marginTop: 8 }}><span style={{ color: COLORS.deltaGain }}>Delta {deltaSection.metric.label} ({selectedPair})</span></div>
          <div style={{ color: 'var(--color-text-muted)', marginBottom: 6 }}>{electionPairLabel(deltaSection.anoInicio, deltaSection.anoFim)}</div>
          <div className="popup-row"><span className="popup-label">Inicio</span><span className="stat-val">{deltaSection.startTotal.toLocaleString('pt-BR')}</span></div>
          <div className="popup-row"><span className="popup-label">Fim</span><span className="stat-val">{deltaSection.endTotal.toLocaleString('pt-BR')}</span></div>
          <div className="popup-row"><span className="popup-label">Saldo</span><span className="stat-val">{formatSigned(deltaSection.total)}</span></div>
          <div className="popup-row"><span className="popup-label">Ganhos</span><span className="stat-val">{deltaSection.gained.toLocaleString('pt-BR')}</span></div>
          <div className="popup-row"><span className="popup-label">Perdas</span><span className="stat-val">{deltaSection.lost.toLocaleString('pt-BR')}</span></div>
        </>
      )}
      {deltaNaSection && (
        <>
          <div style={{ marginTop: 8 }}><span style={{ color: COLORS.deltaGain }}>Delta {deltaNaSection.metric.label} ({selectedPair})</span></div>
          <div className="control-note">N/A ({deltaNaSection.reason}) — sem dados para exibir no mapa nesta combinacao.</div>
        </>
      )}
    </div>
  );
}
