"""Format validation-plugin based on JHOVE."""

from typing import Optional
import os
from dataclasses import dataclass
from pathlib import Path
import subprocess
import json
from functools import lru_cache

from dcm_common.logger import LoggingContext as Context, Logger
from dcm_common.plugins import Signature, Argument, JSONType, Dependency

from dcm_object_validator.plugins import FidoMIMETypePlugin
from dcm_object_validator.plugins.identification.interface import (
    FormatIdentificationResult,
)
from .interface import FormatValidationPlugin, ValidationPluginResultPart


@dataclass
class JHOVEPluginResult(ValidationPluginResultPart):
    """Data model for the result of JHOVE-based plugin-invocations."""

    module: Optional[str] = None
    raw: Optional[dict] = None


class _JHOVELoader:
    """
    Helper class with definitions to pre-load JHOVE-metadata (before
    defining Plugin).
    """

    DEFAULT_JHOVE_CMD = os.environ.get("DEFAULT_JHOVE_CMD", "jhove")

    @classmethod
    @lru_cache(maxsize=1)  # this is not expected to change over time..
    def requirements_met(cls, cmd: Optional[str] = None) -> tuple[bool, str]:
        """Check whether JHOVE is available."""
        try:
            result = subprocess.run(
                [cmd or cls.DEFAULT_JHOVE_CMD],
                check=False,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                return False, f"JHOVE returned with an error: {result.stderr}"
        except FileNotFoundError as exc_info:
            return False, f"Unable to load JHOVE: {exc_info}"
        return True, "ok"

    @classmethod
    @lru_cache(maxsize=1)  # this is not expected to change over time..
    def load_info(cls) -> Optional[dict]:
        """
        Returns general information of JHOVE app as dictionary. If not
        successful, returns `None` instead.
        """
        if not cls.requirements_met()[0]:
            return None
        result = subprocess.run(
            [cls.DEFAULT_JHOVE_CMD, "-h", "JSON"],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return None
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return None

    @classmethod
    def load_modules(cls) -> dict[str, str]:
        """Returns a mapping of JHOVE-modules identifier and version."""
        info = cls.load_info()
        if info is None:
            return {}
        return {
            module.get("module", "?"): module.get("release", "?")
            for module in info.get("jhove", {})
            .get("app", {})
            .get("modules", [])
        }

    @classmethod
    def load_version(cls) -> str:
        """Returns JHOVE version."""
        info = cls.load_info()
        if info is None:
            return "?"
        return info.get("jhove", {}).get("release", "?")


class JHOVEFidoMIMETypePlugin(FormatValidationPlugin):
    """
    File format validation based on JHOVE [1] with format-identification
    using fido [2].

    [1] https://github.com/openpreserve/jhove
    [2] https://github.com/openpreserve/fido
    """

    _IDENTIFICATION_PLUGIN = FidoMIMETypePlugin
    _IDENTIFICATION_PLUGIN_ARGS = {}

    _NAME = f"jhove-{_IDENTIFICATION_PLUGIN.name}"
    _DISPLAY_NAME = "JHOVE-Plugin"
    _DESCRIPTION = (
        "File format validation using JHOVE (with format-identification "
        + f"via '{_IDENTIFICATION_PLUGIN.display_name}' "
        + f"({_IDENTIFICATION_PLUGIN.name}))."
    )
    _DEPENDENCIES = [
        Dependency("JHOVE", _JHOVELoader.load_version())
    ] + _IDENTIFICATION_PLUGIN.dependencies.dependencies
    _SIGNATURE = Signature(
        path=FormatValidationPlugin.signature.properties["path"],
        batch=FormatValidationPlugin.signature.properties["batch"],
        format=Argument(
            type_=JSONType.STRING,
            required=False,
            description=(
                "explicitly specify file-format; takes precedence over "
                + "identification-plugin"
            ),
            example="image/jpeg",
        ),
        module=Argument(
            type_=JSONType.STRING,
            required=False,
            description=(
                "request specific JHOVE-module; takes precedence over "
                + "using identification-plugin to determine the correct "
                + "module"
            ),
            example="JPEG-hul",
        ),
    )

    _DEFAULT_JHOVE_CMD = _JHOVELoader.DEFAULT_JHOVE_CMD
    _AUTO_MODULE = "auto"
    _MODULES = _JHOVELoader.load_modules() | {_AUTO_MODULE: "-"}
    _DEFAULT_MODULE_MAP = {
        "AIFF-hul": ["audio/x-aiff"],
        "GIF-hul": ["image/gif"],
        "HTML-hul": ["text/html"],
        "JPEG-hul": ["image/jpeg"],
        "JPEG2000-hul": ["image/jp2", "image/jpx"],
        "PDF-hul": ["application/pdf"],
        "TIFF-hul": ["image/tiff", "image/tiff-fx", "image/ief"],
        "WAVE-hul": ["audio/vnd.wave"],
        "XML-hul": ["text/xml"],
        "PNG-gdm": ["image/png"],
    }
    _INFO = {
        "moduleVersions": _MODULES,
        "moduleTypeMap": {
            # _MODULES is out of scope..
            module: types
            for module, types in _DEFAULT_MODULE_MAP.items()
            if module in _JHOVELoader.load_modules()
        },
    }
    _ERROR_FMT = "{msg} (file '{file}', module '{module}', id '{id_}')"
    _INFO_FMT = "{msg} (file '{file}', module '{module}')"

    @classmethod
    def requirements_met(cls) -> tuple[bool, str]:
        ok, msg = cls._IDENTIFICATION_PLUGIN.requirements_met()
        if not ok:
            return ok, msg
        return _JHOVELoader.requirements_met(cls._DEFAULT_JHOVE_CMD)

    def __init__(self, **kwargs) -> None:
        self.identification_plugin = self._IDENTIFICATION_PLUGIN()
        super().__init__(**kwargs)

    def _get_format(
        self, record_path: Path, kwargs
    ) -> FormatIdentificationResult:
        """Returns `FormatIdentificationResult` for `record_path`."""
        # explicit override
        if "format" in kwargs:
            return FormatIdentificationResult(
                fmt=[kwargs["format"]], success=True
            )

        return self.identification_plugin.get(
            None,
            **(self._IDENTIFICATION_PLUGIN_ARGS | {"path": str(record_path)}),
        )

    def _get_jhove_module(self, fmt: list[str]) -> str:
        """Returns JHOVE-module based on given `fmt`."""
        return next(
            (
                module
                for module, fmts in self.info["moduleTypeMap"].items()
                if any(f in fmts for f in fmt)
            ),
            self._AUTO_MODULE,  # AUTO-DETECT
        )

    def _finalize_fail(
        self,
        result: JHOVEPluginResult | FormatIdentificationResult,
        reason: str,
    ) -> None:
        """
        Helper to finalize `JHOVEPluginResult`'s log and data.
        """
        result.log.log(
            Context.ERROR,
            body=f"Call to JHOVE failed: {reason}",
        )
        result.success = False

    def _collect_errors(self, record: dict) -> list[str]:
        """Returns a list of errors listed in the given JHOVE record."""
        return [
            self._ERROR_FMT.format(
                msg=message.get("message", "?"),
                file=record.get("uri", "?"),
                module=record.get("reportingModule", {}).get("name", "?"),
                id_=message.get("id", "?"),
            )
            for message in record.get("messages", [])
            if message.get("severity", "") == "error"
        ]

    def _get_part(self, record_path: Path, /, **kwargs) -> JHOVEPluginResult:
        result = JHOVEPluginResult(
            path=record_path, log=Logger(default_origin=self.display_name)
        )
        result.log.log(
            Context.INFO,
            body=f"Calling JHOVE on file '{record_path}'.",
        )

        # find JHOVE-module
        if "module" in kwargs:
            result.module = kwargs["module"]
        else:
            identification_result = self._get_format(record_path, kwargs)
            if not identification_result.success:
                self._finalize_fail(
                    result,
                    # pylint: disable=consider-using-f-string
                    "Format identification using '{}' failed: {}".format(
                        kwargs["identification"]["plugin"],
                        (
                            identification_result.log[Context.ERROR][-1][
                                "body"
                            ]
                            if Context.ERROR in identification_result.log
                            else "Unknown error."
                        ),
                    ),
                )
                return result
            result.log.log(
                Context.INFO,
                origin=identification_result.log.default_origin,
                body=(
                    f"Identified file '{record_path}' as "
                    + f"'{identification_result.fmt}'."
                ),
            )

            result.module = self._get_jhove_module(identification_result.fmt)

        # validate module is available
        if result.module not in self._MODULES:
            self._finalize_fail(
                result, f"Requested module '{result.module}' not available."
            )
            return result

        # make call to JHOVE
        subprocess_result = subprocess.run(
            [
                _JHOVELoader.DEFAULT_JHOVE_CMD,
                "-h",
                "JSON",
            ]
            + (
                []
                if result.module == self._AUTO_MODULE
                else ["-m", result.module]
            )
            + [
                str(record_path),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        # jhove returned error
        if subprocess_result.returncode != 0:
            self._finalize_fail(
                result,
                f"JHOVE returned with error: {subprocess_result.stderr}",
            )
            return result

        # parse and evaluate output
        try:
            result.raw = json.loads(subprocess_result.stdout)
        except json.JSONDecodeError:
            self._finalize_fail(
                result,
                f"Unable to read JHOVE's response: {subprocess_result.stdout}",
            )
            return result

        try:
            record = result.raw.get("jhove", {}).get("repInfo", {})[0]
        except IndexError:
            self._finalize_fail(
                result,
                f"JHOVE's response is empty: {subprocess_result.stdout}",
            )
            return result

        for message in self._collect_errors(record):
            result.log.log(
                Context.ERROR,
                body=message,
            )

        result.module = record.get("reportingModule", {}).get(
            "name", result.module
        )
        result.log.log(
            Context.INFO,
            body=self._INFO_FMT.format(
                msg=record.get("status", "?"),
                file=record.get("uri", "?"),
                module=result.module,
            ),
        )

        result.success = True
        result.valid = Context.ERROR not in result.log

        return result
