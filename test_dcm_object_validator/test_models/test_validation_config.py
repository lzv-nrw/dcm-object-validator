"""Test module for the `ValidationConfig` data model."""

from pathlib import Path
from dcm_common.models.data_model import get_model_serialization_test

from dcm_object_validator.models import Target, ValidationConfig, PluginConfig


test_plugin_config_json = get_model_serialization_test(
    PluginConfig, ((("plugin-id", {}), {}),)
)

test_validation_config_json = get_model_serialization_test(
    ValidationConfig,
    (
        ((Target(Path(".")), {}), {}),
        (
            (
                Target(Path(".")),
                {"0": PluginConfig("plugin-id", {})},
            ),
            {},
        ),
    ),
)
