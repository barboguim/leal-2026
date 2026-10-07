export const COLORS = {
  hugo_leal: '#8B4A9C',
  felipe_peixoto: '#1B7952',
  psd: '#1E3A5F',
  psdOlive: '#6E7B3D',
  psdOrange: '#E07A1F',
  deltaLoss: '#B91C1C',
  deltaNeutral: '#EDEFF2',
  deltaGain: '#0F766E',
  profileAccent: '#312E81',
  yearMunicipal: '#CA8A04',
  yearGeral: '#BE185D',
  potentialAccent: '#A6396B',
};

export const LABELS = {
  hugo_leal: 'Hugo Leal',
  felipe_peixoto: 'Felipe Peixoto',
  psd: 'PSD',
};

// leal-2026 is a Hugo-only product (see docs/LINEAGE.md). Felipe/PSD color and
// label entries are retained for now so untouched components that reference
// them do not crash; they are not rendered because BASE_KEYS, LAYER_ORDER, and
// CANDIDATE_ROWS all skip them.
export const BASE_KEYS = ['hugo_leal'];

export const DELTA_METRICS = {
  hugo: { label: 'Hugo', field: 'delta_hugo' },
  felipe: { label: 'Felipe', field: 'delta_felipe' },
  psd: { label: 'PSD', field: 'delta_psd' },
};

export const COMPETITOR_LAYER_BY_METRIC = { hugo: 'hugo_leal', felipe: 'felipe_peixoto' };

export const PROFILE_DIMENSIONS = [
  {
    id: 'genero',
    label: 'Genero',
    metrics: [
      { id: 'mulheres', label: '% Mulheres', field: 'pct_mulheres', mapMetric: true },
      { id: 'homens', label: '% Homens', field: 'pct_homens', mapMetric: true },
      { id: 'genero_nao_informado', label: '% Nao informado', field: 'pct_genero_nao_informado', mapMetric: false },
    ],
  },
  {
    id: 'idade',
    label: 'Faixa etaria',
    metrics: [
      { id: 'jovens_16_24', label: '% Jovens 16-24', field: 'pct_jovens_16_24', mapMetric: true },
      { id: 'adultos_25_59', label: '% Adultos 25-59', field: 'pct_adultos_25_59', mapMetric: true },
      { id: '60_mais', label: '% 60+', field: 'pct_60_mais', mapMetric: true },
      { id: 'idade_nao_informado', label: '% Nao informado', field: 'pct_idade_nao_informado', mapMetric: false },
    ],
  },
  {
    id: 'escolaridade',
    label: 'Escolaridade',
    metrics: [
      { id: 'ate_fundamental', label: '% Ate Fundamental', field: 'pct_ate_fundamental', mapMetric: true },
      { id: 'ensino_medio', label: '% Ensino Medio', field: 'pct_ensino_medio', mapMetric: true },
      { id: 'ensino_superior', label: '% Ensino Superior', field: 'pct_ensino_superior', mapMetric: true },
      { id: 'escolaridade_nao_informado', label: '% Nao informado', field: 'pct_escolaridade_nao_informado', mapMetric: false },
    ],
  },
];

export const PROFILE_METRICS = Object.fromEntries(
  PROFILE_DIMENSIONS.flatMap(d => d.metrics).map(m => [m.id, m])
);
