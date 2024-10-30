"""Input handlers for the 'DCM Object Validator'-app."""

from pathlib import Path

from data_plumber_http import Property, Object, String, Url, Array
from dcm_common.services.handlers import TargetPath

from dcm_object_validator.models import Target


def get_validate_object_handler(cwd: Path, default_modules: list[str]):
    """
    Returns parameterized handler (based on cwd and default modules
    from app_config)
    """
    return Object(
        properties={
            Property("validation", required=True): Object(
                properties={
                    Property("target", required=True): Object(
                        model=Target,
                        properties={
                            Property("path", required=True):
                                TargetPath(
                                    _relative_to=cwd, cwd=cwd, is_file=True
                                )
                        },
                        accept_only=["path"]
                    ),
                    Property("modules", default=default_modules):
                        Array(items=String()),
                    Property("args"): Object(
                        properties={
                            Property("file_integrity"): Object(
                                properties={
                                    Property("method"): String(
                                        enum=["md5", "sha1", "sha256", "sha512"]
                                    ),
                                    Property("value"): String()
                                },
                                accept_only=["method", "value"]
                            )
                        },
                        accept_only=["file_integrity"]
                    ),
                },
                accept_only=["target", "modules", "args"]
            ),
            Property("callbackUrl", name="callback_url"):
                Url(schemes=["http", "https"])
        },
        accept_only=["validation", "callbackUrl"]
    ).assemble()


def get_validate_ip_handler(cwd: Path, default_modules: list[str]):
    """
    Returns parameterized handler (based on cwd and default modules
    from app_config)
    """
    return Object(
        properties={
            Property("validation", required=True): Object(
                properties={
                    Property("target", required=True): Object(
                        model=Target,
                        properties={
                            Property("path", required=True):
                                TargetPath(
                                    _relative_to=cwd, cwd=cwd, is_dir=True
                                )
                        },
                        accept_only=["path"]
                    ),
                    Property("modules", default=default_modules):
                        Array(items=String()),
                    Property("args"): Object(
                        properties={
                            Property("payload_structure"): Object(
                                properties={
                                    Property(
                                        "profileUrl",
                                        name="payload_profile_url"
                                    ): Url(),
                                },
                                accept_only=["profileUrl"]
                            )
                        },
                        accept_only=["payload_structure"]
                    ),
                },
                accept_only=["target", "modules", "args"]
            ),
            Property("callbackUrl", name="callback_url"):
                Url(schemes=["http", "https"])
        },
        accept_only=["validation", "callbackUrl"]
    ).assemble()
