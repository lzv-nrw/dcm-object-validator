"""Configuration module for the 'Object Validator'-app."""

import os
import itertools
from subprocess import CalledProcessError
from pathlib import Path
from importlib.metadata import version
import yaml
from lzvnrw_supplements.supplements import dict_from_remote_or_local_JSON
from dcm_bag_validator \
    import errors, payload_integrity, payload_structure, file_format
from dcm_bag_validator.file_format_plugins \
    import jhove
import dcm_object_validator
import dcm_object_validator_api


class ObjectValidatorConfig():
    """
    Configuration for the 'Object Validator'-app.
    """

    # ------ GENERAL ------
    # allow CORS (requires python package Flask-CORS)
    ALLOW_CORS = (int(os.environ.get("ALLOW_CORS") or 0)) == 1
    # Path to the working directory (typically mount point of the
    # shared file system)
    FS_MOUNT_POINT = Path(os.environ.get("FS_MOUNT_POINT") or "/file_storage")
    # control expiration of job tokens
    #   do tokens expire?
    JOB_TOKEN_EXPIRES = (int(os.environ.get("JOB_TOKEN_EXPIRES") or 1)) == 1
    #   duration in seconds
    JOB_TOKEN_DURATION = int(os.environ.get("JOB_TOKEN_DURATION") or 3600)
    # orchestrator limit
    QUEUE_LIMIT = int(os.environ.get("QUEUE_LIMIT") or 1)

    # ------ VALIDATION ------
    # payload profile
    PAYLOAD_PROFILE_URL = \
        os.environ.get("PAYLOAD_PROFILE_URL") \
        or "file://" + str(Path(dcm_object_validator.__file__).parent
            / "static" / "payload_profile.json")
    PAYLOAD_PROFILE = dict_from_remote_or_local_JSON(PAYLOAD_PROFILE_URL)
    # jhove_app location
    JHOVE_APP = os.environ.get("JHOVE_APP") or "jhove"
    # define default validation options (create Validator-objects)
    # identifiers
    PAYLOAD_STRUCTURE = "payload_structure"
    PAYLOAD_INTEGRITY = "payload_integrity"
    FILE_FORMAT = "file_format"
    FILE_FORMAT_PREFIX = "file_format_"
    # list for all supported plugins
    SUPPORTED_FILE_FORMAT_PLUGINS = {
        FILE_FORMAT_PREFIX + "jhove": {
            "validator": (
                list(itertools.chain(
                    *jhove.FileFormatValidator_JhovePlugin.FILETYPE_MODULES.values()
                )),
                lambda jhove_app=JHOVE_APP, **kwargs:
                    jhove.FileFormatValidator_JhovePlugin(jhove_app)
            ),
        }
    }
    # default plugins for file_format
    DEFAULT_FILE_FORMAT_PLUGINS = SUPPORTED_FILE_FORMAT_PLUGINS
    VALIDATOR_OPTIONS = {
        PAYLOAD_STRUCTURE: {
            "validator":
                lambda
                payload_profile_url=PAYLOAD_PROFILE_URL,
                payload_profile=PAYLOAD_PROFILE,
                **kwargs:
                    payload_structure.PayloadStructureValidator(
                        payload_profile_url,
                        profile=payload_profile
                    ),
            "errors": (errors.PayloadStructureValidationError),
        },
        PAYLOAD_INTEGRITY: {
            "validator":
                lambda **kwargs:
                    payload_integrity.PayloadIntegrityValidator(),
            "errors": (errors.PayloadIntegrityValidationError),
        },
        FILE_FORMAT: {
            "validator":
                lambda
                file_format_plugins=[
                    (v["validator"][0], v["validator"][1]())
                        for v in DEFAULT_FILE_FORMAT_PLUGINS.values()
                ],
                **kwargs:
                    file_format.FileFormatValidator(
                        file_format_plugins
                    ),
            "errors": (errors.FileFormatValidationError, CalledProcessError),
        }
    }

    # ------ IDENTIFY ------
    # generate self-description
    API_DOCUMENT = \
        Path(dcm_object_validator_api.__file__).parent / "openapi.yaml"
    API = yaml.load(
        API_DOCUMENT.read_text(encoding="utf-8"),
        Loader=yaml.SafeLoader
    )
    CONTAINER_SELF_DESCRIPTION = {
        "api_version":
            API["info"]["version"],
        "container_version": version("dcm-object-validator"),
        "validator_lib_version": version("dcm-bag-validator"),
        "default_profile_version":
            PAYLOAD_PROFILE["BagIt-Payload-Profile-Info"]["Version"],
        "default_profile_identifier": PAYLOAD_PROFILE_URL,
        "description":
            "This container supports the validation of IPs and Objects "
                + "using the modules: "
                + "".join("\n * " + v for v in VALIDATOR_OPTIONS.keys()) + ".",
        "modules": [ # full-modules
            {
                "name": identifier,
                "description": v["validator"]().VALIDATOR_TAG + ": "
                    + v["validator"]().VALIDATOR_DESCRIPTION
            } for identifier, v in VALIDATOR_OPTIONS.items()
        ] + [ # file_format-plugins
            {
                "name": identifier,
                "description": v["validator"][1]().VALIDATOR_TAG + ": "
                    + v["validator"][1]().VALIDATOR_DESCRIPTION + "\n\n"
                    + f"plugin is associated with the MIME-Types: {str(v['validator'][0])}"
            } for identifier, v in SUPPORTED_FILE_FORMAT_PLUGINS.items()
        ]
    }
