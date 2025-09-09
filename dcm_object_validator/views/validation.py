"""
Validation View-class definition
"""

from typing import Optional
import os
from uuid import uuid4

from flask import Blueprint, jsonify, Response, request
from data_plumber_http.decorators import flask_handler, flask_args, flask_json
from dcm_common import LoggingContext as Context
from dcm_common.orchestra import JobConfig, JobContext, JobInfo
from dcm_common import services

from dcm_object_validator.handlers import get_validate_handler
from dcm_object_validator.models import Report, ValidationConfig
from dcm_object_validator.plugins.validation import ValidationPlugin


class ValidationView(services.OrchestratedView):
    """View-class for object-/ip-validation."""

    NAME = "validation"

    def register_job_types(self):
        self.config.worker_pool.register_job_type(
            self.NAME, self.validate, Report
        )

    def configure_bp(self, bp: Blueprint, *args, **kwargs) -> None:
        @bp.route("/validate", methods=["POST"])
        @flask_handler(  # unknown query
            handler=services.no_args_handler,
            json=flask_args,
        )
        @flask_handler(  # process validation
            handler=get_validate_handler(
                cwd=self.config.FS_MOUNT_POINT,
                acceptable_plugins=self.config.validation_plugins,
            ),
            json=flask_json,
        )
        def validate(
            validation: ValidationConfig,
            token: Optional[str] = None,
            callback_url: Optional[str] = None,
        ):
            """Submit for validation."""
            try:
                token = self.config.controller.queue_push(
                    token or str(uuid4()),
                    JobInfo(
                        JobConfig(
                            self.NAME,
                            original_body=request.json,
                            request_body={
                                "validation": validation.json,
                                "callback_url": callback_url,
                            },
                        ),
                        report=Report(
                            host=request.host_url, args=request.json
                        ),
                    ),
                )
            # pylint: disable=broad-exception-caught
            except Exception as exc_info:
                return Response(
                    f"Submission rejected: {exc_info}",
                    mimetype="text/plain",
                    status=500,
                )

            return jsonify(token.json), 201

        self._register_abort_job(bp, "/validate")

    def validate(self, context: JobContext, info: JobInfo):
        """Job instructions for the '/validate' endpoint."""
        os.chdir(self.config.FS_MOUNT_POINT)
        validation_config = ValidationConfig.from_json(
            info.config.request_body["validation"]
        )
        info.report.log.set_default_origin("Object Validator")

        # set progress info
        info.report.progress.verbose = (
            f"preparing validation of '{validation_config.target.path}'"
        )
        context.push()

        # iterate requested plugins
        for id_, plugin_config in validation_config.plugins.items():
            # collect plugin-info
            plugin: ValidationPlugin = self.config.validation_plugins[
                plugin_config.plugin
            ]
            info.report.progress.verbose = (
                f"calling plugin '{plugin.display_name}'"
            )
            info.report.log.log(
                Context.INFO, body=f"Calling plugin '{plugin.display_name}'"
            )
            context.push()

            # configure execution context for plugin
            plugin_context = plugin.create_context(
                info.report.progress.create_verbose_update_callback(
                    plugin.display_name
                ),
                context.push,
            )
            info.report.data.details[id_] = plugin_context.result

            # run plugin logic
            plugin.get(
                plugin_context,
                **(
                    {"path": str(validation_config.target.path)}
                    | plugin_config.args
                ),
            )
            info.report.log.merge(
                plugin_context.result.log.pick(Context.ERROR)
            )
            if not plugin_context.result.success:
                info.report.log.log(
                    Context.ERROR,
                    body=f"Call to plugin '{plugin.display_name}' failed.",
                )
            context.push()

        # eval and log
        info.report.data.success = all(
            p.success for p in info.report.data.details.values()
        )
        if info.report.data.success:
            info.report.data.valid = all(
                p.valid for p in info.report.data.details.values()
            )
            if info.report.data.valid:
                info.report.log.log(
                    Context.INFO,
                    body="Target is valid.",
                )
            else:
                info.report.log.log(
                    Context.ERROR,
                    # pylint: disable=consider-using-f-string
                    body="Target is invalid (got {} error(s)).".format(
                        sum(
                            not p.valid
                            for p in info.report.data.details.values()
                        )
                    ),
                )
        else:
            info.report.log.log(
                Context.ERROR,
                # pylint: disable=consider-using-f-string
                body=(
                    "Validation incomplete ({} plugin(s) gave bad response).".format(
                        sum(
                            not p.success
                            for p in info.report.data.details.values()
                        )
                    )
                ),
            )
        context.push()

        # make callback; rely on _run_callback to push progress-update
        info.report.progress.complete()
        self._run_callback(
            context, info, info.config.request_body.get("callback_url")
        )
