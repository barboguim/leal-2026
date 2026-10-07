import { COLORS } from '../lib/constants';
import { formatSigned } from '../lib/format';
import EyeToggle from './EyeToggle.jsx';

// Sidebar group: "Comparativo" — pick a pair of years, see the delta map.
// Count = Hugo's net delta for the selected pair. Below the chips: a Resumo
// block with Inicio / Fim / Saldo / Ganhos / Perdas. This absorbs what the
// standalone StatsPanel used to be — the user wanted the summary under
// Comparativo, not as a free-floating section.

export default function ComparativoLayer({
  visible, onToggleVisible,
  pairs, selectedPair, onSelectPair,
  pairMeta,
  deltaTotal, startTotal, endTotal, gained, lost,
  anoInicio, anoFim,
}) {
  return (
    <details className={'group' + (visible ? '' : ' is-hidden')} open>
      <summary className="group-row">
        <EyeToggle visible={visible} onToggle={onToggleVisible} label="Comparativo" />
        <span className="dot" style={{ background: COLORS.deltaGain }} />
        <span className="group-label">Comparativo</span>
      </summary>

      <div className="group-body">
        {pairs.length === 0 && (
          <div className="control-note">nenhum par disponivel</div>
        )}
        {pairs.length > 0 && (
          <div className="delta-pair-list">
            {pairs.map(pair => (
              <button
                key={pair}
                type="button"
                className={'delta-pair-chip' + (pair === selectedPair ? ' active' : '')}
                onClick={() => onSelectPair(pair)}
              >
                {pair}
              </button>
            ))}
          </div>
        )}
        {pairMeta && (
          <div className="delta-pair-context">
            <span>{pairMeta.tipo_par}</span>
            {pairMeta.cargoDiferente && <span className="delta-pair-warning">cargo diferente</span>}
          </div>
        )}
        <div className="delta-legend">
          <span>perdeu</span><span className="delta-scale" /><span>ganhou</span>
        </div>

        {deltaTotal != null && (
          <div className="compare-stats">
            <div className="popup-row"><span className="popup-label">{anoInicio ?? 'Inicio'}</span><span className="stat-val">{startTotal?.toLocaleString('pt-BR') ?? '—'}</span></div>
            <div className="popup-row"><span className="popup-label">{anoFim ?? 'Fim'}</span><span className="stat-val">{endTotal?.toLocaleString('pt-BR') ?? '—'}</span></div>
            <div className="popup-row"><span className="popup-label">Saldo</span><span className="stat-val">{formatSigned(deltaTotal)}</span></div>
            <div className="popup-row"><span className="popup-label">Ganhos</span><span className="stat-val">{gained?.toLocaleString('pt-BR') ?? '0'}</span></div>
            <div className="popup-row"><span className="popup-label">Perdas</span><span className="stat-val">{lost?.toLocaleString('pt-BR') ?? '0'}</span></div>
          </div>
        )}
      </div>
    </details>
  );
}
