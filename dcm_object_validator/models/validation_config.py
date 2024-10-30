"""
ValidationConfig data-model definition
"""

from typing import Optional, Any

from dcm_common.models import JSONable, DataModel

from dcm_object_validator.models.validation_modules \
    import ValidatorType, BagitProfileModule, \
        PayloadStructureModule, PayloadIntegrityModule, FileFormatModule, \
        JhovePluginModule, FileIntegrityModule


SUPPORTED_VALIDATORS = {
    BagitProfileModule.identifier: BagitProfileModule,
    PayloadStructureModule.identifier: PayloadStructureModule,
    PayloadIntegrityModule.identifier: PayloadIntegrityModule,
    FileIntegrityModule.identifier: FileIntegrityModule,
    FileFormatModule.identifier: FileFormatModule,
}
SUPPORTED_PLUGINS = {
    FileFormatModule.plugin_prefix + JhovePluginModule.identifier: \
        JhovePluginModule
}


class ValidationConfig(DataModel):
    """
    Validation config `DataModel`

    Processes job-specific module selection on instantiation.

    Keyword arguments:
    allowed -- exhaustive list of validator-identifiers that should
               be accepted
    modules -- job-specific selection of modules; a value of `None`
               corresponds to `allowed`
    kwargs -- dictionary of validation job-specific arguments (these
              are passed to the validation modules, e.g. profiles)
    """

    def __init__(
        self,
        allowed: list[str],
        modules: Optional[list[str]],
        kwargs: dict[str, Any]
    ) -> None:
        self.modules: dict[str, ValidatorType] = {}
        self.rejections: list[tuple[str, str]] = []
        self._process(allowed, modules, kwargs)

    @property
    def json(self) -> JSONable:
        return {
            "modules": list(self.modules.keys()),
            "rejections": dict(self.rejections)
        }

    def _process(
        self,
        allowed: list[str],
        modules: Optional[list[str]],
        kwargs: dict[str, Any]
    ) -> None:
        # handle default selection for modules
        if modules is None:
            _modules = allowed
        else:
            _modules = list(set(modules))  # make items unique

        file_format_plugins = []
        # iterate modules
        for module in _modules:
            # reject if not listed as supported in request
            if module not in allowed:
                self.rejections.append(
                    (
                        module,
                        f"Validation module '{module}' is not allowed in this context."
                    )
                )
                continue
            # reject if unknown
            if module not in SUPPORTED_VALIDATORS \
                    and module not in SUPPORTED_PLUGINS:
                self.rejections.append(
                    (
                        module,
                        f"Unknown validation module/plugin '{module}'."
                    )
                )
                continue
            # pre-process file-format plugins and postpone creating
            # file-format validator
            if module.startswith(FileFormatModule.plugin_prefix):
                file_format_plugins.append(module)
                continue
            if module == FileFormatModule.identifier:
                continue
            # register validator
            self.modules[module] = \
                SUPPORTED_VALIDATORS[module].get_validator(
                    **(kwargs.get(module, {}) or {})
                )

        # handle plugin-selection of file-format validation
        # use all plugins if only generic file-format identifier is
        # given
        if len(file_format_plugins) == 0 \
                and FileFormatModule.identifier in _modules:
            file_format_plugins = list(SUPPORTED_PLUGINS.keys())

        # build specific file_format-validator if requested
        if len(file_format_plugins) > 0 \
                and FileFormatModule.identifier in allowed:
            self.modules[FileFormatModule.identifier] = \
                FileFormatModule.get_validator(
                    list_of_validators=[
                        (
                            SUPPORTED_PLUGINS[v].plugin.DEFAULT_FILE_FORMATS,
                            SUPPORTED_PLUGINS[v].get_plugin(
                                **(kwargs.get(v, {}) or {})
                            )
                        )
                        for v in file_format_plugins
                    ],
                    **(kwargs.get(FileFormatModule.identifier, {}) or {})
                )
