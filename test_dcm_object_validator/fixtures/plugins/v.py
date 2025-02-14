from dcm_common.logger import Logger
from dcm_common.plugins import Signature

from dcm_object_validator.plugins.validation.interface import (
    ValidationPlugin,
    ValidationPluginResultPart,
)


class ExternalPlugin(ValidationPlugin):
    _NAME = "custom-validation-plugin"
    _DISPLAY_NAME = "Custom-Plugin"
    _DESCRIPTION = "Custom validation-plugin."
    _SIGNATURE = Signature(
        path=ValidationPlugin.signature.properties["path"],
        batch=ValidationPlugin.signature.properties["batch"],
    )

    def _get_part(
        self, record_path, /, **kwargs
    ) -> ValidationPluginResultPart:
        result = ValidationPluginResultPart(
            path=record_path, log=Logger(default_origin=self.display_name)
        )
        return result
