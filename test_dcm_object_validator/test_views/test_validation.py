"""'Object Validator'-app test-module for validation-endpoint."""

from typing import Optional
from dataclasses import dataclass

import pytest
from dcm_common import LoggingContext as Context
from dcm_common.plugins.demo import DemoPlugin, DemoPluginResult

from dcm_object_validator import app_factory
from dcm_object_validator.config import AppConfig


@dataclass
class _DemoPluginResult(DemoPluginResult):
    valid: Optional[bool] = None


class _DemoPluginValid(DemoPlugin):
    _NAME = "demo-valid"
    _CONTEXT = "validation"
    _RESULT_TYPE = _DemoPluginResult

    def get(self, context, /, **kwargs):
        context.result.log.log(
            Context.INFO, body=f"Working on '{kwargs.get('path')}'"
        )
        if kwargs.get("success", False):
            context.result.log.log(Context.INFO, body="Valid..")
            context.result.valid = True
        return super().get(context, **kwargs)


class _DemoPluginInvalid(DemoPlugin):
    _NAME = "demo-invalid"
    _CONTEXT = "validation"
    _RESULT_TYPE = _DemoPluginResult

    def get(self, context, /, **kwargs):
        if kwargs.get("success", False):
            context.result.log.log(Context.ERROR, body="Invalid..")
            context.result.valid = False
        return super().get(context, **kwargs)


@pytest.fixture(name="app")
def _app(fixtures):
    """Create instance of 'Object Validator'-app in TESTING-state."""

    # setup config-class
    class TestingConfig(AppConfig):
        """Test config"""

        VALIDATION_PLUGINS = [_DemoPluginValid, _DemoPluginInvalid]
        TESTING = True
        FS_MOUNT_POINT = fixtures
        ORCHESTRATION_AT_STARTUP = False
        ORCHESTRATION_DAEMON_INTERVAL = 0.001
        ORCHESTRATION_ORCHESTRATOR_INTERVAL = 0.001
        ORCHESTRATION_ABORT_NOTIFICATIONS_STARTUP_INTERVAL = 0.01

    # create app using factory
    app = app_factory(TestingConfig(), block=True)

    return app


@pytest.fixture(name="client")
def create_client(app):
    """Create testing client."""
    return app.test_client()


def test_validate_minimal(client, object_good, wait_for_report):
    """Minimal test for the POST-/validate-endpoint."""

    response = client.post(
        "/validate",
        json={
            "validation": {
                "target": {"path": str(object_good)},
                "plugins": {
                    "0": {
                        "plugin": _DemoPluginValid.name,
                        "args": {
                            "success": True,
                        },
                    }
                },
            }
        },
    )

    assert response.status_code == 201
    assert client.put("/orchestration?until-idle", json={}).status_code == 200

    # wait for job to finish
    report = wait_for_report(client, response.json["value"])

    assert report["data"]["success"]
    assert report["data"]["valid"]
    assert report["data"]["details"]["0"]["success"]
    assert report["data"]["details"]["0"]["valid"]


def test_validate_invalid(client, object_good, wait_for_report):
    """
    Test behavior for the POST-/validate-endpoint mixed validity.
    """

    response = client.post(
        "/validate",
        json={
            "validation": {
                "target": {"path": str(object_good)},
                "plugins": {
                    "0": {
                        "plugin": _DemoPluginValid.name,
                        "args": {
                            "success": True,
                        },
                    },
                    "1": {
                        "plugin": _DemoPluginInvalid.name,
                        "args": {
                            "success": True,
                        },
                    },
                },
            }
        },
    )

    assert response.status_code == 201
    assert client.put("/orchestration?until-idle", json={}).status_code == 200

    # wait for job to finish
    report = wait_for_report(client, response.json["value"])

    assert report["data"]["success"]
    assert not report["data"]["valid"]
    assert Context.ERROR.name in report["log"]
    assert len(report["log"][Context.ERROR.name]) == 2


def test_validate_unsuccessful(client, object_good, wait_for_report):
    """
    Test behavior for the POST-/validate-endpoint for mixed success.
    """

    response = client.post(
        "/validate",
        json={
            "validation": {
                "target": {"path": str(object_good)},
                "plugins": {
                    "0": {
                        "plugin": _DemoPluginValid.name,
                        "args": {
                            "success": True,
                        },
                    },
                    "1": {
                        "plugin": _DemoPluginValid.name,
                        "args": {
                            "success": False,
                        },
                    },
                },
            }
        },
    )

    assert response.status_code == 201
    assert client.put("/orchestration?until-idle", json={}).status_code == 200

    # wait for job to finish
    report = wait_for_report(client, response.json["value"])

    assert not report["data"]["success"]
    assert "valid" not in report["data"]
    assert Context.ERROR.name in report["log"]
    assert len(report["log"][Context.ERROR.name]) == 3


def test_validate_explicit_path_in_args(
    client, object_good, object_bad, wait_for_report
):
    """
    Test behavior for the POST-/validate-endpoint when explicitly
    passing a path as plugin-arg.
    """

    response = client.post(
        "/validate",
        json={
            "validation": {
                "target": {"path": str(object_good)},
                "plugins": {
                    "0": {
                        "plugin": _DemoPluginValid.name,
                        "args": {
                            "success": True,
                        },
                    },
                    "1": {
                        "plugin": _DemoPluginValid.name,
                        "args": {
                            "path": str(object_bad),
                            "success": True,
                        },
                    }
                },
            }
        },
    )

    assert response.status_code == 201
    assert client.put("/orchestration?until-idle", json={}).status_code == 200

    # wait for job to finish
    report = wait_for_report(client, response.json["value"])

    assert report["data"]["success"]
    assert str(object_good) in str(report["data"]["details"]["0"]["log"])
    assert str(object_bad) not in str(report["data"]["details"]["0"]["log"])
    assert str(object_bad) in str(report["data"]["details"]["1"]["log"])
