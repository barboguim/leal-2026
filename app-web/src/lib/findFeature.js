export function findYearLocalFeature(data, layerKey, ano, nrLocal) {
  const fc = data[layerKey];
  if (!fc) return null;
  return fc.features.find(
    f => f.properties.ano === ano && String(f.properties.nr_local) === String(nrLocal)
  ) || null;
}
