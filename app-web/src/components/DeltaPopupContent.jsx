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

function sameName(a, b) {
  const norm = (s) => String(s || '').replace(/\s+/g, ' ').trim().toUpperCase();
  const na = norm(a);
  const nb = norm(b);
  return na.length > 0 && na === nb;
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

// Collapse a sorted list of secao numbers into run-length ranges for display:
// ["1","2","3","7","9","10"] -> "1–3, 7, 9–10". Matches mobi-pleito-2026's
// collapse_ranges util. Operates on strings because leading zeros matter in
// TSE's secao numbering (we preserve them verbatim).
function collapseRanges(sections) {
  if (!sections || sections.length === 0) return '';
  const nums = sections.map(s => ({ raw: s, n: parseInt(s, 10) })).filter(x => Number.isFinite(x.n));
  if (nums.length === 0) return sections.join(', ');
  nums.sort((a, b) => a.n - b.n);
  const parts = [];
  let runStart = nums[0];
  let prev = nums[0];
  for (let i = 1; i < nums.length; i++) {
    const cur = nums[i];
    if (cur.n === prev.n + 1) { prev = cur; continue; }
    parts.push(runStart.raw === prev.raw ? runStart.raw : `${runStart.raw}–${prev.raw}`);
    runStart = cur;
    prev = cur;
  }
  parts.push(runStart.raw === prev.raw ? runStart.raw : `${runStart.raw}–${prev.raw}`);
  return parts.join(', ');
}

function parseLineage(json) {
  if (!json) return [];
  try { return JSON.parse(json); } catch { return []; }
}

function LineageList({ title, items }) {
  if (!items || items.length === 0) return null;
  return (
    <div className="lineage-group">
      <div className="lineage-title">{title}</div>
      <ul className="lineage-list">
        {items.map((it, i) => (
          <li key={i}>
            <div className="lineage-count">
              {it.count} {it.count === 1 ? 'seção' : 'seções'}
              <span className="lineage-arrow"> · </span>
              <span className="lineage-local">{it.nm_local || `Local ${it.nr_local}`}</span>
            </div>
            {it.secoes && it.secoes.length > 0 && (
              <div className="lineage-detail">seções {collapseRanges(it.secoes)}</div>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

function SectionsBlock({ p }) {
  const inicio = Number(p.secoes_inicio) || 0;
  const fim = Number(p.secoes_fim) || 0;
  if (inicio === 0 && fim === 0) return null;

  const mantidas = Number(p.secoes_comuns) || 0;
  const novas = Number(p.secoes_adicionadas) || 0;
  const removidas = Number(p.secoes_removidas) || 0;

  const currentName = p.nm_local;
  const recebidas = parseLineage(p.secoes_recebidas).filter(it => !sameName(it.nm_local, currentName));
  const enviadas = parseLineage(p.secoes_enviadas).filter(it => !sameName(it.nm_local, currentName));

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
      <LineageList title={`Vieram para cá em ${p.ano_fim}`} items={recebidas} />
      <LineageList title={`Saíram deste local em ${p.ano_fim}`} items={enviadas} />
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
