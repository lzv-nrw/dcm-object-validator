"""Format validation-plugin based on JHOVE for BagIt-bags."""

from pathlib import Path

from dcm_common.util import list_directory_content

from dcm_object_validator.plugins import FidoMIMETypePlugin
from .jhove import JHOVEFidoMIMETypePlugin


class JHOVEFidoMIMETypeBagItPlugin(JHOVEFidoMIMETypePlugin):
    """
    File format validation based on JHOVE [1] with format-identification
    using fido [2] and target in BagIt[3]-format.


    [1] https://github.com/openpreserve/jhove
    [2] https://github.com/openpreserve/fido
    [3] https://datatracker.ietf.org/doc/html/rfc8493
    """

    _IDENTIFICATION_PLUGIN = FidoMIMETypePlugin
    _IDENTIFICATION_PLUGIN_ARGS = {}

    _NAME = f"jhove-{_IDENTIFICATION_PLUGIN.name}-bagit"
    _DISPLAY_NAME = "JHOVE-Plugin"
    _DESCRIPTION = (
        "File format validation using JHOVE (with format-identification "
        + f"via '{_IDENTIFICATION_PLUGIN.display_name}' "
        + f"({_IDENTIFICATION_PLUGIN.name})). Validates only payload-"
        + "section of given BagIt-bag."
    )

    @classmethod
    def _validate_more(cls, kwargs):
        if not kwargs.get("batch", True):
            return False, "this plugin only supports batch-mode"
        return super()._validate_more(kwargs)

    def _get_records(  # pylint: disable=unused-argument
        self, path: Path, /, **kwargs
    ) -> list[Path]:
        if not (path / "data").is_dir():
            return []
        return list_directory_content(
            path / "data", "**/*", lambda p: p.is_file()
        )
