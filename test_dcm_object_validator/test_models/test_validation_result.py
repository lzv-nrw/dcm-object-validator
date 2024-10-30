"""ValidationResult-data model test-module."""

from dcm_common import Logger
from dcm_common.models.data_model import get_model_serialization_test

from dcm_object_validator.models.validation_result \
    import ValidationModuleResult, ValidationResult


test_validationmoduleresult_json = get_model_serialization_test(
    ValidationModuleResult, (
        ((True, Logger()), {}),
    )
)


test_validationresult_json = get_model_serialization_test(
    ValidationResult, (
        ((), {}),
        ((True, {"a": ValidationModuleResult(True, Logger())}), {}),
    )
)


def test_validationresult_register_module():
    """Test method `register_module` of model `ValidationResult`."""

    result = ValidationResult()

    assert result.valid is None

    result.register_module(
        "module", True, Logger()
    )
    result.eval()

    assert result.valid

    result.register_module(
        "module2", False, Logger()
    )
    result.eval()

    assert not result.valid

    assert isinstance(result.details, dict)
