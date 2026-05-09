import logging
from sqlalchemy import inspect
from app.db.session import ConnectionParams, get_db_connections
from app.utils.structures import TimePeriod
from app.utils.utils import LoggerAdapter

default_logger = logging.getLogger(__name__)

logger = LoggerAdapter("ApiDbProxy", default_logger)


class ApiDbProxy:
    connection: ConnectionParams = get_db_connections()

    def _from_time_period_to_table_name(self, time_period: TimePeriod) -> str:
        match time_period:
            case TimePeriod.DAILY:
                return "weather_daily"
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
        table_name = self._from_time_period_to_table_name(time_period)
        return self.get_column_names(table_name)
