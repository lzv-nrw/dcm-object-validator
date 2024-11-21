# Digital Curation Manager - Object Validator

The 'DCM Object Validator'-API provides functionality to validate file formats and file integrity.
This repository contains the corresponding Flask app definition.
For the associated OpenAPI-document, please refer to the sibling package [`dcm-object-validator-api`](https://github.com/lzv-nrw/dcm-object-validator-api).

The contents of this repository are part of the [`Digital Curation Manager`](https://github.com/lzv-nrw/digital-curation-manager).

## Local install
Make sure to include the extra-index-url `https://zivgitlab.uni-muenster.de/api/v4/projects/9020/packages/pypi/simple` in your [pip-configuration](https://pip.pypa.io/en/stable/cli/pip_install/#finding-packages) to enable an automated install of all dependencies.
Using a virtual environment is recommended.

1. Install with
   ```
   pip install .
   ```
1. Configure service environment to fit your needs ([see here](#environmentconfiguration)).
1. Run app as
   ```
   flask run --port=8080
   ```
1. To manually use the API, either run command line tools like `curl` as, e.g.,
   ```
   curl -X 'POST' \
     'http://localhost:8080/validate/object' \
     -H 'accept: application/json' \
     -H 'Content-Type: application/json' \
     -d '{
     "validation": {
       "target": {
         "path": "obj/abcde-12345-fghijk-67890.tiff"
       },
       "modules": [
         "file_format",
         "file_integrity"
       ],
       "args": {
         "file_integrity": {
           "method": "md5",
           "value": "46a78da2a246a86f76d066db766cda4f"
         }
       }
     }
   }'
   ```
   or run a gui-application, like Swagger UI, based on the OpenAPI-document provided in the sibling package [`dcm-object-validator-api`](https://github.com/lzv-nrw/dcm-object-validator-api).

## Run with docker compose
Simply run
```
docker compose up
```
By default, the app listens on port 8080.
The docker volume `file_storage` is automatically created and data will be written in `/file_storage`.
To rebuild an already existing image, run `docker compose build`.

Additionally, a Swagger UI is hosted at
```
http://localhost/docs
```

Afterwards, stop the process and enter `docker compose down`.

## Tests
Install additional dev-dependencies with
```
pip install -r dev-requirements.txt
```
Run unit-tests with
```
pytest -v -s
```

## Environment/Configuration
Service-specific environment variables are
* `JHOVE_APP` [DEFAULT "jhove"]: location of local jhove app
* `PAYLOAD_PROFILE_URL` [DEFAULT "file://\<path-to-dcm-object-validator\>/static/payload_profile.json"]: url to bagit payload profile in JSON-format

Additionally this service provides environment options for
* `BaseConfig`,
* `OrchestratedAppConfig`, and
* `FSConfig`

as listed [here](https://github.com/lzv-nrw/dcm-common#app-configuration).

# Contributors
* Sven Haubold
* Orestis Kazasidis
* Stephan Lenartz
* Kayhan Ogan
* Michael Rahier
* Steffen Richters-Finger
* Malte Windrath
* Roman Kudinov