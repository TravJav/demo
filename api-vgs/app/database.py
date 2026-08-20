from collections.abc import Generator
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings

settings = get_settings()
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def create_db_engine(database_url: str) -> Engine:
    if database_url == "sqlite+pysqlite:///:memory:":
        return create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

    if database_url.startswith("sqlite"):
        return create_engine(
            database_url,
            connect_args={"check_same_thread": False},
        )

    return create_engine(database_url, pool_pre_ping=True)


engine = create_db_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    run_migrations(engine)


def get_alembic_config() -> Config:
    config = Config(PROJECT_ROOT / "alembic.ini")
    config.set_main_option("sqlalchemy.url", settings.database_url)
    return config


def run_migrations(bind: Engine) -> None:
    config = get_alembic_config()
    with bind.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")


def get_db() -> Generator[Session]:
    with SessionLocal() as db:
        yield db
