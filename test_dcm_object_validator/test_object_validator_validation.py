"""'Object Validator'-app test-module for validation-endpoints."""

import os
from time import sleep
import pytest
from lzvnrw_supplements.supplements import hash_from_file
from dcm_object_validator.validation import process_module_selection
from dcm_object_validator.config import ObjectValidatorConfig


@pytest.fixture(scope="module", name="callback_host")
def callback_host_fixture():
    return "0.0.0.0"
@pytest.fixture(scope="module", name="callback_port")
def callback_port_fixture():
    return "8081"
@pytest.fixture(scope="module", name="callback_path")
def callback_path_fixture():
    return "/callback"
@pytest.fixture(scope="module", name="callback_environ")
def callback_environ_fixture():
    return "098f6bcd4621d373cade4e832627b4f6"

@pytest.fixture(scope="module", autouse=True)
def callback_app_service(
    request, callback_host, callback_port, callback_path, callback_environ
):
    """
    As a callback-listener, use a minimal flask app that sets an environment
    variable if it is called. This enables to check whether a callback was
    successful.
    """
    from flask import Flask
    from flask import request as flask_request
    from threading import Thread

    app = Flask(__name__)

    @app.route(callback_path, methods=["POST"])
    def main():
        # set value of environment variable then return expected status
        os.environ[callback_environ] = flask_request.json["token"]
        return "success", 200

    # set some initial value for environment variable
    os.environ[callback_environ] = "0"

    Thread(target=lambda:
        app.run(
            host=callback_host,
            port=callback_port,
            debug=False
        ),
        daemon=True
    ).start()

    # delete environment variable after session
    def auto_resource_fin():
        del os.environ[callback_environ]

    request.addfinalizer(auto_resource_fin)

##############################
####  process_module_selection
def test_process_module_selection_default():
    """Test default behavior of method `process_module_selection`."""

    modules, rejections = process_module_selection(
        ObjectValidatorConfig,
        None
    )

    assert isinstance(modules, dict)
    assert set(modules.keys()) \
        == set(ObjectValidatorConfig.VALIDATOR_OPTIONS.keys())
    assert isinstance(rejections, list)
    assert len(rejections) == 0

def test_process_module_selection_empty():
    """Test empty list-behavior of method `process_module_selection`."""

    modules, rejections = process_module_selection(
        ObjectValidatorConfig,
        []
    )

    assert isinstance(modules, dict)
    assert len(modules.keys()) == 0
    assert isinstance(rejections, list)
    assert len(rejections) == 0

def test_process_module_selection_single():
    """Test single entry in list for method `process_module_selection`."""

    modules, rejections = process_module_selection(
        ObjectValidatorConfig,
        [ObjectValidatorConfig.PAYLOAD_INTEGRITY]
    )

    assert isinstance(modules, dict)
    assert list(modules.keys()) == [ObjectValidatorConfig.PAYLOAD_INTEGRITY]
    assert isinstance(rejections, list)
    assert len(rejections) == 0

def test_process_module_selection_unknown():
    """Test unknown entries in list for method `process_module_selection`."""

    unknown1 = "unknown"
    unknown2 = "unknown2"

    modules, rejections = process_module_selection(
        ObjectValidatorConfig,
        [ObjectValidatorConfig.PAYLOAD_INTEGRITY, unknown1, unknown2]
    )

    assert list(modules.keys()) == [ObjectValidatorConfig.PAYLOAD_INTEGRITY]
    assert len(rejections) == 2
    assert rejections[0][0] == unknown1
    assert rejections[1][0] == unknown2

def test_process_module_selection_profile():
    """Test profile_url-argument for method `process_module_selection`."""

    modules, rejections = process_module_selection(
        ObjectValidatorConfig,
        [ObjectValidatorConfig.PAYLOAD_STRUCTURE],
        ObjectValidatorConfig.PAYLOAD_PROFILE_URL
    )

    assert list(modules.keys()) == [ObjectValidatorConfig.PAYLOAD_STRUCTURE]
    assert len(rejections) == 0
    assert modules[ObjectValidatorConfig.PAYLOAD_STRUCTURE]["validator"] \
        != ObjectValidatorConfig.VALIDATOR_OPTIONS[ObjectValidatorConfig.PAYLOAD_STRUCTURE]["validator"]

def test_process_module_selection_profile_bad():
    """Test bad profile_url-argument for method `process_module_selection`."""

    modules, rejections = process_module_selection(
        ObjectValidatorConfig,
        [ObjectValidatorConfig.PAYLOAD_STRUCTURE, ObjectValidatorConfig.PAYLOAD_INTEGRITY],
        "bad_url"
    )

    assert list(modules.keys()) == [ObjectValidatorConfig.PAYLOAD_INTEGRITY]
    assert len(rejections) == 1
    assert rejections[0][0] == ObjectValidatorConfig.PAYLOAD_STRUCTURE


##############################
####  /validate_object
def test_validate_object_with_checksum(
    client, fixtures_path, object_good, validate_file_patcher_factory
):
    """Minimal test of validate_object-endpoint with checksum."""

    validate_file_patcher = validate_file_patcher_factory(0)
    validate_file_patcher.start()

    _hash = hash_from_file("md5", fixtures_path / object_good)
    response = client.post(
        "/validate_object",
        json={
            "object": {"path": str(fixtures_path / object_good)},
            "checksum": {"method": "md5", "value": _hash}
        }
    )

    assert response.status_code == 201
    token = response.json["token"]

    # wait for job to finish
    max_sleep = 10
    c_sleep = 0
    while c_sleep < max_sleep:
        sleep(1)
        response = client.get(
            f"/report?token={token}"
        )
        if response.status_code == 200:
            break
        c_sleep = c_sleep + 1

    assert "valid" in response.json
    assert response.json["valid"]
    assert "Checksum" in str(response.json["info"])

    validate_file_patcher.stop()

def test_validate_object_with_checksum_bad(
    client, fixtures_path, object_good, validate_file_patcher_factory
):
    """Minimal test of validate_object-endpoint with checksum (bad md5)."""

    validate_file_patcher = validate_file_patcher_factory(0)
    validate_file_patcher.start()

    _hash = hash_from_file("md5", fixtures_path / object_good)
    response = client.post(
        "/validate_object",
        json={
            "object": {"path": str(fixtures_path / object_good)},
            "checksum": {"method": "md5", "value": _hash + "a"}
        }
    )

    assert response.status_code == 201
    token = response.json["token"]

    # wait for job to finish
    max_sleep = 10
    c_sleep = 0
    while c_sleep < max_sleep:
        sleep(1)
        response = client.get(
            f"/report?token={token}"
        )
        if response.status_code == 200:
            break
        c_sleep = c_sleep + 1

    assert "valid" in response.json
    assert not response.json["valid"]
    assert "Checksum" in str(response.json["errors"])

    validate_file_patcher.stop()

def test_validate_object_with_checksum_unknown(
    client, fixtures_path, object_good, validate_file_patcher_factory
):
    """Minimal test of validate_object-endpoint with checksum (unknown method)."""

    response = client.post(
        "/validate_object",
        json={
            "object": {"path": str(fixtures_path / object_good)},
            "checksum": {"method": "md5a", "value": "a"}
        }
    )

    assert response.status_code == 422

def test_validate_object_201(
    client, fixtures_path, object_good, validate_file_patcher_factory
):
    """Minimal test of validate_object-endpoint; status 201."""

    validate_file_patcher = validate_file_patcher_factory(0)
    validate_file_patcher.start()
    response = client.post(
        "/validate_object",
        json={"object": {"path": str(fixtures_path / object_good)}}
    )

    assert response.status_code == 201

    assert "token" in response.json

    validate_file_patcher.stop()

@pytest.mark.parametrize(
    ("json", "status"),
    [
        ({"no_Object": None}, 400),
        ({"object": {"no_path": None}}, 400),
        ({"object": {"path": "invalid/path"}}, 404),
        ({"object": {"path": None}}, 422),
    ],
    ids=["no_Object", "no_path", "invalid_path", "null_path"]
)
def test_validate_object_4xx(client, json, status):
    """Minimal test of validate_object-endpoint; status 4xx."""

    response = client.post(
        "/validate_object",
        json=json
    )

    assert response.status_code == status

def test_validate_object_503(
    client, fixtures_path, object_good, validate_file_patcher_factory
):
    """
    Minimal test of validate_object-endpoint; status 503.

    To this end, fake the validate_file-method of FileFormatValidator to
    take a set amount of time. This ensures that the queue is filled up
    for the test.
    """

    fake_duration = 0.1
    validate_file_patcher = validate_file_patcher_factory(fake_duration)

    validate_file_patcher.start()

    # submit two jobs (second is expected to be rejected)
    response = client.post(
        "/validate_object",
        json={"object": {"path": str(fixtures_path / object_good)}}
    )
    response = client.post(
        "/validate_object",
        json={"object": {"path": str(fixtures_path / object_good)}}
    )

    assert response.status_code == 503

    # check for successful submission after first accepted job has finished
    sleep(fake_duration + 0.1)
    response = client.post(
        "/validate_object",
        json={"object": {"path": str(fixtures_path / object_good)}}
    )

    assert response.status_code == 201

    validate_file_patcher.stop()

##############################
####  /validate_ip
def test_validate_ip_201(
    client, fixtures_path, ip_good, validate_bag_patcher_factory
):
    """Minimal test of validate_ip-endpoint; status 201."""

    validate_bag_patcher = validate_bag_patcher_factory(0)
    validate_bag_patcher.start()
    response = client.post(
        "/validate_ip",
        json={"IP": {"path": str(fixtures_path / ip_good)}}
    )

    assert response.status_code == 201

    assert "token" in response.json

    validate_bag_patcher.stop()

@pytest.mark.parametrize(
    ("json", "status"),
    [
        ({"no_IP": None}, 400),
        ({"IP": {"no_path": None}}, 400),
        ({"IP": {"path": "invalid/path"}}, 404),
        ({"IP": {"path": None}}, 422),
    ],
    ids=["no_IP", "no_path", "invalid_path", "null_path"]
)
def test_validate_ip_4xx(client, json, status):
    """Minimal test of validate_ip-endpoint; status 4xx."""

    response = client.post(
        "/validate_ip",
        json=json
    )

    assert response.status_code == status

def test_validate_ip_503(
    client, fixtures_path, ip_good, validate_bag_patcher_factory
):
    """
    Minimal test of validate_ip-endpoint; status 503.

    To this end, fake the validate_file-method of FileFormatValidator to
    take a set amount of time. This ensures that the queue is filled up
    for the test.
    """

    fake_duration = 0.1
    validate_bag_patcher = validate_bag_patcher_factory(fake_duration)

    validate_bag_patcher.start()

    # submit two jobs (second is expected to be rejected)
    response = client.post(
        "/validate_ip",
        json={"IP": {"path": str(fixtures_path / ip_good)}}
    )
    response = client.post(
        "/validate_ip",
        json={"IP": {"path": str(fixtures_path / ip_good)}}
    )

    assert response.status_code == 503

    # check for successful submission after first accepted job has finished
    sleep(fake_duration + 0.1)
    response = client.post(
        "/validate_ip",
        json={"IP": {"path": str(fixtures_path / ip_good)}}
    )

    assert response.status_code == 201

    validate_bag_patcher.stop()

##############################
####  /report
def test_validate_object_get_report(
    client, fixtures_path, object_good, validate_file_patcher_factory
):
    """Test for the /report-GET endpoint."""

    validate_file_patcher = validate_file_patcher_factory(0)
    validate_file_patcher.start()

    # submit job
    response = client.post(
        "/validate_object",
        json={"object": {"path": str(fixtures_path / object_good)}}
    )

    assert response.status_code == 201
    token = response.json["token"]

    # wait until job is completed
    max_sleep = 10
    c_sleep = 0
    while c_sleep < max_sleep:
        sleep(1)
        response = client.get(
            f"/report?token={token}"
        )
        if response.status_code == 200:
            break
        c_sleep = c_sleep + 1

    assert "valid" in response.json
    assert response.json["valid"]

    validate_file_patcher.stop()

def test_validate_object_get_report_unknown(
    client, fixtures_path, object_good, validate_file_patcher_factory
):
    """Test for the /report-GET endpoint for unknown job."""

    response = client.get(
        "/report?token=test"
    )
    assert response.status_code == 404

def test_validate_object_get_report_unfinished(
    client, fixtures_path, object_good, validate_file_patcher_factory
):
    """Test for the /report-GET endpoint for unfinished job."""

    validate_file_patcher = validate_file_patcher_factory(1)
    validate_file_patcher.start()

    # submit job
    response = client.post(
        "/validate_object",
        json={"object": {"path": str(fixtures_path / object_good)}}
    )

    assert response.status_code == 201
    token = response.json["token"]

    # do not wait until job is completed
    response = client.get(
        f"/report?token={token}"
    )
    assert response.status_code == 503

    validate_file_patcher.stop()

def test_validate_object_get_report_bad(client, fixtures_path, object_bad):
    """Test for the /report-GET endpoint with bad result."""

    # submit job
    response = client.post(
        "/validate_object",
        json={"object": {"path": str(fixtures_path / object_bad)}}
    )

    assert response.status_code == 201
    token = response.json["token"]

    # wait until job is completed
    max_sleep = 10
    c_sleep = 0
    while c_sleep < max_sleep:
        sleep(1)
        response = client.get(
            f"/report?token={token}"
        )
        if response.status_code == 200:
            break
        c_sleep = c_sleep + 1

    assert "valid" in response.json
    assert not response.json["valid"]
    assert "errors" in response.json
    assert "JHOVE" in str(response.json["errors"])

@pytest.mark.parametrize(
    ("endpoint", "json_target", "target"),
    [
        ("/validate_object", "object", "object"),
        ("/validate_ip", "IP", "IP"),
    ],
    ids=["/validate_object", "/validate_ip"]
)
def test_termination_callback(
    client, fixtures_path, endpoint, json_target, target, targets_good,
    callback_host, callback_port, callback_path, callback_environ
):
    """
    Test for the callbacks of /validate_x using the flask-app stated in the
    callback_app_service-fixture.
    """

    # set environment variable beforehand
    os.environ[callback_environ] = "0"

    # define callback-url
    callback_url = f"http://{callback_host}:{callback_port}{callback_path}"

    # submit job
    response = client.post(
        endpoint,
        json={
            json_target: {"path": str(fixtures_path / targets_good[target])},
            "callbackUrl": callback_url
        }
    )

    assert response.status_code == 201
    token = response.json["token"]

    # wait until job is completed
    max_sleep = 10
    c_sleep = 0
    while c_sleep < max_sleep:
        sleep(1)
        response = client.get(
            f"/report?token={token}"
        )
        if response.status_code == 200:
            break
        c_sleep = c_sleep + 1

    # check whether callback has been executed
    assert os.environ[callback_environ] == token


def test_report_unknown_query_input(client):
    """
    Test validation-blueprint `/report` route for acceptance of
    unknown query.
    """

    response = client.get("/report?some_query", json={})
    assert response.status_code == 400
    assert b"some_query" in response.data


@pytest.mark.parametrize(
    "endpoint",
    ["validate_object", "validate_ip"]
)
def test_validation_unknown_query_input(client, endpoint):
    """
    Test validation-blueprint `/validate_X` routes' for acceptance of
    unknown query.
    """

    response = client.post(f"/{endpoint}?some_query", json={})
    assert response.status_code == 400
    assert b"some_query" in response.data


@pytest.mark.parametrize(
    "endpoint",
    ["validate_object", "validate_ip"]
)
def test_validation_unknown_body_input(client, endpoint):
    """
    Test validation-blueprint `/validate_X` routes' for acceptance of
    unknown contents in requestBody.
    """

    response = client.post(f"/{endpoint}", json={"some_argument": "value"})
    assert response.status_code == 400
    assert b"some_argument" in response.data
