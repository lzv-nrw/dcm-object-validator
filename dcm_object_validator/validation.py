"""
Contains validation-related supplemental definitions and a factory
for Blueprints defining the validation-endpoints of the
'Object Validator'-app.

Blueprints generated from `validation_bp_factory` are parameterized by
an `ObjectValidatorConfig`-config and an `Orchestrator`-object.
"""

from typing import Optional, Any
from subprocess import CalledProcessError
import threading
import requests
from flask import Blueprint, request, jsonify
from dcm_bag_validator.logger import ValidationLogger
from lzvnrw_supplements.supplements import now, hash_from_file
from lzvnrw_supplements.input_processing import CompositeHandler
from lzvnrw_supplements.orchestration \
    import unique_token_factory, list_expired, Job, Orchestrator
from dcm_object_validator.config import ObjectValidatorConfig
from dcm_object_validator import handlers


def process_module_selection(
    config: ObjectValidatorConfig,
    list_of_modules: Optional[list[str]],
    payload_profile_url: Optional[str] = None
) -> tuple[dict[str, Any], list[tuple[str, str]]]:
    """
    Processes job-specific module-selection and returns tuple of
    `VALIDATOR_OPTIONS`-dict and a list of tuples for unknown modules.
    The `VALIDATOR_OPTIONS`-dict contains dictionaries with keys
    'validator' and 'errors'. (See `config.ObjectValidatorConfig` for
    reference.) The unknown-modules list pairs of module-identifiers and
    a reason for rejection as string.

    Keyword arguments:
    config -- config providing default module settings
    list_of_modules -- job-specific selection of modules;
                       a value of `None` corresponds to default config
    payload_profile_url -- optional profile for the payload_structure-
                           module
                           (default None: the default payload_profile
                           is used in the payload_structure-module)
    """

    def _generate_rejection_error_message(
        module: str, exc_info: Exception
    ) -> str:
        return f"Cannot initialize module '{module}' " \
            f"({type(exc_info).__name__}): {str(exc_info)}"

    # handle default selection for modules
    if list_of_modules is None:
        _list_of_modules = list(config.VALIDATOR_OPTIONS.keys())
    else:
        _list_of_modules = list_of_modules

    validator_options = {}
    rejected_modules = []

    # split by context file_format or no-file_format
    file_format_modules = [
        x for x in _list_of_modules
            if (x == config.FILE_FORMAT or x.startswith(config.FILE_FORMAT_PREFIX))
    ]
    no_file_format_modules = [
        x for x in _list_of_modules
            if x not in file_format_modules
    ]

    # process file_format-modules
    file_format_plugins = {}
    # the keys in ffkwargs have to match those kwargs used in the
    # lambda-factories defined in config.SUPPORTED_FILE_FORMAT_PLUGINS
    # - unused for now -
    ffkwargs: dict[str, Any] = {}
    # iterate file_format-modules
    for module in file_format_modules:
        # ---------------------
        # FILE_FORMAT
        if module == config.FILE_FORMAT:
            try:
                file_format_plugins.update(
                    {
                        plugin: (v["validator"][0], v["validator"][1](**ffkwargs))
                            for plugin, v in config.DEFAULT_FILE_FORMAT_PLUGINS.items()
                    }
                )
            except Exception as exc_info:
                rejected_modules.append(
                    (
                        module,
                        _generate_rejection_error_message(module, exc_info)
                    )
                )
            continue

        # ---------------------
        # FILE_FORMAT_PLUGINS
        if module in config.SUPPORTED_FILE_FORMAT_PLUGINS:
            try:
                file_format_plugins[module] = \
                    (
                        config.SUPPORTED_FILE_FORMAT_PLUGINS[module]["validator"][0],
                        config.SUPPORTED_FILE_FORMAT_PLUGINS[module]["validator"][1](**ffkwargs),
                    )
            except Exception as exc_info:
                rejected_modules.append(
                    (
                        module,
                        _generate_rejection_error_message(module, exc_info)
                    )
                )
            continue

        # ---------------------
        # unknown plugin
        rejected_modules.append(
            (
                module,
                f"Unknown or unavailable file_format-plugin '{module}'."
            )
        )

    # create file_format-validator
    if len(file_format_plugins) > 0:
        validator_options[config.FILE_FORMAT] = {
            "validator": config.VALIDATOR_OPTIONS[config.FILE_FORMAT]["validator"](
                file_format_plugins=file_format_plugins.values()
            ),
            "errors": config.VALIDATOR_OPTIONS[config.FILE_FORMAT]["errors"]
        }

    # iterate non-file_format-modules
    # the keys in kwargs have to match those kwargs used in the
    # lambda-factories defined in config.VALIDATOR_OPTIONS
    kwargs = {}
    if payload_profile_url is not None:
        kwargs.update({
            "payload_profile_url": payload_profile_url,
            "payload_profile": payload_profile_url
        })
    for module in no_file_format_modules:
        # ---------------------
        # try instantiation of modules (if provided, with given parameters)
        if module in config.VALIDATOR_OPTIONS:
            try:
                validator_options[module] = {
                    "validator": config.VALIDATOR_OPTIONS[module]["validator"](
                        **kwargs
                    ),
                    "errors": config.VALIDATOR_OPTIONS[module]["errors"]
                }
            except Exception as exc_info:
                rejected_modules.append(
                    (
                        module,
                        _generate_rejection_error_message(module, exc_info)
                    )
                )
            continue

        # ---------------------
        # unknown modules
        rejected_modules.append(
            (
                module,
                f"Unknown or unavailable module '{module}'."
            )
        )

    return validator_options, rejected_modules


# define callback-behavior
def termination_callback_hook_factory(input_data):
    """
    Factory for termination callbacks. Returns function to be used as a
    `Job`'s 'completion'-hook.

    Keyword arguments:
    input_data -- dictionary of input arguments containing information
                  on 'callback_url'
    """
    def termination_callback_hook(x):
        if "callback_url" in input_data:
            # make callback
            response = requests.post(
                input_data["callback_url"],
                json={"token": x.token.value},
                timeout=10
            )

            # if unexpected response code, write to log
            if response.status_code != 200:
                x.report.log(
                    x.REPORT_ERROR_KEY,
                    f"Failed callback to '{input_data['callback_url']}', "
                        + f"expected status '200' but got '{response.status_code}'."
                )
    return termination_callback_hook


def validation_bp_factory(
    config: ObjectValidatorConfig,
    orchestrator: Orchestrator
) -> Blueprint:
    """
    Returns a Blueprint with routes and logic for the validation of IPs
    in a working directory relative to `config.FS_MOUNT_POINT`.

    config -- app config derived from `ObjectValidatorConfig`
    orchestrator -- `Orchestrator`-object to be used for scheduling
    """

    # create Blueprint
    validation_blueprint = Blueprint(
        "validation",
        __name__
    )

    # accepted jobs are listed as a pair of (unique) tokens and
    # Job-objects in this dictionary
    all_jobs: dict[str, Job] = {}

    @validation_blueprint.route("/report", methods=["GET"])
    def get_report():
        """Get report by job_token."""

        # handle unknown arguments
        msg, status = CompositeHandler(
            handlers=[
                *handlers.get_unknown_handler(  # query
                    request_body=list(request.args.keys()),
                    known=["token"],
                    msg_fmt="Unknown query-argument '{}'."
                ),
                # omit body-validation (Unsupported Media Type)
            ],
            good_response=lambda x, y: ("", handlers.DEFAULT_GOOD_RESPONSE)
        ).eval("")
        if status != handlers.DEFAULT_GOOD_RESPONSE:
            return msg, status

        # validate request format and exit if invalid
        msg, status, input_data = handlers.TOKEN_HANDLER.eval(
            (request.args, all_jobs)
        )
        if status != handlers.DEFAULT_GOOD_RESPONSE:
            return msg, status

        if "valid" in input_data["job"].additional_info:
            valid = input_data["job"].additional_info["valid"]
        else:
            valid = False

        # return results
        return jsonify(
            valid=valid,
            warnings=input_data["job"].report.get_report_on(
                ValidationLogger.REPORT_WARNING_KEY
            ),
            errors=input_data["job"].report.get_report_on(
                ValidationLogger.REPORT_ERROR_KEY
            ),
            info=input_data["job"].report.get_report_on(
                ValidationLogger.REPORT_INFO_KEY
            )
        )

    object_input_handler = CompositeHandler(
        handlers=[
            handlers.get_object_handler(config),
            handlers.MODULES_HANDLER,
            handlers.CALLBACKURL_HANDLER,
            handlers.CHECKSUM_HANDLER
        ],
        good_response=lambda x, y: (
            "",
            handlers.DEFAULT_GOOD_RESPONSE,
            {k: v for h in y for k, v in h[2].items()}
        )
    )

    @validation_blueprint.route("/validate_object", methods=["POST"])
    def validate_object():
        """Submit object for validation."""

        # handle unknown arguments
        msg, status = CompositeHandler(
            handlers=[
                *handlers.get_unknown_handler(  # query
                    request_body=list(request.args.keys()),
                    known=[],
                    msg_fmt="Unknown query-argument '{}'."
                ),
                *handlers.get_unknown_handler(  # body
                    request_body=list(request.json.keys()),
                    known=list(config.API["paths"]["/validate_object"]
                        ["post"]["requestBody"]["content"]["application/json"]
                        ["schema"]["properties"].keys()),
                    msg_fmt="Unknown argument '{}' in request body."
                ),
            ],
            good_response=lambda x, y: ("", handlers.DEFAULT_GOOD_RESPONSE)
        ).eval("")
        if status != handlers.DEFAULT_GOOD_RESPONSE:
            return msg, status

        # validate request format and exit if invalid
        msg, status, input_data = object_input_handler.eval(request.json)
        if status != handlers.DEFAULT_GOOD_RESPONSE:
            return msg, status

        # check availability by trying to submit job to queue
        success = False
        if orchestrator.ready():
            # process module-selection
            modules, rejected = process_module_selection(
                config,
                input_data["modules"]
            )

            # instantiate logger-object
            report = ValidationLogger()
            # prepare Job's command
            def cmd():
                exitcode = 0

                # copy module-selection errors to report
                for module, rejection_msg in rejected:
                    report.log(
                        report.REPORT_ERROR_KEY,
                        f"Module Selector: {rejection_msg}"
                    )
                    exitcode = 1
                # print warnings for ignored modules
                if input_data["modules"] is not None:
                    for module in input_data["modules"]:
                        if module != config.FILE_FORMAT and \
                                not module.startswith(config.FILE_FORMAT_PREFIX):
                            report.log(
                                report.REPORT_WARNING_KEY,
                                f"Module Selector: Ignoring module '{module}'."
                            )

                #--------------------------
                # checksum-validation
                CHECKSUM_VALIDATION_TAG = "Object Checksum Validation"
                if "checksum" not in input_data:
                    report.log(
                        report.REPORT_INFO_KEY,
                        f"{CHECKSUM_VALIDATION_TAG}: "
                            + "Skipped checksum validation."
                    )
                else:
                    _hashed = hash_from_file(
                        input_data["checksum"]["method"],
                        input_data["target"]
                    )
                    if _hashed == input_data["checksum"]["value"]:
                        report.log(
                            report.REPORT_INFO_KEY,
                            f"{CHECKSUM_VALIDATION_TAG}: \033[32mChecksum is valid.\033[0m"
                        )
                    else:
                        report.log(
                            report.REPORT_INFO_KEY,
                            f"{CHECKSUM_VALIDATION_TAG}: \033[31mChecksum is invalid.\033[0m"
                                + f" (Expected '{input_data['checksum']['value']}' but found '{_hashed}'.)"
                        )
                        report.log(
                            report.REPORT_ERROR_KEY,
                            f"{CHECKSUM_VALIDATION_TAG}: Validation failed."
                                + f" (Expected '{input_data['checksum']['value']}' but found '{_hashed}'.)"
                        )
                        exitcode = 1
                #--------------------------
                # file format-validation
                if "file_format" in modules:
                    file_format = modules["file_format"]
                    try:
                        this_exitcode = file_format["validator"].validate_file(
                            input_data["target"],
                            report_back=False,
                            clear_report=True,
                            log_summary=True
                        )
                        if this_exitcode != 0:
                            exitcode = 1
                    except file_format["errors"] as exc_info:
                        # FIXME: CalledProcessErrors should be caught by the
                        # respective file_format-plugin but are not (currently)
                        # (therefore information on what part of the validation
                        # failed is lost)
                        # Remove this block after update in the dcm-bag-validator-
                        # project
                        if isinstance(exc_info, CalledProcessError):
                            report.log(
                                report.REPORT_ERROR_KEY,
                                f"{file_format['validator'].VALIDATOR_TAG}: {str(exc_info)}"
                            )
                        exitcode = 1
                    if hasattr(file_format["validator"], "report") \
                            and file_format["validator"].report is not None:
                        report.copy_report(file_format["validator"].report)
                return {"valid": exitcode == 0}

            # instantiate Job
            job = Job(
                unique_token_factory(
                    [j.token for j in all_jobs.values()],
                    expires=config.JOB_TOKEN_EXPIRES,
                    duration=config.JOB_TOKEN_DURATION
                ),
                cmd=cmd,
                logger=report,
                hooks={
                    "completion": termination_callback_hook_factory(input_data)
                }
            )
            # attempt to submit
            success = orchestrator.submit(job)

        if not success:
            return "Service unavailable: " \
                + "maximum number of submissions reached.", 503

        # successfully submitted job
        all_jobs[job.token.value] = job

        # clean up history
        for job in list_expired(list(all_jobs.values())):
            del all_jobs[job.token.value]

        report.log(
            ValidationLogger.REPORT_INFO_KEY,
            f"Job queued at {now()}."
        )

        # trigger execution (if no job is currently running)
        if not orchestrator.processing:
            threading.Thread(target=orchestrator.process, daemon=True).start()

        return jsonify(job.token.to_dict()), 201

    ip_input_handler = CompositeHandler(
        handlers=[
            handlers.get_ip_handler(config),
            handlers.MODULES_HANDLER,
            handlers.PROFILEURL_HANDLER,
            handlers.CALLBACKURL_HANDLER
        ],
        good_response=lambda x, y: (
            "",
            handlers.DEFAULT_GOOD_RESPONSE,
            {k: v for h in y for k, v in h[2].items()}
        )
    )

    @validation_blueprint.route("/validate_ip", methods=["POST"])
    def validate_ip():
        """Submit ip for validation."""

        # handle unknown arguments
        msg, status = CompositeHandler(
            handlers=[
                *handlers.get_unknown_handler(  # query
                    request_body=list(request.args.keys()),
                    known=[],
                    msg_fmt="Unknown query-argument '{}'."
                ),
                *handlers.get_unknown_handler(  # body
                    request_body=list(request.json.keys()),
                    known=list(config.API["paths"]["/validate_ip"]
                        ["post"]["requestBody"]["content"]["application/json"]
                        ["schema"]["properties"].keys()),
                    msg_fmt="Unknown argument '{}' in request body."
                ),
            ],
            good_response=lambda x, y: ("", handlers.DEFAULT_GOOD_RESPONSE)
        ).eval("")
        if status != handlers.DEFAULT_GOOD_RESPONSE:
            return msg, status

        # validate request format and exit if invalid
        msg, status, input_data = ip_input_handler.eval(request.json)
        if status != handlers.DEFAULT_GOOD_RESPONSE:
            return msg, status

        success = False
        if orchestrator.ready():
            # process module-selection
            modules, rejected = process_module_selection(
                config,
                input_data["modules"],
                input_data["profile_url"]
            )

            # instantiate logger-object
            report = ValidationLogger()
            # prepare Job's command
            def cmd():
                exitcode = 0

                # copy module-selection errors to report
                for module, rejection_msg in rejected:
                    report.log(
                        report.REPORT_ERROR_KEY,
                        f"Module Selector: {rejection_msg}"
                    )
                    exitcode = 1

                # perform validation
                for module in modules.values():
                    try:
                        module["validator"].validate_bag(
                            input_data["target"], report_back=False
                        )
                    except module["errors"] as exc_info:
                        # FIXME: CalledProcessErrors should be caught by the
                        # respective file_format-plugin but are not (currently)
                        # (therefore information on what part of the validation
                        # failed is lost)
                        # Remove this block after update in the dcm-bag-validator-
                        # project
                        if isinstance(exc_info, CalledProcessError):
                            report.log(
                                report.REPORT_ERROR_KEY,
                                f"{module['validator'].VALIDATOR_TAG}: {str(exc_info)}"
                            )
                        exitcode = 1
                    report.copy_report(module["validator"].report)
                return {"valid": exitcode == 0}

            # instantiate Job
            job = Job(
                unique_token_factory(
                    [j.token for j in all_jobs.values()],
                    expires=config.JOB_TOKEN_EXPIRES,
                    duration=config.JOB_TOKEN_DURATION
                ),
                cmd=cmd,
                logger=report,
                hooks={
                    "completion": termination_callback_hook_factory(input_data)
                }
            )
            # attempt to submit
            success = orchestrator.submit(job)
        if not success:
            return "Service unavailable: " \
                + "maximum number of submissions reached.", 503

        # successfully submitted job
        all_jobs[job.token.value] = job

        # clean up history
        for job in list_expired(list(all_jobs.values())):
            del all_jobs[job.token.value]

        report.log(
            ValidationLogger.REPORT_INFO_KEY,
            f"Job queued at {now()}."
        )

        # trigger execution (if no job is currently running)
        if not orchestrator.processing:
            threading.Thread(target=orchestrator.process, daemon=True).start()

        return jsonify(job.token.to_dict()), 201

    return validation_blueprint
