import { getAqiSlug } from "@/constants/aqi";
import Badge from "@/components/ui/Badge";
import Skeleton from "@/components/ui/Skeleton";

export default function Sidebar({ stations, selectedStationId, onSelectStation, loading }) {
  return (
    <div className="card station-dir-card">
      <h3 className="station-dir-title">CPCB Station Directory</h3>
      <div className="station-dir-list">
        {loading
          ? Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} height="44px" className="station-skeleton" />
            ))
          : stations.map((st) => {
              const isSelected = st.id === selectedStationId;
              const slug = getAqiSlug(st.aqi);
              return (
                <div
                  key={st.id}
                  onClick={() => onSelectStation(st.id)}
                  className={`station-list-row${isSelected ? " active" : ""}`}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => e.key === "Enter" && onSelectStation(st.id)}
                >
                  <div>
                    <span className={`station-row-name${isSelected ? " selected" : ""}`}>{st.name}</span>
                    <span className="station-row-sub">{st.city}, {st.state}</span>
                  </div>
                  <Badge variant={slug}>{st.aqi.toFixed(0)}</Badge>
                </div>
              );
            })}
      </div>
    </div>
  );
}
