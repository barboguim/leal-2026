export function aggregateByLocal(features) {
  const byLocal = {};
  features.forEach(f => {
    const key = f.properties.nr_local;
    if (!byLocal[key]) {
      byLocal[key] = {
        type: 'Feature',
        geometry: f.geometry,
        properties: {
          ...f.properties,
          QT_VOTOS: 0,
          n_secoes: 0,
          _years: {},
        },
      };
    }
    byLocal[key].properties.QT_VOTOS += f.properties.QT_VOTOS;
    byLocal[key].properties.n_secoes = Math.max(byLocal[key].properties.n_secoes, f.properties.n_secoes);
    byLocal[key].properties._years[f.properties.ano] = f.properties.QT_VOTOS;
  });
  return Object.values(byLocal);
}
