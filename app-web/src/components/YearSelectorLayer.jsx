import { electionType } from '../lib/format';
import { COLORS } from '../lib/constants';
import EyeToggle from './EyeToggle.jsx';

// Sidebar group: "Ano a ano" — controls which single year's Hugo markers
// appear on the map. Count = total Hugo votes for that year.

export default function YearSelectorLayer({
  visible, onToggleVisible,
  years, selectedYear, onYearChange,
  locaisCount, prevYear, newLocaisCount, goneLocaisCount,
}) {
  const changeParts = [];
  if (prevYear != null) {
    if (newLocaisCount > 0) changeParts.push(`${newLocaisCount} ${newLocaisCount === 1 ? 'novo' : 'novos'}`);
    if (goneLocaisCount > 0) changeParts.push(`${goneLocaisCount} ${goneLocaisCount === 1 ? 'saiu' : 'saíram'}`);
  }

  return (
    <details className={'group' + (visible ? '' : ' is-hidden')}>
      <summary className="group-row">
        <EyeToggle visible={visible} onToggle={onToggleVisible} label="Ano a ano" />
        <span className="dot" style={{ background: COLORS.hugo_leal }} />
        <span className="group-label">Ano a ano</span>
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
        {Number.isFinite(locaisCount) && locaisCount > 0 && (
          <div className="status-caption">
            <strong>{locaisCount}</strong> {locaisCount === 1 ? 'local' : 'locais'} com votos de Hugo
            {changeParts.length > 0 && (
              <span className="status-caption-sub"> · desde {prevYear}: {changeParts.join(', ')}</span>
            )}
          </div>
        )}
      </div>
    </details>
  );
}
