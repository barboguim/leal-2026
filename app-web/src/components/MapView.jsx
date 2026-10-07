import { MapContainer, TileLayer, ZoomControl } from 'react-leaflet';

export default function MapView({ children }) {
  return (
    <MapContainer
      center={[-22.9017, -43.0783]}
      zoom={13}
      zoomControl={false}
      style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, zIndex: 1 }}
    >
      <ZoomControl position="topright" />
      {/* Esri's World_Light_Gray_Base — free, no API key, same light aesthetic
          as Carto's old light_all. CARTO's cdn now requires an API key (seen
          2026-10-07 at carto.com/basemaps/apikey). */}
      <TileLayer
        url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}"
        attribution='Tiles &copy; <a href="https://www.esri.com/">Esri</a>'
        maxZoom={16}
      />
      {children}
    </MapContainer>
  );
}
