def test_processor_knowledge_base_lists_known_processors(client) -> None:
    response = client.get("/knowledge-base/processors")

    assert response.status_code == 200

    processors = response.json()
    processor_names = {processor["name"] for processor in processors}

    assert processor_names == {"stripely", "adyenta"}
    assert {processor["protocol"] for processor in processors} == {
        "json_https",
        "soap_1_1",
    }


def test_processor_knowledge_base_filters_by_currency(client) -> None:
    response = client.get("/knowledge-base/processors?currency=EUR")

    assert response.status_code == 200
    assert [processor["name"] for processor in response.json()] == ["adyenta"]


def test_processor_knowledge_base_reads_single_profile(client) -> None:
    response = client.get("/knowledge-base/processors/stripely")

    assert response.status_code == 200

    profile = response.json()
    assert profile["idempotency_supported"] is True
    assert profile["amount_unit"] == "minor"
    assert "insufficient_funds" in profile["soft_decline_codes"]


def test_processor_knowledge_base_returns_404_for_unknown_processor(client) -> None:
    response = client.get("/knowledge-base/processors/unknown")

    assert response.status_code == 404
