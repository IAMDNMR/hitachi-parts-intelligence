"""
The database session.

`get_db` is a FastAPI dependency: it hands a route a session and closes it
when the request ends, regardless of whether the route raised. Nothing in
the routers touches the engine directly, so the routers do not know or care
whether they are talking to SQLite or Postgres.
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings

settings = get_settings()

# SQLite needs this flag to allow use across the threads FastAPI's test
# client and dev server both create; Postgres and every other backend
# ignore it, so it is safe to pass unconditionally.
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
