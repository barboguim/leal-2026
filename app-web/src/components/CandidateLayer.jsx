import { electionType, formatSigned } from '../lib/format';
import { COLORS } from '../lib/constants';
import EyeToggle from './EyeToggle.jsx';

export default function CandidateLayer({
  metricKey, label, color, visible, onToggleVisible, count,
  years, selectedYear, onYearChange,
  pairs, isComparing, onToggleCompare, selectedPair, onSelectPair,
  deltaTotal, pairMeta,
}) {
  return (
    <details className={'cand' + (visible ? '' : ' is-hidden')}>
      <summary className="cand-row">
        <EyeToggle visible={visible} onToggle={onToggleVisible} label={label} />
        <span className="layer-dot" style={{ background: color }} />
        <span className="cand-name">{label}</span>
        <span className="layer-count">{count ?? '—'}</span>
      </summary>

      <div className="cand-body">
        <div className="year-bar">
          <button
            type="button"
            className={'year-btn' + (selectedYear === null ? ' active' : '')}
            onClick={() => onYearChange(null)}
          >
            Todos
          </button>
          {years.map(y => (
            <button
              type="button"
              key={y}
              className={'year-btn' + (selectedYear === y ? ' active' : '') + ' ' + electionType(y).toLowerCase()}
              title={electionType(y)}
              onClick={() => onYearChange(y)}
            >
              {y}
            </button>
          ))}
        </div>
        <div className="year-type-legend">
          <span><span className="dot" style={{ background: COLORS.yearMunicipal }} /> Municipal</span>
          <span><span className="dot" style={{ background: COLORS.yearGeral }} /> Geral</span>
        </div>

        <label className="delta-toggle-row">
          <input type="checkbox" checked={isComparing} onChange={() => onToggleCompare(metricKey)} />
          Comparar dois anos
        </label>

        {isComparing && (
          <div className="cand-compare">
            <div className="delta-pair-list">
              {pairs.length === 0 && <span className="delta-pair-empty">nenhum par disponivel</span>}
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
            {pairMeta && (
              <div className="delta-pair-context">
                <span>{pairMeta.tipo_par}</span>
                {pairMeta.cargoDiferente && <span className="delta-pair-warning">cargo diferente</span>}
              </div>
            )}
            <div className="delta-legend">
              <span>perdeu</span><span className="delta-scale" /><span>ganhou</span>
              {deltaTotal != null && <span className="layer-count" style={{ marginLeft: 'auto' }}>{formatSigned(deltaTotal)}</span>}
            </div>
          </div>
        )}
      </div>
    </details>
  );
}
