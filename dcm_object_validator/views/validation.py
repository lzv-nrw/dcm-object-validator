"""
Validation View-class definition
"""

from typing import Optional

from flask import Blueprint, jsonify
from data_plumber_http.decorators import flask_handler, flask_args, flask_json
from dcm_common import LoggingContext as Context
from dcm_common.orchestration import Job, JobConfig
from dcm_common import services

from dcm_object_validator.handlers import get_validate_handler
from dcm_object_validator.models import Report, ValidationConfig
from dcm_object_validator.plugins.validation import ValidationPlugin


class ValidationView(services.OrchestratedView):
    """View-class for object-/ip-validation."""

    NAME = "validation"

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
            validation: ValidationConfig, callback_url: Optional[str] = None
        ):
            """Submit for validation."""
            token = self.orchestrator.submit(
                JobConfig(
                    request_body={
                        "validation": validation.json,
                        "callback_url": callback_url,
                    },
                    context=self.NAME,
                )
            )

            return jsonify(token.json), 201

        self._register_abort_job(bp, "/validate")

    def get_job(self, config: JobConfig) -> Job:
        return Job(
            cmd=lambda push, data: self.validate(
                push,
                data,
                ValidationConfig.from_json(config.request_body["validation"]),
            ),
            hooks={
                "startup": services.default_startup_hook,
                "success": services.default_success_hook,
                "fail": services.default_fail_hook,
                "abort": services.default_abort_hook,
                "completion": services.termination_callback_hook_factory(
                    config.request_body.get("callback_url", None),
                ),
            },
            name="Object Validator",
        )

    def validate(
        self,
        push,
        report: Report,
        validation_config: ValidationConfig,
    ):
        """
        Job instructions for the '/validate' endpoint.

        Orchestration standard-arguments:
        push -- (orchestration-standard) push `report` to host process
        report -- (orchestration-standard) common report-object shared
                  via `push`

        Keyword arguments:
        validation_config -- a `ValidationConfig`-object
        """

        # set progress info
        report.progress.verbose = (
            f"preparing validation of '{validation_config.target.path}'"
        )
        push()

        # iterate requested plugins
        for id_, plugin_config in validation_config.plugins.items():
            # collect plugin-info
            plugin: ValidationPlugin = self.config.validation_plugins[
                plugin_config.plugin
            ]
            report.progress.verbose = f"calling plugin '{plugin.display_name}'"
            report.log.log(
                Context.INFO, body=f"Calling plugin '{plugin.display_name}'"
            )
            push()

            # configure execution context
            context = plugin.create_context(
                report.progress.create_verbose_update_callback(
                    plugin.display_name
                ),
                push,
            )
            report.data.details[id_] = context.result

            # run plugin logic
            plugin.get(
                context,
                **(
                    {"path": str(validation_config.target.path)}
                    | plugin_config.args
                ),
            )
            report.log.merge(context.result.log.pick(Context.ERROR))
            if not context.result.success:
                report.log.log(
                    Context.ERROR,
                    body=f"Call to plugin '{plugin.display_name}' failed.",
                )
            push()

        # eval and log
        report.data.success = all(
            p.success for p in report.data.details.values()
        )
        if report.data.success:
            report.data.valid = all(
                p.valid for p in report.data.details.values()
            )
            if report.data.valid:
                report.log.log(
                    Context.INFO,
                    body="Target is valid.",
                )
            else:
                report.log.log(
                    Context.ERROR,
                    # pylint: disable=consider-using-f-string
                    body="Target is invalid (got {} error(s)).".format(
                        sum(not p.valid for p in report.data.details.values())
                    ),
                )
        else:
            report.log.log(
                Context.ERROR,
                # pylint: disable=consider-using-f-string
                body=(
                    "Validation incomplete ({} plugin(s) gave bad response).".format(
                        sum(
                            not p.success for p in report.data.details.values()
                        )
                    )
                ),
            )
        push()
