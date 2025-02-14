"""Format identification-plugin-interface."""

from typing import Optional
from dataclasses import dataclass, field
import abc

from dcm_common.plugins import (
    PluginInterface,
    PluginResult,
    PluginExecutionContext,
    Signature,
    Argument,
    JSONType,
)


@dataclass
class FormatIdentificationResult(PluginResult):
    """
    Data model for the result of `FormatIdentificationPlugin`-
    invocations.
    """

    fmt: Optional[list[str]] = None
    success: Optional[bool] = None


@dataclass
class FormatIdentificationContext(PluginExecutionContext):
    """
    Data model for the execution context of
    `FormatIdentificationPlugin`-invocations.
    """

    result: FormatIdentificationResult = field(
        default_factory=FormatIdentificationResult
    )


class FormatIdentificationPlugin(PluginInterface, metaclass=abc.ABCMeta):
    """
    File format identification plugin-base class.

    An implementation of this interface should only ever extend the
    default `_SIGNATURE`.

    The plugin-context is already being set here.

    An implementation's `PluginResult` should inherit from
    `FormatIdentificationResult`.
    """

    _CONTEXT = "identification"
    _SIGNATURE = Signature(
        path=Argument(
            type_=JSONType.STRING,
            required=False,
            description=(
                "target file for format identification; if omitted, filled "
                + "automatically by parent format-validation plugin"
            ),
            example="relative/path/to/file.jpg",
        )
    )
    _RESULT_TYPE = FormatIdentificationResult

    @abc.abstractmethod
    def _get(
        self, context: FormatIdentificationContext, /, **kwargs
    ) -> FormatIdentificationResult:
        raise NotImplementedError(
            f"Class '{self.__class__.__name__}' does not define method 'get'."
        )

    def get(  # this simply narrows down the involved types
        self, context: Optional[FormatIdentificationContext], /, **kwargs
    ) -> FormatIdentificationResult:
        return super().get(context, **kwargs)
