export function pointInRing(point, ring) {
  const x = point[0];
  const y = point[1];
  let inside = false;

  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const xi = ring[i][0];
    const yi = ring[i][1];
    const xj = ring[j][0];
    const yj = ring[j][1];
    const intersect = ((yi > y) !== (yj > y)) &&
      (x < ((xj - xi) * (y - yi)) / ((yj - yi) || 1e-12) + xi);
    if (intersect) inside = !inside;
  }

  return inside;
}

export function pointInGeometry(point, geometry) {
  if (!geometry) return false;
  if (geometry.type === 'Polygon') {
    const rings = geometry.coordinates || [];
    if (!rings.length) return false;
    if (!pointInRing(point, rings[0])) return false;
    for (let i = 1; i < rings.length; i++) {
      if (pointInRing(point, rings[i])) return false;
    }
    return true;
  }

  if (geometry.type === 'MultiPolygon') {
    return (geometry.coordinates || []).some(poly => pointInGeometry(point, { type: 'Polygon', coordinates: poly }));
  }

  return false;
}

export function normalizeText(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toUpperCase()
    .trim();
}

export function featureName(feature) {
  const props = feature?.properties || {};
  return props.tx_nome || props.si_nome || props.Nome_Ecid || props.nome || props.name || '';
}

export function passesGeoFilter(props, selectedRegion, selectedBairro) {
  const region = normalizeText(selectedRegion);
  const bairro = normalizeText(selectedBairro);
  const featureRegion = normalizeText(props.__region || '');
  const featureBairro = normalizeText(props.__bairro_geo || props.bairro || '');

  if (region !== 'ALL' && featureRegion !== region) return false;
  if (bairro !== 'ALL' && featureBairro !== bairro) return false;
  return true;
}

function findContainingName(point, features) {
  for (const feature of features) {
    if (pointInGeometry(point, feature.geometry)) {
      return normalizeText(featureName(feature));
    }
  }
  return '';
}

export function annotateFeatureCollection(fc, regionFeatures, bairroFeatures) {
  if (!fc) return fc;
  return {
    ...fc,
    features: fc.features.map(f => {
      if (!f.geometry) return f;
      const point = f.geometry.coordinates;
      return {
        ...f,
        properties: {
          ...f.properties,
          __region: findContainingName(point, regionFeatures),
          __bairro_geo: findContainingName(point, bairroFeatures),
        },
      };
    }),
  };
}
