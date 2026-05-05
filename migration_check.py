from alembic.config import Config
from alembic import command
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os
import logging


logger = logging.getLogger(__name__)

alembic_cfg = Config("alembic.ini")

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(BASE_DIR, ".env"))

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    context = MigrationContext.configure(conn)
    current_rev = context.get_current_revision()

script = ScriptDirectory.from_config(alembic_cfg)
head_rev = script.get_current_head()

if current_rev != head_rev:
    print("Need to apply migrations")
else:
    print("All migrations applied")
