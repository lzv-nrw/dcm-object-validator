"""
Validation View-class definition
"""

from typing import Optional
from pathlib import Path

from flask import Blueprint, jsonify
from data_plumber_http.decorators import flask_handler, flask_args, flask_json
from dcm_common import LoggingContext as Context, Logger
from dcm_common.orchestration import Job, JobConfig
from dcm_common import services

from dcm_object_validator.handlers import (
    get_validate_object_handler, get_validate_ip_handler
)
from dcm_object_validator.models.validation_modules \
    import complete_validator_kwargs
from dcm_object_validator.models.validation_config \
    import ValidationConfig, SUPPORTED_VALIDATORS
from dcm_object_validator.models import Report, Target


def validate(
    push,
    target: Target,
    validation_config: ValidationConfig,
    report: Report,
    register_rejected_modules: bool = True
):
    """
    Job instructions for the '/validate/<object|ip>' endpoint.

    The function is defined separately to allow its use in other
    services.

    Orchestration standard-arguments:
    push -- (orchestration-standard) push `data` to host process

    Keyword arguments:
    target --  a `Target` object related to the request
    validation_config -- a `ValidationConfig`-config
    report -- `Report`-object associated with this `Job`
    register_rejected_modules -- if `True`, consider rejected
                                    modules in the report (overall
                                    validity and log)
                                    (default True)
    """
    # process rejections
    if register_rejected_modules and len(validation_config.rejections) > 0:
        report.progress.verbose = (
            f"processing rejections for '{target.path}'"
        )
        push()
        rejection_report = Logger(default_origin="Module Selector")
        rejection_report.log(
            Context.ERROR,
            body=[rejection[1] for rejection in validation_config.rejections]
        )
        target.validation.register_module(
            "module_selector", False, rejection_report
        )

    # perform validation
    total = len(validation_config.modules)
    current = 0
    for identifier, module in validation_config.modules.items():
        report.progress.verbose = (
            f"validating '{target.path}' with '{identifier}'"
        )
        push()
        this_exitcode = 0
        try:
            if target.path.is_file():
                module.validate_file(
                    target.path, report_back=False
                )
            else:
                module.validate_bag(
                    target.path, report_back=False
                )
        except SUPPORTED_VALIDATORS[identifier].errors:
            this_exitcode = 1
        target.validation.register_module(
            identifier,
            this_exitcode == 0,
            module.log or Logger()  # sometime, for some reason, no Logger
                                    # is created in Validation Module
        )
        current += 1
        report.progress.numeric = int(100*current/total)
        push()
    if total > 0:
        report.data.eval()
    else:
        report.data.valid = (
            not register_rejected_modules
            or len(validation_config.rejections) == 0
        )
    push()
    return report.json


class ValidationView(services.OrchestratedView):
    """View-class for object-/ip-validation."""
    NAME = "validation"

    def configure_bp(self, bp: Blueprint, *args, **kwargs) -> None:
        self._configure_object_validation(
            bp,
            handler=get_validate_object_handler(
                cwd=self.config.FS_MOUNT_POINT,
                default_modules=(
                    self.config.DEFAULT_OBJECT_VALIDATORS
                    + self.config.DEFAULT_OBJECT_FILE_FORMAT_PLUGINS
                )
            ),
            default_modules=self.config.DEFAULT_OBJECT_VALIDATORS,
            default_plugins=self.config.DEFAULT_OBJECT_FILE_FORMAT_PLUGINS,
            default_kwargs=self.config.DEFAULT_VALIDATOR_KWARGS
        )
        self._configure_ip_validation(
            bp,
            handler=get_validate_ip_handler(
                cwd=self.config.FS_MOUNT_POINT,
                default_modules=(
                    self.config.DEFAULT_IP_VALIDATORS
                    + self.config.DEFAULT_IP_FILE_FORMAT_PLUGINS
                )
            ),
            default_modules=self.config.DEFAULT_IP_VALIDATORS,
            default_plugins=self.config.DEFAULT_IP_FILE_FORMAT_PLUGINS,
            default_kwargs=self.config.DEFAULT_VALIDATOR_KWARGS
        )

        self._register_abort_job(bp, "/validate")

    def _configure_object_validation(
        self, bp: Blueprint, handler,
        default_modules, default_plugins, default_kwargs
    ) -> None:
        """Adds route for object validation to blueprint"""
        @bp.route("/validate/object", methods=["POST"])
        @flask_handler(  # unknown query
            handler=services.no_args_handler,
            json=flask_args,
        )
        @flask_handler(  # process validation
            handler=handler,
            json=flask_json,
        )
        def validate_object(
            validation: dict,
            callback_url: Optional[str] = None
        ):
            """Submit for validation."""
            validation["target"] = validation["target"].json
            token = self.orchestrator.submit(
                JobConfig(
                    request_body={
                        "validation": validation, "callback_url": callback_url
                    },
                    properties={
                        "default_validators": default_modules,
                        "default_plugins": default_plugins,
                        "default_kwargs": default_kwargs
                    },
                    context=self.NAME
                )
            )

            return jsonify(token.json), 201

    def _configure_ip_validation(
        self, bp: Blueprint, handler,
        default_modules, default_plugins, default_kwargs
    ) -> None:
        """Adds route for ip validation to blueprint"""
        @bp.route("/validate/ip", methods=["POST"])
        @flask_handler(  # unknown query
            handler=services.no_args_handler,
            json=flask_args,
        )
        @flask_handler(  # process validation
            handler=handler,
            json=flask_json,
        )
        def validate_ip(
            validation: dict,
            callback_url: Optional[str] = None
        ):
            """Submit for validation."""
            validation["target"] = validation["target"].json
            token = self.orchestrator.submit(
                JobConfig(
                    request_body={
                        "validation": validation, "callback_url": callback_url
                    },
                    properties={
                        "default_validators": default_modules,
                        "default_plugins": default_plugins,
                        "default_kwargs": default_kwargs
                    },
                    context=self.NAME
                )
            )

            return jsonify(token.json), 201

    def get_job(self, config: JobConfig) -> Job:
        return Job(
            cmd=lambda push, data: validate(
                push=push,
                validation_config=ValidationConfig(
                    allowed=config.properties["default_validators"]
                    + config.properties["default_plugins"],
                    modules=config.request_body["validation"]["modules"],
                    kwargs=complete_validator_kwargs(
                        config.request_body["validation"].get("args", {}),
                        config.properties["default_kwargs"]
                    )
                ),
                register_rejected_modules=True,
                target=Target(
                    Path(config.request_body["validation"]["target"]["path"]),
                    data.data
                ),
                report=data
            ),
            hooks={
                "startup": services.default_startup_hook,
                "success": services.default_success_hook,
                "fail": services.default_fail_hook,
                "abort": services.default_abort_hook,
                "completion": services.termination_callback_hook_factory(
                    config.request_body.get("callback_url", None),
                )
            },
            name="Object Validator"
        )
