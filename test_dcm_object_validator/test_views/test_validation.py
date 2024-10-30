"""'Object Validator'-app test-module for validation-endpoints."""

import os
from time import sleep
from hashlib import md5

import requests
import pytest
from dcm_common import LoggingContext as Context


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
        os.environ[callback_environ] = flask_request.json["value"]
        return "success", 200

    # set some initial value for environment variable
    os.environ[callback_environ] = "0"

    Thread(
        target=lambda:
            app.run(
                host=callback_host,
                port=callback_port,
                debug=False
            ),
        daemon=True
    ).start()

    # wait for app to start
    max_sleep = 250
    c_sleep = 0
    while c_sleep < max_sleep:
        sleep(0.25)
        response = requests.post(
            f"http://{callback_host}:{callback_port}{callback_path}",
            json={
                "value": "0"
            },
            timeout=1
        )
        if response.status_code == 200:
            break
        c_sleep = c_sleep + 1

    # delete environment variable after session
    def auto_resource_fin():
        del os.environ[callback_environ]

    request.addfinalizer(auto_resource_fin)


# #############################
# ###  /validate_object
def test_validate_object_with_checksum(
    client, fixtures, object_good, validate_file_patcher_factory,
    wait_for_report
):
    """Minimal test of validate_object-endpoint with checksum."""

    validate_file_patcher = validate_file_patcher_factory(0)
    validate_file_patcher.start()

    _hash = md5((fixtures / object_good).read_bytes()).hexdigest()
    response = client.post(
        "/validate/object",
        json={
            "validation": {
                "target": {"path": str(object_good)},
                "args": {
                    "file_integrity": {"method": "md5", "value": _hash}
                }
            }
        }
    )
    assert response.status_code == 201
    assert client.put("/orchestration?until-idle", json={}).status_code == 200

    # wait for job to finish
    report = wait_for_report(client, response.json["value"])

    assert report["data"]["valid"]
    assert report["data"]["details"]["file_integrity"]["valid"]
    assert "Checksum" in str(
        report["data"]["details"]["file_integrity"]["log"][Context.INFO.name]
    )

    validate_file_patcher.stop()


def test_validate_object_with_checksum_bad(
    client, fixtures, object_good, validate_file_patcher_factory,
    wait_for_report
):
    """Minimal test of validate_object-endpoint with checksum (bad md5)."""

    validate_file_patcher = validate_file_patcher_factory(0)
    validate_file_patcher.start()

    _hash = md5((fixtures / object_good).read_bytes()).hexdigest()
    response = client.post(
        "/validate/object",
        json={
            "validation": {
                "target": {"path": str(object_good)},
                "args": {
                    "file_integrity": {"method": "md5", "value": _hash + "a"}
                }
            }
        }
    )
    assert client.put("/orchestration?until-idle", json={}).status_code == 200

    # wait for job to finish
    report = wait_for_report(client, response.json["value"])

    assert not report["data"]["valid"]
    assert not report["data"]["details"]["file_integrity"]["valid"]
    assert "Checksum" in str(
        report["data"]["details"]["file_integrity"]["log"][Context.ERROR.name]
    )

    validate_file_patcher.stop()


def test_validate_object_with_checksum_unknown(
    client, object_good
):
    """Minimal test of validate_object-endpoint with checksum (unknown method)."""

    response = client.post(
        "/validate/object",
        json={
            "validation": {
                "target": {"path": str(object_good)},
                "args": {
                    "file_integrity": {"method": "md5a", "value": "a"}
                }
            }
        }
    )
    assert response.status_code == 422


def test_validate_object_201(
    client, object_good, validate_file_patcher_factory
):
    """Minimal test of validate_object-endpoint; status 201."""

    validate_file_patcher = validate_file_patcher_factory(0)
    validate_file_patcher.start()
    response = client.post(
        "/validate/object",
        json={
            "validation": {
                "target": {"path": str(object_good)},
                "modules": ["file_format"]
            }
        }
    )
    assert response.status_code == 201
    assert client.put("/orchestration?until-idle", json={}).status_code == 200

    assert "value" in response.json

    validate_file_patcher.stop()


@pytest.mark.parametrize(
    ("json", "status"),
    [
        ({"no_Object": None}, 400),
        ({"target": {"no_path": None}}, 400),
        ({"target": {"path": "invalid/path"}}, 404),
        ({"target": {"path": None}}, 422),
    ],
    ids=["no_Object", "no_path", "invalid_path", "null_path"]
)
def test_validate_object_4xx(client, json, status):
    """Minimal test of validate_object-endpoint; status 4xx."""

    response = client.post(
        "/validate/object",
        json={
            "validation": json | {"modules": ["file_format"]}
        }
    )
    assert response.status_code == status


# #############################
# ###  /validate_ip
def test_validate_ip_201(
    client, ip_good, validate_bag_patcher_factory
):
    """Minimal test of validate_ip-endpoint; status 201."""

    validate_bag_patcher = validate_bag_patcher_factory(0)
    validate_bag_patcher.start()
    response = client.post(
        "/validate/ip",
        json={
            "validation": {
                "target": {"path": str(ip_good)}
            }
        }
    )
    assert response.status_code == 201

    assert "value" in response.json

    validate_bag_patcher.stop()


@pytest.mark.parametrize(
    ("json", "status"),
    [
        ({"no_IP": None}, 400),
        ({"target": {"no_path": None}}, 400),
        ({"target": {"path": "invalid/path"}}, 404),
        ({"target": {"path": None}}, 422),
    ],
    ids=["no_IP", "no_path", "invalid_path", "null_path"]
)
def test_validate_ip_4xx(client, json, status):
    """Minimal test of validate/ip-endpoint; status 4xx."""

    response = client.post(
        "/validate/ip",
        json={
            "validation": json
        }
    )
    assert response.status_code == status

##############################


@pytest.mark.parametrize(
    ("endpoint", "target"),
    [
        ("/validate/object", "object"),
        ("/validate/ip", "IP"),
    ],
    ids=["/validate/object", "/validate/ip"]
)
def test_termination_callback(
    client, endpoint, target, targets_good,
    callback_host, callback_port, callback_path, callback_environ,
    wait_for_report
):
    """
    Test for the callbacks of /validate/x using the flask-app stated in the
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
            "validation": {
                "target": {"path": str(targets_good[target])},
                "modules": ["file_format"]
            },
            "callbackUrl": callback_url
        }
    )
    assert client.put("/orchestration?until-idle", json={}).status_code == 200

    # wait until job is completed
    wait_for_report(client, response.json["value"])

    # check whether callback has been executed
    assert os.environ[callback_environ] == response.json["value"]


@pytest.mark.parametrize(
    "endpoint",
    ["validate/object", "validate/ip"]
)
def test_validation_unknown_query_input(client, endpoint):
    """
    Test validation-blueprint `/validate/X` routes' for acceptance of
    unknown query.
    """

    response = client.post(f"/{endpoint}?some_query", json={})
    assert response.status_code == 400
    assert b"some_query" in response.data


@pytest.mark.parametrize(
    "endpoint",
    ["validate/object", "validate/ip"]
)
def test_validation_unknown_body_input(client, endpoint):
    """
    Test validation-blueprint `/validate/X` routes' for acceptance of
    unknown contents in requestBody.
    """

    response = client.post(f"/{endpoint}", json={"some_argument": "value"})
    assert response.status_code == 400
    assert b"some_argument" in response.data
    client.delete("/orchestration", json={})


@pytest.mark.parametrize(
    ("path", "target"),
    [
        ("/validate/object", "object_good"),
        ("/validate/ip", "ip_good"),
    ],
    ids=["object", "ip"]
)
def test_validate_empty_modules_list(
    path, target, request, client, wait_for_report
):
    """Minimal test of validation-endpoints with empty modules list."""

    response = client.post(
        path,
        json={
            "validation": {
                "target": {
                    "path":
                        str(request.getfixturevalue(target))
                },
                "modules": []
            }
        }
    )
    assert client.put("/orchestration?until-idle", json={}).status_code == 200

    # wait for job to finish
    report = wait_for_report(client, response.json["value"])

    assert report["data"]["valid"]
    assert len(report["data"]["details"]) == 0


@pytest.mark.parametrize(
    ("path", "target"),
    [
        ("/validate/object", "object_good"),
        ("/validate/ip", "ip_good"),
    ],
    ids=["object", "ip"]
)
def test_validate_unknown_modules_list(
    path, target, request, client, wait_for_report
):
    """Minimal test of validation-endpoints with unknown module."""

    response = client.post(
        path,
        json={
            "validation": {
                "target": {
                    "path":
                        str(request.getfixturevalue(target))
                },
                "modules": ["unknown"]
            }
        }
    )
    assert client.put("/orchestration?until-idle", json={}).status_code == 200

    # wait for job to finish
    report = wait_for_report(client, response.json["value"])

    assert not report["data"]["valid"]
    assert len(report["data"]["details"]) == 1
    assert "module_selector" in report["data"]["details"]
    assert "ERROR" in report["data"]["details"]["module_selector"]["log"]
