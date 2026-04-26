class WeatherForecastError(Exception):
    """Базовое исключение приложения."""
    pass


class CityNotFoundError(WeatherForecastError):
    """Выбрасывается, когда город не может быть геокодирован."""

    def __init__(self, city: str) -> None:
        self.city = city
        super().__init__(f"Город не найден или не может быть геокодирован: '{city}'")


class ModelNotAvailableError(WeatherForecastError):
    """Выбрасывается, когда не загружена ML-модель и невозможно получить прогноз."""

    def __init__(self, reason: str = "Модель не загружена") -> None:
        self.reason = reason
        super().__init__(f"Модель прогнозирования недоступна: {reason}")


class InsufficientDataError(WeatherForecastError):
    """Выбрасывается, когда недостаточно исторических данных для построения признаков."""

    def __init__(self, city: str, required_days: int, available_days: int) -> None:
        self.city = city
        self.required_days = required_days
        self.available_days = available_days
        super().__init__(
            f"Недостаточно данных для '{city}': "
            f"требуется {required_days} дней, доступно {available_days}"
        )


class ExternalAPIError(WeatherForecastError):
    """Выбрасывается, когда внешний API (например Open-Meteo) возвращает ошибку."""

    def __init__(self, service: str, detail: str) -> None:
        self.service = service
        self.detail = detail
        super().__init__(f"Ошибка внешнего API [{service}]: {detail}")
