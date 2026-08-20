from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

from app.database import engine, get_alembic_config


def test_database_bootstrap_uses_alembic_head() -> None:
    config = get_alembic_config()
    expected_head = ScriptDirectory.from_config(config).get_current_head()

    with engine.connect() as connection:
        tables = set(inspect(connection).get_table_names())
        version = connection.execute(
            text("SELECT version_num FROM alembic_version"),
        ).scalar_one()

    assert version == expected_head
    assert {
        "alembic_version",
        "flights",
        "hotels",
        "idempotency_records",
        "ledger",
        "line_items",
        "processor_attempts",
        "transactions",
        "vacations",
    }.issubset(tables)
