"""
Test module for the package `dcm-object-validator-sdk`.
"""

from time import sleep

import pytest
import dcm_object_validator_sdk

from dcm_object_validator import app_factory
from dcm_object_validator.config import AppConfig
from dcm_object_validator.plugins import IntegrityPlugin


@pytest.fixture(name="testing_config")
def _testing_config(file_storage):
    """Returns test-config"""
    # setup config-class
    class TestingConfig(AppConfig):
        VALIDATION_PLUGINS = [IntegrityPlugin]
        ORCHESTRATION_DAEMON_INTERVAL = 0.001
        ORCHESTRATION_ORCHESTRATOR_INTERVAL = 0.001
        FS_MOUNT_POINT = file_storage
    return TestingConfig


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

    # remove None-values in plugin-arg 'default'- or 'example'-fields
    # incorrectly generated by the sdk
    # (https://zivgitlab.uni-muenster.de/ULB/lzvnrw/team-se/dcm-import-module-api/-/issues/48)
    response_dict = response.to_dict()

    def remove_nones(dict_: dict) -> None:
        if "default" in dict_ and dict_["default"] is None:
            del dict_["default"]
        if "example" in dict_ and dict_["example"] is None:
            del dict_["example"]
        for p in dict_.get("properties", {}).values():
            remove_nones(p)
    for plugin in response_dict["configuration"]["plugins"].values():
        remove_nones(plugin["signature"])

    assert response_dict == testing_config().CONTAINER_SELF_DESCRIPTION


def test_validation_report(
    validation_sdk: dcm_object_validator_sdk.ValidationApi, app, run_service,
    object_good, object_good_md5
):
    """Test endpoints POST-/validate and GET-/report."""

    run_service(app)
    submission = validation_sdk.validate(
        {
            "validation": {
                "target": {
                    "path": str(object_good)
                },
                "plugins": {
                    "0": {
                        "plugin": IntegrityPlugin.name,
                        "args": {
                            "batch": False,
                            "value": object_good_md5
                        }
                    }
                }
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
