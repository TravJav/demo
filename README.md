# VGS Demo

## Backend

The `api-vgs` service was initialized with `uv`:

```sh
uv init api-vgs --bare
cd api-vgs
uv add "fastapi[standard]" pydantic-settings
uv add sqlalchemy "psycopg[binary]"
uv add --dev pytest httpx ruff
```

Architecture and MVP hardening rules are documented in
[`docs/MVP_ADVANCEMENTS.md`](docs/MVP_ADVANCEMENTS.md). In short: routes stay thin,
dependency wiring constructs a shared-session repository bundle, services own database
transactions, repositories own ORM access, and ledger changes are append-only.

Run it locally:

```sh
cd api-vgs
uv sync
uv run fastapi dev app/main.py
```

The local default database URL is `postgresql+psycopg://vgs:vgs@localhost:5433/vgs`.

Checks:

```sh
cd api-vgs
uv run pytest
uv run ruff check .
```

`api-vgs` keeps unit tests under `tests/unit`; `pyproject.toml` points pytest there, so
`uv run pytest` is the normal dev command. Test dependencies are in the `test` group and the `dev`
group includes both `test` and `lint`. Runtime builds use `uv sync --no-dev`, copy only `app/`, and
exclude `tests/` from the Docker context.

## Frontend

The React TypeScript frontend was created from the README's Vite template command:

```sh
pnpm create vite@latest frontend --template react-ts
cd frontend
pnpm install
```

If `pnpm` is not installed directly, use Corepack:

```sh
corepack pnpm@10.18.3 install
```

## Docker

Start the API, frontend, and memory-backed Postgres database:

```sh
docker compose up --build
```

Services:

- API: `http://localhost:8000`
- API health: `http://localhost:8000/health`
- API docs: `http://localhost:8000/docs`
- Processor knowledge base: `http://localhost:8000/knowledge-base/processors`
- Transaction reconciliation: `POST http://localhost:8000/reconcile/transactions/{transaction_id}`
- Frontend: `http://localhost:5174`
- Postgres: `localhost:5433`

Compose defines the shared `vgs-network` bridge network for all containers. The `postgres`
service stores `/var/lib/postgresql/data` on `tmpfs`, so database state is ephemeral and
memory-backed.

## API Model

The backend creates five tables from `models.md`:

- `vacations`
- `flights`, with `vacation_id -> vacations.id`
- `hotels`, with `vacation_id -> vacations.id`
- `transactions`, with `line_item -> vacations.id`
- `ledger`, with `transaction_id -> transactions.id`

All `id` fields are primary keys. Ledger rows are append-only at the API layer and with a
Postgres trigger that rejects `UPDATE` and `DELETE`.

Ledger rows are signed money movements tied to a transaction: charges are positive, refunds are
negative, and adjustments must be non-zero. Processor references on ledger rows are
movement-specific, so refund references do not overwrite the transaction's original charge
reference.

The API avoids broad locks. Reconciliation uses a short local transaction-row lock while updating
state and appending ledger movements; external processor calls should happen outside database locks
and rely on idempotency keys plus unique movement references.

Create an atomic vacation checkout:

```sh
curl -X POST http://localhost:8000/vacations \
  -H 'Content-Type: application/json' \
  -d '{
    "package_name": "Atlas Tokyo Launch",
    "payment": {
      "amount": "1299.99",
      "currency": "USD"
    },
    "flights": [
      {
        "name": "Outbound",
        "flight_number": "VG101",
        "reference_number": "FLT-ABC",
        "seat": "12A"
      }
    ],
    "hotels": [
      {
        "name": "Atlas Shinjuku",
        "booking_number": "HTL-123",
        "reference_number": "HOTEL-ABC"
      }
    ]
  }'
```

The endpoint writes vacation, flights, hotels, transaction, and ledger rows inside one database
transaction. If any insert fails, the whole checkout is rolled back.

Inspect processor capabilities:

```sh
curl http://localhost:8000/knowledge-base/processors
curl http://localhost:8000/knowledge-base/processors?currency=EUR
```

Reconcile a transaction and append a refund ledger movement:

```sh
curl -X POST http://localhost:8000/reconcile/transactions/{transaction_id} \
  -H 'Content-Type: application/json' \
  -d '{
    "status": "refunded",
    "processor": "stripely",
    "processor_reference": "re_1QaB3cD4eF5gH6iJ",
    "amount": "50.00",
    "currency": "USD",
    "ledger_entry_type": "refund"
  }'
```

# demo
