import logging
from sqlalchemy import inspect
from typing import Dict, Any
from typing import TypeAliasType
from app.db.session import ConnectionParams, get_db_connections
from app.utils.structures import TimePeriod, Coordinates, City, Place
from app.core.logging import LoggerAdapter
from app.router.messages.messages import (
    PlacedResponseData,
    ResponseParams,
    ResponseSpecificParams,
)
from app.db.models.city import City as CityTable
from app.db.models.weather_daily import WeatherDaily

default_logger = logging.getLogger(__name__)

logger = LoggerAdapter("ApiDbProxy", default_logger)

TableType = TypeAliasType("TableType", Any)


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
        with self.connection.get_session() as session:
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

    def check_city_existence(self, city: City) -> CityTable:
        with self.connection.get_session() as session:
            cities = session.query(CityTable).filter_by(name=city.name).all()
            if len(cities) == 1:
                return cities[0]
            elif len(cities) == 0:
                raise ValueError(f"No city found with name '{city.name}'")
            else:
                raise ValueError(
                    f"Multiple cities ({len(cities)}) found with name '{city.name}'"
                )

    def get_all_cities(self) -> list[Place]:
        with self.connection.get_session() as session:
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
        db_city: CityTable = self.check_city_existence(city)
        db_lat: float = db_city.latitude
        db_lon: float = db_city.longitude

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
            session.commit()
