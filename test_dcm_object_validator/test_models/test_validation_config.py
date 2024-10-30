"""ValidationConfig-data model test-module."""

import pytest

from dcm_object_validator.models.validation_modules import FileFormatModule
from dcm_object_validator.models import validation_config


@pytest.fixture(name="supported_modules")
def _supported_modules():
    return list(validation_config.SUPPORTED_VALIDATORS.keys()) \
        + list(validation_config.SUPPORTED_PLUGINS.keys())


@pytest.fixture(name="default_kwargs")
def _default_kwargs():
    return {
        "bagit_profile": {
            "bagit_profile_url": "some-url",
            "bagit_profile": {
                "BagIt-Profile-Info": {"Source-Organization": ""}
            },
            "ignore_baginfo_tag_case": False
        }
    }


def test_ValidationConfig_json(supported_modules, default_kwargs):
    """Test property `json` of model `ValidationConfig`."""

    config = validation_config.ValidationConfig(
        supported_modules,
        ["bagit_profile"],
        default_kwargs
    )
    json = config.json

    assert "modules" in json
    assert "rejections" in json


def test_ValidationConfig_default_modules(default_kwargs):
    """Test default modules for model `ValidationConfig`."""

    config = validation_config.ValidationConfig(
        ["bagit_profile"],
        None,
        default_kwargs
    )
    json = config.json

    assert len(json["modules"]) == 1
    assert "bagit_profile" in json["modules"]


def test_ValidationConfig_rejections_not_allowed(default_kwargs):
    """Test property `rejections` in model `ValidationConfig`."""

    config = validation_config.ValidationConfig(
        ["not_bagit_profile"],
        ["bagit_profile"],
        default_kwargs
    )
    json = config.json

    assert len(json["rejections"]) == 1

    assert "bagit_profile" in json["rejections"]


def test_ValidationConfig_rejections_unknown(
    supported_modules, default_kwargs
):
    """Test property `rejections` in model `ValidationConfig`."""

    config = validation_config.ValidationConfig(
        supported_modules,
        ["bagit_profile", "unknown"],
        default_kwargs
    )
    json = config.json

    assert len(json["rejections"]) == 1

    assert "unknown" in json["rejections"]


def test_ValidationConfig_missing_kwarg(supported_modules):
    """Test missing kwarg in model `ValidationConfig`."""

    with pytest.raises(TypeError):
        config = validation_config.ValidationConfig(
            supported_modules,
            ["bagit_profile"],
            {}
        )


def test_ValidationConfig_plugin_basic(supported_modules):
    """Test plugin in modules in model `ValidationConfig`."""

    config = validation_config.ValidationConfig(
        supported_modules,
        [FileFormatModule.plugin_prefix + "jhove"],
        {}
    )
    json = config.json

    assert len(json["modules"]) == 1
    assert FileFormatModule.identifier in json["modules"]
    assert len(config.modules[json["modules"][0]].validators) == 1


def test_ValidationConfig_plugin_multiple_individually(supported_modules):
    """Test adding all plugins individually in model `ValidationConfig`."""

    config = validation_config.ValidationConfig(
        supported_modules,
        validation_config.SUPPORTED_PLUGINS,
        {}
    )
    json = config.json

    assert len(json["modules"]) == 1
    assert FileFormatModule.identifier in json["modules"]
    assert len(config.modules[json["modules"][0]].validators) \
        == len(validation_config.SUPPORTED_PLUGINS)


def test_ValidationConfig_plugin_all(supported_modules):
    """Test adding all plugins via file_format in model `ValidationConfig`."""

    config = validation_config.ValidationConfig(
        supported_modules,
        ["file_format"],
        {}
    )
    json = config.json

    assert len(json["modules"]) == 1
    assert FileFormatModule.identifier in json["modules"]
    assert len(config.modules[json["modules"][0]].validators) \
        == len(validation_config.SUPPORTED_PLUGINS)


def test_ValidationConfig_plugin_single_override(supported_modules):
    """Test adding all plugins via file_format in model `ValidationConfig`."""

    config = validation_config.ValidationConfig(
        supported_modules,
        [FileFormatModule.plugin_prefix + "jhove", "file_format"],
        {}
    )
    json = config.json

    assert len(json["modules"]) == 1
    assert FileFormatModule.identifier in json["modules"]
    assert len(config.modules[json["modules"][0]].validators) \
        == len(validation_config.SUPPORTED_PLUGINS)


def test_ValidationConfig_file_format_not_allowed_but_requested():
    """Test requiring but not allowing 'file_format' in `ValidationConfig`."""

    config = validation_config.ValidationConfig(
        [],
        [FileFormatModule.identifier],
        {}
    )
    json = config.json

    assert len(json["modules"]) == 0


def test_ValidationConfig_file_format_plugin_not_allowed_but_requested():
    """
    Test requiring but not allowing 'file_format_plugin' in `ValidationConfig`.
    """

    config = validation_config.ValidationConfig(
        [],
        [FileFormatModule.plugin_prefix + "jhove"],
        {}
    )
    json = config.json

    assert len(json["modules"]) == 0
