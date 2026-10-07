function competitorRows(props) {
  const rows = [];
  for (let i = 1; i <= 3; i++) {
    const nome = props[`top${i}_nome`];
    if (!nome) continue;
    const partido = props[`top${i}_partido`] || '-';
    const votos = Number(props[`top${i}_votos`] || 0).toLocaleString('pt-BR');
    rows.push(
      <div className="popup-row" key={i}>
        <span className="popup-label">{i}º</span>
        <span className="popup-val">{nome} ({partido}) — {votos}</span>
      </div>
    );
  }
  return rows.length ? rows : (
    <div className="popup-row"><span className="popup-label">Sem dados</span></div>
  );
}

export default function CompetitorSection({ title, props }) {
  return (
    <details className="popup-competitors">
      <summary>{title}</summary>
      {competitorRows(props)}
    </details>
  );
}
