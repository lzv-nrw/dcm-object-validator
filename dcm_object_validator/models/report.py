"""
Report data-model definition
"""

from dataclasses import dataclass, field

from dcm_common.orchestra import Report as BaseReport

from dcm_object_validator.models.validation_result import ValidationResult


@dataclass
class Report(BaseReport):
    data: ValidationResult = field(default_factory=ValidationResult)
