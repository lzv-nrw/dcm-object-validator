"""General file integrity-validation plugin."""

from typing import Optional, Callable
from dataclasses import dataclass
from pathlib import Path
import abc
from hashlib import (
    md5 as _md5,
    sha1 as _sha1,
    sha256 as _sha256,
    sha512 as _sha512,
)
from functools import partial

from dcm_common.util import qjoin
from dcm_common.logger import LoggingContext as Context, Logger
from dcm_common.plugins import (
    Signature,
    Argument,
    JSONType,
)

from .interface import ValidationPlugin, ValidationPluginResultPart


def _get_hash(file: Path, method: Callable, block: int) -> str:
    """
    Calculate and return hash of `file` using the given `method`
    and a block-size of `block`.

    See https://stackoverflow.com/a/1131255
    """
    hash_ = method()
    with open(file, "rb") as f:
        while True:
            buffer = f.read(block)
            if not buffer:
                break
            hash_.update(buffer)
    return hash_.hexdigest()


md5 = partial(_get_hash, method=_md5, block=2**16)
sha1 = partial(_get_hash, method=_sha1, block=2**16)
sha256 = partial(_get_hash, method=_sha256, block=2**16)
sha512 = partial(_get_hash, method=_sha512, block=2**16)


@dataclass
class IntegrityPluginResult(ValidationPluginResultPart):
    """Data model for the result of `IntegrityPlugin`-invocations."""

    method: Optional[str] = None


class IntegrityBasePlugin(ValidationPlugin, metaclass=abc.ABCMeta):
    """
    Interface containing common parts for plugins providing file-
    integrity validation based on checksums.

    An implementation requires:
    * if `batch` is `False`, `_get_part` to be called with `"value"` in
      its `kwargs`
    * if `batch` is `True`, `_get_part` to be called with `"manifest"`
      in its `kwargs` (an object of filenames and hash-values)
    """

    _SUPPORTED_METHODS = {
        # functions listed here are expected to accept a file path as
        # `Path` and return a hash as string
        "md5": md5,
        "sha1": sha1,
        "sha256": sha256,
        "sha512": sha512,
    }
    _SIGNATURE = Signature(
        path=ValidationPlugin.signature.properties["path"],
        batch=ValidationPlugin.signature.properties["batch"],
        method=Argument(
            type_=JSONType.STRING,
            required=False,
            description=(
                "identifier for a checksum-algorith; "
                + f"one of {qjoin(_SUPPORTED_METHODS.keys())};"
                + " if left empty, use heuristics to determine algorithm"
            ),
            example="md5",
        ),
    )
    _INFO = {
        "algorithms": list(_SUPPORTED_METHODS.keys()),
    }

    def _finalize_fail(
        self, result: IntegrityPluginResult, reason: str
    ) -> None:
        """
        Helper to finalize `IntegrityPluginResult`'s log and data.
        """
        result.log.log(
            Context.ERROR,
            body=reason,
        )
        result.success = False

    @classmethod
    def _get_method(cls, hash_: str) -> Optional[str]:
        """
        Returns (heuristically determined) method identifier based on a
        given hash.
        """
        if not hash_.isalnum():
            return None
        match len(hash_):
            case 128:
                return "sha512"
            case 64:
                return "sha256"
            case 40:
                return "sha1"
            case 32:
                return "md5"
        return None

    def _get_hash(self, file: Path, method: str) -> str:
        """
        Calculate hash of `file` using the method associated with the
        given identifier `method`.
        """
        return self._SUPPORTED_METHODS[method](file)

    def _get_records(self, path: Path, /, **kwargs):
        # only list files that appear in the given manifest
        return [path / f for f in kwargs["manifest"]]

    def _get_part(
        self, record_path: Path, /, **kwargs
    ) -> IntegrityPluginResult:
        result = IntegrityPluginResult(
            path=record_path,
            log=Logger(default_origin=self.display_name)
        )
        if not record_path.exists():
            self._finalize_fail(
                result,
                f"File '{record_path}' does not exist.",
            )
            return result

        # find expected hash-value
        if "value" in kwargs:
            expected_value = kwargs["value"]
        else:
            expected_value = next(
                (
                    v
                    for f, v in kwargs["manifest"].items()
                    if (Path(kwargs["path"]) / f).resolve()
                    == record_path.resolve()
                ),
                None,
            )
            if expected_value is None:
                # this should not happen since records are filtered
                # beforehand via `_get_records`
                self._finalize_fail(
                    result,
                    f"Cannot find hash for '{record_path}' in manifest.",
                )
                return result

        # determine hash-method
        if "method" in kwargs:
            result.method = kwargs["method"]
        else:
            result.method = self._get_method(expected_value)
            if result.method is None:
                self._finalize_fail(
                    result,
                    "Heuristic detection of hashing algorithm failed "
                    + f"(file '{record_path}', checksum '{expected_value}').",
                )
                return result
            if result.method not in self._SUPPORTED_METHODS:
                self._finalize_fail(
                    result,
                    (
                        "Heuristic detection of hashing algorithm yielded "
                        + f"'{result.method}' but this method is not "
                        + f"supported (file '{record_path}', checksum"
                        + f" '{expected_value}')."
                    ),
                )
                return result

        # calculate hash
        hash_ = self._get_hash(record_path, result.method)

        # evaluate result
        result.valid = hash_ == expected_value
        if not result.valid:
            result.log.log(
                Context.ERROR,
                body=(
                    f"Bad {result.method}-hash '{hash_}' for file "
                    + f"'{record_path}' (expected '{expected_value}')."
                ),
            )
        else:
            result.log.log(
                Context.INFO,
                body=(f"Checksum of file '{record_path}' is good."),
            )
        result.success = True

        return result


class IntegrityPlugin(IntegrityBasePlugin):
    """
    File integrity validation based on checksums.

    Implements the `IntegrityBasePlugin` by requesting the missing
    information (value/manifest) from user and validating if request is
    complete beforehand.
    """

    _NAME = "integrity"
    _DISPLAY_NAME = "Integrity-Plugin"
    _DESCRIPTION = "File integrity validation."
    _SIGNATURE = Signature(
        path=IntegrityBasePlugin.signature.properties["path"],
        batch=IntegrityBasePlugin.signature.properties["batch"],
        method=IntegrityBasePlugin.signature.properties["method"],
        value=Argument(
            type_=JSONType.STRING,
            required=False,
            description=(
                "expected checksum value (only applicable if 'batch' is false)"
            ),
            example="46a78da2a246a86f76d066db766cda4f",
        ),
        manifest=Argument(
            type_=JSONType.OBJECT,
            required=False,
            description=(
                "expected checksums by filepath (only applicable if 'batch' "
                + "is true); file paths are required to be given relative to "
                + "'path'; only files listed here are accounted for"
            ),
            additional_properties=True,
        ),
    )

    @classmethod
    def _validate_more(cls, kwargs):
        if not kwargs.get("batch", True) and "value" not in kwargs:
            return False, "missing required 'value' (checksum)"
        if kwargs.get("batch", True) and "manifest" not in kwargs:
            return False, "missing required 'manifest' (checksums)"
        return super()._validate_more(kwargs)
