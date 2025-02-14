"""Test module for the fido-based plugins."""

from pathlib import Path

import pytest

from dcm_object_validator.plugins import FidoPUIDPlugin, FidoMIMETypePlugin


RUN_FIDO_TESTS = FidoPUIDPlugin.requirements_met()


@pytest.mark.skipif(not RUN_FIDO_TESTS[0], reason=RUN_FIDO_TESTS[1])
def test_requirements_met():
    """Test method `requirements_met` of `Fido..Plugin`s."""

    assert FidoPUIDPlugin.requirements_met()[0]

    class BadFidoRequirements(FidoPUIDPlugin):
        """Test-plugin for testing unmet requirements."""

        _DEFAULT_FIDO_CMD = "unknown-cmd"

    assert not BadFidoRequirements.requirements_met()[0]


@pytest.mark.skipif(not RUN_FIDO_TESTS[0], reason=RUN_FIDO_TESTS[1])
def test_get_simple_puid(file_storage: Path, object_good: Path):
    """Test method `get` of `FidoPUIDPlugin` for simple file."""
    plugin = FidoPUIDPlugin()
    result = plugin.get(None, path=str(file_storage / object_good))
    assert result.success
    assert len(result.fmt) == 1
    assert "fmt/43" in result.fmt


@pytest.mark.skipif(not RUN_FIDO_TESTS[0], reason=RUN_FIDO_TESTS[1])
def test_get_simple_mimetype(file_storage: Path, object_good: Path):
    """Test method `get` of `FidoMIMETypePlugin` for simple file."""
    plugin = FidoMIMETypePlugin()
    result = plugin.get(None, path=str(file_storage / object_good))
    assert result.success
    assert len(result.fmt) == 1
    assert "image/jpeg" in result.fmt


@pytest.mark.skipif(not RUN_FIDO_TESTS[0], reason=RUN_FIDO_TESTS[1])
def test_get_multiple_formats_puid(file_storage: Path, object_bad: Path):
    """
    Test method `get` of `FidoPUIDPlugin` for file with matches for
    multiple puids.
    """
    plugin = FidoPUIDPlugin()
    result = plugin.get(None, path=str(file_storage / object_bad))
    assert result.success
    assert len(result.fmt) > 1
    assert "fmt/153" in result.fmt


@pytest.mark.skipif(not RUN_FIDO_TESTS[0], reason=RUN_FIDO_TESTS[1])
def test_get_multiple_formats_mimetype(file_storage: Path, object_bad: Path):
    """
    Test method `get` of `FidoMIMETypePlugin` for file with matches for
    multiple puids.
    """
    plugin = FidoMIMETypePlugin()
    result = plugin.get(None, path=str(file_storage / object_bad))
    assert result.success
    assert len(result.fmt) == 1
    assert "image/tiff" in result.fmt


@pytest.mark.skipif(not RUN_FIDO_TESTS[0], reason=RUN_FIDO_TESTS[1])
def test_get_missing_file(file_storage: Path):
    """
    Test method `get` of `FidoPUIDPlugin` for non-existing file.
    """
    plugin = FidoMIMETypePlugin()
    result = plugin.get(None, path=str(file_storage / "unknown-file"))
    assert not result.success
