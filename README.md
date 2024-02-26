# LZV.nrw DCM Object Validator
View the OpenAPI document for this project at [dcm-object-validator-api](https://github.com/lzv-nrw/dcm-object-validator-api).

## Preparation
Prepare a venv by
* cloning all required LZV.nrw-dependencies (see `setup.py`),
* performing the following steps for every dependency:
  1. check out required tag/version,
  1. manually edit the `setup.py`-files by adding a version-string, e.g.,
     ```
     setup(
         version="X.Y.Z",
         name="lzvnrw-supplements",
         ...
     )
     ```
     (the version "X.Y.Z" should be chosen as the name of the checked out tag), and
  1. install that dependency by issuing `pip install <path-to-repo>`
* and, finally, installing this package itself with `pip install .`

## Tests
Run `flask` test-module (after installing `dev-requirements.txt`) via
```
pytest
```

## Run
Run the 'Object Validator'-app locally with
```
flask --app dcm_object_validator_app run
```
The working directory (i.e. the mount point of the (shared) "File Storage")
can be set via the environment variable `FS_MOUNT_POINT` and defaults to
`/file_storage` (see [this section](#environmentconfiguration) for more details).

## Environment/Configuration
Available environment variables are
* `ALLOW_CORS` [DEFAULT 0]: have flask-app allow cross-origin-resource-sharing; needed for hosting swagger-ui with `try-it` functionality
* `FS_MOUNT_POINT` [DEFAULT "/file_storage"]: Path to the working directory (typically mount point of the shared file system)
* `JOB_TOKEN_EXPIRES` [DEFAULT 1]: whether job tokens (and their associated info like report) expire
* `JOB_TOKEN_DURATION` [DEFAULT 3600]: time until job token expires in seconds
* `QUEUE_LIMIT` [DEFAULT 1]: maximum length of job-queue
* `JHOVE_APP` [DEFAULT "jhove"]: location of local jhove app
* `PAYLOAD_PROFILE_URL` [DEFAULT "./dcm_object_validator/static/payload_profile.json"]: url to bagit payload profile in JSON-format

# Contributors
* Sven Haubold
* Orestis Kazasidis
* Stephan Lenartz
* Kayhan Ogan
* Michael Rahier
* Steffen Richters-Finger
* Malte Windrath
