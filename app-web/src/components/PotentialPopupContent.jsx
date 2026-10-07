export default function PotentialPopupContent({ p }) {
  return (
    <div>
      <div className="popup-title">{p.nm_local || `Local ${p.nr_local}`}</div>
      <div className="popup-bairro">{p.bairro || ''}</div>
      <div className="popup-row"><span className="popup-label">Posicao no ranking</span><span className="popup-val">{p.rank}</span></div>
      <div className="popup-row"><span className="popup-label">Hugo — participacao atual</span><span className="popup-val">{p.pct_share}%</span></div>
      {p.maior_semelhanca && (
        <div className="popup-row"><span className="popup-label">Maior semelhanca em</span><span className="popup-val">{p.maior_semelhanca}</span></div>
      )}
      <div className="control-note">
        Similaridade de composicao do eleitorado com as bases de Hugo — nao indica quem vai votar nem preve resultado.
      </div>
    </div>
  );
}
