# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.2](https://github.com/kallegrens/immich-migrator/compare/v0.3.1...v0.3.2) (2025-12-14)


### Documentation

* update README title with emoji ([d296363](https://github.com/kallegrens/immich-migrator/commit/d29636317b8d22c901d5e64947b9a78a7ef37e0a))

## [0.3.1](https://github.com/kallegrens/immich-migrator/compare/v0.3.0...v0.3.1) (2025-12-14)


### Bug Fixes

* **ci:** refactor asset generation ([fe7a3df](https://github.com/kallegrens/immich-migrator/commit/fe7a3dfaffb43e2db1d42a7a7bf8ed371199ee0e))

## [0.3.0](https://github.com/kallegrens/immich-migrator/compare/v0.2.0...v0.3.0) (2025-12-13)


### ⚠ BREAKING CHANGES

* Initial release v0.1.0

### Features

* implement immich-migrator CLI tool for server-to-server migration ([4129f65](https://github.com/kallegrens/immich-migrator/commit/4129f656695f8692a5d42028f5eac53195678535))


### Bug Fixes

* **ci:** add broader perms for workflows ([d8424c1](https://github.com/kallegrens/immich-migrator/commit/d8424c1bd79a5103c289ba2979acfe1df1dc4050))
* **ci:** add token to release-please ([d0668d1](https://github.com/kallegrens/immich-migrator/commit/d0668d1471113011c7402cca519c0a58b67de67b))
* **ci:** fix shell linting ([3b38902](https://github.com/kallegrens/immich-migrator/commit/3b38902f2e0e6e0f8da455f2cedf7f0e5241b9a6))
* **ci:** fix two commit sha's ([5715402](https://github.com/kallegrens/immich-migrator/commit/5715402696b39a9bf3e5fe3eb6a01705c17b81d1))
* **ci:** make pre-commit match the github actions linting workflow ([1188b9a](https://github.com/kallegrens/immich-migrator/commit/1188b9a14c8307b7fb145128aa967695e5e203fc))
* **ci:** pass secrets.GITHUB_TOKEN to setup-uv steps ([4acc186](https://github.com/kallegrens/immich-migrator/commit/4acc186711355c46dab03203f7dd605804bc03f5))
* **ci:** remove online-audits from zizmor & pin version for caching ([686b323](https://github.com/kallegrens/immich-migrator/commit/686b3231e8da2f4085cc1e392aaa4b1147d3820d))
* **ci:** simplify release-please-config.json ([587a060](https://github.com/kallegrens/immich-migrator/commit/587a0605a26cf8a93aca730c6587dd9df565c9a2))
* **ci:** use official zizmor action ([596edef](https://github.com/kallegrens/immich-migrator/commit/596edef93c12a4a504e2814373583d0c4d3e9798))
* correct uv dependency installation in GitHub Actions workflows ([9937f6f](https://github.com/kallegrens/immich-migrator/commit/9937f6fda7b264720b94f0bf64b9b283e587a09e))


### Documentation

* update installation commands to use modern uv syntax ([e47daa1](https://github.com/kallegrens/immich-migrator/commit/e47daa1e3755506007bcb015b3b81cc0ef1bb233))

## [0.2.0](https://github.com/kallegrens/immich-migrator/compare/immich-migrator-v0.1.0...immich-migrator-v0.2.0) (2025-12-12)


### ⚠ BREAKING CHANGES

* Initial release v0.1.0

### Features

* implement immich-migrator CLI tool for server-to-server migration ([4129f65](https://github.com/kallegrens/immich-migrator/commit/4129f656695f8692a5d42028f5eac53195678535))


### Bug Fixes

* **ci:** add broader perms for workflows ([d8424c1](https://github.com/kallegrens/immich-migrator/commit/d8424c1bd79a5103c289ba2979acfe1df1dc4050))
* **ci:** fix two commit sha's ([5715402](https://github.com/kallegrens/immich-migrator/commit/5715402696b39a9bf3e5fe3eb6a01705c17b81d1))
* **ci:** make pre-commit match the github actions linting workflow ([1188b9a](https://github.com/kallegrens/immich-migrator/commit/1188b9a14c8307b7fb145128aa967695e5e203fc))
* **ci:** pass secrets.GITHUB_TOKEN to setup-uv steps ([4acc186](https://github.com/kallegrens/immich-migrator/commit/4acc186711355c46dab03203f7dd605804bc03f5))
* **ci:** remove online-audits from zizmor & pin version for caching ([686b323](https://github.com/kallegrens/immich-migrator/commit/686b3231e8da2f4085cc1e392aaa4b1147d3820d))
* **ci:** simplify release-please-config.json ([587a060](https://github.com/kallegrens/immich-migrator/commit/587a0605a26cf8a93aca730c6587dd9df565c9a2))
* **ci:** use official zizmor action ([596edef](https://github.com/kallegrens/immich-migrator/commit/596edef93c12a4a504e2814373583d0c4d3e9798))
* correct uv dependency installation in GitHub Actions workflows ([9937f6f](https://github.com/kallegrens/immich-migrator/commit/9937f6fda7b264720b94f0bf64b9b283e587a09e))


### Documentation

* update installation commands to use modern uv syntax ([e47daa1](https://github.com/kallegrens/immich-migrator/commit/e47daa1e3755506007bcb015b3b81cc0ef1bb233))

## [0.1.0] - 2025-12-10

### Added

- Initial release of immich-migrator
- Interactive TUI for album selection using Questionary
- Support for migrating photo albums between Immich servers
- Batch processing with configurable batch sizes
- Progress tracking with Rich-based progress bars
- State persistence for resumable migrations
- Checksum verification for data integrity
- EXIF metadata injection using pyexiftool
- Comprehensive test suite with unit, integration, and contract tests
- CLI interface with Typer framework
- Support for live photos and sidecar files

### Features

- Album-based migration workflow
- Configurable temporary directory for downloads
- Adjustable log levels (DEBUG, INFO, WARNING, ERROR)
- Retry logic with exponential backoff using tenacity
- Async HTTP operations with httpx
- Pydantic-based data validation

[0.1.0]: https://github.com/kallegrens/immich-migrator/releases/tag/v0.1.0
