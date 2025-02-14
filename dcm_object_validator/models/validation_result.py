"""
ValidationResult data-model definition
"""

from typing import Optional
from dataclasses import dataclass, field

from dcm_common.models import DataModel

from dcm_object_validator.plugins.validation import ValidationPluginResult


@dataclass
class ValidationResult(DataModel):
    """
    Validation result `DataModel`
    """

    success: Optional[bool] = None
    valid: Optional[bool] = None
    details: dict[str, ValidationPluginResult] = field(default_factory=dict)
