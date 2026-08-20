import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

os.environ["API_VGS_DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

from app.database import engine, init_db
from app.main import app
from app.models import Base


@pytest.fixture(autouse=True)
def reset_database() -> Generator[None]:
    Base.metadata.drop_all(bind=engine)
    init_db()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client() -> Generator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
