"""Test module for the integrity-plugin."""

import hashlib
from pathlib import Path

from dcm_common.logger import LoggingContext as Context
import pytest

from dcm_object_validator.plugins import IntegrityPlugin


@pytest.fixture(name="default_plugin")
def _default_plugin():
    return IntegrityPlugin()


# --------------------------------------------------------------------
# ------ these tests basically test the ValidationPlugin-interface


def test_get_missing_path(default_plugin: IntegrityPlugin):
    """Test method `get` of `IntegrityPlugin` for missing path."""
    result = default_plugin.get(
        None,
        value="",
    )

    assert not result.success
    assert Context.ERROR in result.log
    for msg in result.log[Context.ERROR]:
        print(msg.body)


def test_get_invalid_path_batch(
    default_plugin: IntegrityPlugin, file_storage: Path, object_good: Path
):
    """Test method `get` of `IntegrityPlugin` for invalid path (batch)."""
    result = default_plugin.get(
        None,
        path=str(file_storage / object_good),
        value="",
    )

    assert not result.success
    assert Context.ERROR in result.log
    for msg in result.log[Context.ERROR]:
        print(msg.body)


# --------------------------------------------------------------------
# ------ integrity-specific tests


def test_get_invalid_path_no_batch(
    default_plugin: IntegrityPlugin, file_storage: Path
):
    """Test method `get` of `IntegrityPlugin` for invalid path (no-batch)."""
    result = default_plugin.get(
        None,
        path=str(file_storage),
        batch=False,
        value="",
    )

    assert not result.success
    assert Context.ERROR in result.log
    for msg in result.log[Context.ERROR]:
        print(msg.body)


def test_get_simple_file(
    default_plugin: IntegrityPlugin,
    file_storage: Path,
    object_good: Path,
    object_good_md5,
):
    """Test method `get` of `IntegrityPlugin` for simple file."""
    result = default_plugin.get(
        None,
        path=str(file_storage / object_good),
        method="md5",
        value=object_good_md5,
        batch=False,
    )

    assert result.success
    assert result.valid

    assert isinstance(result.records, dict)
    assert len(result.records) == 1
    assert 0 in result.records
    assert result.records[0].valid
    assert result.records[0].success
    assert result.records[0].path == file_storage / object_good
    assert result.records[0].method == "md5"
    assert Context.ERROR not in result.records[0].log


@pytest.mark.parametrize(
    "method",
    ["md5", "sha1", "sha256", "sha512"],
)
def test_get_auto_method(
    method,
    default_plugin: IntegrityPlugin,
    fixtures: Path,
    file_storage: Path,
    object_good: Path,
):
    """Test method `get` of `IntegrityPlugin` with method-auto detect."""

    result = default_plugin.get(
        None,
        path=str(file_storage / object_good),
        value=getattr(hashlib, method)(
            (fixtures / object_good).read_bytes()
        ).hexdigest(),
        batch=False,
    )

    assert result.success
    assert result.records[0].method == method


def test_get_auto_method_fail(
    default_plugin: IntegrityPlugin, file_storage: Path, object_good: Path
):
    """
    Test method `get` of `IntegrityPlugin` when failing method-auto
    detect.
    """
    result = default_plugin.get(
        None,
        path=str(file_storage / object_good),
        value="unknown",
        batch=False,
    )

    assert not result.success
    assert result.records[0].method is None
    assert Context.ERROR in result.records[0].log
    for msg in result.records[0].log[Context.ERROR]:
        print(msg.body)


def test_get_failed_checksum(
    default_plugin: IntegrityPlugin, file_storage: Path, object_good: Path
):
    """Test method `get` of `IntegrityPlugin` with bad checksum."""
    result = default_plugin.get(
        None,
        path=str(file_storage / object_good),
        method="md5",
        value="00000000000000000000000000000000",
        batch=False,
    )

    assert result.success
    assert not result.valid

    assert Context.ERROR in result.records[0].log
    for msg in result.records[0].log[Context.ERROR]:
        print(msg.body)


def test_get_batch(
    default_plugin: IntegrityPlugin,
    file_storage: Path,
    object_good: Path,
    object_bad: Path,
    object_good_md5,
    object_bad_md5,
):
    """Test method `get` of `IntegrityPlugin` in batch mode."""
    result = default_plugin.get(
        None,
        path=str((file_storage / object_good).parent),
        method="md5",
        manifest={
            object_good.name: object_good_md5,
            object_bad.name: object_bad_md5,
        },
    )

    assert result.success
    assert result.valid

    assert len(result.records) == 2
    assert result.records[0].success
    assert Context.ERROR not in result.records[0].log
    assert result.records[1].success
    assert Context.ERROR not in result.records[1].log


def test_get_batch_missing_manifest(
    default_plugin: IntegrityPlugin, file_storage: Path, object_good: Path
):
    """
    Test method `get` of `IntegrityPlugin` in batch mode (but missing
    manifest).
    """
    result = default_plugin.get(
        None,
        path=str((file_storage / object_good).parent),
    )

    assert not result.success
    assert result.records is None

    assert Context.ERROR in result.log
    for msg in result.log[Context.ERROR]:
        print(msg.body)


def test_get_batch_different_methods(
    default_plugin: IntegrityPlugin,
    file_storage: Path,
    object_good: Path,
    object_bad: Path,
    object_good_sha1,
    object_bad_md5,
):
    """
    Test method `get` of `IntegrityPlugin` in batch mode (using
    file-specific algorithms).
    """
    result = default_plugin.get(
        None,
        path=str((file_storage / object_good).parent),
        manifest={
            object_good.name: object_good_sha1,
            object_bad.name: object_bad_md5,
        },
    )

    assert result.success
    assert set(r.method for r in result.records.values()) == {"md5", "sha1"}


def test_get_batch_omit_files_not_in_manifest(
    default_plugin: IntegrityPlugin, file_storage: Path, object_good: Path, object_good_md5
):
    """
    Test method `get` of `IntegrityPlugin` in batch mode (not listing
    all files in manifest).
    """
    result = default_plugin.get(
        None,
        path=str((file_storage / object_good).parent),
        manifest={
            object_good.name: object_good_md5,
        },
    )

    assert result.success
    assert len(result.records) == 1


def test_get_batch_error_missing_files(
    default_plugin: IntegrityPlugin, file_storage: Path, object_good: Path
):
    """
    Test method `get` of `IntegrityPlugin` in batch mode (error if file
    appears in manifest but does not exist).
    """
    result = default_plugin.get(
        None,
        path=str((file_storage / object_good).parent),
        manifest={
            "unknown-file": "",
        },
    )

    assert not result.success
    assert len(result.records) == 1
    assert Context.ERROR in result.records[0].log
    for msg in result.records[0].log[Context.ERROR]:
        print(msg.body)
