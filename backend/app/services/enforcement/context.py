from typing import Dict, Any, List

class EnforcementContext:
    """
    Immutable shared context object carrying station metadata and Phase 1 Intelligence metrics.
    Ensures that all downstream enforcement modules query standard attributes from a single source.
    """
    def __init__(
        self,
        station_id: str,
        station_name: str,
        city: str,
        latitude: float,
        longitude: float,
        forecast: List[Dict[str, Any]],
        risk_assessment: Dict[str, Any],
        source_attribution: Dict[str, Any],
        confidence: Dict[str, Any],
        municipal_recommendations: List[str],
        weather: Dict[str, Any],
        history_trend: Dict[str, Any],
        profile: Dict[str, Any] = None
    ):
        self._station_id = station_id
        self._station_name = station_name
        self._city = city
        self._latitude = latitude
        self._longitude = longitude
        self._forecast = list(forecast) if forecast else []
        self._risk_assessment = dict(risk_assessment) if risk_assessment else {}
        self._source_attribution = dict(source_attribution) if source_attribution else {}
        self._confidence = dict(confidence) if confidence else {}
        self._municipal_recommendations = list(municipal_recommendations) if municipal_recommendations else []
        self._weather = dict(weather) if weather else {}
        self._history_trend = dict(history_trend) if history_trend else {}
        self._profile = dict(profile) if profile else {}

    @property
    def profile(self) -> Dict[str, Any]:
        return self._profile

    @property
    def station_id(self) -> str:
        return self._station_id

    @property
    def station_name(self) -> str:
        return self._station_name

    @property
    def city(self) -> str:
        return self._city

    @property
    def latitude(self) -> float:
        return self._latitude

    @property
    def longitude(self) -> float:
        return self._longitude

    @property
    def forecast(self) -> List[Dict[str, Any]]:
        return self._forecast

    @property
    def risk_assessment(self) -> Dict[str, Any]:
        return self._risk_assessment

    @property
    def source_attribution(self) -> Dict[str, Any]:
        return self._source_attribution

    @property
    def confidence(self) -> Dict[str, Any]:
        return self._confidence

    @property
    def municipal_recommendations(self) -> List[str]:
        return self._municipal_recommendations

    @property
    def weather(self) -> Dict[str, Any]:
        return self._weather

    @property
    def history_trend(self) -> Dict[str, Any]:
        return self._history_trend
