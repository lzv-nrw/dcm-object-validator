"""Test module for the JHOVE-plugins."""

from pathlib import Path

from dcm_common.logger import LoggingContext as Context
import pytest

from dcm_object_validator.plugins import (
    JHOVEFidoMIMETypePlugin,
    FidoMIMETypePlugin,
)


RUN_FIDO_TESTS = FidoMIMETypePlugin.requirements_met()
RUN_JHOVE_TESTS = JHOVEFidoMIMETypePlugin.requirements_met()


@pytest.fixture(name="default_plugin")
def _default_plugin():
    return JHOVEFidoMIMETypePlugin()


@pytest.mark.skipif(not RUN_JHOVE_TESTS[0], reason=RUN_JHOVE_TESTS[1])
def test_requirements_met():
    """Test method `requirements_met` of `JHOVEFidoMIMETypePlugin`."""

    assert JHOVEFidoMIMETypePlugin.requirements_met()[0]

    class BadJHOVEFidoMIMETypePlugin(JHOVEFidoMIMETypePlugin):
        """Test-plugin for testing unmet requirements."""

        _DEFAULT_JHOVE_CMD = "unknown-cmd"

    assert not BadJHOVEFidoMIMETypePlugin.requirements_met()[0]


@pytest.mark.skipif(not RUN_JHOVE_TESTS[0], reason=RUN_JHOVE_TESTS[1])
def test_requirements_met_identification_plugin():
    """
    Test method `requirements_met` of `JHOVEFidoMIMETypePlugin` in case
    of bad response of identification-plugin.
    """
    assert JHOVEFidoMIMETypePlugin.requirements_met()[0]

    class BadIdentificationPlugin(
        # pylint: disable=protected-access
        JHOVEFidoMIMETypePlugin._IDENTIFICATION_PLUGIN
    ):
        @classmethod
        def requirements_met(cls):
            return False, ""

    class BadJHOVEFidoMIMETypePlugin(JHOVEFidoMIMETypePlugin):
        _IDENTIFICATION_PLUGIN = BadIdentificationPlugin

    assert not BadJHOVEFidoMIMETypePlugin.requirements_met()[0]


@pytest.mark.skipif(not RUN_JHOVE_TESTS[0], reason=RUN_JHOVE_TESTS[1])
def test_constructor_ok():
    """Test constructor of `JHOVEFidoMIMETypePlugin`."""
    JHOVEFidoMIMETypePlugin()


@pytest.mark.skipif(not RUN_JHOVE_TESTS[0], reason=RUN_JHOVE_TESTS[1])
@pytest.mark.skipif(not RUN_FIDO_TESTS[0], reason=RUN_FIDO_TESTS[1])
def test_get_simple_file(
    default_plugin: JHOVEFidoMIMETypePlugin,
    file_storage: Path,
    object_good: Path,
):
    """Test method `get` of `JHOVEFidoMIMETypePlugin` for simple file."""
    result = default_plugin.get(
        None, path=str(file_storage / object_good), batch=False
    )

    assert result.success
    assert result.valid

    assert isinstance(result.records, dict)
    assert len(result.records) == 1
    assert 0 in result.records
    assert result.records[0].valid
    assert result.records[0].success
    assert result.records[0].path == file_storage / object_good
    assert result.records[0].module == "JPEG-hul"
    assert result.records[0].raw is not None
    assert Context.ERROR not in result.records[0].log


@pytest.mark.skipif(not RUN_JHOVE_TESTS[0], reason=RUN_JHOVE_TESTS[1])
def test_get_auto_module(
    default_plugin: JHOVEFidoMIMETypePlugin,
    file_storage: Path,
    object_good: Path,
):
    """Test method `get` of `JHOVEFidoMIMETypePlugin` with the 'auto'-module."""
    result = default_plugin.get(
        None, path=str(file_storage / object_good), batch=False, module="auto"
    )

    assert result.success
    assert result.records[0].module == "JPEG-hul"


@pytest.mark.skipif(not RUN_JHOVE_TESTS[0], reason=RUN_JHOVE_TESTS[1])
def test_get_explicit_module(
    default_plugin: JHOVEFidoMIMETypePlugin,
    file_storage: Path,
    object_good: Path,
):
    """
    Test method `get` of `JHOVEFidoMIMETypePlugin` with an explicitly chosen module.
    """
    result = default_plugin.get(
        None,
        path=str(file_storage / object_good),
        batch=False,
        module="TIFF-hul",
    )

    assert result.success
    assert not result.valid
    assert result.records[0].module == "TIFF-hul"
    assert result.records[0].success
    assert not result.records[0].valid
    assert Context.ERROR in result.records[0].log
    for msg in result.records[0].log[Context.ERROR]:
        print(msg.body)


@pytest.mark.skipif(not RUN_JHOVE_TESTS[0], reason=RUN_JHOVE_TESTS[1])
def test_get_explicit_format(
    default_plugin: JHOVEFidoMIMETypePlugin,
    file_storage: Path,
    object_good: Path,
):
    """
    Test method `get` of `JHOVEFidoMIMETypePlugin` with an explicitly chosen file
    format.
    """
    result = default_plugin.get(
        None,
        path=str(file_storage / object_good),
        batch=False,
        format="image/tiff",
    )

    assert result.success
    assert not result.valid
    assert result.records[0].module == "TIFF-hul"
    assert result.records[0].success
    assert not result.records[0].valid
    assert Context.ERROR in result.records[0].log
    for msg in result.records[0].log[Context.ERROR]:
        print(msg.body)


@pytest.mark.skipif(not RUN_JHOVE_TESTS[0], reason=RUN_JHOVE_TESTS[1])
def test_get_unknown_module(
    default_plugin: JHOVEFidoMIMETypePlugin,
    file_storage: Path,
    object_good: Path,
):
    """
    Test method `get` of `JHOVEFidoMIMETypePlugin` with an unknown module.
    """
    result = default_plugin.get(
        None,
        path=str(file_storage / object_good),
        batch=False,
        module="unknown-module",
    )

    assert not result.success
    assert result.records[0].module == "unknown-module"
    assert Context.ERROR in result.records[0].log
    for msg in result.records[0].log[Context.ERROR]:
        print(msg.body)


@pytest.mark.skipif(not RUN_JHOVE_TESTS[0], reason=RUN_JHOVE_TESTS[1])
@pytest.mark.skipif(not RUN_FIDO_TESTS[0], reason=RUN_FIDO_TESTS[1])
def test_get_bad_file(
    default_plugin: JHOVEFidoMIMETypePlugin,
    file_storage: Path,
    object_bad: Path,
):
    """Test method `get` of `JHOVEFidoMIMETypePlugin` with a bad file."""
    result = default_plugin.get(
        None, path=str(file_storage / object_bad), batch=False
    )

    assert result.success
    assert not result.valid
    assert result.records[0].success
    assert not result.records[0].valid
    assert Context.ERROR in result.records[0].log
    for msg in result.records[0].log[Context.ERROR]:
        print(msg.body)


@pytest.mark.skipif(not RUN_JHOVE_TESTS[0], reason=RUN_JHOVE_TESTS[1])
@pytest.mark.skipif(not RUN_FIDO_TESTS[0], reason=RUN_FIDO_TESTS[1])
def test_get_batch(
    default_plugin: JHOVEFidoMIMETypePlugin,
    file_storage: Path,
    object_bad: Path,
):
    """Test method `get` of `JHOVEFidoMIMETypePlugin` in batch mode."""
    result = default_plugin.get(
        None, path=str((file_storage / object_bad).parent)
    )

    assert result.success
    assert not result.valid
    assert len(result.records) == 2
    assert result.records[0].valid or result.records[1].valid
    assert {result.records[0].module, result.records[1].module} == {
        "JPEG-hul",
        "TIFF-hul",
    }
