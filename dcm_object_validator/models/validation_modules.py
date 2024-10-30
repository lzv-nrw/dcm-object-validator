"""
Validation Module model definitions

The contents of this file serve as a compatibility layer for the
inhomogeneous constructor-signatures of the individual validator-modules
in `dcm_bag_validator`.

With the classes inheriting from `ValidatorModule` or
`FileFormatPluginModule`, the `ValidationConfig` can uniformly create
instances of the various validators. For this it utilizes the functions
`get_validator` and `get_plugin` in conjunction with the `kwargs_map`.
"""

from typing import TypeAlias
from subprocess import CalledProcessError
from copy import deepcopy

from dcm_bag_validator \
    import errors, bagit_profile, payload_integrity, payload_structure, \
        file_format, file_integrity
from dcm_bag_validator.file_format_plugins \
    import file_format_interface, jhove


# define validation options
ValidatorType: TypeAlias = bagit_profile.ProfileValidator \
    | file_integrity.FileIntegrityValidator \
    | payload_integrity.PayloadIntegrityValidator \
    | payload_structure.PayloadStructureValidator \
    | file_format.FileFormatValidator


def complete_validator_kwargs(
    user_kwargs: dict, default: dict
) -> dict:
    """
    Returns `user_kwargs` completed using the `default`-values.

    Keyword arguments:
    user_kwargs -- kwargs in request
    default -- default kwargs
    """
    result = deepcopy(default)
    for module, module_kwargs in user_kwargs.items():
        for kwarg, value in module_kwargs.items():
            if module in result:
                result[module][kwarg] = value
            # FIXME: special treatments for cached profiles..
            if module == "payload_structure" \
                    and kwarg == "payload_profile_url":
                del result[module]["payload_profile"]
            if module == "bagit_profile" \
                    and kwarg == "bagit_profile_url":
                del result[module]["bagit_profile"]
    return result


class ValidatorModule:
    """Superclass for validator modules."""
    identifier: str
    errors: tuple
    validator: type
    kwargs_map: dict[str, str]  # this maps from container-parameters to
                                # library parameters

    @classmethod
    def get_validator(cls, **kwargs) -> ValidatorType:
        """
        Returns an instance of a `ValidatorType`. All kwargs are passed
        along into its constructor.
        """
        return cls.validator(
            **{kw: kwargs[v] for kw, v in cls.kwargs_map.items() if v in kwargs}
        )


class FileFormatPluginModule:
    """Superclass for file format-validator plugin modules."""
    identifier: str
    plugin: type
    kwargs_map: dict[str, str]

    @classmethod
    def get_plugin(cls, **kwargs) -> file_format_interface.FileFormatValidatorInterface:
        """
        Returns an instance of a `file_format_interface.FileFormatValidatorInterface`.
        All kwargs are passed along into its constructor.
        """
        return cls.plugin(
            **{kw: kwargs[v] for kw, v in cls.kwargs_map.items() if v in kwargs}
        )


class BagitProfileModule(ValidatorModule):
    """BagIt profile validator module"""
    identifier = "bagit_profile"
    errors = (errors.ProfileValidationError, )
    validator = bagit_profile.ProfileValidator
    kwargs_map = {
        "url": "bagit_profile_url",
        "profile": "bagit_profile",
        "ignore_baginfo_tag_case": "ignore_baginfo_tag_case"
    }


class PayloadStructureModule(ValidatorModule):
    """BagIt payload profile validator module"""
    identifier = "payload_structure"
    errors = (errors.PayloadStructureValidationError, )
    validator = payload_structure.PayloadStructureValidator
    kwargs_map = {
        "url": "payload_profile_url",
        "profile": "payload_profile"
    }


class PayloadIntegrityModule(ValidatorModule):
    """Payload integrity validator module"""
    identifier = "payload_integrity"
    errors = (errors.PayloadIntegrityValidationError, )
    validator = payload_integrity.PayloadIntegrityValidator
    kwargs_map = {}


class FileIntegrityModule(ValidatorModule):
    """File integrity validator module"""
    identifier = "file_integrity"
    errors = (errors.PayloadIntegrityValidationError, )
    validator = file_integrity.FileIntegrityValidator
    kwargs_map = {
        "method": "method",
        "value": "value"
    }


class FileFormatModule(ValidatorModule):
    """File format validator module"""
    identifier = "file_format"
    plugin_prefix = "file_format_"
    errors = (errors.FileFormatValidationError, CalledProcessError)
    validator = file_format.FileFormatValidator
    kwargs_map = {
        "list_of_validators": "list_of_validators"
    }


class JhovePluginModule(FileFormatPluginModule):
    """Jhove-plugin for file format validator module"""
    identifier = "jhove"
    plugin = jhove.JhovePlugin
    kwargs_map = {
        "jhove_app": "jhove_app"
    }
