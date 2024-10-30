
from time import sleep
from pathlib import Path
from unittest import mock

import pytest
from dcm_common.services.tests import (
    fs_setup, fs_cleanup, external_service, run_service, wait_for_report
)

from dcm_object_validator import app_factory, config


@pytest.fixture(scope="session", name="fixtures")
def _fixtures():
    return Path("test_dcm_object_validator/fixtures")


@pytest.fixture(scope="session", name="file_storage")
def _file_storage():
    return Path("test_dcm_object_validator/file_storage")


@pytest.fixture(name="testing_config")
def _testing_config(file_storage):
    """Returns test-config"""
    # setup config-class
    class TestingConfig(config.AppConfig):
        ORCHESTRATION_DAEMON_INTERVAL = 0.001
        ORCHESTRATION_ORCHESTRATOR_INTERVAL = 0.001
        FS_MOUNT_POINT = file_storage
    return TestingConfig


# define fixture-directory-contents
@pytest.fixture(name="ip_good")
def ip_good():
    return Path("test-bag")


# define fixture-directory-contents
@pytest.fixture(name="ip_bad")
def ip_bad():
    return Path("test-bag_bad")


# define fixture-directory-contents
@pytest.fixture(name="object_good")
def object_good():
    return Path("objects/sample.jpg")


# define fixture-directory-contents
@pytest.fixture(name="object_bad")
def object_bad():
    return Path("objects/sample_bad.tiff")


@pytest.fixture(name="targets_good")
def targets_good(
    object_good,
    ip_good
):
    return {
        "object": object_good,
        "IP": ip_good
    }


# define 'Object Validator'
@pytest.fixture(name="app")
def create_backend_app(fixtures):
    """Create instance of 'Object Validator'-app in TESTING-state."""

    # setup config-class
    class TestingConfig(config.AppConfig):
        TESTING = True
        FS_MOUNT_POINT = fixtures
        ORCHESTRATION_AT_STARTUP = False
        ORCHESTRATION_DAEMON_INTERVAL = 0.001
        ORCHESTRATION_ORCHESTRATOR_INTERVAL = 0.001
        ORCHESTRATION_ABORT_NOTIFICATIONS_STARTUP_INTERVAL = 0.01

    # create app using factory
    app = app_factory(TestingConfig())

    return app


@pytest.fixture(name="client")
def create_client(app):
    """Create testing client."""
    return app.test_client()


@pytest.fixture(name="validate_file_patcher_factory")
def validate_file_patcher_factory():
    """
    Returns factory for generating patchers for fake
    FileFormatValidator.validate_file with sleep-duration as parameter.
    """
    def validate_file_patcher(sec: float):
        """Returns patcher for fake FileFormatValidator.validate_file"""
        def faked_validate_file(*args, **kwargs):
            sleep(sec)
            return 0
        return mock.patch(
            "dcm_bag_validator.file_format.FileFormatValidator.validate_file",
            side_effect=faked_validate_file
        )
    return validate_file_patcher


@pytest.fixture(name="validate_bag_patcher_factory")
def validate_bag_patcher_factory():
    """
    Returns factory for generating patchers for fake
    FileFormatValidator.validate_bag with sleep-duration as parameter.
    """
    def validate_bag_patcher(sec: float):
        """Returns patcher for fake FileFormatValidator.validate_bag"""
        def faked_validate_file(*args, **kwargs):
            sleep(sec)
            return 0
        return mock.patch(
            "dcm_bag_validator.file_format.FileFormatValidator.validate_bag",
            side_effect=faked_validate_file
        )
    return validate_bag_patcher
