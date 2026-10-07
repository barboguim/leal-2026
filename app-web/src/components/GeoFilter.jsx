export default function GeoFilter({
  regions, bairros, selectedRegion, selectedBairro, onRegionChange, onBairroChange,
  showRegionBoundaries, showBairroBoundaries, onToggleRegionBoundaries, onToggleBairroBoundaries,
  disabled,
}) {
  return (
    <div className="control-grid">
      <div className="control-row">
        <select className="control-select" value={selectedRegion} disabled={disabled} onChange={(e) => onRegionChange(e.target.value)}>
          <option value="all">Todas as regioes</option>
          {regions.map(r => <option key={r} value={r}>{r}</option>)}
        </select>
        <select className="control-select" value={selectedBairro} disabled={disabled} onChange={(e) => onBairroChange(e.target.value)}>
          <option value="all">Todos os bairros</option>
          {bairros.map(b => <option key={b} value={b}>{b}</option>)}
        </select>
      </div>
      <label className="control-toggle">
        <input type="checkbox" checked={showRegionBoundaries} onChange={onToggleRegionBoundaries} />
        <span>Mostrar limites das regioes</span>
      </label>
      <label className="control-toggle">
        <input type="checkbox" checked={showBairroBoundaries} onChange={onToggleBairroBoundaries} />
        <span>Mostrar limites dos bairros</span>
      </label>
    </div>
  );
}
