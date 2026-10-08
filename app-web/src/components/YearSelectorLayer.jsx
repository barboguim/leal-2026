import { electionType } from '../lib/format';
import { COLORS } from '../lib/constants';
import EyeToggle from './EyeToggle.jsx';

// Sidebar group: "Ano a ano" — controls which single year's Hugo markers
// appear on the map, with a structured year-summary block below.

function fmtPct(n, total) {
  if (!total || !Number.isFinite(total) || total === 0) return '';
  return `${((n / total) * 100).toFixed(1).replace('.', ',')}%`;
}

function fmtSigned(n) {
  if (n === 0) return '0';
  return `${n > 0 ? '+' : ''}${n.toLocaleString('pt-BR')}`;
}

export default function YearSelectorLayer({
  visible, onToggleVisible,
  years, selectedYear, onYearChange,
  locaisCount, prevYear, newLocaisCount, goneLocaisCount,
  yearTotal, topLocal, avgPerLocal,
  topBairros, zonaStats, prevYearTotal,
}) {
  const changeParts = [];
  if (prevYear != null) {
    if (newLocaisCount > 0) changeParts.push(`${newLocaisCount} ${newLocaisCount === 1 ? 'novo' : 'novos'}`);
    if (goneLocaisCount > 0) changeParts.push(`${goneLocaisCount} ${goneLocaisCount === 1 ? 'saiu' : 'saíram'}`);
  }

  const growthAbs = (Number.isFinite(prevYearTotal) && prevYearTotal != null && Number.isFinite(yearTotal))
    ? yearTotal - prevYearTotal : null;
  const growthPct = (growthAbs != null && prevYearTotal > 0)
    ? ((growthAbs / prevYearTotal) * 100) : null;

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

        {Number.isFinite(yearTotal) && yearTotal > 0 && (
          <div className="year-summary">
            <div className="year-summary-headline">
              <span className="year-summary-big">{yearTotal.toLocaleString('pt-BR')}</span>
              <span className="year-summary-label">votos em {selectedYear}</span>
            </div>
            <div className="year-summary-sub">
              {locaisCount} {locaisCount === 1 ? 'local' : 'locais'}
              {Number.isFinite(avgPerLocal) && avgPerLocal > 0 && (
                <> · média {avgPerLocal.toFixed(1).replace('.', ',')} por local</>
              )}
              {growthAbs != null && prevYearTotal > 0 && (
                <> · <span className={growthAbs >= 0 ? 'growth-positive' : 'growth-negative'}>{fmtSigned(growthAbs)} ({growthPct >= 0 ? '+' : ''}{growthPct.toFixed(0)}%)</span> desde {prevYear}</>
              )}
              {changeParts.length > 0 && (
                <> · {changeParts.join(', ')}</>
              )}
            </div>

            {topBairros && topBairros.length > 0 && (
              <div className="year-summary-section">
                <div className="year-summary-head">Top bairros</div>
                <ul className="year-summary-list">
                  {topBairros.map(({ name, votes }) => (
                    <li key={name}>
                      <span className="year-summary-name">{name}</span>
                      <span className="year-summary-val">{votes.toLocaleString('pt-BR')} <span className="year-summary-dim">{fmtPct(votes, yearTotal)}</span></span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {zonaStats && zonaStats.length > 0 && (
              <div className="year-summary-section">
                <div className="year-summary-head">Por zona</div>
                <ul className="year-summary-list">
                  {zonaStats.map(({ zona, votes }) => (
                    <li key={zona}>
                      <span className="year-summary-name">Zona {zona}</span>
                      <span className="year-summary-val">{votes.toLocaleString('pt-BR')} <span className="year-summary-dim">{fmtPct(votes, yearTotal)}</span></span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {topLocal && (
              <div className="year-summary-section year-summary-top">
                <div className="year-summary-head">Local mais forte</div>
                <div className="year-summary-top-name">{topLocal.nm}</div>
                <div className="year-summary-top-stat">
                  {topLocal.votes.toLocaleString('pt-BR')} votos <span className="year-summary-dim">{fmtPct(topLocal.votes, yearTotal)}</span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </details>
  );
}
