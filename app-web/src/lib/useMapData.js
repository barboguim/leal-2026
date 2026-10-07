export function useMapData() {
  return typeof window !== 'undefined' && window.DATA ? window.DATA : null;
}
