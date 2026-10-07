import { useState, useEffect } from 'react';

const REGION_SERVICE = 'https://geo.niteroi.rj.gov.br/arcgis/rest/services/Aplicacoes/PD_MAPA1_mapservice/MapServer';
const REGION_URL = `${REGION_SERVICE}/10/query?where=1%3D1&outFields=tx_nome,si_nome&returnGeometry=true&f=geojson&outSR=4326`;
const BAIRRO_URL = `${REGION_SERVICE}/20/query?where=1%3D1&outFields=tx_nome&returnGeometry=true&f=geojson&outSR=4326`;

async function fetchGeoJson(url) {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`Failed to load ${url}: ${resp.status}`);
  return resp.json();
}

export function useBoundaries() {
  const [regionFeatures, setRegionFeatures] = useState([]);
  const [bairroFeatures, setBairroFeatures] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([fetchGeoJson(REGION_URL), fetchGeoJson(BAIRRO_URL)])
      .then(([regions, bairros]) => {
        if (cancelled) return;
        setRegionFeatures(regions.features || []);
        setBairroFeatures(bairros.features || []);
      })
      .catch(err => {
        if (cancelled) return;
        console.warn('boundary load failed', err);
        setError(err);
      });
    return () => { cancelled = true; };
  }, []);

  return { regionFeatures, bairroFeatures, error };
}
