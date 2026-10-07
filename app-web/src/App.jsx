import { useState, useMemo, useEffect } from 'react';
import MapView from './components/MapView.jsx';
import MarkerLayer from './components/MarkerLayer.jsx';
import DeltaLayer from './components/DeltaLayer.jsx';
import CompareTable from './components/CompareTable.jsx';
import StatsPanel from './components/StatsPanel.jsx';
import CandidateLayer from './components/CandidateLayer.jsx';
import IntensityLegend from './components/IntensityLegend.jsx';
import { useMapData } from './lib/useMapData.js';
import { aggregateByLocal } from './lib/aggregate.js';
import { COLORS, LABELS, BASE_KEYS, DELTA_METRICS } from './lib/constants.js';

// leal-2026 is a Hugo-only product. The deep strip of Felipe/PSD code paths
// is deferred; narrowing these three lists hides them from the UI.
const LAYER_ORDER = ['hugo_leal'];
const TOGGLE_ID_BY_LAYER_KEY = { hugo_leal: 'hugo' };
const CANDIDATE_ROWS = [
  { baseKey: 'hugo_leal', metricKey: 'hugo', label: LABELS.hugo_leal, color: COLORS.hugo_leal },
];

// 2018-2022 is the one pair that is verified fully-gated for Hugo under the
// candidacy-matrix pairing rule. The 2022-2026 pair becomes the default once
// script 06 is re-run with 2026 included (deferred).
function defaultPairFor(pairs) {
  if (pairs.includes('2022-2026')) return '2022-2026';
  if (pairs.includes('2018-2022')) return '2018-2022';
  return pairs[pairs.length - 1] ?? null;
}

export default function App() {
  const rawData = useMapData();
  const data = rawData;

  const yearsByCandidate = useMemo(() => {
    const result = {};
    for (const key of BASE_KEYS) {
      result[key] = [...new Set((data?.[key]?.features || []).map(f => Number(f.properties.ano)).filter(Number.isFinite))].sort((a, b) => a - b);
    }
    return result;
  }, [data]);

  const pairsByMetric = useMemo(() => {
    if (!data?.vote_deltas) return {};
    const result = {};
    for (const [key, metric] of Object.entries(DELTA_METRICS)) {
      const valid = new Set(
        data.vote_deltas.features
          .filter(f => f.properties[metric.field] !== null && f.properties[metric.field] !== undefined)
          .map(f => f.properties.pair)
      );
      result[key] = [...valid].sort((a, b) => Number(a.slice(0, 4)) - Number(b.slice(0, 4)));
    }
    return result;
  }, [data]);

  const [candidateYears, setCandidateYears] = useState(() => {
    const result = {};
    for (const key of BASE_KEYS) {
      const years = yearsByCandidate[key] || [];
      // Default to the most recent cycle (2026) when available.
      result[key] = years[years.length - 1] ?? null;
    }
    return result;
  });

  const defaultDeltaPair = defaultPairFor(pairsByMetric.hugo || []);
  const [activeDeltaCandidate, setActiveDeltaCandidate] = useState(null);
  const [selectedYearA, setSelectedYearA] = useState(() => (defaultDeltaPair ? Number(defaultDeltaPair.split('-')[0]) : null));
  const [selectedYearB, setSelectedYearB] = useState(() => (defaultDeltaPair ? Number(defaultDeltaPair.split('-')[1]) : null));
  const [toggles, setToggles] = useState({ hugo: true });
  const [compareSelection, setCompareSelection] = useState(null);

  useEffect(() => {
    const handler = (e) => {
      const cp = document.getElementById('compare-panel');
      if (cp && !cp.contains(e.target) && !e.target.closest('.leaflet-interactive')) {
        setCompareSelection(null);
      }
    };
    document.addEventListener('click', handler);
    return () => document.removeEventListener('click', handler);
  }, []);

  function handleCandidateYearChange(baseKey, year) {
    setCandidateYears(prev => ({ ...prev, [baseKey]: year }));
  }

  function handleToggleVisible(baseKey) {
    const toggleId = TOGGLE_ID_BY_LAYER_KEY[baseKey];
    const turningOff = toggles[toggleId];
    setToggles(t => ({ ...t, [toggleId]: !t[toggleId] }));
    if (turningOff && activeDeltaCandidate === toggleId) {
      setActiveDeltaCandidate(null);
      setSelectedYearA(null);
      setSelectedYearB(null);
    }
  }

  function handleToggleCompare(metricKey) {
    if (activeDeltaCandidate === metricKey) {
      setActiveDeltaCandidate(null);
      setSelectedYearA(null);
      setSelectedYearB(null);
      return;
    }
    setActiveDeltaCandidate(metricKey);
    if (!toggles[metricKey]) {
      setToggles(t => ({ ...t, [metricKey]: true }));
    }
    const pair = defaultPairFor(pairsByMetric[metricKey] || []);
    setSelectedYearA(pair ? Number(pair.split('-')[0]) : null);
    setSelectedYearB(pair ? Number(pair.split('-')[1]) : null);
  }

  function handleSelectPair(pairStr) {
    const [yearA, yearB] = pairStr.split('-').map(Number);
    setSelectedYearA(yearA);
    setSelectedYearB(yearB);
  }

  if (!data) {
    return <div style={{ padding: 24 }}>Dados nao carregados.</div>;
  }

  const pair = selectedYearA != null && selectedYearB != null ? `${selectedYearA}-${selectedYearB}` : null;
  const selectedPairFeature = pair
    ? data.vote_deltas?.features.find(f => f.properties.pair === pair)
    : null;
  const selectedPairMeta = selectedPairFeature
    ? {
        tipo_par: selectedPairFeature.properties.tipo_par,
        cargoDiferente: Boolean(selectedPairFeature.properties[`cargo_diferente_${activeDeltaCandidate}`]),
      }
    : null;

  // Precompute per-local vote share so markers can be colored by intensity.
  // Share = this local's QT_VOTOS / sum of all locais' QT_VOTOS for the
  // selected year. Shows where Hugo's base is concentrated.
  const counts = {};
  const markerLayers = LAYER_ORDER
    .filter(key => toggles[TOGGLE_ID_BY_LAYER_KEY[key]])
    .map(key => {
      const fc = data[key];
      if (!fc) return null;
      const candYear = candidateYears[key];
      const filtered = candYear ? fc.features.filter(f => f.properties.ano === candYear) : fc.features;
      const points = candYear ? filtered : aggregateByLocal(filtered);
      const total = points.reduce((s, f) => s + Number(f.properties.QT_VOTOS || 0), 0);
      const withShare = points.map(f => ({
        ...f,
        properties: {
          ...f.properties,
          share_pct: total > 0 ? (Number(f.properties.QT_VOTOS || 0) / total) * 100 : 0,
        },
      }));
      const maxShare = withShare.reduce((m, f) => Math.max(m, f.properties.share_pct), 0);
      const id = TOGGLE_ID_BY_LAYER_KEY[key];
      counts[id] = total.toLocaleString('pt-BR');
      return { key, features: withShare, maxShare };
    })
    .filter(Boolean);

  const deltaFeats = data.vote_deltas && pair
    ? data.vote_deltas.features.filter(f => f.properties.pair === pair)
    : [];
  let deltaTotal = null;
  if (data.vote_deltas && pair && activeDeltaCandidate) {
    const metric = DELTA_METRICS[activeDeltaCandidate];
    const gatedDeltaFeats = deltaFeats.filter(f => f.properties[metric.field] !== null && f.properties[metric.field] !== undefined);
    if (gatedDeltaFeats.length > 0) {
      deltaTotal = gatedDeltaFeats.reduce((s, f) => s + Number(f.properties[metric.field]), 0);
    }
  }

  const hugoLayer = markerLayers.find(l => l.key === 'hugo_leal');

  return (
    <>
      <MapView>
        {markerLayers.map(({ key, features, maxShare }) => (
          <MarkerLayer
            key={key}
            layerKey={key}
            features={features}
            maxShare={maxShare}
            onSelect={(p, coords) => setCompareSelection({ props: p, coords })}
          />
        ))}
        {activeDeltaCandidate && pair && (
          <DeltaLayer features={deltaFeats} metric={DELTA_METRICS[activeDeltaCandidate]} selectedDeltaMetric={activeDeltaCandidate} data={data} />
        )}
      </MapView>

      <div id="panel">
        <div className="panel-header">
          <div>
            <h1>Mapa eleitoral · Hugo Leal</h1>
            <div className="subtitle">Niterói — 2010 → 2026</div>
          </div>
        </div>

        <div className="section-title">Camadas</div>
        {CANDIDATE_ROWS.map(({ baseKey, metricKey, label, color }) => (
          <CandidateLayer
            key={baseKey}
            metricKey={metricKey}
            label={label}
            color={color}
            visible={toggles[TOGGLE_ID_BY_LAYER_KEY[baseKey]]}
            onToggleVisible={() => handleToggleVisible(baseKey)}
            count={counts[TOGGLE_ID_BY_LAYER_KEY[baseKey]]}
            years={yearsByCandidate[baseKey] || []}
            selectedYear={candidateYears[baseKey]}
            onYearChange={(year) => handleCandidateYearChange(baseKey, year)}
            pairs={pairsByMetric[metricKey] || []}
            isComparing={activeDeltaCandidate === metricKey}
            onToggleCompare={handleToggleCompare}
            selectedPair={pair}
            onSelectPair={handleSelectPair}
            deltaTotal={activeDeltaCandidate === metricKey ? deltaTotal : null}
            pairMeta={activeDeltaCandidate === metricKey ? selectedPairMeta : null}
          />
        ))}

        {hugoLayer && hugoLayer.features.length > 0 && (
          <IntensityLegend maxShare={hugoLayer.maxShare} year={candidateYears.hugo_leal} />
        )}

        <StatsPanel
          data={data}
          candidateYears={candidateYears}
          selectedRegion="all"
          selectedBairro="all"
          selectedPair={pair}
          selectedDeltaMetric={activeDeltaCandidate}
          deltaEnabled={activeDeltaCandidate != null}
        />
      </div>

      <CompareTable selection={compareSelection} data={data} />
    </>
  );
}
