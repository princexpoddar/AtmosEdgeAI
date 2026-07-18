import { useEffect, useRef, useState } from "react";
import { MapContainer, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { Search } from "lucide-react";
import { getAqiColor } from "@/constants/aqi";
import Skeleton from "@/components/ui/Skeleton";

// Fix default leaflet icon paths broken by bundlers
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

function buildIcon(station, isSelected) {
  const color = getAqiColor(station.aqi);
  return L.divIcon({
    className: "custom-map-marker-container",
    html: `
      <div class="custom-marker-pulsing${isSelected ? " active" : ""}" style="background-color:${color}"></div>
      <div class="custom-marker-pill${isSelected ? " selected" : ""}" style="border-color:${color};color:${color}">
        <span>${Math.round(station.aqi)}</span>
      </div>
    `,
    iconSize: [34, 34],
    iconAnchor: [17, 17],
  });
}

// Inner component that has access to the map instance
function MarkerLayer({ stations, selectedStationId, onSelectStation, activeLayer }) {
  const map = useMap();
  const markersRef = useRef({});
  const prevStationIdsRef = useRef(new Set());

  useEffect(() => {
    const currentIds = new Set(stations.map((s) => s.id));

    // Remove markers for stations no longer in the list
    prevStationIdsRef.current.forEach((id) => {
      if (!currentIds.has(id) && markersRef.current[id]) {
        markersRef.current[id].remove();
        delete markersRef.current[id];
      }
    });
    prevStationIdsRef.current = currentIds;

    stations.forEach((st) => {
      const isSelected = st.id === selectedStationId;
      const icon = buildIcon(st, isSelected);

      if (markersRef.current[st.id]) {
        // Update icon in-place — no destroy/re-create
        markersRef.current[st.id].setIcon(icon);
      } else {
        // Create marker for new station
        const marker = L.marker([st.latitude, st.longitude], { icon })
          .addTo(map)
          .on("click", () => onSelectStation(st.id));

        marker.bindTooltip(
          `<div class="leaflet-tooltip-card">
            <strong>${st.name}</strong><br/>
            AQI: ${Math.round(st.aqi)} (${st.category})<br/>
            Temp: ${st.temp?.toFixed(1)}°C | Humidity: ${st.humidity?.toFixed(0)}%
          </div>`,
          { direction: "top", offset: [0, -10] }
        );

        markersRef.current[st.id] = marker;
      }
    });
  }, [stations, selectedStationId, activeLayer, map, onSelectStation]);

  // Pan to selected station
  useEffect(() => {
    if (selectedStationId && markersRef.current[selectedStationId]) {
      const latlng = markersRef.current[selectedStationId].getLatLng();
      map.setView(latlng, Math.max(map.getZoom(), 8), { animate: true, duration: 1.2 });
    }
  }, [selectedStationId, map]);

  return null;
}

function TileTheme({ theme }) {
  const map = useMap();
  useEffect(() => {
    const isDark = theme === "dark";
    const url = isDark
      ? "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
      : "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png";
    const attribution = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>';

    map.eachLayer((layer) => {
      if (layer instanceof L.TileLayer) map.removeLayer(layer);
    });
    L.tileLayer(url, { attribution }).addTo(map);
  }, [theme, map]);
  return null;
}

export default function Map({ stations, selectedStationId, onSelectStation, theme = "dark", activeLayer = "aqi" }) {
  const [searchQuery, setSearchQuery] = useState("");

  if (!stations) {
    return <Skeleton className="map-skeleton" />;
  }

  const handleSearch = (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    const matched = stations.find(
      (s) =>
        s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.city.toLowerCase().includes(searchQuery.toLowerCase())
    );
    if (matched) {
      onSelectStation(matched.id);
      setSearchQuery("");
    }
  };

  return (
    <div className="map-root">
      <form onSubmit={handleSearch} className="map-search-form">
        <div className="map-search-wrap">
          <span className="map-search-icon">
            <Search size={13} />
          </span>
          <input
            type="text"
            placeholder="Search stations or cities…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="map-search-input"
          />
        </div>
        <button type="submit" className="btn btn-primary map-search-btn">Go</button>
      </form>

      <MapContainer
        center={[21.0, 78.9]}
        zoom={5}
        zoomControl={false}
        className="map-container"
        style={{ width: "100%", height: "100%", minHeight: "440px" }}
      >
        <TileTheme theme={theme} />
        <MarkerLayer
          stations={stations}
          selectedStationId={selectedStationId}
          onSelectStation={onSelectStation}
          activeLayer={activeLayer}
        />
      </MapContainer>
    </div>
  );
}
