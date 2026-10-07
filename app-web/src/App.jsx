import { useState, useMemo, useEffect } from 'react';
import MapView from './components/MapView.jsx';
import MarkerLayer from './components/MarkerLayer.jsx';
import DeltaLayer from './components/DeltaLayer.jsx';
import ProfileLayer from './components/ProfileLayer.jsx';
import PotentialLayer from './components/PotentialLayer.jsx';
import ProfileMetricFilter from './components/ProfileMetricFilter.jsx';
import BoundaryLayer from './components/BoundaryLayer.jsx';
import CompareTable from './components/CompareTable.jsx';
import StatsPanel from './components/StatsPanel.jsx';
import CandidateLayer from './components/CandidateLayer.jsx';
import GeoFilter from './components/GeoFilter.jsx';
import { useMapData } from './lib/useMapData.js';
import { useBoundaries } from './lib/useBoundaries.js';
import { aggregateByLocal } from './lib/aggregate.js';
import { annotateFeatureCollection, normalizeText, featureName, passesGeoFilter } from './lib/geo.js';
import { electionType } from './lib/format.js';
import { COLORS, LABELS, BASE_KEYS, DELTA_METRICS, PROFILE_METRICS } from './lib/constants.js';

const LAYER_ORDER = ['psd', 'felipe_peixoto', 'hugo_leal'];
const TOGGLE_ID_BY_LAYER_KEY = { psd: 'psd', felipe_peixoto: 'felipe', hugo_leal: 'hugo' };
// Sidebar display order (Hugo, Felipe, PSD) is independent of LAYER_ORDER above,
// which controls map z-order (PSD drawn first/bottom, Hugo last/top).
const CANDIDATE_ROWS = [
  { baseKey: 'hugo_leal', metricKey: 'hugo', label: LABELS.hugo_leal, color: COLORS.hugo_leal },
  { baseKey: 'felipe_peixoto', metricKey: 'felipe', label: LABELS.felipe_peixoto, color: COLORS.felipe_peixoto },
  { baseKey: 'psd', metricKey: 'psd', label: 'PSD (total)', color: COLORS.psd },
];

// 2018-2022 is verified against real vote_deltas data to be fully gated for
// Hugo (the default candidate) -- unlike 2022-2024, which doesn't exist under
// the matrix-gated pairing, and 2020-2024, which leaves Hugo gated to null
// everywhere. Reused both at mount and whenever a candidate's "Comparar dois
// anos" toggle switches on, so every candidate gets the same sane default
// (its own most-recent pair) rather than carrying over another candidate's.
function defaultPairFor(pairs) {
  return pairs.includes('2018-2022') ? '2018-2022' : (pairs[pairs.length - 1] ?? null);
}

export default function App() {
  const rawData = useMapData();
  const { regionFeatures, bairroFeatures } = useBoundaries();

  const data = useMemo(() => {
    if (!rawData) return null;
    if (regionFeatures.length === 0 && bairroFeatures.length === 0) return rawData;
    const annotated = { ...rawData };
    [...BASE_KEYS, 'vote_deltas', 'voter_profile', 'potential_hugo'].forEach(key => {
      if (annotated[key]) annotated[key] = annotateFeatureCollection(annotated[key], regionFeatures, bairroFeatures);
    });
    return annotated;
  }, [rawData, regionFeatures, bairroFeatures]);

  const yearsByCandidate = useMemo(() => {
    const result = {};
    for (const key of BASE_KEYS) {
      result[key] = [...new Set((data?.[key]?.features || []).map(f => Number(f.properties.ano)).filter(Number.isFinite))].sort((a, b) => a - b);
    }
    return result;
  }, [data]);

  const profileYears = useMemo(() => {
    if (!data?.voter_profile) return [];
    return [...new Set(data.voter_profile.features.map(f => Number(f.properties.ano)).filter(Number.isFinite))].sort((a, b) => a - b);
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

  const regionOptions = useMemo(() => {
    const map = new Map(regionFeatures.map(f => [normalizeText(featureName(f)), featureName(f)]));
    return [...map.values()].sort((a, b) => a.localeCompare(b, 'pt-BR'));
  }, [regionFeatures]);

  const bairroOptions = useMemo(() => {
    const map = new Map(bairroFeatures.map(f => [normalizeText(featureName(f)), featureName(f)]));
    return [...map.values()].sort((a, b) => a.localeCompare(b, 'pt-BR'));
  }, [bairroFeatures]);

  const [candidateYears, setCandidateYears] = useState(() => {
    const result = {};
    for (const key of BASE_KEYS) {
      const years = yearsByCandidate[key] || [];
      result[key] = years.includes(2022) ? 2022 : (years[years.length - 1] ?? null);
    }
    return result;
  });

  const [selectedProfileYear, setSelectedProfileYear] = useState(() => (
    profileYears.includes(2022) ? 2022 : (profileYears[profileYears.length - 1] ?? null)
  ));

  const defaultDeltaPair = defaultPairFor(pairsByMetric.hugo || []);
  const [activeDeltaCandidate, setActiveDeltaCandidate] = useState('hugo');
  const [selectedYearA, setSelectedYearA] = useState(() => (defaultDeltaPair ? Number(defaultDeltaPair.split('-')[0]) : null));
  const [selectedYearB, setSelectedYearB] = useState(() => (defaultDeltaPair ? Number(defaultDeltaPair.split('-')[1]) : null));
  const [selectedRegion, setSelectedRegion] = useState('all');
  const [selectedBairro, setSelectedBairro] = useState('all');
  const [toggles, setToggles] = useState({ hugo: true, felipe: true, psd: false, profile: false, potential: false, regionBoundaries: true, bairroBoundaries: false });
  const [selectedProfileMetricId, setSelectedProfileMetricId] = useState('mulheres');
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

  // Comparing implies visible, both ways: hiding the candidate that's
  // currently comparing turns comparison off (no delta layer for dots you
  // can't see); turning comparison on for a hidden candidate shows it.
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

  // Only one candidate's delta comparison is active at a time -- checking a
  // candidate's "Comparar dois anos" switches the active one (and picks that
  // candidate's own default pair); unchecking the active one turns delta off.
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

  // The chip list only ever renders pairs valid for the active candidate, so
  // whatever it passes here is already a real, selectable pair.
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

  const counts = {};
  const markerLayers = LAYER_ORDER
    .filter(key => toggles[TOGGLE_ID_BY_LAYER_KEY[key]])
    .map(key => {
      const fc = data[key];
      if (!fc) return null;
      const candYear = candidateYears[key];
      const filtered = (candYear ? fc.features.filter(f => f.properties.ano === candYear) : fc.features)
        .filter(f => passesGeoFilter(f.properties, selectedRegion, selectedBairro));
      const points = candYear ? filtered : aggregateByLocal(filtered);
      const id = TOGGLE_ID_BY_LAYER_KEY[key];
      counts[id] = points.reduce((s, f) => s + f.properties.QT_VOTOS, 0).toLocaleString('pt-BR');
      return { key, features: points };
    })
    .filter(Boolean);

  const deltaFeats = data.vote_deltas && pair
    ? data.vote_deltas.features.filter(f => f.properties.pair === pair).filter(f => passesGeoFilter(f.properties, selectedRegion, selectedBairro))
    : [];
  let deltaTotal = null;
  if (data.vote_deltas && pair && activeDeltaCandidate) {
    const metric = DELTA_METRICS[activeDeltaCandidate];
    const gatedDeltaFeats = deltaFeats.filter(f => f.properties[metric.field] !== null && f.properties[metric.field] !== undefined);
    if (gatedDeltaFeats.length > 0) {
      deltaTotal = gatedDeltaFeats.reduce((s, f) => s + Number(f.properties[metric.field]), 0);
    }
  }

  const profileFeats = data.voter_profile && selectedProfileYear
    ? data.voter_profile.features.filter(f => f.properties.ano === selectedProfileYear).filter(f => passesGeoFilter(f.properties, selectedRegion, selectedBairro))
    : [];

  const potentialFeats = data.potential_hugo
    ? data.potential_hugo.features.filter(f => passesGeoFilter(f.properties, selectedRegion, selectedBairro))
    : [];

  return (
    <>
      <MapView>
        {toggles.regionBoundaries && regionFeatures.length > 0 && (
          <BoundaryLayer features={regionFeatures} selectedName={selectedRegion} inactiveColor="#7f8aa6" opacity={0.95} fillOpacity={0.02} />
        )}
        {toggles.bairroBoundaries && bairroFeatures.length > 0 && (
          <BoundaryLayer features={bairroFeatures} selectedName={selectedBairro} inactiveColor="#c7b56a" opacity={0.8} fillOpacity={0.01} />
        )}
        {markerLayers.map(({ key, features }) => (
          <MarkerLayer
            key={key}
            layerKey={key}
            features={features}
            onSelect={(p, coords) => setCompareSelection({ props: p, coords })}
          />
        ))}
        {activeDeltaCandidate && pair && (
          <DeltaLayer features={deltaFeats} metric={DELTA_METRICS[activeDeltaCandidate]} selectedDeltaMetric={activeDeltaCandidate} data={data} />
        )}
        {toggles.profile && (
          <ProfileLayer features={profileFeats} metric={PROFILE_METRICS[selectedProfileMetricId]} />
        )}
        {toggles.potential && (
          <PotentialLayer features={potentialFeats} />
        )}
      </MapView>

      <div id="panel">
        <div className="panel-header">
          <div>
            <h1>MAPA ELEITORAL</h1>
            <div className="subtitle">Analise Territorial — Niterói</div>
          </div>
        </div>

        <div className="section-title">Candidatos</div>
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

        <div className="section-title">Perfil do Eleitorado</div>
        <label className="layer-row">
          <input type="checkbox" checked={toggles.profile} onChange={() => setToggles(t => ({ ...t, profile: !t.profile }))} />
          <span className="layer-dot" style={{ background: COLORS.profileAccent }} />
          <span className="layer-label">Perfil do eleitorado</span>
          <span className="layer-count">{profileFeats.length || '-'}</span>
        </label>
        <div className="year-bar">
          {profileYears.map(y => (
            <button
              type="button"
              key={y}
              className={'year-btn' + (selectedProfileYear === y ? ' active' : '') + ' ' + electionType(y).toLowerCase()}
              title={electionType(y)}
              onClick={() => setSelectedProfileYear(y)}
            >
              {y}
            </button>
          ))}
        </div>
        <div className="year-type-legend">
          <span><span className="dot" style={{ background: COLORS.yearMunicipal }} /> Municipal</span>
          <span><span className="dot" style={{ background: COLORS.yearGeral }} /> Geral</span>
        </div>
        <ProfileMetricFilter selectedMetricId={selectedProfileMetricId} onChange={setSelectedProfileMetricId} />
        <div className="delta-legend"><span>menor concentracao</span><span className="profile-scale" /><span>maior concentracao</span></div>

        <div className="section-title">Zonas com Potencial</div>
        <label className="layer-row">
          <input type="checkbox" checked={toggles.potential} onChange={() => setToggles(t => ({ ...t, potential: !t.potential }))} />
          <span className="layer-dot" style={{ background: COLORS.potentialAccent }} />
          <span className="layer-label">Similaridade com bases de Hugo</span>
          <span className="layer-count">{potentialFeats.length || '-'}</span>
        </label>
        <div className="control-note">Composicao do eleitorado similar as bases de Hugo, nos locais onde ele hoje tem menor participacao — nao indica quem vai votar.</div>

        <div className="section-title">Regiao / Bairro</div>
        <GeoFilter
          regions={regionOptions}
          bairros={bairroOptions}
          selectedRegion={selectedRegion}
          selectedBairro={selectedBairro}
          onRegionChange={setSelectedRegion}
          onBairroChange={setSelectedBairro}
          showRegionBoundaries={toggles.regionBoundaries}
          showBairroBoundaries={toggles.bairroBoundaries}
          onToggleRegionBoundaries={() => setToggles(t => ({ ...t, regionBoundaries: !t.regionBoundaries }))}
          onToggleBairroBoundaries={() => setToggles(t => ({ ...t, bairroBoundaries: !t.bairroBoundaries }))}
          disabled={regionOptions.length === 0}
        />
        <div className="control-note">Os filtros usam os limites oficiais do Plano Diretor de Niteroi.</div>

        <StatsPanel
          data={data}
          candidateYears={candidateYears}
          selectedRegion={selectedRegion}
          selectedBairro={selectedBairro}
          selectedPair={pair}
          selectedDeltaMetric={activeDeltaCandidate}
          deltaEnabled={activeDeltaCandidate != null}
        />
      </div>

      <CompareTable selection={compareSelection} data={data} />
    </>
  );
}
