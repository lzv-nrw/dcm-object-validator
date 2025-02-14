"""Test module for the integrity-bagit-plugin."""

from pathlib import Path
from uuid import uuid4
from shutil import copytree

from dcm_common.logger import LoggingContext as Context
import pytest

from dcm_object_validator.plugins import BagItIntegrityPlugin


@pytest.fixture(name="default_plugin")
def _default_plugin():
    return BagItIntegrityPlugin()


@pytest.fixture(name="duplicate_bag")
def _duplicate_bag(file_storage: Path, bag_good: Path):
    """Duplicates bag_good to another directory."""
    duplicate = file_storage / str(uuid4())
    copytree(file_storage / bag_good, duplicate)
    return duplicate


def test_get_minimal(
    default_plugin: BagItIntegrityPlugin,
    file_storage: Path,
    bag_good: Path,
):
    """Test method `get` of `BagItIntegrityPlugin` for simple bag."""
    result = default_plugin.get(None, path=str(file_storage / bag_good))

    assert result.success
    assert result.valid

    assert isinstance(result.records, dict)
    assert len(result.records) == 7
    assert result.records[0].method == "sha512"
    assert Context.ERROR not in result.records[0].log


def test_get_explicit_method(
    default_plugin: BagItIntegrityPlugin,
    file_storage: Path,
    bag_good: Path,
):
    """
    Test method `get` of `BagItIntegrityPlugin` with an explicitly
    selected method.
    """
    result = default_plugin.get(
        None, path=str(file_storage / bag_good), method="sha256"
    )

    assert result.success
    assert result.records[0].method == "sha256"


def test_get_explicit_method_unavailable(
    default_plugin: BagItIntegrityPlugin,
    file_storage: Path,
    bag_good: Path,
):
    """
    Test method `get` of `BagItIntegrityPlugin` with an explicitly
    selected method.
    """
    result = default_plugin.get(
        None, path=str(file_storage / bag_good), method="md5"
    )

    assert not result.success
    assert Context.ERROR in result.log
    for msg in result.log[Context.ERROR]:
        print(msg.body)


def test_get_no_batch(
    default_plugin: BagItIntegrityPlugin,
    file_storage: Path,
    bag_good: Path,
):
    """
    Test method `get` of `BagItIntegrityPlugin` with batch=False.
    """
    result = default_plugin.get(
        None, path=str(file_storage / bag_good), batch=False
    )

    assert not result.success
    assert Context.ERROR in result.log
    for msg in result.log[Context.ERROR]:
        print(msg.body)


@pytest.mark.parametrize("manifest", ["manifest", "tagmanifest"])
def test_get_missing_manifest(
    manifest: str, default_plugin: BagItIntegrityPlugin, duplicate_bag: Path
):
    """
    Test method `get` of `BagItIntegrityPlugin` for a missing manifest-
    file.
    """
    (duplicate_bag / f"{manifest}-sha256.txt").unlink()
    (duplicate_bag / f"{manifest}-sha512.txt").unlink()
    result = default_plugin.get(None, path=str(duplicate_bag))

    assert not result.success
    assert Context.ERROR in result.log
    assert f" {manifest} " in str(result.log)
    for msg in result.log[Context.ERROR]:
        print(msg.body)


def test_get_mixed_manifest(
    default_plugin: BagItIntegrityPlugin, duplicate_bag: Path
):
    """
    Test method `get` of `BagItIntegrityPlugin` for a mix of methods for
    manifest-files.
    """
    (duplicate_bag / "manifest-sha256.txt").unlink()
    (duplicate_bag / "tagmanifest-sha512.txt").unlink()
    (duplicate_bag / "tagmanifest-sha256.txt").write_text(
        "".join(
            map(
                lambda line: (
                    "" if "manifest-sha256.txt" in line else (line + "\n")
                ),
                (duplicate_bag / "tagmanifest-sha256.txt")
                .read_text(encoding="utf-8")
                .split("\n"),
            )
        ),
        encoding="utf-8",
    )
    result = default_plugin.get(None, path=str(duplicate_bag))

    assert result.success
    assert result.records[0].method == "sha512"
    assert result.records[5].method == "sha256"


def test_get_bad_manifest(
    default_plugin: BagItIntegrityPlugin, duplicate_bag: Path
):
    """
    Test method `get` of `BagItIntegrityPlugin` for a bad manifest-file.
    """
    (duplicate_bag / "tagmanifest-sha512.txt").write_text(
        "a\n123\n",
        encoding="utf-8",
    )
    result = default_plugin.get(None, path=str(duplicate_bag))

    assert not result.success
    assert Context.ERROR in result.log
    for msg in result.log[Context.ERROR]:
        print(msg.body)


def test_get_bad_bag(
    default_plugin: BagItIntegrityPlugin, duplicate_bag: Path
):
    """
    Test method `get` of `BagItIntegrityPlugin` for an invalid bag.
    """
    # prepend character to hashes
    (duplicate_bag / "tagmanifest-sha512.txt").write_text(
        "\n".join(
            map(
                lambda line: f"a{line[1:]}",
                (duplicate_bag / "tagmanifest-sha512.txt")
                .read_text(encoding="utf-8").strip()
                .split("\n"),
            )
        ),
        encoding="utf-8",
    )
    result = default_plugin.get(None, path=str(duplicate_bag))

    assert result.success
    assert not result.valid
    assert Context.ERROR in result.log
    for msg in result.log[Context.ERROR]:
        print(msg.body)
