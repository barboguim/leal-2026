import ProfileSection from './ProfileSection';

export default function ProfilePopupContent({ p }) {
  return (
    <div>
      <div className="popup-title">{p.nm_local || `Local ${p.nr_local}`}</div>
      <div className="popup-bairro">{p.bairro || ''}</div>
      <div className="popup-row"><span className="popup-label">Ano</span><span className="popup-val">{p.ano}</span></div>
      <ProfileSection props={p} defaultOpen />
    </div>
  );
}
