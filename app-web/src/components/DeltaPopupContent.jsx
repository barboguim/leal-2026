import CompetitorSection from './CompetitorSection';
import { formatSigned, electionPairLabel, STATUS_LABELS } from '../lib/format';
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

// Human-readable section status for the local across the two years.
// local_status comes from scripts/06_build_vote_deltas.py and is one of:
// 'both' / 'start_only' / 'end_only' / 'vote_data_only'.
function localStatusLabel(status, anoInicio, anoFim) {
  if (status === 'start_only') return `Local desapareceu em ${anoFim}`;
  if (status === 'end_only') return `Local novo em ${anoFim}`;
  if (status === 'vote_data_only') return 'Local sem dados cadastrais';
  return `Local ativo em ${anoInicio} e ${anoFim}`;
}

function SectionsBlock({ p }) {
  const inicio = Number(p.secoes_inicio) || 0;
  const fim = Number(p.secoes_fim) || 0;
  if (inicio === 0 && fim === 0) return null;

  const mantidas = Number(p.secoes_comuns) || 0;
  const novas = Number(p.secoes_adicionadas) || 0;
  const removidas = Number(p.secoes_removidas) || 0;
  const movedIn = Number(p.secoes_movidas_in) || 0;
  const movedOut = Number(p.secoes_movidas_out) || 0;

  return (
    <div className="section-block">
      <div className="section-block-title">Seções neste local</div>
      <div className="section-block-note">{localStatusLabel(p.local_status, p.ano_inicio, p.ano_fim)}</div>
      <PopupRow
        label={`${p.ano_inicio} → ${p.ano_fim}`}
        value={`${inicio} → ${fim} seções`}
      />
      {(mantidas || novas || removidas) ? (
        <PopupRow
          label="Composição"
          value={`${mantidas} mantidas · ${novas} novas · ${removidas} removidas`}
        />
      ) : null}
      {(movedIn || movedOut) ? (
        <PopupRow
          label="Movimento"
          value={`+${movedIn} vieram de outro local · ${movedOut} foram para outro`}
        />
      ) : null}
    </div>
  );
}

export default function DeltaPopupContent({ p, metric, color, selectedDeltaMetric, findYearLocalFeature }) {
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
      {competitorLayer && (startFeat?.properties?.top1_nome || endFeat?.properties?.top1_nome) && (
        <>
          <CompetitorSection title={`Concorrencia ${p.ano_inicio}`} props={startFeat ? startFeat.properties : {}} />
          <CompetitorSection title={`Concorrencia ${p.ano_fim}`} props={endFeat ? endFeat.properties : {}} />
        </>
      )}
      <SectionsBlock p={p} />
    </div>
  );
}
