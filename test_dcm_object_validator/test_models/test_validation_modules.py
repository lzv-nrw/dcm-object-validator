"""ValidationModule- and FileFormatPluginModule-tests."""

import pytest

from dcm_object_validator.models import validation_modules


@pytest.mark.parametrize(
    ("plugin", "kwargs"),
    [
        (
            validation_modules.JhovePluginModule,
            {
                "jhove_app": "app"
            }
        ),
    ],
    ids=[
        "JhovePluginModule"
    ]
)
def test_plugin_basic_constructor(plugin, kwargs):
    """Test constructors of `FileFormatPluginModule`."""

    plugin.get_plugin(**kwargs)


@pytest.mark.parametrize(
    ("module", "kwargs"),
    [
        (
            validation_modules.BagitProfileModule,
            {
                "bagit_profile_url": "some-url",
                "bagit_profile": {
                    "BagIt-Profile-Info": {"Source-Organization": ""}
                },
                "ignore_baginfo_tag_case": False
            }
        ),
        (
            validation_modules.PayloadStructureModule,
            {
                "payload_profile_url": "some-url",
                "payload_profile": {}
            }
        ),
        (
            validation_modules.PayloadIntegrityModule,
            {}
        ),
        (
            validation_modules.FileFormatModule,
            {
                "list_of_validators": [
                    (
                        r"text/plain",
                        validation_modules.JhovePluginModule.get_plugin()
                    )
                ]
            }
        ),
    ],
    ids=[
        "BagitProfileModule", "PayloadStructureModule",
        "PayloadIntegrityModule", "FileFormatModule"
    ]
)
def test_module_basic_constructor(module, kwargs):
    """Test constructors of `ValidationModules`."""

    module.get_validator(**kwargs)
