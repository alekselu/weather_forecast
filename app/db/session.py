import logging
from dataclasses import dataclass, field
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.logging import LoggerAdapter
from app.utils.utils import DATABASE_URL

default_logger = logging.getLogger(__name__)
logger = LoggerAdapter("SESSION", default_logger)


def _create_engine() -> Engine:
    try:
        return create_engine(DATABASE_URL)
    except Exception as e:
        logger.critical(f"ERROR occurred while creating engine: {e}")
        raise


@dataclass(frozen=True)
class ConnectionParams:
    db_url: str = DATABASE_URL
    engine: Engine = field(default_factory=_create_engine)
    session_factory: sessionmaker = field(init=False)

    def __post_init__(self):
        object.__setattr__(
            self,
            "session_factory",
            sessionmaker(bind=self.engine),
        )

    def get_session(self) -> Session:
        return self.session_factory()

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def close_engine(self) -> None:
        self.engine.dispose()


db_connections = ConnectionParams()


def get_db_connections() -> ConnectionParams:
    return db_connections
