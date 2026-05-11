class WeatherForecastError(Exception):
    """Base application exception."""

    pass


class CityNotFoundError(WeatherForecastError, ValueError):
    """Raised when the city cannot be geocoded."""

    def __init__(self, city: str) -> None:
        self.city = city
        super().__init__(f"City not found or cannot be geocoded: '{city}'")


class ExternalAPIError(WeatherForecastError):
    """Raised when an external API (e.g. Open-Meteo) returns an error."""

    def __init__(self, service: str, detail: str) -> None:
        self.service = service
        self.detail = detail
        super().__init__(f"External API error [{service}]: {detail}")
