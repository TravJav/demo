


## API structure

Canonical MVP architecture and advancement rules live in `docs/MVP_ADVANCEMENTS.md`.


models
    specific models, one class per model module


services
    workers
    helpers
    payments
    payment_routing
    processor_adapters
    reports
    reconciliation
    knowledge_base
    vacation_service
    flight_service
    and others associated with the models


repos
    each model has its own dedicated repo that is specific to the respective model
    to avoid diffs, contamination of logic but also to separate concerns and practice good code hygiene
    repositories used by one use case are created from one shared Session object
    line_items is the payment-facing item anchor; transactions do not point directly at vacation rows


routes
    system
    vacations
    payments
    reports
    knowledge_base
    reconcile


dependencies
    repository bundle construction
    service construction
    FastAPI dependency wiring
    database session injection isolated outside route modules

migrations
    Alembic owns schema changes
    app startup upgrades the database to head
    generated revisions must be reviewed before commit


tests
    unit tests live under api-vgs/tests/unit
    pytest discovers unit tests from pyproject.toml
    tests and test dependencies are dev-only and not shipped with runtime builds


services are for interacting with the application, performing ORM queries, we do not want raw queries for any application but windows would be acceptable upon justification and approval that should be flagged to the operator

route boundary
    routes never open database transactions
    routes never call commit, rollback, or db.begin
    routes never import Session or get_db directly
    routes call services and translate service exceptions into HTTP responses


service boundary
    services own transaction scopes
    services coordinate repositories from one shared-session bundle
    services enforce atomic writes and reconciliation behavior


locking boundary
    no broad application locks
    no database locks around external processor calls
    reconciliation can lock one local transaction row while appending ledger movements
    refunds can lock one local transaction row while checking remaining refundable balance and appending ledger movements
    duplicate protection should come first from idempotency and unique movement references


production runtime
    API runs on ECS Fargate behind an Application Load Balancer
    load balancer health checks target GET /health with explicit healthy and unhealthy thresholds
    ECS autoscaling uses CloudWatch thresholds such as ALB request count per target, target response time, CPU, memory, and HTTP 5xx rate
    reconciliation stays outside the request path
    Lambda is acceptable for small bounded reconciliation jobs that fit comfortably inside the 15-minute invocation limit
    prefer an EventBridge-scheduled ECS Fargate Celery worker for larger record sets, backfills, or uncertain processor latency
    Terraform manages the cloud resources as infrastructure as code
    Terraform owns VPC/networking, ECS, ALB, autoscaling, alarms, EventBridge schedules, queue or broker resources, IAM, secrets, logs, and database dependencies
