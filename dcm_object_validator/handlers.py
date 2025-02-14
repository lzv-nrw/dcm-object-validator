"""Input handlers for the 'DCM Object Validator'-app."""

from typing import Mapping
from pathlib import Path

from data_plumber_http import Property, Object, Url
from dcm_common.services.handlers import TargetPath, PluginType

from dcm_object_validator.models import ValidationConfig, Target
from dcm_object_validator.plugins.validation import ValidationPlugin


def get_validate_handler(
    cwd: Path, acceptable_plugins: Mapping[str, ValidationPlugin]
):
    """
    Returns parameterized handler (based on cwd and acceptable_plugins)
    """
    return Object(
        properties={
            Property("validation", required=True): Object(
                model=ValidationConfig,
                properties={
                    Property("target", required=True): Object(
                        model=Target,
                        properties={
                            Property("path", required=True): TargetPath(
                                _relative_to=cwd, cwd=cwd, exists=True
                            )
                        },
                        accept_only=["path"],
                    ),
                    Property("plugins", default=lambda **kwargs: {}): Object(
                        additional_properties=PluginType(
                            acceptable_plugins,
                            acceptable_context=["validation"],
                        )
                    ),
                },
                accept_only=["target", "plugins"],
            ),
            Property("callbackUrl", name="callback_url"): Url(
                schemes=["http", "https"]
            ),
        },
        accept_only=["validation", "callbackUrl"],
    ).assemble()
