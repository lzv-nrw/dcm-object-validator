"""Format validation-plugin-interface."""

from typing import Optional
from pathlib import Path
from dataclasses import dataclass, field
import abc

from dcm_common.logger import LoggingContext as Context
from dcm_common.util import list_directory_content
from dcm_common.models import DataModel
from dcm_common.plugins import (
    PluginInterface,
    PluginResult,
    PluginExecutionContext,
    Signature,
    Argument,
    JSONType,
)


@dataclass
class ValidationPluginResultPart(PluginResult):
    """
    Data model for a partial result of `ValidationPlugin`-invocations.
    """

    path: Path
    success: Optional[bool] = None
    valid: Optional[bool] = None

    @DataModel.serialization_handler("path")
    @classmethod
    def path_serialization_handler(cls, value):
        """Handle `path`-serialization."""
        return str(value)

    @DataModel.deserialization_handler("path")
    @classmethod
    def path_deserialization_handler(cls, value):
        """Handle `path`-deserialization."""
        return Path(value)


@dataclass
class ValidationPluginResult(PluginResult):
    """Data model for the result of `ValidationPlugin`-invocations."""

    success: Optional[bool] = None
    valid: Optional[bool] = None
    records: Optional[dict[str, ValidationPluginResultPart]] = None

    def eval(self) -> None:
        """Evaluate success and validity based on current records."""
        self.success = all(record.success for record in self.records.values())
        self.valid = all(record.valid for record in self.records.values())

    @DataModel.serialization_handler("records")
    @classmethod
    def records_serialization_handler(cls, value):
        """Handle `records`-serialization."""
        if value is None:
            DataModel.skip()
        return {k: v.json for k, v in value.items()}

    @DataModel.deserialization_handler("records")
    @classmethod
    def records_deserialization_handler(cls, value):
        """Handle `records`-deserialization."""
        if value is None:
            DataModel.skip()
        return {
            k: ValidationPluginResultPart.from_json(v)
            for k, v in value.items()
        }


@dataclass
class ValidationPluginContext(PluginExecutionContext):
    """
    Data model for the execution context of `ValidationPlugin`-
    invocations.
    """

    result: ValidationPluginResult = field(
        default_factory=ValidationPluginResult
    )


class ValidationPlugin(PluginInterface, metaclass=abc.ABCMeta):
    """
    File validation plugin-base class.

    An implementation of this interface should only ever extend the
    default `_SIGNATURE`.

    The plugin-context is already being set here.

    An implementation's `PluginResult` should inherit from
    `ValidationPluginResult`. Similarly, the return type of `_get_part`
    should inherit from `ValidationPluginResultPart`.
    """

    _CONTEXT = "validation"
    _SIGNATURE = Signature(
        path=Argument(
            type_=JSONType.STRING,
            required=False,
            description=(
                "target for validation; if omitted, filled automatically by "
                + "job based on job-target"
            ),
            example="relative/path/to/file.jpg",
        ),
        batch=Argument(
            type_=JSONType.BOOLEAN,
            required=False,
            description=(
                "if true, 'path' is interpreted as directory and its contents "
                + "are validated in batch (recursively); otherwise 'path' is "
                + "expected to reference a file"
            ),
            default=True,
            example=False,
        ),
    )
    _RESULT_TYPE = ValidationPluginResult

    @classmethod
    def _validate_more(cls, kwargs):
        # if request has been hydrated with a path ..
        if "path" in kwargs:
            # .. check for file if non-batch or ..
            if (
                not kwargs.get("batch", True)
                and not Path(kwargs["path"]).is_file()
            ):
                return False, "non-batch-mode requires 'path' to be a file"
            # .. check for dir if batch
            if kwargs.get("batch", True) and not Path(kwargs["path"]).is_dir():
                return False, "batch-mode requires 'path' to be a directory"
        return True, "ok"

    @classmethod
    def _validate_even_more(cls, kwargs) -> tuple[bool, str]:
        """
        Returns tuple of boolean for validity and string-reasoning.

        This step is `ValidationPlugin`-specific and ensures that the
        request body has been fully hydrated (e.g., 'path'). It should
        only be used with the final request body.
        """
        if "path" not in kwargs:
            return False, "missing value for 'path'"
        return True, "ok"

    @abc.abstractmethod
    def _get_part(
        self, record_path: Path, /, **kwargs
    ) -> ValidationPluginResultPart:
        """
        Returns `ValidationPluginResultPart`, i.e., the validation
        result on a single record.
        """
        raise NotImplementedError(
            f"Class '{self.__class__.__name__}' does not define method "
            + "'_get_part'."
        )

    def _get_records(  # pylint: disable=unused-argument
        self, path: Path, /, **kwargs
    ) -> list[Path]:
        """
        Collects file-targets from the target directory.

        Keyword arguments:
        path -- specific directory in which to search for targets
        kwargs -- all keyword arguments of the request
        """
        return list_directory_content(path, "**/*", lambda p: p.is_file())

    def _get(
        self, context: ValidationPluginContext, /, **kwargs
    ) -> ValidationPluginResult:
        context.set_progress(f"validating request '{kwargs.get('path', '?')}'")
        context.push()

        # validate whether request is ok
        for valid, msg in (
            x
            for x in (
                self._validate_even_more(kwargs),
                self._validate_more(kwargs),
            )
        ):
            if not valid:
                context.result.log.log(
                    Context.ERROR,
                    body=f"Invalid request: {msg}",
                )
                context.result.success = False
                context.push()
                return context.result

        context.set_progress("collecting targets")
        context.push()
        # find records
        if kwargs.get("batch", True):
            records = self._get_records(Path(kwargs["path"]), **kwargs)
        else:
            records = [Path(kwargs["path"])]
        context.result.log.log(
            Context.INFO, body=f"Collected {len(records)} record(s)."
        )

        # process
        context.result.records = {}
        for i, record in enumerate(records):
            context.set_progress(f"processing '{record}'")
            context.push()
            context.result.records[i] = self._get_part(record, **kwargs)
            context.result.log.merge(
                context.result.records[i].log.pick(Context.ERROR)
            )
            context.push()

        context.result.eval()
        if context.result.success:
            context.set_progress("success")
        else:
            context.set_progress("failure")
        context.push()
        return context.result

    def get(  # this simply narrows down the involved types
        self, context: Optional[ValidationPluginContext], /, **kwargs
    ) -> ValidationPluginResult:
        return super().get(context, **kwargs)


class FormatValidationPlugin(ValidationPlugin, metaclass=abc.ABCMeta):
    """
    File format validation plugin-base class.

    An implementation of this interface should only ever extend the
    default `_SIGNATURE`.

    The plugin-context is already being set here.

    An implementation's `PluginResult` should inherit from
    `ValidationPluginResult`.
    """

    _SIGNATURE = Signature(
        path=ValidationPlugin.signature.properties["path"],
        batch=ValidationPlugin.signature.properties["batch"],
    )
