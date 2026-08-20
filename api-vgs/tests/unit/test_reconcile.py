import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import Ledger, Transaction


def create_checkout(client) -> dict:
    response = client.post(
        "/vacations",
        json={
            "package_name": "Atlas Tokyo Launch",
            "payment": {
                "amount": "1299.99",
                "currency": "USD",
            },
        },
    )
    assert response.status_code == 201
    return response.json()


def test_reconcile_transaction_updates_records_and_appends_ledger(client) -> None:
    checkout = create_checkout(client)
    transaction_id = checkout["transaction"]["id"]

    response = client.post(
        f"/reconcile/transactions/{transaction_id}",
        json={
            "status": "refunded",
            "processor": "stripely",
            "processor_reference": "re_1QaB3cD4eF5gH6iJ",
            "amount": "50.00",
            "currency": "usd",
            "ledger_entry_type": "refund",
        },
    )

    assert response.status_code == 200

    result = response.json()
    assert result["updated"] is True
    assert result["transaction"]["status"] == "refunded"
    assert result["transaction"]["processor"] == "stripely"
    assert result["transaction"]["processor_reference"] is None
    assert result["transaction"]["reconciled_at"]
    assert result["ledger"]["entry_type"] == "refund"
    assert Decimal(str(result["ledger"]["amount"])) == Decimal("-50.00")
    assert result["ledger"]["currency"] == "USD"
    assert result["ledger"]["processor"] == "stripely"
    assert result["ledger"]["processor_reference"] == "re_1QaB3cD4eF5gH6iJ"

    with Session(client.app.state.engine) as db:
        transaction = db.get(Transaction, uuid.UUID(transaction_id))
        assert transaction is not None
        assert transaction.status == "refunded"
        assert transaction.processor_reference is None
        assert db.query(Ledger).count() == 2


def test_reconcile_transaction_can_update_without_appending_ledger(client) -> None:
    checkout = create_checkout(client)
    transaction_id = checkout["transaction"]["id"]

    response = client.post(
        f"/reconcile/transactions/{transaction_id}",
        json={
            "status": "failed",
            "processor": "adyenta",
            "processor_reference": "8816281234567891",
        },
    )

    assert response.status_code == 200
    assert response.json()["ledger"] is None

    with Session(client.app.state.engine) as db:
        assert db.query(Ledger).count() == 1


def test_reconcile_ledger_movement_requires_processor_reference(client) -> None:
    checkout = create_checkout(client)
    transaction_id = checkout["transaction"]["id"]

    response = client.post(
        f"/reconcile/transactions/{transaction_id}",
        json={
            "status": "refunded",
            "amount": "50.00",
            "currency": "USD",
            "ledger_entry_type": "refund",
        },
    )

    assert response.status_code == 422


def test_reconcile_charge_can_set_transaction_processor_reference(client) -> None:
    checkout = create_checkout(client)
    transaction_id = checkout["transaction"]["id"]

    response = client.post(
        f"/reconcile/transactions/{transaction_id}",
        json={
            "status": "succeeded",
            "processor": "adyenta",
            "processor_reference": "8816281234567890",
        },
    )

    assert response.status_code == 200
    assert response.json()["transaction"]["processor_reference"] == "8816281234567890"


def test_reconcile_transaction_returns_404_for_missing_transaction(client) -> None:
    response = client.post(
        f"/reconcile/transactions/{uuid.uuid4()}",
        json={"status": "failed"},
    )

    assert response.status_code == 404
