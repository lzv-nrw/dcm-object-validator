"""
Test module for the `dcm_object_validator/handlers.py`.
"""

import pytest
from data_plumber_http.settings import Responses

from dcm_object_validator.plugins import IntegrityPlugin
from dcm_object_validator import handlers


@pytest.mark.parametrize(
    ("json", "status"),
    (
        pytest_args := [
            ({"no-validation": None}, Responses().MISSING_REQUIRED.status),
            (
                {
                    "validation": {},
                },
                Responses().MISSING_REQUIRED.status,
            ),
            (
                {"validation": {"target": {}}},
                Responses().MISSING_REQUIRED.status,
            ),
            (
                {"validation": {"target": {"path": "bad"}}},
                Responses().RESOURCE_NOT_FOUND.status,
            ),
            (
                {"validation": {"target": {"path": "dir"}}},
                Responses().GOOD.status,
            ),
            (
                {
                    "validation": {
                        "target": {"path": "dir"},
                        "plugins": None,
                    }
                },
                Responses().BAD_TYPE.status,
            ),
            (
                {
                    "validation": {
                        "target": {"path": "good"},
                        "plugins": {
                            "0": {
                                "plugin": IntegrityPlugin.name,
                                "args": {"manifest": {}},
                            }
                        },
                    }
                },
                Responses().GOOD.status,
            ),
            (
                {
                    "validation": {"target": {"path": "dir"}},
                    "token": None,
                },
                422,
            ),
            (
                {
                    "validation": {"target": {"path": "dir"}},
                    "token": "non-uuid",
                },
                422,
            ),
            (
                {
                    "validation": {"target": {"path": "dir"}},
                    "token": "37ee72d6-80ab-4dcd-a68d-f8d32766c80d",
                },
                Responses().GOOD.status,
            ),
        ]
    ),
    ids=[f"stage {i+1}" for i in range(len(pytest_args))],
)
def test_validate_handler(fixtures, json, status, object_good):
    "Test `get_validate_handler`."

    try:
        if json["validation"]["target"]["path"] == "good":
            json["validation"]["target"]["path"] = str(object_good)
        if json["validation"]["target"]["path"] == "bad":
            json["validation"]["target"]["path"] = str(object_good) + "_"
        if json["validation"]["target"]["path"] == "dir":
            json["validation"]["target"]["path"] = str(
                object_good.parent
            )
    except KeyError:
        pass

    output = handlers.get_validate_handler(
        fixtures, {IntegrityPlugin.name: IntegrityPlugin()}
    ).run(json=json)

    assert output.last_status == status
    if status != Responses().GOOD.status:
        print(output.last_message)
