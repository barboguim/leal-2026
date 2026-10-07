import { useState, useMemo, useEffect } from 'react';
import MapView from './components/MapView.jsx';
import MarkerLayer from './components/MarkerLayer.jsx';
import DeltaLayer from './components/DeltaLayer.jsx';
import CompareTable from './components/CompareTable.jsx';
import YearSelectorLayer from './components/YearSelectorLayer.jsx';
import ComparativoLayer from './components/ComparativoLayer.jsx';
import IntensityLegend from './components/IntensityLegend.jsx';
import { useMapData } from './lib/useMapData.js';
import { aggregateByLocal } from './lib/aggregate.js';
import { DELTA_METRICS } from './lib/constants.js';

const HUGO = 'hugo_leal';

function defaultPairFor(pairs) {
  // 2022-2026 is the newest Geral-to-Geral pair, which is the default users
  // land on. Historic fallback goes to the most recent pair the dataset has.
  if (pairs.includes('2022-2026')) return '2022-2026';
  if (pairs.includes('2018-2022')) return '2018-2022';
  return pairs[pairs.length - 1] ?? null;
}

export default function App() {
  const rawData = useMapData();
  const data = rawData;

  const years = useMemo(() => {
    const feats = data?.[HUGO]?.features || [];
    return [...new Set(feats.map(f => Number(f.properties.ano)).filter(Number.isFinite))].sort((a, b) => a - b);
  }, [data]);

  const pairs = useMemo(() => {
    if (!data?.vote_deltas) return [];
    const valid = new Set(
      data.vote_deltas.features
        .filter(f => f.properties.delta_hugo !== null && f.properties.delta_hugo !== undefined)
        .map(f => f.properties.pair)
    );
    // Keep only consecutive Geral-to-Geral pairs (4-year gap). The pipeline
    // can emit cross-pairs like 2010-2018 when a candidate skips a cycle,
    // but those confuse the "evolucao" story in the UI.
    return [...valid]
      .filter(p => {
        const [a, b] = p.split('-').map(Number);
        return b - a === 4;
      })
      .sort((a, b) => Number(a.slice(0, 4)) - Number(b.slice(0, 4)));
  }, [data]);

  const [selectedYear, setSelectedYear] = useState(null);
  const [selectedPair, setSelectedPair] = useState(null);
  const [showYears, setShowYears] = useState(true);
  const [showCompare, setShowCompare] = useState(false);
  const [compareSelection, setCompareSelection] = useState(null);
  const [panelCollapsed, setPanelCollapsed] = useState(false);

  // Default selections once data lands. Year picks the most recent cycle
  // (2026 when the pipeline has it). Pair picks 2022-2026 when available,
  // 2018-2022 otherwise.
  useEffect(() => {
    if (selectedYear == null && years.length > 0) {
      setSelectedYear(years[years.length - 1]);
    }
  }, [years, selectedYear]);
  useEffect(() => {
    if (selectedPair == null && pairs.length > 0) {
      setSelectedPair(defaultPairFor(pairs));
    }
  }, [pairs, selectedPair]);

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

  if (!data) {
    return <div style={{ padding: 24 }}>Dados nao carregados.</div>;
  }

  // --- Markers (Ano a ano) --------------------------------------------------
  // share_pct = this local's QT_VOTOS / max QT_VOTOS across Hugo's locais
  // that year. "Relative intensity": the strongest local that year reads as
  // 100 %, everyone else is a share of it. Picked over absolute Hugo-share
  // because the absolute metric produces values in the 0 – 5 % range, which
  // doesn't feel like 'intensity'. Relative gives a natural 0 – 100 % scale,
  // intuitive bins (0-20, 20-40, …) and recolors each year on its own terms
  // (Hugo's strongest 2010 local vs. his strongest 2026 local are both the
  // top of their own cycle, which is what a map viewer intuits).
  const hugoFC = data[HUGO];
  const yearFeats = (selectedYear ? hugoFC.features.filter(f => f.properties.ano === selectedYear) : hugoFC.features);
  const localPoints = selectedYear ? yearFeats : aggregateByLocal(yearFeats);
  const yearMax = localPoints.reduce((m, f) => Math.max(m, Number(f.properties.QT_VOTOS || 0)), 0);
  const yearTotal = localPoints.reduce((s, f) => s + Number(f.properties.QT_VOTOS || 0), 0);
  const featuresWithShare = localPoints.map(f => {
    const votos = Number(f.properties.QT_VOTOS || 0);
    const intensity_pct = yearMax > 0 ? (votos / yearMax) * 100 : 0;
    // share_pct kept for the popup (absolute "% of Hugo's total votes" is
    // still a useful figure once the user is looking at a specific local).
    const share_pct = yearTotal > 0 ? (votos / yearTotal) * 100 : 0;
    return { ...f, properties: { ...f.properties, share_pct, intensity_pct } };
  });
  // Five equal 20-point bins cover the full 0 – 100 scale cleanly.
  const breaks = [20, 40, 60, 80];

  // --- Delta (Comparativo) --------------------------------------------------
  const metric = DELTA_METRICS.hugo;
  const pairFeats = selectedPair && data.vote_deltas
    ? data.vote_deltas.features.filter(f => f.properties.pair === selectedPair)
    : [];
  const gatedDeltaFeats = pairFeats.filter(f => f.properties[metric.field] !== null && f.properties[metric.field] !== undefined);
  const deltaTotal = gatedDeltaFeats.length ? gatedDeltaFeats.reduce((s, f) => s + Number(f.properties[metric.field]), 0) : null;
  const startTotal = gatedDeltaFeats.reduce((s, f) => s + (Number(f.properties.votos_hugo_inicio) || 0), 0);
  const endTotal = gatedDeltaFeats.reduce((s, f) => s + (Number(f.properties.votos_hugo_fim) || 0), 0);
  const gained = gatedDeltaFeats.reduce((s, f) => s + Math.max(Number(f.properties[metric.field]), 0), 0);
  const lost = gatedDeltaFeats.reduce((s, f) => s + Math.max(-Number(f.properties[metric.field]), 0), 0);
  const pairMeta = gatedDeltaFeats[0]
    ? {
        tipo_par: gatedDeltaFeats[0].properties.tipo_par,
        cargoDiferente: Boolean(gatedDeltaFeats[0].properties.cargo_diferente_hugo),
      }
    : null;

  return (
    <>
      <MapView>
        {showYears && (
          <MarkerLayer
            layerKey={HUGO}
            features={featuresWithShare}
            breaks={breaks}
            onSelect={(p, coords) => setCompareSelection({ props: p, coords })}
          />
        )}
        {showCompare && selectedPair && (
          <DeltaLayer features={pairFeats} metric={metric} selectedDeltaMetric="hugo" data={data} />
        )}
      </MapView>

      <div id="panel" className={panelCollapsed ? 'collapsed' : undefined}>
        <div className="panel-header">
          <div>
            <h1>Mapa eleitoral</h1>
            <div className="subtitle">Hugo Leal · Niterói 2010 → 2026</div>
          </div>
          {/* Mobile-only chevron. Styled to appear only below the 640 px
              breakpoint; invisible on desktop, where the whole panel is
              always visible. Pattern lifted from mobi-pleito-2026. */}
          <button
            type="button"
            className="panel-toggle"
            aria-label={panelCollapsed ? 'Expandir painel' : 'Recolher painel'}
            onClick={() => setPanelCollapsed(v => !v)}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>
        </div>
        <div id="panel-body">

        <div className="section-title">Camadas</div>

        <YearSelectorLayer
          visible={showYears}
          onToggleVisible={() => setShowYears(v => !v)}
          years={years}
          selectedYear={selectedYear}
          onYearChange={setSelectedYear}
        />

        <ComparativoLayer
          visible={showCompare}
          onToggleVisible={() => setShowCompare(v => !v)}
          pairs={pairs}
          selectedPair={selectedPair}
          onSelectPair={setSelectedPair}
          pairMeta={pairMeta}
          deltaTotal={deltaTotal}
          startTotal={startTotal}
          endTotal={endTotal}
          gained={gained}
          lost={lost}
          anoInicio={selectedPair ? Number(selectedPair.split('-')[0]) : null}
          anoFim={selectedPair ? Number(selectedPair.split('-')[1]) : null}
        />

        {showYears && featuresWithShare.length > 0 && (
          <IntensityLegend year={selectedYear} />
        )}
        </div>
      </div>

      <CompareTable selection={compareSelection} data={data} />
    </>
  );
}
