# MVP Advancements

This MVP should present a mature backend shape even while vendor integrations are still sandboxed.
The core principle is separation of concerns: HTTP routing, application orchestration, persistence,
and processor knowledge must stay in separate layers.

## Target Architecture

The backend is organized around these layers:

- `app/routes/`: FastAPI routers. Routes validate HTTP input, inject dependencies, call services,
  translate domain errors into HTTP status codes, and return response schemas.
- `app/services/`: Application use cases. Services own orchestration, database transaction
  boundaries, idempotency decisions, reconciliation workflows, and cross-repository coordination.
- `app/repositories/`: ORM persistence adapters. Repositories encapsulate SQLAlchemy reads and
  writes for a specific model or aggregate. `Repositories` is the per-request repository bundle and
  guarantees all repositories share one SQLAlchemy `Session`.
- `app/models/`: SQLAlchemy ORM models. Each table has its own module and class.
- `app/dependencies.py`: FastAPI dependency wiring that constructs the shared repository bundle and
  services from the database session provider. Route modules should depend on service factories from
  here instead of importing `Session` or `get_db` directly.
- `app/schemas.py`: Pydantic request and response contracts for the public API.
- `app/database.py`: Engine, session factory, schema initialization, and database-level safeguards.
- `tests/unit/`: Development-only unit tests. Pytest is configured in `pyproject.toml` to run this
  tree by default.

The route layer must never open database transactions. Routes should depend on services, not on
database sessions directly. Services receive a `Repositories` bundle backed by one shared session,
so every repository write in a use case participates in the same atomic transaction. All
`db.begin()`, `commit`, `rollback`, and multi-record consistency rules belong in services.

## Current MVP Shape

The current implementation follows this split:

- Vacation checkout is handled by `VacationService`, which atomically creates vacation, flight,
  hotel, transaction, and ledger rows.
- Reconciliation is handled by `ReconcileService`, which updates transaction state and appends
  refund or adjustment ledger entries.
- Processor capability knowledge is handled by `KnowledgeBaseService`, which exposes Stripely and
  Adyenta integration constraints from the supplied specs.
- Routers under `app/routes/` do not contain transaction blocks or direct ORM queries.
- Service factories live in `app/dependencies.py`, keeping session wiring outside route modules and
  constructing one `Repositories` bundle per request.
- Ledger entries remain append-only through ORM event guards and the Postgres trigger installed by
  `init_db()`.

## Ledger Model

The ledger is the immutable money-movement history. `Transaction` is the lifecycle anchor for a
payment attempt; `Ledger` records the financial movements tied to that transaction.

Transaction rules:

- `amount` is the original positive transaction amount.
- `currency` is uppercase ISO 4217.
- `status` is constrained to `pending`, `succeeded`, `failed`, `refused`, `refunded`, or `unknown`.
- `processor_reference` is for the original charge or authorization reference, not every later
  movement.

Ledger rules:

- Ledger rows are append-only; they are never updated or deleted.
- `entry_type` is constrained to `charge`, `refund`, or `adjustment`.
- Charges are positive amounts.
- Refunds are negative amounts.
- Adjustments may be positive or negative, but not zero.
- `processor` and `processor_reference` are movement-specific, so a refund can keep its own external
  refund id without overwriting the transaction's original charge reference.
- `(processor, processor_reference)` is unique for non-null movement references.
- `created_at`, `currency`, and `transaction_id` are indexed for reconciliation and reporting paths.

## Locking Posture

This service should not use broad application locks. Payment rails need idempotency, uniqueness, and
short database transactions more than coarse locking.

Use locks narrowly:

- Do not hold a database lock while calling an external processor.
- Use request idempotency keys and processor movement references to prevent duplicate charges,
  refunds, and reconciliation events.
- Use database uniqueness for external movement references whenever they are available.
- Use a short row-level transaction lock on the local `Transaction` row when reconciliation updates
  transaction state and appends a ledger movement for that transaction.
- Use the same lock pattern before adding over-refund protection, because that will need to read the
  existing ledger total and append a new refund atomically.

The current MVP follows this posture: reconciliation locks the target transaction row inside the
service transaction, then appends any ledger movement through the shared-session repository bundle.
Routes still do not know about locking or transactions.

## Route Rules

Routes are thin HTTP adapters:

- Accept request schemas and path/query parameters.
- Resolve services through FastAPI dependencies.
- Call one service method for the use case.
- Map known service exceptions to HTTP errors.
- Return Pydantic response schemas.

Routes must not:

- Call `db.begin()`, `db.commit()`, or `db.rollback()`.
- Import `Session` or `get_db` directly.
- Build multi-model ORM writes directly.
- Contain processor routing, retry, failover, ledger, or reconciliation decisions.
- Use raw SQL.

## Service Rules

Services are the application boundary:

- Own transaction scopes for any write use case.
- Coordinate multiple repositories through one shared-session `Repositories` bundle.
- Enforce atomicity and consistency.
- Decide whether ledger entries should be appended.
- Normalize processor outcomes into local transaction statuses.
- Raise domain-specific exceptions for routes to translate.

Services may use raw SQL only when the ORM cannot express a necessary operation cleanly. Any raw SQL
should be isolated, documented in code, and justified in the relevant service or repository.

## Repository Rules

Repositories keep persistence concerns local:

- One repository should focus on one model or aggregate.
- Repositories used in a single service call must come from the same `Repositories` bundle.
- The bundle must be built from one SQLAlchemy `Session`; mixed-session repository objects are a
  correctness bug because they break atomic writes.
- Repositories expose intent-named methods, not broad query construction to routes.
- Repositories should not own cross-model workflows.
- Repositories should not translate errors into HTTP responses.

## MVP Hardening Priorities

1. Add first-class payment charge and refund routes that use processor-agnostic request schemas.
2. Add processor adapter interfaces for Stripely and Adyenta, with mock implementations matching
   the provided contracts.
3. Add a routing service that chooses processors by currency, capability, failure mode, and retry
   safety.
4. Add idempotency storage for inbound VGS requests, especially because Adyenta does not support
   processor-side idempotency.
5. Extend reconciliation to ingest processor status lookups and normalize external states into local
   transaction and ledger records.
6. Add ledger reporting endpoints for net volume, refunds, processor volume, and daily totals.
7. Add structured audit records for processor attempts, failover decisions, reconciliation updates,
   and manual adjustments.
8. Add Alembic migrations before this leaves demo mode; `create_all()` is acceptable only for the
   current MVP bootstrap.

## Acceptance Bar

Before adding a new write endpoint:

- The route is limited to HTTP concerns.
- The service owns the transaction boundary.
- The service uses one shared-session `Repositories` bundle.
- The repository owns ORM access.
- The ledger is append-only.
- Tests prove success, not-found or validation failures, and rollback behavior when relevant.

Tests and test dependencies must remain dev-only. Runtime builds use `uv sync --no-dev`, do not copy
`tests/`, and should not ship pytest, httpx, or lint tooling.
