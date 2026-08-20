import uuid
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Ledger, LineItem, Transaction, Vacation


def test_create_vacation_checkout_persists_atomic_package(client) -> None:
    response = client.post(
        "/vacations",
        json={
            "package_name": "Atlas Tokyo Launch",
            "payment": {
                "amount": "1299.99",
                "currency": "USD",
            },
            "flights": [
                {
                    "name": "Outbound",
                    "flight_number": "VG101",
                    "reference_number": "FLT-ABC",
                    "seat": "12A",
                }
            ],
            "hotels": [
                {
                    "name": "Atlas Shinjuku",
                    "booking_number": "HTL-123",
                    "reference_number": "HOTEL-ABC",
                }
            ],
        },
    )

    assert response.status_code == 201

    body = response.json()
    vacation = body["vacation"]
    transaction = body["transaction"]
    ledger = body["ledger"]

    assert vacation["package_name"] == "Atlas Tokyo Launch"
    assert len(vacation["flights"]) == 1
    assert len(vacation["hotels"]) == 1
    assert transaction["line_item"] == vacation["id"]
    assert transaction["line_item_id"] != vacation["id"]
    assert transaction["psp_ref"]
    assert transaction["status"] == "succeeded"
    assert ledger["transaction_id"] == transaction["id"]
    assert ledger["entry_type"] == "charge"

    read_response = client.get(f"/vacations/{vacation['id']}")
    assert read_response.status_code == 200
    assert read_response.json()["id"] == vacation["id"]


def test_currency_must_be_standardized_to_usd(client) -> None:
    response = client.post(
        "/vacations",
        json={
            "package_name": "Atlas Paris Launch",
            "payment": {
                "amount": "100.00",
                "currency": "EUR",
            },
        },
    )

    assert response.status_code == 422


def test_ledger_entries_are_append_only(client) -> None:
    response = client.post(
        "/vacations",
        json={
            "package_name": "Atlas Lisbon Launch",
            "payment": {
                "amount": "100.00",
                "currency": "USD",
            },
        },
    )
    assert response.status_code == 201

    with Session(client.app.state.engine) as db:
        ledger = db.query(Ledger).one()
        ledger.amount = Decimal("1.00")

        with pytest.raises(ValueError, match="append-only"):
            db.commit()


def test_ledger_refunds_must_be_negative(client) -> None:
    response = client.post(
        "/vacations",
        json={
            "package_name": "Atlas Madrid Launch",
            "payment": {
                "amount": "100.00",
                "currency": "USD",
            },
        },
    )
    assert response.status_code == 201
    transaction_id = uuid.UUID(response.json()["transaction"]["id"])

    with Session(client.app.state.engine) as db:
        db.add(
            Ledger(
                transaction_id=transaction_id,
                amount=Decimal("10.00"),
                currency="USD",
                entry_type="refund",
            ),
        )

        with pytest.raises(IntegrityError):
            db.commit()


def test_ledger_charges_must_be_positive(client) -> None:
    response = client.post(
        "/vacations",
        json={
            "package_name": "Atlas Osaka Launch",
            "payment": {
                "amount": "100.00",
                "currency": "USD",
            },
        },
    )
    assert response.status_code == 201
    transaction_id = uuid.UUID(response.json()["transaction"]["id"])

    with Session(client.app.state.engine) as db:
        db.add(
            Ledger(
                transaction_id=transaction_id,
                amount=Decimal("-10.00"),
                currency="USD",
                entry_type="charge",
            ),
        )

        with pytest.raises(IntegrityError):
            db.commit()


def test_checkout_persists_all_expected_tables(client) -> None:
    response = client.post(
        "/vacations",
        json={
            "package_name": "Atlas Seoul Launch",
            "payment": {
                "amount": "499.50",
                "currency": "USD",
            },
        },
    )
    assert response.status_code == 201

    with Session(client.app.state.engine) as db:
        assert db.query(Vacation).count() == 1
        assert db.query(LineItem).count() == 1
        assert db.query(Transaction).count() == 1
        assert db.query(Ledger).count() == 1
