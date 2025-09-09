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


@pytest.fixture(name="testing_config_w_test_plugins")
def _testing_config_w_test_plugins(testing_config):
    """Create instance of 'Object Validator'-app in TESTING-state."""

    class TestingConfig(testing_config):
        VALIDATION_PLUGINS = [_DemoPluginValid, _DemoPluginInvalid]

    return TestingConfig


def test_validate_minimal(testing_config_w_test_plugins, object_good):
    """Minimal test for the POST-/validate-endpoint."""
    app = app_factory(testing_config_w_test_plugins())
    client = app.test_client()

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

    app.extensions["orchestra"].stop(stop_on_idle=True)
    report = client.get(f"/report?token={response.json['value']}").json

    assert report["data"]["success"]
    assert report["data"]["valid"]
    assert report["data"]["details"]["0"]["success"]
    assert report["data"]["details"]["0"]["valid"]


def test_validate_invalid(testing_config_w_test_plugins, object_good):
    """
    Test behavior for the POST-/validate-endpoint mixed validity.
    """
    app = app_factory(testing_config_w_test_plugins())
    client = app.test_client()

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

    app.extensions["orchestra"].stop(stop_on_idle=True)
    report = client.get(f"/report?token={response.json['value']}").json

    assert report["data"]["success"]
    assert not report["data"]["valid"]
    assert Context.ERROR.name in report["log"]
    assert len(report["log"][Context.ERROR.name]) == 2


def test_validate_unsuccessful(testing_config_w_test_plugins, object_good):
    """
    Test behavior for the POST-/validate-endpoint for mixed success.
    """
    app = app_factory(testing_config_w_test_plugins())
    client = app.test_client()

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

    app.extensions["orchestra"].stop(stop_on_idle=True)
    report = client.get(f"/report?token={response.json['value']}").json

    assert not report["data"]["success"]
    assert "valid" not in report["data"]
    assert Context.ERROR.name in report["log"]
    assert len(report["log"][Context.ERROR.name]) == 3


def test_validate_explicit_path_in_args(
    testing_config_w_test_plugins, object_good, object_bad
):
    """
    Test behavior for the POST-/validate-endpoint when explicitly
    passing a path as plugin-arg.
    """
    app = app_factory(testing_config_w_test_plugins())
    client = app.test_client()

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
                    },
                },
            }
        },
    )
    assert response.status_code == 201

    app.extensions["orchestra"].stop(stop_on_idle=True)
    report = client.get(f"/report?token={response.json['value']}").json

    assert report["data"]["success"]
    assert str(object_good) in str(report["data"]["details"]["0"]["log"])
    assert str(object_bad) not in str(report["data"]["details"]["0"]["log"])
    assert str(object_bad) in str(report["data"]["details"]["1"]["log"])
