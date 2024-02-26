"""
Contains a factory for Blueprints defining the default-endpoints of the
'Object Validator'-app.

Blueprints generated from default_bp_factory are parameterized by an
`ObjectValidatorConfig`-config and an `Orchestrator`-object.
"""

from flask import Blueprint, jsonify, request
from lzvnrw_supplements.input_processing import CompositeHandler
from lzvnrw_supplements.orchestration import Orchestrator
from dcm_object_validator.config import ObjectValidatorConfig
from dcm_object_validator import handlers


def default_bp_factory(
    config: ObjectValidatorConfig,
    orchestrator: Orchestrator
) -> Blueprint:
    """
    Returns a Blueprint with routes and logic for the default-endpoints
    listed in the API-specification.

    config -- app config derived from ObjectValidatorConfig
              (requires properties `CONTAINER_SELF_DESCRIPTION`)
    orchestrator -- `Orchestrator`-object to be used for scheduling
    """

    default_blueprint = Blueprint(
        "default",
        __name__
    )

    def get_unknown_input_handler():
        """
        Helper that returns unknown-argument `Handler` for neither
        accepting query-string nor json-requestBody.
        """
        return CompositeHandler(
            handlers=[
                *handlers.get_unknown_handler(  # query
                    request_body=list(request.args.keys()),
                    known=[],
                    msg_fmt="Unknown query-argument '{}'."
                ),
                # omit body-validation (Unsupported Media Type)
            ],
            good_response=lambda x, y: ("", handlers.DEFAULT_GOOD_RESPONSE)
        )

    @default_blueprint.route("/ping", methods=["GET"])
    def ping():
        """Handle ping-request."""

        # handle unknown arguments
        msg, status = get_unknown_input_handler().eval("")
        if status != handlers.DEFAULT_GOOD_RESPONSE:
            return msg, status

        return "pong"

    @default_blueprint.route("/status", methods=["GET"])
    def status():
        """Handle status-request."""

        # handle unknown arguments
        msg, status = get_unknown_input_handler().eval("")
        if status != handlers.DEFAULT_GOOD_RESPONSE:
            return msg, status

        return jsonify(ready=orchestrator.ready())

    @default_blueprint.route("/identify", methods=["GET"])
    def identify():
        """Handle identify-request."""

        # handle unknown arguments
        msg, status = get_unknown_input_handler().eval("")
        if status != handlers.DEFAULT_GOOD_RESPONSE:
            return msg, status

        return jsonify(config.CONTAINER_SELF_DESCRIPTION)

    return default_blueprint
