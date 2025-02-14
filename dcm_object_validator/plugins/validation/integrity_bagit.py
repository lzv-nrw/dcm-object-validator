"""BagIt-related file integrity-validation plugin."""

from pathlib import Path

from dcm_common.util import qjoin
from dcm_common.logger import LoggingContext as Context

from .interface import (
    ValidationPluginContext,
    ValidationPluginResult,
)
from .integrity import IntegrityBasePlugin


class BagItIntegrityPlugin(IntegrityBasePlugin):
    """
    File integrity validation for files in BagIt[1]-format.

    [1] https://datatracker.ietf.org/doc/html/rfc8493

    Implements the `IntegrityBasePlugin` by reading manifest-information
    from the given Bag-directory.
    """

    _NAME = "integrity-bagit"
    _DISPLAY_NAME = "Integrity-Plugin"
    _DESCRIPTION = "File integrity validation for files in BagIt-format."

    @classmethod
    def _validate_more(cls, kwargs):
        if not kwargs.get("batch", True):
            return False, "this plugin only supports batch-mode"
        return super()._validate_more(kwargs)

    @classmethod
    def _validate_even_more(cls, kwargs) -> tuple[bool, str]:
        ok, msg = super()._validate_even_more(kwargs)
        if not ok:
            return ok, msg
        if "manifest" not in kwargs:
            return False, "unable to load manifest information from target"
        return True, "ok"

    def _get(
        self, context: ValidationPluginContext, /, **kwargs
    ) -> ValidationPluginResult:
        context.set_progress(
            f"generating manifest information from '{kwargs.get('path', '?')}'"
        )
        context.push()
        manifest = {}
        if "path" in kwargs:
            methods = list(
                filter(
                    lambda x: x in self._SUPPORTED_METHODS,
                    (
                        ["sha512", "sha256", "sha1", "md5"]
                        if kwargs.get("method") is None
                        else [kwargs["method"]]
                    ),
                )
            )
            for f in ["manifest", "tagmanifest"]:
                # find best manifest-files (manifest and tag-manifest)
                file = None
                for method in methods:
                    file = Path(kwargs["path"]) / f"{f}-{method}.txt"
                    if file.is_file():
                        break
                if not file or not file.is_file():
                    context.set_progress("failed to find manifest")
                    context.result.log.log(
                        Context.ERROR,
                        body=(
                            f"Cannot locate valid {f} among methods "
                            + qjoin(methods)
                        ),
                    )
                    context.result.success = False
                    context.push()
                    return context.result

                # read contents and write into manifest-dict
                try:
                    manifest.update(
                        {
                            filename: checksum
                            for checksum, filename in map(
                                lambda line: line.split(maxsplit=1),
                                file.read_text(encoding="utf-8")
                                .strip()
                                .split("\n"),
                            )
                        }
                    )
                # pylint: disable=broad-exception-caught
                except Exception as exc_info:
                    context.set_progress("failed to read manifest")
                    context.result.log.log(
                        Context.ERROR,
                        body=(
                            f"Cannot read manifest file '{file}': {exc_info}"
                        ),
                    )
                    context.result.success = False
                    context.push()
                    return context.result

        return super()._get(context, **(kwargs | {"manifest": manifest}))
