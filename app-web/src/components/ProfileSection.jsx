import { PROFILE_DIMENSIONS } from '../lib/constants';

function formatPct(v) {
  if (v === null || v === undefined) return '—';
  return `${Number(v).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`;
}

export default function ProfileSection({ props, defaultOpen = false }) {
  const total = props.total_eleitores;

  return (
    <details className="popup-competitors" open={defaultOpen || undefined}>
      <summary>Perfil do eleitorado deste local</summary>
      <div className="control-note">Composicao do eleitorado local — nao indica em quem estes eleitores votaram.</div>
      <div className="popup-row">
        <span className="popup-label">Total eleitores</span>
        <span className="popup-val">{total != null ? Number(total).toLocaleString('pt-BR') : '—'}</span>
      </div>
      {PROFILE_DIMENSIONS.map(dim => (
        <div key={dim.id}>
          <div className="popup-row" style={{ borderTop: '1px solid var(--color-border)', marginTop: 4, paddingTop: 4 }}>
            <span className="popup-label">{dim.label}</span>
          </div>
          {dim.metrics.map(m => (
            <div className="popup-row" key={m.id}>
              <span className="popup-label">{m.label}</span>
              <span className="popup-val">{formatPct(props[m.field])}</span>
            </div>
          ))}
        </div>
      ))}
    </details>
  );
}
