import CompetitorSection from './CompetitorSection';
import { formatSigned, formatPct, electionPairLabel, STATUS_LABELS } from '../lib/format';
import { COMPETITOR_LAYER_BY_METRIC } from '../lib/constants';

function PopupRow({ label, value, color }) {
  return (
    <div className="popup-row">
      <span className="popup-label">{label}</span>
      <span className="popup-val" style={color ? { color } : undefined}>{value}</span>
    </div>
  );
}

function candidateSummary(inicio, fim, delta, status, cargoDiferente) {
  if (delta == null) {
    const reason = STATUS_LABELS[status] || 'sem dados';
    return `N/A (${reason})`;
  }
  const cargoNote = cargoDiferente ? ' (cargo diferente)' : '';
  return `${inicio} -> ${fim} (${formatSigned(delta)})${cargoNote}`;
}

export default function DeltaPopupContent({ p, metric, color, selectedDeltaMetric, findYearLocalFeature }) {
  const moved = (Number(p.secoes_movidas_in) || 0) + (Number(p.secoes_movidas_out) || 0);
  const competitorLayer = COMPETITOR_LAYER_BY_METRIC[selectedDeltaMetric];
  const startFeat = competitorLayer ? findYearLocalFeature(competitorLayer, p.ano_inicio, p.nr_local) : null;
  const endFeat = competitorLayer ? findYearLocalFeature(competitorLayer, p.ano_fim, p.nr_local) : null;
  const primaryValue = p[metric.field] == null
    ? `N/A (${STATUS_LABELS[p[`candidacy_status_${selectedDeltaMetric}`]] || 'sem dados'})`
    : formatSigned(p[metric.field]);

  return (
    <div>
      <div className="popup-eyebrow">COMPARACAO ELEITORAL</div>
      <div className="popup-title">{p.nm_local || `Local ${p.nr_local}`}</div>
      <div className="popup-bairro">{p.bairro || ''}</div>
      <PopupRow label="Par" value={p.pair} />
      <PopupRow label="Tipo de eleicao" value={p.tipo_par || electionPairLabel(p.ano_inicio, p.ano_fim)} />
      <PopupRow label={`Delta ${metric.label}`} value={primaryValue} color={p[metric.field] == null ? undefined : color} />
      <PopupRow label="Hugo" value={candidateSummary(p.votos_hugo_inicio, p.votos_hugo_fim, p.delta_hugo, p.candidacy_status_hugo, p.cargo_diferente_hugo)} />
      <PopupRow label="Secoes" value={`${p.secoes_inicio || 0} -> ${p.secoes_fim || 0}`} />
      <PopupRow label="Troca de secoes" value={formatPct((Number(p.secao_churn) || 0) * 100)} />
      {moved > 0 && <PopupRow label="Secoes com troca" value={`+${p.secoes_movidas_in || 0} / -${p.secoes_movidas_out || 0}`} />}
      {competitorLayer && (
        <>
          <CompetitorSection title={`Concorrencia ${p.ano_inicio}`} props={startFeat ? startFeat.properties : {}} />
          <CompetitorSection title={`Concorrencia ${p.ano_fim}`} props={endFeat ? endFeat.properties : {}} />
        </>
      )}
    </div>
  );
}
