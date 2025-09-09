# Changelog

## [6.0.0] - 2025-09-09

### Changed

- **Breaking:** migrated to API v6

## [5.2.0] - 2025-08-20

### Added

- added support for submission token

## [5.1.0] - 2025-08-14

### Changed

- migrated to new extension system

## [5.0.1] - 2025-07-25

### Fixed

- fixed initialization of ScalableOrchestrator with ORCHESTRATION_PROCESSES

## [5.0.0] - 2025-02-14

### Changed

- Dockerfile: switched to non root-user, pinned JHOVE version, and added checksum validation for JHOVE
- migrated to API v5

### Added

- added (JHOVE-based) plugin for file format-validation in BagIt-format
- added support for importing external plugins
- added plugin for file integrity-validation using the BagIt-format
- added plugin for file integrity-validation
- added (JHOVE-based) plugin for file format-validation
- added validation-plugin interface and related definitions
- added (fido-based) format identification plugins

### Removed

- removed docker compose file
- removed `dcm-bag-validator` dependency

## [4.0.1] - 2024-11-21

### Changed

- updated package metadata, Dockerfiles, and README

## [4.0.0] - 2024-10-15

### Changed

- **Breaking:** implemented changes of API v4 (`738453e5`, `6d34194a`)
- migrated to `dcm-common` (scalable orchestration and related components; latest `DataModel`) (`738453e5`, `6d34194a`)

## [3.0.0] - 2024-07-24

### Changed

- improved report.progress.verbose messages (`a5df790a`)
- **Breaking:** updated to API v3 (`201416b3`, `33623e26`)

### Fixed

- fixed bad values for `data.valid` in intermediate reports (`33623e26`)

## [2.0.1] - 2024-04-30

### Fixed

- fixed erroneous handling of `target.path` (`d1742b97`)

## [2.0.0] - 2024-04-25

### Changed
- **Breaking:** shorten name of app-starter `app.py` (`47a1999e`)
- **Breaking:** shorten name of config-class (`f31adfc0`, `48569299`)
- updated version for `lzvnrw_supplements.orchestration` (`11ebc93b`)
- **Breaking:** implemented changed object validator api (`11ebc93b`, `8bc1041a`)
- improved code-quality by introducing proper data models (`11ebc93b`)
- refactored endpoint paths and app structure (`6c2b24e0`)
- separated job instructions for the validation endpoints (`e32a9ad7`, `11ebc93b`)
- changed request.host to request.host_url for the host-property of a report (`b93d9783`)
- updated input-handling based on data-plumber-http (`758f2620`)

### Added

- added extras-dependency for `Flask-CORS` (`fe808c10`)
- added py.typed marker to package (`72670dc6`)

## [1.0.0] - 2024-01-26

### Changed

- **Breaking:** change object property capitalization in requestBodies (changed in api) (`abc47cb1`)
- **Breaking:** change set of status codes (changed in api) (`eae6f6f2`)
- **Breaking:** change name of parameter 'validation_token' to 'token' (`cb36a1be`)
- make use of GitLab package registry in Dockerfiles (`06e8a13e`)

### Fixed

- improved and updated README usage-instructions for changed behavior (`870d47dc`) 
- fix url handler behavior (`cbc93948`, `428275af`)

## [0.1.0] - 2024-01-19

### Changed

- initial release of dcm-object-validator