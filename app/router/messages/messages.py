from dataclasses import dataclass, fields, asdict
from datetime import date, datetime
from typing import ClassVar, Any, Dict
from abc import ABC, abstractmethod


@dataclass
class NecessaryRequestParams:
    latitude: float
    longitude: float


@dataclass
class TimeFormat:
    time_format: ClassVar[str] = "%Y-%m-%d"

    @classmethod
    def str_to_date(cls, string: str):
        return datetime.strptime(string, cls.time_format)


@dataclass
class TimeRequestParams:
    start_date: date
    end_date: date
    _time_format: ClassVar[TimeFormat] = TimeFormat()

    def as_params(self) -> Dict[str, str]:
        return dict(
            map(
                lambda item: (item[0], item[1].strftime(self._time_format.time_format)),
                asdict(self).items(),
            )
        )

    @classmethod
    def str_to_date(cls, string: str):
        return cls._time_format.str_to_date(string)


@dataclass
class DataParams(ABC):
    @classmethod
    @abstractmethod
    def get_time_period(cls) -> str:
        pass


@dataclass
class DailyDataParams(DataParams):
    temperature_2m_mean: float
    temperature_2m_min: float
    temperature_2m_max: float

    @classmethod
    def get_time_period(cls) -> str:
        return "daily"


# Maybe will be used later
@dataclass
class HourlyDataParams(DataParams):
    temperature_2m: float

    @classmethod
    def get_time_period(cls) -> str:
        return "hourly"


def get_DataParams_by_period(data_time_period: str, **kwargs) -> DataParams:
    match data_time_period:
        case "daily":
            return DailyDataParams(**kwargs)
        case "hourly":
            return HourlyDataParams(**kwargs)
        case _:
            raise ValueError(f"Unknown period: {data_time_period}, kwargs: {kwargs}")


@dataclass
class Request:
    geo_params: NecessaryRequestParams
    time_params: TimeRequestParams
    data_params: list[type[DataParams]]
    type: str = "GET"
    url_continuation: str = ""

    def get_provided_params(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        result |= asdict(self.geo_params)
        result |= self.time_params.as_params()
        return result

    def get_requested_params(self) -> Dict[str, tuple[str, ...]]:
        """
        Returns:
          {
            "daily": ("temperature_2m_mean", "temperature_2m_min", ...),
            "hourly": ("temperature_2m",)
          }
        """
        result: Dict[str, tuple[str, ...]] = {}
        for data_cls in self.data_params:
            period = data_cls.get_time_period()
            variable_names = tuple(f.name for f in fields(data_cls))
            result[period] = variable_names
        return result


@dataclass
class ResponseParams:
    time: str
    data_params: DataParams
    _time_format: ClassVar[TimeFormat] = TimeFormat()

    @classmethod
    def get_requested_params_except_data(cls):
        return set(f.name for f in fields(cls) if f.name != "data_params")


@dataclass
class ResponseData:
    data: list[ResponseParams]
