import { electionType } from '../lib/format';
import { COLORS } from '../lib/constants';
import EyeToggle from './EyeToggle.jsx';

// Sidebar group: "Ano a ano" — controls which single year's Hugo markers
// appear on the map. Count = total Hugo votes for that year.

export default function YearSelectorLayer({
  visible, onToggleVisible, count,
  years, selectedYear, onYearChange,
}) {
  return (
    <details className={'group' + (visible ? '' : ' is-hidden')} open>
      <summary className="group-row">
        <EyeToggle visible={visible} onToggle={onToggleVisible} label="Ano a ano" />
        <span className="dot" style={{ background: COLORS.hugo_leal }} />
        <span className="group-label">Ano a ano</span>
        <span className="group-count">{count ?? '—'}</span>
      </summary>

      <div className="group-body">
        <div className="year-bar">
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
          <span><span className="dot" style={{ background: COLORS.yearGeral }} /> Geral</span>
          <span><span className="dot" style={{ background: COLORS.yearMunicipal }} /> Municipal</span>
        </div>
      </div>
    </details>
  );
}
