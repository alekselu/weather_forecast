import logging
from dataclasses import dataclass, field
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker
from typing import Any
from app.utils.uitls import LoggerAdapter
from app.utils.uitls import DATABASE_URL

default_logger = logging.getLogger(__name__)

logger = LoggerAdapter("SESSION", default_logger)


def _create_engine() -> Engine:
    try:
        return create_engine(DATABASE_URL)
    except Exception as e:
        logger.critical(f"ERROR occured while creating engine: {e}")
        raise e


@dataclass(frozen=True)
class ConnectionParams:
    db_url: str = DATABASE_URL
    engine: Engine = field(default_factory=_create_engine)

    @property
    def sessionmaker(self):
        return sessionmaker(bind=self.engine)

    def get_session(self):
        return self.sessionmaker()


def get_db_connections() -> ConnectionParams:
    return ConnectionParams()
