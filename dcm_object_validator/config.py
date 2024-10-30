"""Configuration module for the 'Object Validator'-app."""

import os
from pathlib import Path
from importlib.metadata import version
import subprocess
import re

import yaml
from dcm_common.util import get_profile
from dcm_common.services import FSConfig, OrchestratedAppConfig
import dcm_object_validator_api

import dcm_object_validator
from dcm_object_validator.models import validation_config


class AppConfig(FSConfig, OrchestratedAppConfig):
    """
    Configuration for the 'Object Validator'-app.
    """

    # ------ VALIDATION ------
    # define default validation options
    DEFAULT_IP_VALIDATORS = [
        validation_config.PayloadStructureModule.identifier,
        validation_config.PayloadIntegrityModule.identifier,
        validation_config.FileFormatModule.identifier,
    ]
    DEFAULT_OBJECT_VALIDATORS = [
        validation_config.FileIntegrityModule.identifier,
        validation_config.FileFormatModule.identifier,
    ]
    DEFAULT_IP_FILE_FORMAT_PLUGINS = list(
        map(
            lambda x: validation_config.FileFormatModule.plugin_prefix + x,
            [
                validation_config.JhovePluginModule.identifier,
            ]
        )
    )
    DEFAULT_OBJECT_FILE_FORMAT_PLUGINS = DEFAULT_IP_FILE_FORMAT_PLUGINS
    SUPPORTED_VALIDATOR_MODULES = list(
        set(DEFAULT_IP_VALIDATORS + DEFAULT_OBJECT_VALIDATORS)
    )
    SUPPORTED_VALIDATOR_PLUGINS = list(
        set(
            DEFAULT_IP_FILE_FORMAT_PLUGINS + DEFAULT_OBJECT_FILE_FORMAT_PLUGINS
        )
    )
    # default arguments for validator constructors
    # payload profile
    PAYLOAD_PROFILE_URL = \
        os.environ.get("PAYLOAD_PROFILE_URL") \
        or "file://" + str(Path(dcm_object_validator.__file__).parent
            / "static" / "payload_profile.json")
    PAYLOAD_PROFILE = get_profile(PAYLOAD_PROFILE_URL)
    # jhove_app location
    JHOVE_APP = os.environ.get("JHOVE_APP") or "jhove"
    DEFAULT_VALIDATOR_KWARGS = {
        "file_integrity": {},
        "payload_structure": {
            "payload_profile_url": PAYLOAD_PROFILE_URL,
            "payload_profile": PAYLOAD_PROFILE,
        },
        "payload_integrity": {},
        "file_format": {},
        "file_format_jhove": {
            "jhove_app": JHOVE_APP
        },
    }

    # ------ IDENTIFY ------
    # generate self-description
    API_DOCUMENT = \
        Path(dcm_object_validator_api.__file__).parent / "openapi.yaml"
    API = yaml.load(
        API_DOCUMENT.read_text(encoding="utf-8"),
        Loader=yaml.SafeLoader
    )

    def set_identity(self) -> None:
        super().set_identity()
        self.CONTAINER_SELF_DESCRIPTION["description"] = (
            "This API provides endpoints for IP payload and general object"
            + " validation."
        )

        # version
        self.CONTAINER_SELF_DESCRIPTION["version"]["api"] = (
            self.API["info"]["version"]
        )
        self.CONTAINER_SELF_DESCRIPTION["version"]["app"] = version(
            "dcm-object-validator"
        )
        self.CONTAINER_SELF_DESCRIPTION["version"]["profile_payload"] = (
            self.PAYLOAD_PROFILE["BagIt-Payload-Profile-Info"]["Version"]
        )
        try:
            self.CONTAINER_SELF_DESCRIPTION["version"]["software"]["java"] = (
                subprocess.run(
                    ["java", "--version"], capture_output=True, text=True,
                    check=True
                ).stdout.split("\n")[0]
            )
        except (FileNotFoundError, subprocess.CalledProcessError, IndexError):
            self.CONTAINER_SELF_DESCRIPTION["version"]["software"]["java"] = (
                "?"
            )
        try:
            jhove = subprocess.run(
                [self.JHOVE_APP], capture_output=True, text=True, check=True
            ).stdout
            self.CONTAINER_SELF_DESCRIPTION["version"]["software"]["jhove"] = (
                jhove.split("\n")[0]
            )
            # TODO: jhove-modules
            self.CONTAINER_SELF_DESCRIPTION["version"]["software"]["jhove_modules"] = {
                module[0]: module[1] for module in map(
                    lambda x: x.split(),
                    re.findall(r"Module: (.*)", jhove)
                )
            }
        except (FileNotFoundError, subprocess.CalledProcessError, IndexError):
            self.CONTAINER_SELF_DESCRIPTION["version"]["software"]["jhove"] = (
                "?"
            )

        # configuration
        # - settings
        settings = self.CONTAINER_SELF_DESCRIPTION["configuration"]["settings"]
        settings["validation"] = {
            "object": {
                "plugins": self.DEFAULT_OBJECT_VALIDATORS,
            },
            "ip": {
                "payload_profile": self.PAYLOAD_PROFILE_URL,
                "plugins": self.DEFAULT_IP_VALIDATORS,
            },
        }
        # - plugins
        plugins = {}
        for identifier in self.SUPPORTED_VALIDATOR_MODULES:
            plugins[identifier] = {
                "name": identifier,
                "description":
                    validation_config.SUPPORTED_VALIDATORS[identifier].validator.VALIDATOR_TAG + ": "
                    + validation_config.SUPPORTED_VALIDATORS[identifier].validator.VALIDATOR_DESCRIPTION
            }
        for identifier in self.SUPPORTED_VALIDATOR_PLUGINS:
            plugins[identifier] = {
                "name": identifier,
                "description":
                    validation_config.SUPPORTED_PLUGINS[identifier].plugin.VALIDATOR_TAG + ": "
                    + validation_config.SUPPORTED_PLUGINS[identifier].plugin.VALIDATOR_DESCRIPTION
            }
        self.CONTAINER_SELF_DESCRIPTION["configuration"]["plugins"] = plugins
