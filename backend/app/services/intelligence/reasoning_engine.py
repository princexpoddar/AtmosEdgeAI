from abc import ABC, abstractmethod
from backend.app.services.intelligence.context import IntelligenceContext
from backend.app.config.intelligence_rules import STAGNANT_WIND_SPEED_KMH, HIGH_HUMIDITY_THRESHOLD, HIGH_FIRE_INTENSITY_THRESHOLD

class BaseReasoningEngine(ABC):
    """
    Abstract interface for swappable reasoning engines (e.g. Rule-based, LLM-based, or Hybrid).
    """
    @abstractmethod
    def analyze(self, context: IntelligenceContext) -> dict:
        pass

class RuleBasedReasoningEngine(BaseReasoningEngine):
    """
    Rules-based reasoning engine implementing physical and meteorological heuristic checks.
    """
    def analyze(self, context: IntelligenceContext) -> dict:
        reasons = []
        
        # 1. Autoregressive Trend analysis
        hist_df = context.history_df
        if len(hist_df) >= 24:
            recent_pm25 = hist_df["pm25"].tail(24).values
            start_val = recent_pm25[0]
            end_val = recent_pm25[-1]
            diff = end_val - start_val
            if diff > 15.0:
                reasons.append(f"PM2.5 has increased continuously by {diff:.1f} µg/m³ during the last 24 hours.")
            elif diff < -15.0:
                reasons.append(f"PM2.5 has steadily cleared up by {abs(diff):.1f} µg/m³ during the last 24 hours.")
        
        # 2. Meteorological dispersion analysis
        wind_speed = context.current_weather.get("wind_speed", 10.0)
        humidity = context.current_weather.get("humidity", 60.0)
        
        if wind_speed < STAGNANT_WIND_SPEED_KMH:
            reasons.append(f"Low wind speeds ({wind_speed:.1f} km/h) are severely reducing pollutant dispersion.")
        else:
            reasons.append(f"Moderate wind velocity ({wind_speed:.1f} km/h) is facilitating active pollutant transport.")
            
        if humidity > HIGH_HUMIDITY_THRESHOLD:
            reasons.append("High relative atmospheric humidity is promoting local particulate accumulation and swelling.")
            
        # 3. Satellite agricultural transport analysis
        fire_intensity = context.fire_index.get("upwind_fire_intensity", 0.0)
        fire_count = context.fire_index.get("upwind_fire_count", 0)
        if fire_intensity > HIGH_FIRE_INTENSITY_THRESHOLD:
            reasons.append(f"Elevated upwind fire activity ({fire_count} hotspots detected with high intensity) is driving particulate transport into this corridor.")
            
        # Overall narrative
        if not reasons:
            text = "Atmospheric conditions and particulate indicators remain within normal seasonal parameters."
        else:
            text = " ".join(reasons)
            
        return {
            "text": text,
            "reasons_list": reasons
        }
