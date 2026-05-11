from dataclasses import dataclass, fields, asdict
from datetime import date, datetime
from typing import ClassVar, Any, Dict
from abc import ABC, abstractmethod
from enum import StrEnum

from app.utils.structures import TimePeriod, Coordinates


@dataclass
class ISimpleParams(ABC):
    @abstractmethod
    def as_params(self) -> Dict[str, str]:
        pass


@dataclass
class RequiredRequestParams(ISimpleParams):
    coords: Coordinates

    def __init__(self, latitude: float, longitude: float) -> None:
        self.coords = Coordinates(latitude, longitude)

    def as_params(self) -> Dict[str, str]:
        return asdict(self.coords)

    def coordinates(self) -> Coordinates:
        return self.coords


@dataclass
class TimeFormat:
    time_format: ClassVar[str] = "%Y-%m-%d"

    @classmethod
    def str_to_date(cls, string: str) -> datetime:
        return datetime.strptime(string, cls.time_format)

    @classmethod
    def str_from_date(cls, date: datetime) -> str:
        return date.strftime(cls.time_format)


@dataclass
class TimeRequestParams(TimeFormat, ISimpleParams):
    start_date: date
    end_date: date

    def as_params(self) -> Dict[str, str]:
        return dict(
            map(
                lambda item: (item[0], TimeFormat.str_from_date(item[1])),
                asdict(self).items(),
            )
        )


@dataclass
class DataParams(ABC):
    @classmethod
    @abstractmethod
    def time_period(cls) -> TimePeriod:
        pass

    @classmethod
    def field_names(cls) -> tuple[str, ...]:
        return tuple(f.name for f in fields(cls))


@dataclass
class DailyDataParams(DataParams):
    temperature_2m_mean: float
    temperature_2m_min: float
    temperature_2m_max: float

    @classmethod
    def time_period(cls) -> TimePeriod:
        return TimePeriod.DAILY


# Maybe will be used later
@dataclass
class HourlyDataParams(DataParams):
    temperature_2m: float

    @classmethod
    def time_period(cls) -> TimePeriod:
        return TimePeriod.HOURLY


def _data_params_class(time_period: TimePeriod) -> type[DataParams]:
    match time_period:
        case TimePeriod.DAILY:
            return DailyDataParams
        case TimePeriod.HOURLY:
            return HourlyDataParams
        case _:
            raise ValueError(f"Unknown period: {time_period}")


def data_params_by_period(time_period: TimePeriod, **kwargs) -> DataParams:
    params_class: type[DataParams] = _data_params_class(time_period)
    return params_class(**kwargs)


@dataclass
class Request:
    required_params: RequiredRequestParams
    time_params: TimeRequestParams
    time_periods: list[TimePeriod]
    type: str = "GET"
    url_continuation: str = ""

    def provided_params(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        result |= self.required_params.as_params()
        result |= self.time_params.as_params()
        return result

    def requested_params(self) -> Dict[TimePeriod, tuple[str, ...]]:
        """
        Returns:
          {
            "daily": ("temperature_2m_mean", "temperature_2m_min", ...),
            "hourly": ("temperature_2m",)
          }
        """
        result: Dict[TimePeriod, tuple[str, ...]] = {}
        for period in self.time_periods:
            data_cls: type[DataParams] = _data_params_class(period)
            variable_names = data_cls.field_names()
            result[period] = variable_names
        return result

    def coordinates(self) -> Coordinates:
        return self.required_params.coordinates()


@dataclass
class ResponseSpecificParams:
    time: str

    @classmethod
    def as_params_names(cls) -> tuple[str, ...]:
        return tuple(f.name for f in fields(cls))


@dataclass
class ResponseParams(TimeFormat):
    params: ResponseSpecificParams
    data_params: DataParams

    @classmethod
    def specific_params(cls):
        return ResponseSpecificParams.as_params_names()


@dataclass
class ResponseData:
    data: list[ResponseParams]


@dataclass
class PlacedResponseData:
    coords: Coordinates
    data: ResponseData
