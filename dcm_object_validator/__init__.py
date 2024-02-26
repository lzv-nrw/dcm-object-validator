"""
- DCM object validator -
* this flask app serves as interface and orchestrator for the 'Object
  Validator'-Container within the DCM
* it implements the api-description given in `openapi.yaml`
  (included in the sibling-package `dcm_object_validator_api`)
"""

import sys
from flask import Flask
from lzvnrw_supplements.orchestration import Orchestrator
from dcm_object_validator.config import ObjectValidatorConfig
from dcm_object_validator.default import default_bp_factory
from dcm_object_validator.validation import validation_bp_factory


def app_factory(config: ObjectValidatorConfig):
    """
    Returns a flask-app-object.

    config -- app config derived from ObjectValidatorConfig
    """

    # create 'Object Validator'-app
    app = Flask(__name__)
    app.config.from_object(config)

    # handle CORS
    if config.ALLOW_CORS:
        try:
            from flask_cors import CORS
        except ImportError:
            print(
                "ERROR: Missing package 'Flask_CORS' for 'ALLOW_CORS=1'. Exiting..",
                file=sys.stderr
            )
            sys.exit(1)
        cors = CORS(app)

    # create Orchestrator
    orchestrator = Orchestrator(config.QUEUE_LIMIT)

    app.register_blueprint(
      default_bp_factory(config, orchestrator),
      url_prefix="/"
    )

    app.register_blueprint(
      validation_bp_factory(config, orchestrator),
      url_prefix="/"
    )

    return app
