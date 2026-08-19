from collections.abc import Generator

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.models import Base

settings = get_settings()


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
    Base.metadata.create_all(bind=engine)
    install_ledger_append_only_trigger(engine)


def install_ledger_append_only_trigger(bind: Engine) -> None:
    if bind.dialect.name != "postgresql":
        return

    statements = [
        """
        CREATE OR REPLACE FUNCTION prevent_ledger_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'ledger entries are append-only';
        END;
        $$ LANGUAGE plpgsql
        """,
        """
        DROP TRIGGER IF EXISTS prevent_ledger_update ON ledger
        """,
        """
        CREATE TRIGGER prevent_ledger_update
        BEFORE UPDATE OR DELETE ON ledger
        FOR EACH ROW
        EXECUTE FUNCTION prevent_ledger_mutation()
        """,
    ]

    with bind.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def get_db() -> Generator[Session]:
    with SessionLocal() as db:
        yield db
