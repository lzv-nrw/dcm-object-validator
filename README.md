# dcm-object-validator

## Quick start

Run container via `docker compose` with the command
```
docker compose up
```
(see below for more details). A Swagger UI is hosted at
```
http://localhost/docs
```
while (by-default) the app listens to port `8080`.

## Tests
Run `flask` test-module (after installing `dev-requirements.txt`) via
```
pytest
```

## Run with Docker
### Container setup
Use the `compose.yml` to start the `Object Validator`-Container as a service:
```
docker compose up
```
(to rebuild use `docker compose build`).
Afterwards, stop the process for example with `Ctrl`+`C` and enter `docker compose down` (see [this section](#environmentconfiguration) for configuration options).

The build process requires authentication with `zivgitlab.uni-muenster.de` in order to gain access to the required python dependencies.
The Dockerfiles are configured to use the information from `~/.netrc` for this authentication (a gitlab api-token is required).

### File system setup
The currently used docker volume is set up automatically on `docker compose up`. However, in order to move data from the local file system into the container, the container also needs to mount this local file system (along with the volume). To this end, the `compose.yml` can be modified before startup with
```
    ...
      - file_storage:/file_storage
      - type: bind
        source: ./test_dcm_object_validator/fixtures
        target: /local
    ports:
      ...
```
By then opening an interactive session in the container (i.e., after running the compose-script) with
```
docker exec -it <container-id> sh
```
the example bags from the test-related fixtures-directory can be copied over to the volume:
```
cp -r /local/* /file_storage/
```
(The modification to the file `compose.yml` can be reverted after copying.)
Then (with the container still running), the validate-route can be tested on the two bags `test-bag` and `test-bag_bad` with (for example)
```
curl -X 'POST' \
  'http://localhost:8080/validate/ip' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "validation": {
      "target": {
        "path": "test-bag"
      },
      "modules": [
        "file_format"
      ]
    }
  }'
```
The json-response should contain a `token`-value that can be used to get the corresponding report (replace `<token_value>`):
```
curl -X 'GET' \
  'http://localhost:8080/report?token=<token_value>' \
  -H 'accept: application/json'
```
In most cases, it is be more convenient to get this information via web-browser by simply entering the respective url
```
http://localhost:8080/report?token=<token_value>
```

### Swagger UI
The `compose.yml`-file is configured to also start a container which serves the Swagger UI
based on the `openapi.yaml`-document in the working directory (`dcm_object_validator_api/`) at the time of building.
To this end, the `ALLOW_CORS`-environment variable (see below) is set to `ALLOW_CORS=1`
while building the app's image. The UI is served at `http://localhost/docs`.

## Run with python
Run the 'Object Validator'-app locally with
```
flask run --port=8080
```
The working directory (i.e. the mount point of the (shared) "File Storage")
can be set via the environment variable `FS_MOUNT_POINT` and defaults to
`/file_storage` (see [this section](#environmentconfiguration) for more details).

## Environment/Configuration
Service-specific environment variables are
* `JHOVE_APP` [DEFAULT "jhove"]: location of local jhove app
* `PAYLOAD_PROFILE_URL` [DEFAULT "./dcm_object_validator/static/payload_profile.json"]: url to bagit payload profile in JSON-format

Additionally this service provides environment options for
* `BaseConfig`,
* `OrchestratedAppConfig`, and
* `FSConfig`

as listed [here](https://github.com/lzv-nrw/dcm-common/-/tree/dev?ref_type=heads#app-configuration).

# Contributors
* Sven Haubold
* Orestis Kazasidis
* Stephan Lenartz
* Kayhan Ogan
* Michael Rahier
* Steffen Richters-Finger
* Malte Windrath
