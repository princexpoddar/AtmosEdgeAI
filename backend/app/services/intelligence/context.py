import pandas as pd
from typing import Dict, Any, List

class IntelligenceContext:
    """
    Immutable shared context to carry all fetched data assets across
    the reasoning pipeline, preventing duplicated database fetches
    and redundant scaling/feature calculations.
    """
    def __init__(
        self,
        station: Any,
        latest_reading: Any,
        history_df: pd.DataFrame,
        forecasts: List[Dict[str, Any]],
        current_weather: Dict[str, Any],
        fire_index: Dict[str, Any]
    ):
        self.station = station
        self.latest_reading = latest_reading
        self.history_df = history_df
        self.forecasts = forecasts
        self.current_weather = current_weather
        self.fire_index = fire_index
