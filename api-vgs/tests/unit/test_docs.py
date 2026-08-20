def test_openapi_schema_is_available(client) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200

    schema = response.json()
    assert schema["info"]["title"] == "api-vgs"
    assert schema["info"]["version"] == "0.1.0"
    assert "/" in schema["paths"]
    assert "/charges" in schema["paths"]
    assert "/charges/{transaction_id}" in schema["paths"]
    assert "/health" in schema["paths"]
    assert "/knowledge-base/processors" in schema["paths"]
    assert "/reconcile/transactions/{transaction_id}" in schema["paths"]
    assert "/refunds" in schema["paths"]
    assert "/reports/ledger/daily" in schema["paths"]
    assert "/vacations" in schema["paths"]


def test_swagger_docs_are_available(client) -> None:
    response = client.get("/docs")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_redoc_docs_are_available(client) -> None:
    response = client.get("/redoc")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
