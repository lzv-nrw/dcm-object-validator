"""
Test module for the package `dcm-object-validator-sdk`.
"""

from time import sleep

import pytest
import dcm_object_validator_sdk

from dcm_object_validator import app_factory


@pytest.fixture(name="app")
def _app(testing_config):
    return app_factory(testing_config(), as_process=True)


@pytest.fixture(name="default_sdk", scope="module")
def _default_sdk():
    return dcm_object_validator_sdk.DefaultApi(
        dcm_object_validator_sdk.ApiClient(
            dcm_object_validator_sdk.Configuration(
                host="http://localhost:8080"
            )
        )
    )


@pytest.fixture(name="validation_sdk", scope="module")
def _validation_sdk():
    return dcm_object_validator_sdk.ValidationApi(
        dcm_object_validator_sdk.ApiClient(
            dcm_object_validator_sdk.Configuration(
                host="http://localhost:8080"
            )
        )
    )


def test_default_ping(
    default_sdk: dcm_object_validator_sdk.DefaultApi, app, run_service
):
    """Test default endpoint `/ping-GET`."""

    run_service(app)

    response = default_sdk.ping()

    assert response == "pong"


def test_default_status(
    default_sdk: dcm_object_validator_sdk.DefaultApi, app, run_service
):
    """Test default endpoint `/status-GET`."""

    run_service(app)

    response = default_sdk.get_status()

    assert response.ready


def test_default_identify(
    default_sdk: dcm_object_validator_sdk.DefaultApi, app, run_service,
    testing_config
):
    """Test default endpoint `/identify-GET`."""

    run_service(app)

    response = default_sdk.identify()

    assert response.to_dict() == testing_config().CONTAINER_SELF_DESCRIPTION


@pytest.mark.parametrize(
    ("endpoint", "target"),
    [
        ("ip", "test-bag"),
        ("object", "objects/sample.jpg"),
    ],
    ids=["ip", "object"]
)
def test_validation_report(
    default_sdk: dcm_object_validator_sdk.DefaultApi,
    validation_sdk: dcm_object_validator_sdk.ValidationApi, app, run_service,
    endpoint, target
):
    """Test endpoints `/validate/<X>-POST` and `/report-GET`."""

    run_service(app)
    submission = getattr(validation_sdk, f"validate_{endpoint}")(
        {
            "validation": {
                "target": {
                    "path": target
                },
                "modules": ["file_format"]
            }
        }
    )

    while True:
        try:
            report = validation_sdk.get_report(token=submission.value)
            break
        except dcm_object_validator_sdk.exceptions.ApiException as e:
            assert e.status == 503
            sleep(0.1)

    assert report.data.valid


def test_validation_report_404(
    validation_sdk: dcm_object_validator_sdk.ValidationApi, app, run_service
):
    """Test validation endpoint `/report-GET` without previous submission."""

    run_service(app)

    with pytest.raises(dcm_object_validator_sdk.rest.ApiException) as exc_info:
        validation_sdk.get_report(token="some-token")
    assert exc_info.value.status == 404
