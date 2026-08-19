# api-vgs

Basic FastAPI service initialized with `uv`, backed by Postgres for the MVP data model in
`../models.md`.

## Development

```sh
uv sync
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
```

## Endpoints

- `GET /health`
- `GET /docs`
- `POST /vacations`
- `GET /vacations/{vacation_id}`

`POST /vacations` atomically writes the vacation package, flights, hotels, transaction, and
ledger entry. Ledger rows are append-only.
