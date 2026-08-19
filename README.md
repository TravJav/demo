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

# demo
