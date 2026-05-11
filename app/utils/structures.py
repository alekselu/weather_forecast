from enum import StrEnum
from dataclasses import dataclass


@dataclass
class Coordinates:
    latitude: float
    longitude: float


@dataclass
class City:
    name: str
    country_code: str = "ru"


@dataclass
class Place:
    city: City
    coords: Coordinates


class TimePeriod(StrEnum):
    DAILY = "daily"
    HOURLY = "hourly"
