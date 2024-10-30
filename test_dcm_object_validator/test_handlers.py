"""
Test module for the `dcm_object_validator/handlers.py`.
"""

import pytest
from data_plumber_http.settings import Responses

from dcm_object_validator import handlers


@pytest.fixture(name="validate_object_handler")
def _validate_object_handler(fixtures):
    return handlers.get_validate_object_handler(
        fixtures,
        ["some-module"]
    )


@pytest.mark.parametrize(
    ("json", "status"),
    (pytest_args := [
        (
            {"no-validation": None},
            400
        ),
        (  # missing target
            {"validation": {}},
            400
        ),
        (  # missing path
            {"validation": {"target": {}}},
            400
        ),
        (
            {"validation": {"target": {"path": "bad"}}},
            404
        ),
        (
            {"validation": {"target": {"path": "dir"}}},
            422
        ),
        (
            {"validation": {"target": {"path": "good"}}},
            Responses.GOOD.status
        ),
    ]),
    ids=[f"stage {i+1}" for i in range(len(pytest_args))]
)
def test_validate_object_handler(
    validate_object_handler, json, status, object_good, ip_good
):
    "Test `validate_object_handler`."

    try:
        if json["validation"]["target"]["path"] == "good":
            json["validation"]["target"]["path"] = str(object_good)
        if json["validation"]["target"]["path"] == "bad":
            json["validation"]["target"]["path"] = str(object_good) + "_"
        if json["validation"]["target"]["path"] == "dir":
            json["validation"]["target"]["path"] = str(ip_good)
    except KeyError:
        pass

    output = validate_object_handler.run(json=json)

    assert output.last_status == status
    if status != Responses.GOOD.status:
        print(output.last_message)
    else:
        assert output.data.value["validation"]["target"].path == object_good


@pytest.fixture(name="validate_ip_handler")
def _validate_ip_handler(fixtures):
    return handlers.get_validate_ip_handler(
        fixtures,
        ["some-module"]
    )


@pytest.mark.parametrize(
    ("json", "status"),
    (pytest_args := [
        (
            {"no-validation": None},
            400
        ),
        (  # missing target
            {"validation": {}},
            400
        ),
        (  # missing path
            {"validation": {"target": {}}},
            400
        ),
        (
            {"validation": {"target": {"path": "bad"}}},
            404
        ),
        (
            {"validation": {"target": {"path": "file"}}},
            422
        ),
        (
            {"validation": {"target": {"path": "good"}}},
            Responses.GOOD.status
        ),
    ]),
    ids=[f"stage {i+1}" for i in range(len(pytest_args))]
)
def test_validate_ip_handler(
    validate_ip_handler, json, status, object_good, ip_good
):
    "Test `validate_object_handler`."

    try:
        if json["validation"]["target"]["path"] == "good":
            json["validation"]["target"]["path"] = str(ip_good)
        if json["validation"]["target"]["path"] == "bad":
            json["validation"]["target"]["path"] = str(object_good) + "_"
        if json["validation"]["target"]["path"] == "file":
            json["validation"]["target"]["path"] = str(object_good)
    except KeyError:
        pass

    output = validate_ip_handler.run(json=json)

    assert output.last_status == status
    if status != Responses.GOOD.status:
        print(output.last_message)
    else:
        assert output.data.value["validation"]["target"].path == ip_good
