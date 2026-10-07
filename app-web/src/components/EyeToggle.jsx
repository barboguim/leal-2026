// Visibility toggle: show/hide a map layer. The eye-icon pattern replaces the
// checkbox used in the forked repo. Pattern lifted from mobi-pleito-2026
// (sibling site, same owner, same aesthetic).

const EyeIcon = ({ hidden }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    {hidden ? (
      <>
        <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a17.6 17.6 0 0 1-2.16 3.19M6.61 6.61C3.44 8.64 1 12 1 12s4 8 11 8a9.9 9.9 0 0 0 5.39-1.61M9.88 9.88a3 3 0 1 0 4.24 4.24" />
        <path d="M1 1l22 22" />
      </>
    ) : (
      <>
        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8Z" />
        <circle cx="12" cy="12" r="3" />
      </>
    )}
  </svg>
);

export default function EyeToggle({ visible, onToggle, label }) {
  return (
    <button
      type="button"
      className={'eye-toggle' + (visible ? '' : ' is-hidden')}
      onClick={(e) => { e.stopPropagation(); e.preventDefault(); onToggle?.(); }}
      aria-label={visible ? `Ocultar ${label}` : `Mostrar ${label}`}
      title={visible ? 'Ocultar no mapa' : 'Mostrar no mapa'}
    >
      <EyeIcon hidden={!visible} />
    </button>
  );
}
