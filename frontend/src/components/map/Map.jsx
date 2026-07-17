import { useEffect, useRef, useState } from "react";

export default function Map({ stations, selectedStationId, onSelectStation, theme, activeLayer }) {
  const mapContainerRef = useRef(null);
  const mapRef = useRef(null);
  const markersRef = useRef({});
  const [searchQuery, setSearchQuery] = useState("");
  const [leafletLoaded, setLeafletLoaded] = useState(false);

  useEffect(() => {
    if (window.L) {
      setLeafletLoaded(true);
    } else {
      const interval = setInterval(() => {
        if (window.L) {
          setLeafletLoaded(true);
          clearInterval(interval);
        }
      }, 100);
      return () => clearInterval(interval);
    }
  }, []);

  const aqiColors = {
    good: "#10b981",
    satisfactory: "#3b82f6",
    moderate: "#f59e0b",
    poor: "#ef4444",
    "very-poor": "#8b5cf6",
    severe: "#7c2d12"
  };

  const getAqiCategory = (aqi) => {
    if (aqi <= 50) return "good";
    if (aqi <= 100) return "satisfactory";
    if (aqi <= 200) return "moderate";
    if (aqi <= 300) return "poor";
    if (aqi <= 400) return "very-poor";
    return "severe";
  };

  useEffect(() => {
    if (!leafletLoaded || !mapContainerRef.current || mapRef.current) return;

    try {
      const map = window.L.map(mapContainerRef.current, {
        center: [21.0, 78.9],
        zoom: 5,
        zoomControl: false
      });

      window.L.control.zoom({ position: "bottomright" }).addTo(map);
      mapRef.current = map;
    } catch (e) {
      console.error("Leaflet initialization failed:", e);
    }

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, [leafletLoaded]);

  useEffect(() => {
    if (!leafletLoaded || !mapRef.current) return;

    try {
      mapRef.current.eachLayer((layer) => {
        if (layer instanceof window.L.TileLayer) {
          mapRef.current.removeLayer(layer);
        }
      });

      const isDark = theme === "dark";
      const tileUrl = isDark
        ? "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        : "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png";

      const attribution = isDark
        ? '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
        : '&copy; OpenStreetMap contributors &copy; CARTO';

      window.L.tileLayer(tileUrl, { attribution }).addTo(mapRef.current);
    } catch (e) {
      console.error("Leaflet tile layer update failed:", e);
    }
  }, [leafletLoaded, theme]);

  useEffect(() => {
    if (!leafletLoaded || !mapRef.current || !stations) return;

    try {
      const map = mapRef.current;
      
      Object.keys(markersRef.current).forEach((id) => {
        map.removeLayer(markersRef.current[id]);
      });
      markersRef.current = {};

      stations.forEach((st) => {
        const category = getAqiCategory(st.aqi);
        const color = aqiColors[category];
        const isSelected = st.id === selectedStationId;

        let markerText = st.aqi.toFixed(0);
        if (activeLayer === "weather") {
          markerText = `${st.temp.toFixed(0)}°`;
        } else if (activeLayer === "wind") {
          markerText = "💨";
        }

        const icon = window.L.divIcon({
          className: "custom-map-marker-container",
          html: `
            <div class="custom-marker-pulsing ${isSelected ? "active" : ""}" style="background-color: ${color}"></div>
            <div class="custom-marker-pill ${isSelected ? "selected" : ""}" style="border-color: ${color}; color: ${color}">
              <span class="marker-val">${markerText}</span>
            </div>
          `,
          iconSize: [34, 34],
          iconAnchor: [17, 17]
        });

        const marker = window.L.marker([st.latitude, st.longitude], { icon })
          .addTo(map)
          .on("click", () => {
            onSelectStation(st.id);
          });

        marker.bindTooltip(`
          <div class="leaflet-tooltip-card">
            <strong>${st.name}</strong><br/>
            <span>AQI: ${st.aqi.toFixed(0)} (${st.category})</span><br/>
            <span>Temp: ${st.temp.toFixed(1)}°C | Humidity: ${st.humidity.toFixed(0)}%</span>
          </div>
        `, { direction: "top", offset: [0, -10] });

        markersRef.current[st.id] = marker;
      });

      if (selectedStationId && markersRef.current[selectedStationId]) {
        const marker = markersRef.current[selectedStationId];
        map.setView(marker.getLatLng(), 8, { animate: true, duration: 1.5 });
      }
    } catch (e) {
      console.error("Marker rendering failed:", e);
    }
  }, [leafletLoaded, stations, selectedStationId, activeLayer]);

  const handleSearch = (e) => {
    e.preventDefault();
    if (!leafletLoaded || !searchQuery.trim() || !mapRef.current) return;

    const matched = stations.find(s => 
      s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.city.toLowerCase().includes(searchQuery.toLowerCase())
    );

    if (matched) {
      onSelectStation(matched.id);
      setSearchQuery("");
    }
  };

  return (
    <div style={{ position: "relative", width: "100%", height: "100%" }}>
      {!leafletLoaded ? (
        <div style={{ display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", height: "100%", background: "var(--bg-3)", color: "var(--text-3)", gap: "10px" }}>
          <div className="loader-spinner"></div>
          <span>Loading dynamic map engine...</span>
        </div>
      ) : (
        <>
          <form onSubmit={handleSearch} style={{ position: "absolute", top: "15px", left: "15px", zIndex: 1000, display: "flex", gap: "8px" }}>
            <div style={{ position: "relative" }}>
              <i className="fa fa-search" style={{ position: "absolute", left: "12px", top: "10px", color: "var(--text-3)" }}></i>
              <input
                type="text"
                placeholder="Search stations or cities..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  padding: "8px 12px 8px 34px",
                  borderRadius: "20px",
                  border: "1px solid var(--border)",
                  background: "var(--bg-3)",
                  color: "var(--text-1)",
                  fontSize: "12px",
                  width: "240px",
                  boxShadow: "var(--shadow-md)",
                  outline: "none"
                }}
              />
            </div>
            <button
              className="btn btn-primary"
              type="submit"
              style={{ height: "32px", borderRadius: "20px", padding: "0 14px", display: "flex", alignItems: "center" }}
            >
              Go
            </button>
          </form>
          <div ref={mapContainerRef} style={{ width: "100%", height: "100%" }} />
        </>
      )}
    </div>
  );
}
