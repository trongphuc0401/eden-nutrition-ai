from collections.abc import Generator

from sqlalchemy.engine.url import make_url
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


def build_engine():
    url = make_url(settings.database_url)
    connect_args = {}
    if url.get_backend_name().startswith("postgresql"):
        connect_args["connect_timeout"] = 3

    return create_engine(
        settings.database_url,
        connect_args=connect_args,
        pool_pre_ping=True,
    )


engine = build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
