"""Dictionary of Open-Meteo params and a hourly/daily classifier."""
from __future__ import annotations

HOURLY_PARAMS: frozenset[str] = frozenset(
    {
        "temperature_2m",
        "relative_humidity_2m",
        "precipitation",
        "rain",
        "snowfall",
        "surface_pressure",
        "wind_speed_10m",
        "wind_direction_10m",
        "wind_gusts_10m",
        "cloud_cover",
        "shortwave_radiation",
    }
)

DAILY_PARAMS: frozenset[str] = frozenset(
    {
        "temperature_2m_mean",
        "temperature_2m_min",
        "temperature_2m_max",
        "precipitation_sum",
        "rain_sum",
        "snowfall_sum",
        "precipitation_hours",
        "wind_speed_10m_max",
        "wind_gusts_10m_max",
        "shortwave_radiation_sum",
        "sunshine_duration",
        "uv_index_max",
        "daylight_duration",
        "weather_code",
    }
)


def classify_params(
    params: list[str],
) -> tuple[list[str], list[str], list[str]]:
    """
    Разбивает список параметров на hourly, daily, unknown.

    Returns:
        (hourly, daily, unknown)
    """
    hourly, daily, unknown = [], [], []
    for p in params:
        if p in HOURLY_PARAMS:
            hourly.append(p)
        elif p in DAILY_PARAMS:
            daily.append(p)
        else:
            unknown.append(p)
    return hourly, daily, unknown
