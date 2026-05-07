import os
import psycopg
from dataclasses import dataclass, asdict
from typing import Any, Optional, Dict
from contextlib import closing
from psycopg import DatabaseError
from psycopg import Connection as DatabaseConnection


def connection_params() -> dict[str, Any]:
    return {
        "host": os.getenv("DB_HOST", "db"),
        "port": os.getenv("DB_PORT", 5432),
        "dbname": os.getenv("DB_NAME", "weather"),
        "user": os.getenv("DB_USER", "admin"),
        "password": os.getenv("DB_PASSWORD"),
        "connect_timeout": 3,
    }


def connection() -> DatabaseConnection:
    return psycopg.connect(**connection_params())


def is_db_alive(connection: DatabaseConnection) -> bool:
    with closing(connection) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            return cur.fetchone()[0] == 1


@dataclass
class DatabaseHealthResponse:
    status: bool
    response: Optional[str]

    def __str__(self) -> str:
        return f"status: {self.status}\nresponse: {self.response}"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def check_db() -> DatabaseHealthResponse:
    try:
        conn: DatabaseConnection = connection()
        result: bool = is_db_alive(conn)
        return DatabaseHealthResponse(status=result, response=None)
    except DatabaseError as e:
        response_msg: str = f"{type(e).__name__}: {e}\n"
        response_msg += f"sqlstate: {getattr(e, 'sqlstate', None)}\n"

        diag = getattr(e, "diag", None)
        if diag:
            response_msg += f"severity: {diag.severity}\n"
            response_msg += f"message: {diag.message_primary}\n"
            response_msg += f"detail: {diag.message_detail}\n"
            response_msg += f"hint: {diag.message_hint}\n"
            response_msg += f"schema: {diag.schema_name}\n"
            response_msg += f"table: {diag.table_name}\n"
            response_msg += f"column: {diag.column_name}\n"
            response_msg += f"constraint: {diag.constraint_name}\n"
        return DatabaseHealthResponse(status=False, response=response_msg)
    except Exception as e:
        return DatabaseHealthResponse(status=False, response=str(e))
