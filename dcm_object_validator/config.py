"""Module for the 'Object Validator'-app configuration."""

import os
import sys
from collections.abc import Iterable
from pathlib import Path
from importlib.metadata import version

import yaml
from dcm_common.services import FSConfig, OrchestratedAppConfig
from dcm_common.plugins import import_from_directory, PluginInterface
import dcm_object_validator_api

from dcm_object_validator.plugins import (
    FidoPUIDPlugin,
    FidoMIMETypePlugin,
    JHOVEFidoMIMETypePlugin,
    JHOVEFidoMIMETypeBagItPlugin,
    IntegrityPlugin,
    BagItIntegrityPlugin,
)


def plugin_ok(plugin: type[PluginInterface]) -> bool:
    """
    Validates `plugin.requirements_met` and prints warning to stderr
    if not.
    """
    ok, msg = plugin.requirements_met()
    if not ok:
        print(
            f"WARNING: Unable to load plugin '{plugin.display_name}' "
            + f"({plugin.name}): {msg}",
            file=sys.stderr,
        )
    return ok


def load_plugins(
    plugins: Iterable[PluginInterface],
) -> dict[str, PluginInterface]:
    """Loads all provided plugins that meet their requirements."""
    return {Plugin.name: Plugin() for Plugin in plugins if plugin_ok(Plugin)}


class AppConfig(FSConfig, OrchestratedAppConfig):
    """
    Configuration for the 'Object Validator'-app.
    """

    # ------ IDENTIFICATION ------
    ADDITIONAL_IDENTIFICATION_PLUGINS_DIR = (
        Path(os.environ.get("ADDITIONAL_IDENTIFICATION_PLUGINS_DIR"))
        if "ADDITIONAL_IDENTIFICATION_PLUGINS_DIR" in os.environ
        else None
    )
    IDENTIFICATION_PLUGINS = [FidoPUIDPlugin, FidoMIMETypePlugin]

    # ------ VALIDATION ------
    ADDITIONAL_VALIDATION_PLUGINS_DIR = (
        Path(os.environ.get("ADDITIONAL_VALIDATION_PLUGINS_DIR"))
        if "ADDITIONAL_VALIDATION_PLUGINS_DIR" in os.environ
        else None
    )
    VALIDATION_PLUGINS = [
        IntegrityPlugin,
        BagItIntegrityPlugin,
        JHOVEFidoMIMETypePlugin,
        JHOVEFidoMIMETypeBagItPlugin,
    ]

    # ------ IDENTIFY ------
    API_DOCUMENT = (
        Path(dcm_object_validator_api.__file__).parent / "openapi.yaml"
    )
    API = yaml.load(
        API_DOCUMENT.read_text(encoding="utf-8"), Loader=yaml.SafeLoader
    )

    def __init__(self) -> None:
        # load additional identification plugins and initialize
        self.identification_plugins = load_plugins(self.IDENTIFICATION_PLUGINS)
        if self.ADDITIONAL_IDENTIFICATION_PLUGINS_DIR is not None:
            self.identification_plugins.update(
                import_from_directory(
                    self.ADDITIONAL_IDENTIFICATION_PLUGINS_DIR,
                    lambda p: p.context == "identification" and plugin_ok(p),
                )
            )

        # load additional validation plugins and initialize
        self.validation_plugins = load_plugins(self.VALIDATION_PLUGINS)
        if self.ADDITIONAL_VALIDATION_PLUGINS_DIR is not None:
            self.validation_plugins.update(
                import_from_directory(
                    self.ADDITIONAL_VALIDATION_PLUGINS_DIR,
                    lambda p: p.context == "validation" and plugin_ok(p),
                )
            )

        super().__init__()

    def set_identity(self) -> None:
        super().set_identity()
        self.CONTAINER_SELF_DESCRIPTION["description"] = (
            "This API provides endpoints for IP payload and general object"
            + " validation."
        )

        # version
        self.CONTAINER_SELF_DESCRIPTION["version"]["api"] = self.API["info"][
            "version"
        ]
        self.CONTAINER_SELF_DESCRIPTION["version"]["app"] = version(
            "dcm-object-validator"
        )
        if JHOVEFidoMIMETypePlugin.name in self.validation_plugins:
            self.CONTAINER_SELF_DESCRIPTION["version"]["software"]["JHOVE"] = (
                JHOVEFidoMIMETypePlugin.dependencies.json.get("JHOVE", "?")
            )
            self.CONTAINER_SELF_DESCRIPTION["version"]["software"][
                "JHOVE_MODULES"
            ] = JHOVEFidoMIMETypePlugin.info.get("moduleVersions", {})

        # configuration
        # - settings
        # settings = self.CONTAINER_SELF_DESCRIPTION["configuration"]["settings"]
        # - plugins
        self.CONTAINER_SELF_DESCRIPTION["configuration"]["plugins"] = {
            p.name: p.json
            for p in (
                self.identification_plugins | self.validation_plugins
            ).values()
        }
