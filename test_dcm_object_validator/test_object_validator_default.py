"""'Object Validator'-app test-module for default-endpoints."""

import pytest


def test_ping(client):
    """Test ping route."""
    response = client.get("/ping")
    assert response.status_code == 200
    assert response.data == b"pong"

def test_status(client):
    """Test status route."""
    response = client.get("/status")
    assert response.status_code == 200

    assert "ready" in response.json
    assert isinstance(response.json["ready"], bool)

def test_identify(client):
    """Test identify route."""
    response = client.get("/identify")
    assert response.status_code == 200

    for p, t in {
        "api_version": str,
        "container_version": str,
        "validator_lib_version": str,
        "default_profile_version": str,
        "default_profile_identifier": str,
        "description": str,
        "modules": list
    }.items():
        assert p in response.json
        assert isinstance(response.json[p], t)


@pytest.mark.parametrize(
    "endpoint",
    ["ping", "status", "identify"]
)
def test_unknown_query_input(client, endpoint):
    """
    Test default-blueprint endpoint' for acceptance of unknown query.
    """

    response = client.get(f"/{endpoint}?query")
    assert response.status_code == 400
