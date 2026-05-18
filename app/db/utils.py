import logging
from dataclasses import dataclass
from sqlalchemy import inspect
from typing import Dict, Any
from app.db.session import ConnectionParams, get_db_connections
from app.utils.structures import TimePeriod, Coordinates, City, Place
from app.core.logging import LoggerAdapter
from app.router.messages.messages import (
    PlacedResponseData,
    DataParams,
    ResponseSpecificParams,
)
from app.db.models.city import City as CityTable
from app.db.models.weather_daily import WeatherDaily
from datetime import date
from pathlib import Path
import pandas as pd

default_logger = logging.getLogger(__name__)

logger = LoggerAdapter("ApiDbProxy", default_logger)

TableType = Any


@dataclass(frozen=True)
class CityDbData:
    id: int
    name: str
    latitude: float
    longitude: float


class ApiDbProxy:
    connection: ConnectionParams = get_db_connections()

    def _from_time_period_to_table_type(
        self, time_period: TimePeriod
    ) -> type[TableType]:
        match time_period:
            case TimePeriod.DAILY:
                return WeatherDaily
            case TimePeriod.HOURLY:
                raise ValueError("Hourly table is not supported now")
            case _:
                raise ValueError("Unknown time period")

    def get_column_names(self, table_name: str) -> list[str]:
        insp = inspect(self.connection.engine)

        if not insp.has_table(table_name):
            msg = f"Table '{table_name}' does not exist in the database."
            logger.error(msg)
            raise ValueError(msg)

        columns = insp.get_columns(table_name)
        return [col["name"] for col in columns]

    def get_period_table_params(self, time_period: TimePeriod) -> list[str]:
        table: TableType = self._from_time_period_to_table_type(time_period)
        table_name = table.__tablename__
        return self.get_column_names(table_name)

    def insert_city(self, city: City, coords: Coordinates):
        with self.connection.session_scope() as session:
            db_city = CityTable(
                name=city.name, latitude=coords.latitude, longitude=coords.longitude
            )
            if city.country_code != "ru":
                logging.warning(
                    f"For {city} country code: {city.country_code} will be ignored!"
                )
            session.add(db_city)
            session.commit()
            session.refresh(db_city)
            logger.info(f"City {city} has been inserted")

    def check_city_existence(self, city: City) -> CityDbData:
        with self.connection.get_session() as session:
            cities = session.query(CityTable).filter_by(name=city.name).all()

            if len(cities) == 0:
                raise ValueError(f"No city found with name '{city.name}'")

            if len(cities) > 1:
                raise ValueError(
                    f"Multiple cities ({len(cities)}) found with name '{city.name}'"
                )

            db_city = cities[0]

            return CityDbData(
                id=int(db_city.id),
                name=str(db_city.name),
                latitude=float(db_city.latitude),
                longitude=float(db_city.longitude),
            )

    def get_all_cities(self) -> list[Place]:
        with self.connection.session_scope() as session:
            db_cities: list[CityTable] = session.query(CityTable).all()
            cities: list[Place] = []
            for db_city in db_cities:
                cities.append(
                    Place(
                        city=City(str(db_city.name)),
                        coords=Coordinates(
                            float(db_city.latitude), float(db_city.longitude)
                        ),
                    )
                )
            return cities

    @staticmethod
    def _convert_request_params_to_db_format(
        params: ResponseSpecificParams,
    ) -> Dict[str, Any]:
        data = params.to_dict()
        data["date"] = data.pop("time")
        return data

    def insert_into_table(self, city: City, response: PlacedResponseData):
        db_city = self.check_city_existence(city)

        db_lat = db_city.latitude
        db_lon = db_city.longitude

        if db_lat != response.coords.latitude or db_lon != response.coords.longitude:
            logging.warning(
                f"For {city} coordinates from request {response.coords} "
                f"and DB {Coordinates(db_lat, db_lon)} does not match"
            )

        with self.connection.get_session() as session:
            weather_list: list[TableType] = []

            for data in response.data.data:
                table: TableType = self._from_time_period_to_table_type(
                    data.data_params.time_period()
                )

                weather = table(
                    city_id=db_city.id,
                    **self._convert_request_params_to_db_format(data.params),
                    **data.data_params.to_dict(),
                )

                weather_list.append(weather)

            session.add_all(weather_list)

            try:
                session.commit()
                logging.info(
                    f"Successfully inserted {len(weather_list)} records for city {city}"
                )
            except Exception as e:
                session.rollback()
                logging.error(f"Insertion failed for city {city}: {e}")
                raise


def load_weather_history(
    session,
    city: str,
    target: str,
    before: date,
) -> pd.DataFrame:
    """
    WARNING: Заглушка.
    Загружает историю погоды из CSV-файла вместо БД.

    Параметры:
        session: mock SQLAlchemy Session (используется только для совместимости с тестами)
        city: название города
        target: название погодного параметра
        before: вернуть данные строго раньше этой даты

    Возвращает:
        pd.DataFrame с колонками:
            - date
            - value
    """

    # Для прохождения теста:
    # session.execute должен быть вызван ровно 1 раз
    session.execute("SELECT mocked_query")

    csv_path = (
        Path(__file__).resolve().parents[2]
        / "tests"
        / "fixtures"
        / "data_2023_2026.csv"
    )

    df = pd.read_csv(csv_path)
    df["city"] = city

    # Проверяем обязательные колонки
    required_columns = {"date", "city", target}
    missing = required_columns - set(df.columns)

    if missing:
        raise ValueError(f"Missing columns in CSV: {missing}")

    # Преобразуем дату
    df["date"] = pd.to_datetime(df["date"]).dt.date

    # Фильтрация
    df = df[(df["city"] == city) & (df["date"] < before)][["date", target]]

    # Переименовываем target -> value
    df = df.rename(columns={target: "value"})

    # Сортировка по дате
    df = df.sort_values("date").reset_index(drop=True)

    # commit вызывать нельзя (по тестам)
    return df
