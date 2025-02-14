"""Test module for the `ValidationConfig` data model."""

from pathlib import Path

from dcm_common.models.data_model import get_model_serialization_test

from dcm_object_validator.models import ValidationResult
from dcm_object_validator.plugins.validation.interface import (
    ValidationPluginResult,
    ValidationPluginResultPart,
)


test_validation_plugin_result_part_json = get_model_serialization_test(
    ValidationPluginResultPart,
    (
        ((), {"path": Path(".")}),
        (
            (),
            {"success": True, "valid": True, "path": Path(".")},
        ),
    ),
)


test_validation_plugin_result_json = get_model_serialization_test(
    ValidationPluginResult,
    (
        ((), {}),
        (
            (),
            {
                "success": True,
                "valid": True,
                "records": {"0": ValidationPluginResultPart(path=Path("."))},
            },
        ),
    ),
)


test_validation_result_json = get_model_serialization_test(
    ValidationResult,
    (
        ((), {}),
        (
            (),
            {
                "success": True,
                "valid": True,
                "details": {"0": ValidationPluginResult()},
            },
        ),
    ),
)
