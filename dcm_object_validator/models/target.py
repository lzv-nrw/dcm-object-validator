"""
Target data-model definition
"""

from dataclasses import dataclass, field
from pathlib import Path

from dcm_common.models import DataModel

from dcm_object_validator.models.validation_result import ValidationResult


@dataclass
class Target(DataModel):
    """
    Target `DataModel`

    Keyword arguments:
    path -- path to target directory/file relative to FS_MOUNT_POINT
    validation -- associated `ValidationResult`
    """

    path: Path
    validation: ValidationResult = field(default_factory=ValidationResult)

    @DataModel.serialization_handler("path")
    @classmethod
    def path_serialization(cls, value):
        """Performs `path`-serialization."""
        return str(value)

    @DataModel.deserialization_handler("path")
    @classmethod
    def path_deserialization(cls, value):
        """Performs `path`-deserialization."""
        return Path(value)
