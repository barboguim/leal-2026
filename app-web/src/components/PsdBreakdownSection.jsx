function breakdownRows(props) {
  const rows = [];
  for (let i = 1; i <= 3; i++) {
    const nome = props[`psd_top${i}_nome`];
    if (!nome) continue;
    const cargo = props[`psd_top${i}_cargo`] || '-';
    const votos = Number(props[`psd_top${i}_votos`] || 0).toLocaleString('pt-BR');
    const share = Number(props[`psd_top${i}_share`] || 0).toLocaleString('pt-BR', { maximumFractionDigits: 1 });
    rows.push(
      <div className="popup-row" key={i}>
        <span className="popup-label">{i}º</span>
        <span className="popup-val">{nome} ({cargo}) — {votos} — {share}% do PSD no cargo</span>
      </div>
    );
  }
  return rows;
}

function totalPorCargoRows(props) {
  if (!props.psd_total_por_cargo) return [];
  let totals;
  try {
    totals = JSON.parse(props.psd_total_por_cargo);
  } catch {
    return [];
  }
  return Object.entries(totals).map(([cargo, votos]) => (
    <div className="popup-row" key={cargo}>
      <span className="popup-label">{cargo}</span>
      <span className="popup-val">{Number(votos).toLocaleString('pt-BR')} votos</span>
    </div>
  ));
}

export default function PsdBreakdownSection({ props }) {
  const rows = breakdownRows(props);
  const totalRows = totalPorCargoRows(props);
  const count = props.psd_candidate_count;

  return (
    <details className="popup-competitors">
      <summary>Composicao PSD</summary>
      {count != null && (
        <div className="popup-row"><span className="popup-label">{count} candidatos</span></div>
      )}
      {rows.length ? rows : <div className="popup-row"><span className="popup-label">Sem dados</span></div>}
      {totalRows.length > 0 && (
        <>
          <div className="popup-row" style={{ borderTop: '1px solid var(--color-border)', marginTop: 4, paddingTop: 4 }}>
            <span className="popup-label">Total PSD por cargo</span>
          </div>
          {totalRows}
        </>
      )}
    </details>
  );
}
