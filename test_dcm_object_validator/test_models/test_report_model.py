"""Report-data model test-module."""

from dcm_common import Logger
from dcm_common.models import Token
from dcm_common.models.data_model import get_model_serialization_test

from dcm_object_validator.models.validation_result import (
    ValidationModuleResult
)
from dcm_object_validator.models import ValidationResult, Report


test_report_json = get_model_serialization_test(
    Report, (
        ((), {"host": "."}),
        ((), {
            "host": ".",
            "token": Token(),
            "data": ValidationResult(
                True, {"a": ValidationModuleResult(True, Logger())}
            )
        }),
    )
)
