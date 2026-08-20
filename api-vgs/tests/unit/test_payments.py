from sqlalchemy.orm import Session

from app.models import (
    IdempotencyRecord,
    Ledger,
    LineItem,
    ProcessorAttempt,
    Transaction,
    Vacation,
)


def charge_payload(
    *,
    amount_minor: int = 1234,
    currency: str = "USD",
    card_number: str = "4242424242424242",
) -> dict[str, object]:
    return {
        "amount_minor": amount_minor,
        "currency": currency,
        "line_item": "Atlas unified payment",
        "card": {
            "number": card_number,
            "exp_month": 12,
            "exp_year": 2030,
            "cvc": "123",
        },
    }


def test_charge_uses_unified_api_and_replays_idempotently(client) -> None:
    response = client.post(
        "/charges",
        json=charge_payload(),
        headers={"Idempotency-Key": "charge-idem-1"},
    )
    assert response.status_code == 201

    body = response.json()
    assert body["transaction"]["amount"] == "12.34"
    assert body["transaction"]["line_item"] == "Atlas unified payment"
    assert body["line_item"] == "Atlas unified payment"
    assert body["transaction"]["status"] == "succeeded"
    assert body["transaction"]["processor"] == "stripely"
    assert body["ledger"]["entry_type"] == "charge"
    assert body["attempts"][0]["processor"] == "stripely"
    assert body["attempts"][0]["status"] == "succeeded"

    replay = client.post(
        "/charges",
        json=charge_payload(),
        headers={"Idempotency-Key": "charge-idem-1"},
    )
    assert replay.status_code == 201
    assert replay.json() == body

    with Session(client.app.state.engine) as db:
        assert db.query(Transaction).count() == 1
        assert db.query(LineItem).count() == 1
        assert db.query(Vacation).count() == 0
        assert db.query(Ledger).count() == 1
        assert db.query(ProcessorAttempt).count() == 1
        assert db.query(IdempotencyRecord).count() == 1


def test_idempotency_key_cannot_be_reused_for_different_payload(client) -> None:
    response = client.post(
        "/charges",
        json=charge_payload(amount_minor=1000),
        headers={"Idempotency-Key": "charge-idem-conflict"},
    )
    assert response.status_code == 201

    conflict = client.post(
        "/charges",
        json=charge_payload(amount_minor=1001),
        headers={"Idempotency-Key": "charge-idem-conflict"},
    )
    assert conflict.status_code == 409


def test_charge_routes_eur_to_adyenta(client) -> None:
    response = client.post(
        "/charges",
        json=charge_payload(currency="EUR"),
        headers={"Idempotency-Key": "charge-eur"},
    )
    assert response.status_code == 201

    body = response.json()
    assert body["transaction"]["processor"] == "adyenta"
    assert body["attempts"][0]["processor"] == "adyenta"
    assert body["ledger"]["currency"] == "EUR"


def test_retryable_processor_failure_records_failover_attempts(client) -> None:
    response = client.post(
        "/charges",
        json=charge_payload(card_number="4000000000000119"),
        headers={"Idempotency-Key": "charge-retryable-failure"},
    )
    assert response.status_code == 201

    body = response.json()
    assert body["transaction"]["status"] == "failed"
    assert body["ledger"] is None
    assert [attempt["processor"] for attempt in body["attempts"]] == [
        "stripely",
        "adyenta",
    ]
    assert [attempt["status"] for attempt in body["attempts"]] == [
        "failed",
        "failed",
    ]


def test_hard_decline_stops_without_failover(client) -> None:
    response = client.post(
        "/charges",
        json=charge_payload(card_number="4000000000009979"),
        headers={"Idempotency-Key": "charge-hard-decline"},
    )
    assert response.status_code == 201

    body = response.json()
    assert body["transaction"]["status"] == "refused"
    assert body["ledger"] is None
    assert len(body["attempts"]) == 1
    assert body["attempts"][0]["error_code"] == "stolen_card"


def test_refund_appends_negative_ledger_and_report_summarizes_net(client) -> None:
    charge = client.post(
        "/charges",
        json=charge_payload(amount_minor=1000),
        headers={"Idempotency-Key": "charge-refund-report"},
    )
    assert charge.status_code == 201
    transaction_id = charge.json()["transaction"]["id"]

    refund = client.post(
        "/refunds",
        json={"transaction_id": transaction_id, "amount_minor": 400},
        headers={"Idempotency-Key": "refund-partial"},
    )
    assert refund.status_code == 201

    refund_body = refund.json()
    assert refund_body["transaction"]["status"] == "partially_refunded"
    assert refund_body["ledger"]["amount"] == "-4.00"
    assert refund_body["ledger"]["entry_type"] == "refund"
    assert refund_body["attempts"][0]["operation"] == "refund"

    replay = client.post(
        "/refunds",
        json={"transaction_id": transaction_id, "amount_minor": 400},
        headers={"Idempotency-Key": "refund-partial"},
    )
    assert replay.status_code == 201
    assert replay.json() == refund_body

    report_date = charge.json()["transaction"]["created_at"][:10]
    report = client.get(f"/reports/ledger/daily?date={report_date}")
    assert report.status_code == 200
    assert report.json()["currencies"] == [
        {
            "currency": "USD",
            "charges_minor": 1000,
            "refunds_minor": 400,
            "net_minor": 600,
        }
    ]

    with Session(client.app.state.engine) as db:
        assert db.query(Ledger).count() == 2
        assert db.query(ProcessorAttempt).count() == 2


def test_over_refund_is_rejected(client) -> None:
    charge = client.post(
        "/charges",
        json=charge_payload(amount_minor=500),
        headers={"Idempotency-Key": "charge-over-refund"},
    )
    assert charge.status_code == 201

    refund = client.post(
        "/refunds",
        json={"transaction_id": charge.json()["transaction"]["id"], "amount_minor": 501},
        headers={"Idempotency-Key": "refund-too-large"},
    )
    assert refund.status_code == 422
