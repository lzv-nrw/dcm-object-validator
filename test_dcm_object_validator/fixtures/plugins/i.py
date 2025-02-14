from dcm_common.plugins import Signature

from dcm_object_validator.plugins.identification.interface import (
    FormatIdentificationPlugin,
)


class ExternalPlugin(FormatIdentificationPlugin):
    _NAME = "custom-ident-plugin"
    _DISPLAY_NAME = "Custom-Plugin"
    _DESCRIPTION = "Custom format identification-plugin."
    _SIGNATURE = Signature(
        path=FormatIdentificationPlugin.signature.properties["path"],
    )

    def _get(self, context, /, **kwargs):
        return context.result
