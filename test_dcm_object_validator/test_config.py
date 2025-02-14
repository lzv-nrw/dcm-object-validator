"""
Test module for the `dcm_object_validator/config.py`.
"""

import pytest

from dcm_object_validator.plugins import (
    FidoMIMETypePlugin,
    IntegrityPlugin,
    JHOVEFidoMIMETypePlugin,
)
from dcm_object_validator.config import AppConfig


RUN_JHOVE_TESTS = JHOVEFidoMIMETypePlugin.requirements_met()


def test_identify_plugins():
    """Test method `set_identity` of `AppConfig`."""

    class ThisAppConfig(AppConfig):
        """Test config."""

        IDENTIFICATION_PLUGINS = [FidoMIMETypePlugin]
        VALIDATION_PLUGINS = [IntegrityPlugin]

    plugins = ThisAppConfig().CONTAINER_SELF_DESCRIPTION["configuration"][
        "plugins"
    ]

    assert len(plugins) == 2
    assert all(
        p in plugins for p in [FidoMIMETypePlugin.name, IntegrityPlugin.name]
    )
    assert plugins[FidoMIMETypePlugin.name] == FidoMIMETypePlugin.json
    assert plugins[IntegrityPlugin.name] == IntegrityPlugin.json


def test_identify_external_plugins(fixtures):
    """Test mechanism for loading external plugins."""

    class ThisAppConfig(AppConfig):
        """Test config."""

        ADDITIONAL_IDENTIFICATION_PLUGINS_DIR = fixtures / "plugins"
        IDENTIFICATION_PLUGINS = [FidoMIMETypePlugin]
        ADDITIONAL_VALIDATION_PLUGINS_DIR = fixtures / "plugins"
        VALIDATION_PLUGINS = [IntegrityPlugin]

    # assert that plugins have been loaded successfully
    config = ThisAppConfig()
    assert len(config.validation_plugins) == 2
    assert "custom-validation-plugin" in config.validation_plugins
    assert len(config.identification_plugins) == 2
    assert "custom-ident-plugin" in config.identification_plugins

    # assert that plugins are correctly listed in self-description
    assert (
        len(config.CONTAINER_SELF_DESCRIPTION["configuration"]["plugins"]) == 4
    )
    assert all(
        p in config.CONTAINER_SELF_DESCRIPTION["configuration"]["plugins"]
        for p in [
            "custom-validation-plugin",
            "custom-ident-plugin",
        ]
    )


@pytest.mark.skipif(not RUN_JHOVE_TESTS[0], reason=RUN_JHOVE_TESTS[1])
def test_identify_jhove_version():
    """
    Test method `set_identity` of `AppConfig` regarding JHOVE version
    information.
    """

    class EmptyAppConfig(AppConfig):
        """Test config."""

        IDENTIFICATION_PLUGINS = []
        VALIDATION_PLUGINS = []

    class JHOVEAppConfig(AppConfig):
        """Test config."""

        IDENTIFICATION_PLUGINS = []
        VALIDATION_PLUGINS = [JHOVEFidoMIMETypePlugin]

    assert (
        len(
            EmptyAppConfig().CONTAINER_SELF_DESCRIPTION["configuration"][
                "plugins"
            ]
        )
        == 0
    )

    software_empty = EmptyAppConfig().CONTAINER_SELF_DESCRIPTION["version"][
        "software"
    ]
    software_jhove = JHOVEAppConfig().CONTAINER_SELF_DESCRIPTION["version"][
        "software"
    ]
    assert "JHOVE" not in software_empty
    assert "JHOVE" in software_jhove
    assert "JHOVE_MODULES" in software_jhove
