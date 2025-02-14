"""Format identification-plugin based on fido."""

import os
import subprocess

from dcm_common.util import qjoin
from dcm_common.logger import LoggingContext as Context
from dcm_common.plugins import PythonDependency

from .interface import (
    FormatIdentificationPlugin,
    FormatIdentificationResult,
    FormatIdentificationContext,
)


class FidoPUIDPlugin(FormatIdentificationPlugin):
    """
    File format identification based on fido [1] and PRONOM identifiers.

    [1] https://github.com/openpreserve/fido
    """

    _DISPLAY_NAME = "fido/PIUD-Plugin"
    _NAME = "fido-puid"
    _DESCRIPTION = "File format identification based on fido's puid output."
    _DEPENDENCIES = [PythonDependency("opf-fido")]

    _FORMAT_TYPE = "puid"
    _DEFAULT_FIDO_CMD = os.environ.get("DEFAULT_FIDO_CMD", "fido")

    @classmethod
    def requirements_met(cls) -> tuple[bool, str]:
        try:
            result = subprocess.run(
                [cls._DEFAULT_FIDO_CMD, "-h"],
                check=False,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                return False, f"fido returned with an error: {result.stderr}"
        except FileNotFoundError as exc_info:
            return False, f"Unable to load fido: {exc_info}"
        return True, "ok"

    def _finalize_fail(
        self, context: FormatIdentificationContext, reason: str
    ) -> None:
        """
        Helper to finalize `FormatIdentificationResult`'s log and data.
        """
        context.result.log.log(
            Context.ERROR,
            body=f"Call to fido failed: {reason}",
        )
        context.set_progress(f"failure: {reason}")
        context.result.success = False
        context.push()

    def _get(
        self, context: FormatIdentificationContext, /, **kwargs
    ) -> FormatIdentificationResult:
        # initialize
        context.result.log.log(
            Context.INFO, body=f"Calling fido on file '{kwargs['path']}'."
        )
        context.set_progress(f"calling fido on file '{kwargs['path']}'")
        context.push()

        # process
        subprocess_result = subprocess.run(
            [
                self._DEFAULT_FIDO_CMD,
                "-q",
                "-matchprintf",
                f"%(info.{self._FORMAT_TYPE})s ",
                kwargs["path"],
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        # evaluate
        if subprocess_result.returncode != 0:
            self._finalize_fail(context, subprocess_result.stderr)
        else:
            context.result.success = True
            fmts = subprocess_result.stdout.strip().split()
            if len(fmts) == 0:
                self._finalize_fail(
                    context,
                    f"{subprocess_result.stderr} (does the file exist?)",
                )
            else:
                context.result.fmt = list(set(fmts))
                context.result.log.log(
                    Context.INFO,
                    body=f"Identified file '{kwargs['path']}' as "
                    + f"{qjoin(context.result.fmt, ' | ')}.",
                )
                context.set_progress("success")
                context.push()
        return context.result


class FidoMIMETypePlugin(FidoPUIDPlugin):
    """
    File format identification based on fido [1] and MIME-type
    identifiers.

    [1] https://github.com/openpreserve/fido
    """

    _DISPLAY_NAME = "fido/MIME-Plugin"
    _NAME = "fido-mimetype"
    _DESCRIPTION = (
        "File format identification based on fido's MIME-type output."
    )
    _FORMAT_TYPE = "mimetype"
