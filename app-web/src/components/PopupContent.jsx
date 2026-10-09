import CompetitorSection from './CompetitorSection';
import ProfileSection from './ProfileSection';
import { COLORS, LABELS } from '../lib/constants';
import { electionType } from '../lib/format';

function voteShareText(votos, totalValidos) {
  if (votos == null || totalValidos == null || totalValidos === 0) return 'N/A';
  return `${(votos / totalValidos * 100).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`;
}

// Collapse "1,2,3,5,7,8" -> "1–3, 5, 7–8". Same pattern mobi-pleito-2026
// uses for its secao ranges.
function collapseRanges(secoesStrs) {
  if (!secoesStrs || secoesStrs.length === 0) return '';
  const nums = secoesStrs
    .map(s => ({ raw: String(s), n: parseInt(String(s), 10) }))
    .filter(x => Number.isFinite(x.n))
    .sort((a, b) => a.n - b.n);
  if (nums.length === 0) return secoesStrs.join(', ');
  const parts = [];
  let runStart = nums[0];
  let prev = nums[0];
  for (let i = 1; i < nums.length; i++) {
    const cur = nums[i];
    if (cur.n === prev.n + 1) { prev = cur; continue; }
    parts.push(runStart.raw === prev.raw ? runStart.raw : `${runStart.raw}–${prev.raw}`);
    runStart = cur; prev = cur;
  }
  parts.push(runStart.raw === prev.raw ? runStart.raw : `${runStart.raw}–${prev.raw}`);
  return parts.join(', ');
}

function SectionsDetail({ p }) {
  const detail = Array.isArray(p.secoes_detail) ? p.secoes_detail : [];
  if (detail.length === 0) {
    return (
      <div className="popup-row">
        <span className="popup-label">Seções</span>
        <span className="popup-val">{p.n_secoes ?? '—'}</span>
      </div>
    );
  }
  // Group by zona (defensive: a merged local can span zonas). Each row:
  // {zona, secao, votes}. We render the top-level ranges summary + a
  // collapsible per-seção vote list ordered by votes desc.
  const byZona = new Map();
  for (const row of detail) {
    const z = String(row.zona || '');
    if (!byZona.has(z)) byZona.set(z, { rows: [], total: 0 });
    byZona.get(z).rows.push(row);
    byZona.get(z).total += Number(row.votes) || 0;
  }
  return (
    <div className="section-detail">
      {[...byZona.entries()].map(([z, { rows, total }]) => {
        const secoes = rows.map(r => r.secao);
        // Numeric order by seção number — applies to every local, regardless
        // of votes. Easier to scan when the viewer knows the number they're
        // looking for.
        const sortedBySecao = [...rows].sort((a, b) => {
          const na = parseInt(String(a.secao), 10);
          const nb = parseInt(String(b.secao), 10);
          return (Number.isFinite(na) ? na : 0) - (Number.isFinite(nb) ? nb : 0);
        });
        return (
          <div key={z} className="section-detail-zona">
            <div className="section-detail-head">
              Zona {z || '—'} · {rows.length} {rows.length === 1 ? 'seção' : 'seções'} · <strong>{total.toLocaleString('pt-BR')}</strong> votos
            </div>
            <div className="section-detail-ranges">Seções {collapseRanges(secoes)}</div>
            <details className="section-votes-detail">
              <summary>Votos por seção</summary>
              <ul className="section-votes-list">
                {sortedBySecao.map(r => (
                  <li key={r.secao}>
                    <span className="section-votes-secao">Seção {r.secao}</span>
                    <span className="section-votes-count">{(r.votes || 0).toLocaleString('pt-BR')}</span>
                  </li>
                ))}
              </ul>
            </details>
          </div>
        );
      })}
    </div>
  );
}

function parseLineage(json) {
  if (!json) return [];
  try { return JSON.parse(json); } catch { return []; }
}

function sameName(a, b) {
  const norm = (s) => String(s || '').replace(/\s+/g, ' ').trim().toUpperCase();
  const na = norm(a);
  const nb = norm(b);
  return na.length > 0 && na === nb;
}

function LineageBlock({ p, onLineageClick }) {
  const currentName = p.nm_local;
  const recebidasRaw = parseLineage(p.secoes_recebidas);
  const enviadasRaw = parseLineage(p.secoes_enviadas);
  // Drop entries where the "other" local has the same name as this one —
  // that's not a lineage event, it's the same building with a renumbered
  // nr_local. Showing it as "Veio de HILARIO" when the current local IS
  // HILARIO is misleading (mobi-pleito-2026 doesn't do that).
  const recebidas = recebidasRaw.filter(item => !sameName(item.nm_local, currentName));
  const enviadas = enviadasRaw.filter(item => !sameName(item.nm_local, currentName));
  if (recebidas.length === 0 && enviadas.length === 0) return null;
  const prevYear = p.lineage_prev_year;
  const line = (dir) => (item) => {
    const label = item.nm_local || `Local ${item.nr_local}`;
    const clickable = typeof onLineageClick === 'function';
    const nameEl = clickable
      ? (
        <button
          type="button"
          className="lineage-link"
          onClick={(e) => { e.stopPropagation(); onLineageClick(item.nr_zona, item.nr_local); }}
        >{label}</button>
      )
      : <span className="lineage-local">{label}</span>;
    return (
      <li key={`${dir}-${item.nr_zona}-${item.nr_local}`}>
        <div className="lineage-count">
          {dir === 'in' ? 'Veio de' : 'Saiu para'} {nameEl}{' '}
          <span className="lineage-arrow">·</span> {item.count} {item.count === 1 ? 'seção' : 'seções'}
        </div>
        {item.secoes && item.secoes.length > 0 && (
          <div className="lineage-detail">seções {collapseRanges(item.secoes)}</div>
        )}
      </li>
    );
  };
  return (
    <div className="lineage-group">
      <div className="lineage-title">Mudanças de seções{prevYear ? ` desde ${prevYear}` : ''}</div>
      <ul className="lineage-list">
        {recebidas.map(line('in'))}
        {enviadas.map(line('out'))}
      </ul>
    </div>
  );
}

export default function PopupContent({ p, layerKey, onLineageClick }) {
  const hasCompetitors = Boolean(p.top1_nome);
  const hasProfile = Number.isFinite(Number(p.total_eleitores));
  const hasPerformanceShare = Number.isFinite(Number(p.total_votos_validos));

  return (
    <div>
      <div className="popup-eyebrow">LOCAL DE VOTACAO</div>
      <div className="popup-title">{p.nm_local || `Local ${p.nr_local}`}</div>
      <div className="popup-bairro">{p.bairro || ''}</div>
      <div className="popup-row">
        <span className="popup-label">Nome</span>
        <span className="popup-val" style={{ color: COLORS[layerKey] }}>{LABELS[layerKey]}</span>
      </div>
      {p._years ? (
        <>
          {Object.entries(p._years).sort((a, b) => a[0] - b[0]).map(([y, v]) => (
            <div className="popup-row" key={y}>
              <span className="popup-label">{y}</span>
              <span className="popup-val">{v.toLocaleString('pt-BR')}</span>
            </div>
          ))}
          <div className="popup-row" style={{ borderTop: '1px solid var(--color-border)', marginTop: 4, paddingTop: 4 }}>
            <span className="popup-label">Total</span>
            <span className="popup-val">{p.QT_VOTOS.toLocaleString('pt-BR')}</span>
          </div>
        </>
      ) : (
        <>
          {p.cargo && (
            <div className="popup-row"><span className="popup-label">Cargo</span><span className="popup-val">{p.cargo}</span></div>
          )}
          <div className="popup-row"><span className="popup-label">Ano</span><span className="popup-val">{p.ano}</span></div>
          <div className="popup-row"><span className="popup-label">Tipo</span><span className="popup-val">{electionType(p.ano)}</span></div>
          <div className="popup-row"><span className="popup-label">Votos</span><span className="popup-val">{p.QT_VOTOS.toLocaleString('pt-BR')}</span></div>
          {Number.isFinite(Number(p.share_pct)) && (
            <div className="popup-row">
              <span className="popup-label">% dos votos de Hugo</span>
              <span className="popup-val">{Number(p.share_pct).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%</span>
            </div>
          )}
          {Number.isFinite(Number(p.intensity_pct)) && (
            <div className="popup-row">
              <span className="popup-label">Intensidade</span>
              <span className="popup-val">{Number(p.intensity_pct).toLocaleString('pt-BR', { maximumFractionDigits: 0 })}% do local mais forte</span>
            </div>
          )}
          {hasPerformanceShare && (
            <div className="popup-row"><span className="popup-label">% dos votos válidos</span><span className="popup-val">{voteShareText(p.QT_VOTOS, p.total_votos_validos)}</span></div>
          )}
          <SectionsDetail p={p} />
          <LineageBlock p={p} onLineageClick={onLineageClick} />
          {hasCompetitors && <CompetitorSection title="Concorrencia" props={p} />}
          {hasProfile && <ProfileSection props={p} />}
        </>
      )}
    </div>
  );
}
