class WeatherForecastError(Exception):
    """Base application exception."""

    pass


class CityNotFoundError(WeatherForecastError, ValueError):
    """Raised when the city cannot be geocoded."""

    def __init__(self, city: str) -> None:
        self.city = city
        super().__init__(f"City not found or cannot be geocoded: '{city}'")


class ModelNotAvailableError(WeatherForecastError):
    """Raised when no ML model is loaded and cannot produce a forecast."""

    def __init__(self, reason: str = "Model is not loaded") -> None:
        self.reason = reason
        super().__init__(f"Forecast model not available: {reason}")


class InsufficientDataError(WeatherForecastError):
    """Raised when there is not enough historical data to build features."""

    def __init__(self, city: str, required_days: int, available_days: int) -> None:
        self.city = city
        self.required_days = required_days
        self.available_days = available_days
        super().__init__(
            f"Insufficient data for '{city}': "
            f"need {required_days} days, have {available_days}"
        )


class ExternalAPIError(WeatherForecastError):
    """Raised when an external API (e.g. Open-Meteo) returns an error."""

    def __init__(self, service: str, detail: str) -> None:
        self.service = service
        self.detail = detail
        super().__init__(f"External API error [{service}]: {detail}")
