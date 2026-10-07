import CompetitorSection from './CompetitorSection';
import ProfileSection from './ProfileSection';
import { COLORS, LABELS } from '../lib/constants';
import { electionType } from '../lib/format';

function voteShareText(votos, totalValidos) {
  if (votos == null || totalValidos == null || totalValidos === 0) return 'N/A';
  return `${(votos / totalValidos * 100).toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })}%`;
}

export default function PopupContent({ p, layerKey }) {
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
          {hasPerformanceShare && (
            <div className="popup-row"><span className="popup-label">% dos votos válidos</span><span className="popup-val">{voteShareText(p.QT_VOTOS, p.total_votos_validos)}</span></div>
          )}
          <div className="popup-row"><span className="popup-label">Secoes</span><span className="popup-val">{p.n_secoes ?? '—'}</span></div>
          {hasCompetitors && <CompetitorSection title="Concorrencia" props={p} />}
          {hasProfile && <ProfileSection props={p} />}
        </>
      )}
    </div>
  );
}
