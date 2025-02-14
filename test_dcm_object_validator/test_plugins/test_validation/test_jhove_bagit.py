"""Test module for the JHOVE-BagIt-plugin."""

from pathlib import Path

import pytest

from dcm_object_validator.plugins import JHOVEFidoMIMETypeBagItPlugin


RUN_JHOVE_TESTS = JHOVEFidoMIMETypeBagItPlugin.requirements_met()


@pytest.fixture(name="default_plugin")
def _default_plugin():
    return JHOVEFidoMIMETypeBagItPlugin()


@pytest.mark.skipif(not RUN_JHOVE_TESTS[0], reason=RUN_JHOVE_TESTS[1])
@pytest.mark.parametrize("batch", [True, False], ids=["batch", "no-batch"])
def test_validate_more_batch_only(batch, fixtures):
    """Test whether only batch mode is accepted."""
    assert (
        JHOVEFidoMIMETypeBagItPlugin.validate(
            {"path": str(fixtures), "batch": batch}
        )[0]
        is batch
    )


@pytest.mark.skipif(not RUN_JHOVE_TESTS[0], reason=RUN_JHOVE_TESTS[1])
def test_get_minimal(
    default_plugin: JHOVEFidoMIMETypeBagItPlugin,
    file_storage: Path,
    bag_good: Path,
):
    """
    Test method `get` of `JHOVEFidoMIMETypeBagItPlugin` for simple bag.
    (Only payload dir is targeted.)
    """
    result = default_plugin.get(None, path=str(file_storage / bag_good))

    assert result.success
    assert result.valid

    assert isinstance(result.records, dict)
    assert len(result.records) == 2
    assert all(
        record.path.name in ["sample.tiff", "sample.jpg"]
        for record in result.records.values()
    )


@pytest.mark.skipif(not RUN_JHOVE_TESTS[0], reason=RUN_JHOVE_TESTS[1])
def test_get_empty_if_no_bag_payload(
    default_plugin: JHOVEFidoMIMETypeBagItPlugin,
    file_storage: Path,
    object_good: Path,
):
    """
    Test method `get` of `JHOVEFidoMIMETypeBagItPlugin` for 'empty bag'.
    (Only payload dir is targeted.)
    """
    result = default_plugin.get(
        None, path=str(file_storage / object_good.parent)
    )

    assert result.success
    assert result.valid

    assert isinstance(result.records, dict)
    assert len(result.records) == 0
