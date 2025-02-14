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
     'http://localhost:8080/validate' \
     -H 'accept: application/json' \
     -H 'Content-Type: application/json' \
     -d '{
     "validation": {
       "target": {
         "path": "obj/abcde-12345-fghijk-67890.tiff"
       },
       "plugins": {
         "validation-request-1": {
           "plugin": "integrity",
           "args": {
             "method": "md5",
             "value": "46a78da2a246a86f76d066db766cda4f"
           }
         },
         "validation-request-2": {
           "plugin": "jhove",
           "args": {
             "format_identification": {
               "plugin": "fido-mimetype"
             }
           }
         }
       }
     }
   }'
   ```
   or run a gui-application, like Swagger UI, based on the OpenAPI-document provided in the sibling package [`dcm-object-validator-api`](https://github.com/lzv-nrw/dcm-object-validator-api).

### Extra dependencies

#### fido-format identification
The Object Validator app-package defines an optional dependency for support of [`fido`](https://github.com/openpreserve/fido) which is used by fido-based file format identification-plugins.
This extra can be installed with
```
pip install ".[fido]"
```

#### JHOVE-format validation
The Object Validator app-package defines plugins that are based on [JHOVE](https://github.com/openpreserve/jhove).
These will only run if JHOVE can be invoked with the command given in `DEFAULT_JHOVE_CMD` (see, e.g., the `Dockerfile` in this repository for reference).

## List of plugins
Part of this implementation is a plugin-system for both file format-identification and -validation.
It is based on the general-purpose plugin-system implemented in `dcm-common`.

### Format identification
Format indentification-plugins (plugin-context `identification` as referred to in the Object Validator API) serve to generate a string identifier (like a MIME-type) for a file's format.
Currently, the following plugins are pre-defined:
* `fido-mimetype`: returns the MIME-type of a file using `fido` (requires the `fido`-extra)
* `fido-puid`: returns the PRONOM-id of a file using `fido` (requires the `fido`-extra)

### File validation
File validation-plugins (plugin-context `validation` as referred to in the Object Validator API) serve to determine file validity and generate reports on detected errors.
Currently, the following plugins are pre-defined:
* `integrity`: determines file integrity based on checksums
* `integrity-bagit`: determines file integrity based on checksums; reads checksum information from manifest-files as provided by the [BagIt](https://datatracker.ietf.org/doc/html/rfc8493)-format (batch only)
* `jhove-fido-mimetype`: validates file formats using `JHOVE` (requires `JHOVE` to be installed and configured); optionally uses `fido-mimetype`-plugin to identify file-formats and select appropriate JHOVE-module
* `jhove-fido-mimetype-bagit`: same as `jhove-fido-mimetype` but only validate the [BagIt](https://datatracker.ietf.org/doc/html/rfc8493)-bag payload-subdirectory of the given target (batch only)

The expected call signatures (and more) information for individual plugins are provided via the API at runtime (endpoint `GET-/identify`).

### Additional plugins
This service supports dynamically loading additional plugins which implement the common plugin-interface.
In order to load additional plugins, use the environment variables `ADDITIONAL_IDENTIFICATION_PLUGINS_DIR` and `ADDITIONAL_VALIDATION_PLUGINS_DIR`.
If set, the app will search for valid implementations in all modules that are in the given directory-trees.
To qualify as external plugin, the classes need to
* implement the `PluginInterface` as defined in the [`dcm-common`-package](https://github.com/lzv-nrw/dcm-common),
* be named `ExternalPlugin` (only one plugin per module), and
* define the correct context (`"identification"` or `"validation"`, respectively).

It is recommended to use the `FormatIdentificationPlugin`- and `ValidationPlugin`-interfaces defined in this package as basis, e.g., like
```python
from dcm_object_validator.plugins.validation.interface import (
    ValidationPlugin, ValidationPluginResultPart
)

class ExternalPlugin(ValidationPlugin):
    _NAME = "custom-validation-plugin"
    _DISPLAY_NAME = "Custom-Plugin"
    _DESCRIPTION = "Custom validation-plugin."

    def _get_part(
        self, record_path: Path, /, **kwargs
    ) -> ValidationPluginResultPart:
        result = ValidationPluginResultPart(
          # ...
        )
        # ... custom validation code here
        return result
```
Note that plugin-constructors are called without arguments. If a plugin needs additional information in its constructor, the recommended way to handle this is to read that information from the environment instead.

## Docker
Build an image using, for example,
```
docker build -t dcm/object-validator:dev .
```
Then run with
```
docker run --rm --name=object-validator -p 8080:80 dcm/object-validator:dev
```
and test by making a GET-http://localhost:8080/identify request.

For additional information, refer to the documentation [here](https://github.com/lzv-nrw/digital-curation-manager).

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
* `ADDITIONAL_IDENTIFICATION_PLUGINS_DIR` [DEFAULT null]: directory with external identification plugins to be loaded (see also [this explanation](#additional-plugins))
* `ADDITIONAL_VALIDATION_PLUGINS_DIR` [DEFAULT null]: directory with external validation plugins to be loaded (see also [this explanation](#additional-plugins))
* `DEFAULT_FIDO_CMD` [DEFAULT "fido"]: default shell command to invoke fido
* `DEFAULT_JHOVE_CMD` [DEFAULT "jhove"]: default shell command to invoke jhove

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