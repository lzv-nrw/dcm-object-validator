from hashlib import md5, sha1

from pathlib import Path

import pytest
from dcm_common.services.tests import (
    fs_setup,
    fs_cleanup,
    external_service,
    run_service,
    wait_for_report,
)
from dcm_common.orchestra import dillignore

from dcm_object_validator.config import AppConfig
from dcm_object_validator.plugins import IntegrityPlugin


@pytest.fixture(scope="session", name="fixtures")
def _fixtures():
    return Path("test_dcm_object_validator/fixtures")


@pytest.fixture(scope="session", name="file_storage")
def _file_storage():
    return Path("test_dcm_object_validator/file_storage")


@pytest.fixture(scope="session", autouse=True)
def disable_extension_logging():
    """
    Disables the stderr-logging via the helper method `print_status`
    of the `dcm_common.services.extensions`-subpackage.
    """
    # pylint: disable=import-outside-toplevel
    from dcm_common.services.extensions.common import PrintStatusSettings

    PrintStatusSettings.silent = True


@pytest.fixture(name="testing_config")
def _testing_config(file_storage):
    @dillignore("controller", "worker_pool")
    class _AppConfig(AppConfig):
        FS_MOUNT_POINT = file_storage
        VALIDATION_PLUGINS = [IntegrityPlugin]
        TESTING = True
        ORCHESTRA_DAEMON_INTERVAL = 0.01
        ORCHESTRA_WORKER_INTERVAL = 0.01
        ORCHESTRA_WORKER_ARGS = {"messages_interval": 0.01}
    return _AppConfig


@pytest.fixture(name="object_good")
def _object_good():
    """File that is expected to be valid."""
    return Path("objects/sample.jpg")


@pytest.fixture(name="object_good_md5")
def _object_good_md5(fixtures, object_good):
    """md5-hash of object_good."""
    return md5((fixtures / object_good).read_bytes()).hexdigest()


@pytest.fixture(name="object_good_sha1")
def _object_good_sha1(fixtures, object_good):
    """sha1-hash of object_good."""
    return sha1((fixtures / object_good).read_bytes()).hexdigest()


@pytest.fixture(name="object_bad")
def _object_bad():
    """File that is expected to be invalid."""
    return Path("objects/sample_bad.tiff")


@pytest.fixture(name="object_bad_md5")
def _object_bad_md5(fixtures, object_bad):
    """md5-hash of object_bad."""
    return md5((fixtures / object_bad).read_bytes()).hexdigest()


@pytest.fixture(name="bag_good")
def _bag_good():
    """BagIt-bag that is expected to be valid."""
    return Path("test-bag")
