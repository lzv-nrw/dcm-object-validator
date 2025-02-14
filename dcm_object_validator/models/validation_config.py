"""
ValidationConfig data-model definition
"""

from dataclasses import dataclass

from dcm_common.models import JSONObject, DataModel

from .target import Target


@dataclass
class PluginConfig(DataModel):
    """Plugin config `DataModel`"""

    plugin: str
    args: JSONObject


@dataclass
class ValidationConfig(DataModel):
    """Validation config `DataModel`"""

    target: Target
    plugins: dict[str, PluginConfig]
