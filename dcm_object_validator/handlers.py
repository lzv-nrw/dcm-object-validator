"""This module defines a collection of input handlers."""

from typing import Any, Optional
from pathlib import Path
from urllib.parse import urlparse
from lzvnrw_supplements.supplements import SUPPORTED_HASHING_METHODS
from lzvnrw_supplements.input_processing \
    import Handler, CompositeHandler, EnumHandler, KeyHandler, \
        NestedKeyHandler, TypeHandler, OptionalHandler
from dcm_object_validator.config import ObjectValidatorConfig

# this property is used to identify validity/a positive Handler-result
DEFAULT_GOOD_RESPONSE = -1

ACCEPTED_URL_SCHEMES = ["file", "ftp", "sftp", "http", "https"]
ACCEPTED_URL_SCHEMES_CALLBACK = ["http"]


# UNKNOWN arguments
def get_unknown_handler(
    request_body: dict[str, Any],
    known: list[str],
    msg_fmt: Optional[str] = None
) -> list[Handler]:
    """
    Returns a list of `Handler`s where each validates one key of `json`
    against the list of `known` arguments.

    Keyword arguments:
    request_body -- json-requestBody like `Flask`'s `request.json`
    known -- list of accepted arguments
    msg_fmt -- message format that is used in `bad_response`
               (used as `msg.format(y)`)
               (default None)
    """

    # prevent pylint's 'cell-var-from-loop' using this helper
    def _get_enum_handler(y):
        return EnumHandler(
            enum=known,
            preprocessing=lambda x: y,
            bad_response=lambda x: (
                (msg_fmt or "Unknown additional argument '{}'.").format(y),
                400
            )
        )

    return [
        _get_enum_handler(y) for y in request_body
    ]


# to be eval'd with the tuple-argument (request.args, all_jobs)
TOKEN_HANDLER = CompositeHandler(
    handlers=[
        Handler(  # argument exists
            lambda x: x[0].get("token") is not None,
            bad_response=lambda x: (
                "Missing required query-parameter 'token'.",
                400,
                {}
            )
        ),
        TypeHandler(
            # Token has appropriate type (actually redundant since
            # query-parameter must be string)
            str,
            preprocessing=lambda x: x[0].get("token"),
            bad_response=lambda x: (
                "Query-parameter 'token' has bad type. " \
                    + f"Expected str, found {type(x).__name__}.",
                422,
                {}
            )
        ),
        Handler(  # Token is known to the app
            lambda x: x[0].get("token") in x[1],
            bad_response=lambda x: (
                "Query-parameter 'token' unknown/expired. " \
                    + f"({x[0].get('token')})",
                404,
                {}
            )
        ),
        Handler(  # associated Job is completed
            lambda x: x[1][x[0].get("token")].completed,
            bad_response=lambda x: (
                "Job is still being processed.",
                503,
                {}
            )
        ),
    ],
    good_response=lambda x, y: (
        "", DEFAULT_GOOD_RESPONSE, {
            "job": x[1][x[0].get("token")]
        }
    )
)


def get_object_handler(config: ObjectValidatorConfig):
    """
    Factory that returns a `CompositeHandler` to handle the "object"-
    argument of a call to the `/validate_object`-POST-endpoint. It is
    parameterized with the app's config (the `FS_MOUNT_POINT`, in
    particular).

    Keyword arguments:
    config -- some `ObjectValidatorConfig`
    """

    return CompositeHandler(
        handlers=[
            KeyHandler(  # argument exists
                "object",
                bad_response=lambda x: (
                    "Missing required argument 'object'.",
                    400,
                    {}
                )
            ),
            TypeHandler(  # object has appropriate type
                dict,
                preprocessing=lambda x: x["object"],
                bad_response=lambda x: (
                    "Argument 'object' has bad type. " \
                        + f"Expected dict, found {type(x).__name__}.",
                    422,
                    {}
                )
            ),
            NestedKeyHandler(  # object contains path
                ["object", "path"],
                bad_response=lambda x: (
                    "Required property 'path' missing in 'object'.",
                    400,
                    {}
                )
            ),
            TypeHandler(  # object.path has appropriate type
                str,
                preprocessing=lambda x: x["object"]["path"],
                bad_response=lambda x: (
                    "Property 'path' in 'object' has bad type. " \
                        + f"Expected str, found {type(x).__name__}.",
                    422,
                    {}
                )
            ),
            Handler(  # path exists in file-storage
                lambda x:
                    Path(config.FS_MOUNT_POINT / x.lstrip("/")).is_file(),
                preprocessing=lambda x: x["object"]["path"],
                bad_response=lambda x: (
                    f"Resource not found. Target '{x}' invalid or does not " \
                        + "exist.",
                    404,
                    {}
                )
            ),
        ],
        good_response=lambda x, y: (
            "", DEFAULT_GOOD_RESPONSE, {
                "target": Path(
                    config.FS_MOUNT_POINT / x["object"]["path"].lstrip("/")
                )
            }
        )
    )


MODULES_HANDLER = OptionalHandler(
    handler=CompositeHandler(
        handlers=[
            KeyHandler(  # argument exists
                "modules",
                bad_response=lambda x: ("", DEFAULT_GOOD_RESPONSE, {
                    "modules": None
                })
            ),
            TypeHandler(  # modules has appropriate type
                list,
                preprocessing=lambda x: x["modules"],
                bad_response=lambda x: (
                    "Argument 'modules' has bad type. " \
                        + f"Expected list, found {type(x).__name__}.",
                    422,
                    {}
                )
            ),
            Handler(  # modules contains only strings
                check=lambda x: all(isinstance(y, str) for y in x),
                preprocessing=lambda x: x["modules"],
                bad_response=lambda x: (
                    "Some element in argument 'modules' has bad type. " \
                        + "Expected str.",
                    422,
                    {}
                )
            ),
        ],
        good_response=lambda x, y: (
            "", DEFAULT_GOOD_RESPONSE, {"modules": x["modules"]}
        )
    ),
    this_is_fine=lambda x: x[1] == DEFAULT_GOOD_RESPONSE,
    good_response=lambda x, y: y
)
CALLBACKURL_HANDLER = OptionalHandler(
    handler=CompositeHandler(
        handlers=[
            KeyHandler(  # argument exists
                "callbackUrl",
                bad_response=lambda x: ("", DEFAULT_GOOD_RESPONSE, {})
            ),
            TypeHandler(  # callbackUrl has appropriate type
                str,
                preprocessing=lambda x: x["callbackUrl"],
                bad_response=lambda x: (
                    "Argument 'callbackUrl' has bad type. " \
                        + f"Expected str, found {type(x).__name__}.",
                    422,
                    {}
                )
            ),
            Handler(  # validity via urlparse - scheme exists
                lambda x: urlparse(x).scheme != "",
                preprocessing=lambda x: x["callbackUrl"],
                bad_response=lambda x: (
                    f"Argument 'callbackUrl' is missing a url-scheme ('{x}').",
                    404,
                    {}
                )
            ),
            Handler(  # validity via urlparse - netloc exists
                lambda x: urlparse(x).netloc != "",
                preprocessing=lambda x: x["callbackUrl"],
                bad_response=lambda x: (
                    "Argument 'callbackUrl' has bad format. " \
                        + f"Url '{x}' is missing 'netloc'.",
                    422,
                    {}
                )
            ),
            EnumHandler(  # validity of selected scheme
                enum=ACCEPTED_URL_SCHEMES_CALLBACK,
                preprocessing=lambda x: urlparse(x["callbackUrl"]).scheme,
                bad_response=lambda x: (
                    "Scheme of 'callbackUrl' is not allowed. Expected one of " \
                        + f"{ACCEPTED_URL_SCHEMES_CALLBACK}, found '{x}'.",
                    422,
                    {}
                )
            ),
        ],
        good_response=lambda x, y: (
            "", DEFAULT_GOOD_RESPONSE, {"callback_url": x["callbackUrl"]}
        )
    ),
    this_is_fine=lambda x: x[1] == DEFAULT_GOOD_RESPONSE,
    good_response=lambda x, y: y
)
CHECKSUM_HANDLER = OptionalHandler(
    handler=CompositeHandler(
        handlers=[
            KeyHandler(
                "checksum",
                bad_response=lambda x: ("", DEFAULT_GOOD_RESPONSE, {})
            ),
            TypeHandler(  # checksum has appropriate type
                dict,
                preprocessing=lambda x: x["checksum"],
                bad_response=lambda x: (
                    "Argument 'checksum' has bad type. " \
                        + f"Expected dict, found {type(x).__name__}.",
                    422,
                    {}
                )
            ),
            NestedKeyHandler(  # checksum contains method
                ["checksum", "method"],
                bad_response=lambda x: (
                    "Required property 'method' missing in 'checksum'.",
                    400,
                    {}
                )
            ),
            NestedKeyHandler(  # checksum contains value
                ["checksum", "value"],
                bad_response=lambda x: (
                    "Required property 'value' missing in 'checksum'.",
                    400,
                    {}
                )
            ),
            EnumHandler(  # checksum.method is in enum
                enum=(methods := SUPPORTED_HASHING_METHODS.keys()),
                preprocessing=lambda x: x["checksum"]["method"],
                bad_response=lambda x: (
                    "Unsupported value for 'method' in 'checksum': Expected " \
                        + f"one of {methods}, found '{x}'.",
                    422,
                    {}
                )
            ),
            TypeHandler(  # checksum.value has appropriate type
                str,
                preprocessing=lambda x: x["checksum"]["value"],
                bad_response=lambda x: (
                    "Property 'value' in 'checksum' has bad type. " \
                        + f"Expected str, found {type(x).__name__}.",
                    422,
                    {}
                )
            ),
        ],
        good_response=lambda x, y: (
            "", DEFAULT_GOOD_RESPONSE, {"checksum": x["checksum"]}
        )
    ),
    this_is_fine=lambda x: x[1] == DEFAULT_GOOD_RESPONSE,
    good_response=lambda x, y: y
)


def get_ip_handler(config: ObjectValidatorConfig):
    """
    Factory that returns a `CompositeHandler` to handle the "IP"-argument
    of a call to the `/validate_ip`-POST-endpoint. It is parameterized
    with the app's config (the `FS_MOUNT_POINT`, in particular).

    Keyword arguments:
    config -- some `ObjectValidatorConfig`
    """

    return CompositeHandler(
        handlers=[
            KeyHandler(  # argument exists
                "IP",
                bad_response=lambda x: (
                    "Missing required argument 'IP'.",
                    400,
                    {}
                )
            ),
            TypeHandler(  # IP has appropriate type
                dict,
                preprocessing=lambda x: x["IP"],
                bad_response=lambda x: (
                    "Argument 'IP' has bad type. " \
                        + f"Expected dict, found {type(x).__name__}.",
                    422,
                    {}
                )
            ),
            NestedKeyHandler(  # IP contains path
                ["IP", "path"],
                bad_response=lambda x: (
                    "Required property 'path' missing in 'IP'.",
                    400,
                    {}
                )
            ),
            TypeHandler(  # IP.path has appropriate type
                str,
                preprocessing=lambda x: x["IP"]["path"],
                bad_response=lambda x: (
                    "Property 'path' in 'IP' has bad type. " \
                        + f"Expected str, found {type(x).__name__}.",
                    422,
                    {}
                )
            ),
            Handler(  # path exists in file-storage
                lambda x:
                    Path(config.FS_MOUNT_POINT / x.lstrip("/")).is_dir(),
                preprocessing=lambda x: x["IP"]["path"],
                bad_response=lambda x: (
                        f"Resource not found. Target '{x}' invalid or does not " \
                            + "exist.",
                        404,
                        {}
                    )
            ),
        ],
        good_response=lambda x, y: (
            "", DEFAULT_GOOD_RESPONSE, {
                "target": Path(
                    config.FS_MOUNT_POINT / x["IP"]["path"].lstrip("/")
                )
            }
        )
    )


PROFILEURL_HANDLER = OptionalHandler(
    handler=CompositeHandler(
        handlers=[
            KeyHandler(  # argument exists
                "profileUrl",
                bad_response=lambda x: ("", DEFAULT_GOOD_RESPONSE, {
                    "profile_url": None
                })
            ),
            TypeHandler(  # profileUrl has appropriate type
                str,
                preprocessing=lambda x: x["profileUrl"],
                bad_response=lambda x: (
                    "Argument 'profileUrl' has bad type. " \
                        + f"Expected str, found {type(x).__name__}.",
                    422,
                    {}
                )
            ),
            Handler(  # validity via urlparse - scheme exists
                lambda x: urlparse(x).scheme != "",
                preprocessing=lambda x: x["profileUrl"],
                bad_response=lambda x: (
                    f"Argument 'profileUrl' is missing a url-scheme ('{x}').",
                    404,
                    {}
                )
            ),
            Handler(  # validity via urlparse - netloc/path exists
                lambda x: (y := urlparse(x)).netloc != "" or y.path != "",
                preprocessing=lambda x: x["profileUrl"],
                bad_response=lambda x: (
                    "Argument 'profileUrl' has bad format. " \
                        + f"Url '{x}' has neither 'netloc' nor 'path'.",
                    422,
                    {}
                )
            ),
            EnumHandler(  # validity of selected scheme
                enum=ACCEPTED_URL_SCHEMES,
                preprocessing=lambda x: urlparse(x["profileUrl"]).scheme,
                bad_response=lambda x: (
                    "Scheme of 'profileUrl' is not allowed. Expected one of " \
                        + f"{ACCEPTED_URL_SCHEMES}, found '{x}'.",
                    422,
                    {}
                )
            ),
        ],
        good_response=lambda x, y: (
            "", DEFAULT_GOOD_RESPONSE, {"profile_url": x["profileUrl"]}
        )
    ),
    this_is_fine=lambda x: x[1] == DEFAULT_GOOD_RESPONSE,
    good_response=lambda x, y: y
)
