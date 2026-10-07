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
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>'
        maxZoom={19}
      />
      {children}
    </MapContainer>
  );
}
