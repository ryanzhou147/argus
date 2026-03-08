import os

from .repositories.base import EventRepository
from .repositories.pg import PostgresEventRepository

_dsn = os.getenv(
    "DATABASE_URL",
    "postgresql://hackcanada:hackcanada147@eventsdb.cje6002y43xf.us-east-2.rds.amazonaws.com:5432/postgres",
)

_repo: EventRepository = PostgresEventRepository(_dsn)


def get_repository() -> EventRepository:
    return _repo
