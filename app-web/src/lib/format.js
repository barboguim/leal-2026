export function electionType(year) {
  return Number(year) % 4 === 0 ? 'Municipal' : 'Geral';
}

// Shared reason labels for candidacy_status_* fields — used both in the
// per-feature delta popup and the aggregate stats-panel N/A state, so the
// wording stays consistent everywhere a gated-out candidacy is explained.
export const STATUS_LABELS = {
  nao_concorreu: 'nao concorreu',
  nao_concorreu_inicio: 'nao concorreu no ano inicial',
  nao_concorreu_fim: 'nao concorreu no ano final',
  tipo_incompativel: 'tipos de eleicao incompativeis',
  partido_inexistente: 'partido ainda nao existia',
};

export function electionPairLabel(startYear, endYear) {
  return `${electionType(startYear)} -> ${electionType(endYear)}`;
}

export function formatSigned(value) {
  const n = Math.round(Number(value) || 0);
  return `${n > 0 ? '+' : ''}${n.toLocaleString('pt-BR')}`;
}

export function formatPct(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return '-';
  return `${n > 0 ? '+' : ''}${n.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`;
}
