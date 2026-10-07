import { BASE_KEYS, COLORS, LABELS } from '../lib/constants';

export default function CompareTable({ selection, data }) {
  if (!selection) return null;
  const { props: clickedProps } = selection;
  const localId = clickedProps.nr_local;

  const rows = BASE_KEYS.map(key => {
    const fc = data[key];
    if (!fc) return null;
    const localFeats = fc.features.filter(f => f.properties.nr_local === localId);
    if (localFeats.length === 0) return null;
    const byYear = {};
    localFeats.forEach(f => { byYear[f.properties.ano] = f.properties.QT_VOTOS; });
    return { key, byYear };
  }).filter(Boolean);

  if (rows.length === 0) return null;

  const allYears = [...new Set(rows.flatMap(r => Object.keys(r.byYear)))].sort();

  return (
    <div id="compare-panel">
      <div style={{ fontWeight: 700, marginBottom: 8 }}>{clickedProps.nm_local || `Local ${localId}`}</div>
      <table style={{ borderCollapse: 'collapse', width: '100%' }}>
        <tbody>
          <tr>
            <td></td>
            {allYears.map(y => (
              <td key={y} style={{ padding: '2px 8px', color: 'var(--color-text-muted)', fontSize: 11, textAlign: 'right' }}>{y}</td>
            ))}
          </tr>
          {rows.map(r => (
            <tr key={r.key}>
              <td style={{ padding: '2px 8px', color: COLORS[r.key], fontWeight: 600, whiteSpace: 'nowrap' }}>{LABELS[r.key]}</td>
              {allYears.map(y => (
                <td key={y} style={{ padding: '2px 8px', textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
                  {r.byYear[y] ? r.byYear[y].toLocaleString('pt-BR') : '—'}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
