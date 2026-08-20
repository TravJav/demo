# api-vgs

Basic FastAPI service initialized with `uv`, backed by Postgres for the MVP data model in
`../models.md`.

The current MVP architecture rules are captured in `../docs/MVP_ADVANCEMENTS.md`: route modules
stay HTTP-only, dependency wiring constructs a shared-session repository bundle, services own
database transactions, repositories own ORM access, and reconciliation updates append ledger records
instead of mutating history.

## Development

```sh
uv sync
uv run alembic upgrade head
uv run fastapi dev app/main.py
```

The default database URL is `postgresql+psycopg://vgs:vgs@localhost:5433/vgs`. From the repo
root, run the Compose Postgres service before starting the API locally:

```sh
docker compose up postgres
```

## Checks

```sh
uv run pytest
uv run ruff check .
uv run alembic check
```

`uv run alembic upgrade head` applies schema migrations using `API_VGS_DATABASE_URL`.
`uv run alembic revision --autogenerate -m "describe change"` creates the next migration from the
SQLAlchemy model diff; review generated migrations before committing them.

Unit tests live under `tests/unit`, and `uv run pytest` picks that up from
`[tool.pytest.ini_options]` in `pyproject.toml`. Test-only tools are in the `test` dependency group;
the `dev` group is the superset that includes both `test` and `lint`.

Tests are part of the development toolchain only. The Docker image runs `uv sync --no-dev`, copies
only `app/`, `alembic.ini`, and `migrations/`, and `.dockerignore` excludes `tests/`, so unit tests
and test dependencies are not shipped with the runtime service. Alembic is a runtime dependency
because the API applies migrations on startup.

## Endpoints

- `GET /health`
- `POST /charges`
- `GET /charges/{transaction_id}`
- `POST /refunds`
- `GET /reports/ledger/daily`
- `GET /knowledge-base/processors`
- `GET /knowledge-base/processors/{processor_name}`
- `POST /reconcile/transactions/{transaction_id}`
- `GET /docs`
- `POST /vacations`
- `GET /vacations/{vacation_id}`

`POST /vacations` atomically writes the vacation package, flights, hotels, transaction, and
ledger entry. Ledger rows are append-only.

`POST /charges` is the unified processor-agnostic charge API. It accepts integer minor units,
requires an `Idempotency-Key` header, routes by currency across mocked Stripely REST and Adyenta
SOAP adapters, records each processor attempt, and appends a charge ledger entry only when a
processor succeeds.

`POST /refunds` appends a negative ledger entry against the original transaction, records the refund
processor attempt, and rejects over-refunds. `GET /reports/ledger/daily?date=YYYY-MM-DD` summarizes
gross charges, refunds, and net amount by currency from ledger rows.

Ledger entries are signed immutable money movements: charges are positive, refunds are negative,
and adjustments must be non-zero. Movement-specific processor references live on ledger rows, while
the transaction keeps the lifecycle status and original processor reference.

Locking stays narrow: reconciliation locks the local transaction row only while updating state and
appending ledger rows, and refunds lock the local transaction row while checking remaining refundable
balance and appending the refund. Processor calls should not run under a database lock in production;
duplicate protection comes from inbound idempotency keys and unique movement references.

`GET /knowledge-base/processors` exposes the current processor integration knowledge base for
Stripely and Adyenta, including supported currencies, amount conventions, idempotency behavior,
decline codes, and source documents. Pass `?currency=USD`, `?currency=EUR`, or `?currency=GBP`
to filter route candidates.

`POST /reconcile/transactions/{transaction_id}` updates local transaction records from processor
outcomes and can append a ledger entry for refunds or adjustments without mutating historical
ledger rows.
