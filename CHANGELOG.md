# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.7](https://github.com/kallegrens/immich-migrator/compare/v0.4.6...v0.4.7) (2026-01-07)


### Bug Fixes

* reset only specific album state upon mismatch ([feda284](https://github.com/kallegrens/immich-migrator/commit/feda2846ff1f5d11970b9e80488ebd234fda126d))

## [0.4.6](https://github.com/kallegrens/immich-migrator/compare/v0.4.5...v0.4.6) (2026-01-04)


### Bug Fixes

* don't clear state.json for all albums if inconsistent ([94831e5](https://github.com/kallegrens/immich-migrator/commit/94831e5e1f21dd52aedd0dac779d46e9ba829cdd))

## [0.4.5](https://github.com/kallegrens/immich-migrator/compare/v0.4.4...v0.4.5) (2025-12-29)


### Bug Fixes

* allow mime types with special symbols like + and - ([b26aabd](https://github.com/kallegrens/immich-migrator/commit/b26aabdc15578cc915700ef7b839e2ca308a395f))

## [0.4.4](https://github.com/kallegrens/immich-migrator/compare/v0.4.3...v0.4.4) (2025-12-17)


### Bug Fixes

* improve logging and progress bars ([7ab0073](https://github.com/kallegrens/immich-migrator/commit/7ab007382dfd227018d23894e01c944ab1bbd38d))

## [0.4.3](https://github.com/kallegrens/immich-migrator/compare/v0.4.2...v0.4.3) (2025-12-16)


### Documentation

* update CONTRIBUTING, README and SECURITY (migrate command + wording) ✨📝 ([64c77e5](https://github.com/kallegrens/immich-migrator/commit/64c77e567e7fb595efc149755b3be7782c52f79b))

## [0.4.2](https://github.com/kallegrens/immich-migrator/compare/v0.4.1...v0.4.2) (2025-12-15)


### Bug Fixes

* **ci:** fix md rendering in releases ([6f1e339](https://github.com/kallegrens/immich-migrator/commit/6f1e339563bb509a28c171656a9b23dbc7fa4943))

## [0.4.1](https://github.com/kallegrens/immich-migrator/compare/v0.4.0...v0.4.1) (2025-12-15)


### Bug Fixes

* **ci:** remove immutability and adapt ci ([acd1137](https://github.com/kallegrens/immich-migrator/commit/acd1137dfdcf434355adfc4c17de3b7de3b7be6d))

## [0.4.0](https://github.com/kallegrens/immich-migrator/compare/v0.3.7...v0.4.0) (2025-12-15)


### ⚠ BREAKING CHANGES

* Initial release v0.1.0

### Features

* implement immich-migrator CLI tool for server-to-server migration ([4129f65](https://github.com/kallegrens/immich-migrator/commit/4129f656695f8692a5d42028f5eac53195678535))


### Bug Fixes

* **ci:** add broader perms for workflows ([d8424c1](https://github.com/kallegrens/immich-migrator/commit/d8424c1bd79a5103c289ba2979acfe1df1dc4050))
* **ci:** add token to release-please ([d0668d1](https://github.com/kallegrens/immich-migrator/commit/d0668d1471113011c7402cca519c0a58b67de67b))
* **ci:** branch rules requires exact job name with pull_request suffix ([7a329d3](https://github.com/kallegrens/immich-migrator/commit/7a329d3da9e3ac2a413fd34060fecae177e6ace5))
* **ci:** fix command for cyclonedx-py sbom generation ([11fa306](https://github.com/kallegrens/immich-migrator/commit/11fa306a033beb4434e10366461946dc2239f2b7))
* **ci:** fix metadata appending, switched to anchore sbom ([efc3ff7](https://github.com/kallegrens/immich-migrator/commit/efc3ff74ce2bb94fde74f9094bc8d55b6eaef8ff))
* **ci:** fix publish trigger ([ef27931](https://github.com/kallegrens/immich-migrator/commit/ef27931d58970eb6566a5452920351f5b142e332))
* **ci:** fix shell linting ([3b38902](https://github.com/kallegrens/immich-migrator/commit/3b38902f2e0e6e0f8da455f2cedf7f0e5241b9a6))
* **ci:** fix two commit sha's ([5715402](https://github.com/kallegrens/immich-migrator/commit/5715402696b39a9bf3e5fe3eb6a01705c17b81d1))
* **ci:** make pre-commit match the github actions linting workflow ([1188b9a](https://github.com/kallegrens/immich-migrator/commit/1188b9a14c8307b7fb145128aa967695e5e203fc))
* **ci:** pass secrets.GITHUB_TOKEN to setup-uv steps ([4acc186](https://github.com/kallegrens/immich-migrator/commit/4acc186711355c46dab03203f7dd605804bc03f5))
* **ci:** refactor asset generation ([fe7a3df](https://github.com/kallegrens/immich-migrator/commit/fe7a3dfaffb43e2db1d42a7a7bf8ed371199ee0e))
* **ci:** remove online-audits from zizmor & pin version for caching ([686b323](https://github.com/kallegrens/immich-migrator/commit/686b3231e8da2f4085cc1e392aaa4b1147d3820d))
* **ci:** remove sigstore, it's overkill ([5e9f489](https://github.com/kallegrens/immich-migrator/commit/5e9f48967a6a2cb817df13a6f6e4a80aa35208e5))
* **ci:** simplify release-please-config.json ([587a060](https://github.com/kallegrens/immich-migrator/commit/587a0605a26cf8a93aca730c6587dd9df565c9a2))
* **ci:** stop ci from running redundantly & add branch rulesets ([a9c1d22](https://github.com/kallegrens/immich-migrator/commit/a9c1d22a9d78f8cc1c2bf82f95cc77e4eb19427a))
* **ci:** switch to actionlint-docker to include shellcheck automatically ([5010fd5](https://github.com/kallegrens/immich-migrator/commit/5010fd5a6e4468e8a49defd4682cff362a8cd13d))
* **ci:** use official zizmor action ([596edef](https://github.com/kallegrens/immich-migrator/commit/596edef93c12a4a504e2814373583d0c4d3e9798))
* correct uv dependency installation in GitHub Actions workflows ([9937f6f](https://github.com/kallegrens/immich-migrator/commit/9937f6fda7b264720b94f0bf64b9b283e587a09e))
* **docs:** add release-please marker in README.md ([7d6197f](https://github.com/kallegrens/immich-migrator/commit/7d6197f0672f74226661a31e3f430750eedbf653))


### Documentation

* fix command to prefix uv and call main too ([d272ffa](https://github.com/kallegrens/immich-migrator/commit/d272ffac5ab0455b680f0c25d18627a8a8b2659b))
* fix README to let release-please pick up version changes ([fe82010](https://github.com/kallegrens/immich-migrator/commit/fe820108e03387af06cc02339f203e52a08fe8bb))
* overhaul the readme and add AGENT.md ([7f6d997](https://github.com/kallegrens/immich-migrator/commit/7f6d9975aa3750ba17b410531bb56b1f9cc33ecc))
* update installation commands to use modern uv syntax ([e47daa1](https://github.com/kallegrens/immich-migrator/commit/e47daa1e3755506007bcb015b3b81cc0ef1bb233))
* update README title with emoji ([d296363](https://github.com/kallegrens/immich-migrator/commit/d29636317b8d22c901d5e64947b9a78a7ef37e0a))

## [0.3.7](https://github.com/kallegrens/immich-migrator/compare/v0.3.6...v0.3.7) (2025-12-15)


### Bug Fixes

* **ci:** branch rules requires exact job name with pull_request suffix ([7a329d3](https://github.com/kallegrens/immich-migrator/commit/7a329d3da9e3ac2a413fd34060fecae177e6ace5))
* **ci:** stop ci from running redundantly & add branch rulesets ([a9c1d22](https://github.com/kallegrens/immich-migrator/commit/a9c1d22a9d78f8cc1c2bf82f95cc77e4eb19427a))


### Documentation

* fix command to prefix uv and call main too ([d272ffa](https://github.com/kallegrens/immich-migrator/commit/d272ffac5ab0455b680f0c25d18627a8a8b2659b))

## [0.3.6](https://github.com/kallegrens/immich-migrator/compare/v0.3.5...v0.3.6) (2025-12-15)


### Bug Fixes

* **ci:** remove sigstore, it's overkill ([5e9f489](https://github.com/kallegrens/immich-migrator/commit/5e9f48967a6a2cb817df13a6f6e4a80aa35208e5))

## [0.3.5](https://github.com/kallegrens/immich-migrator/compare/v0.3.4...v0.3.5) (2025-12-14)


### Bug Fixes

* **ci:** fix metadata appending, switched to anchore sbom ([efc3ff7](https://github.com/kallegrens/immich-migrator/commit/efc3ff74ce2bb94fde74f9094bc8d55b6eaef8ff))

## [0.3.4](https://github.com/kallegrens/immich-migrator/compare/v0.3.3...v0.3.4) (2025-12-14)


### Bug Fixes

* **ci:** fix command for cyclonedx-py sbom generation ([11fa306](https://github.com/kallegrens/immich-migrator/commit/11fa306a033beb4434e10366461946dc2239f2b7))

## [0.3.3](https://github.com/kallegrens/immich-migrator/compare/v0.3.2...v0.3.3) (2025-12-14)


### Bug Fixes

* **ci:** switch to actionlint-docker to include shellcheck automatically ([5010fd5](https://github.com/kallegrens/immich-migrator/commit/5010fd5a6e4468e8a49defd4682cff362a8cd13d))
* **docs:** add release-please marker in README.md ([7d6197f](https://github.com/kallegrens/immich-migrator/commit/7d6197f0672f74226661a31e3f430750eedbf653))


### Documentation

* fix README to let release-please pick up version changes ([fe82010](https://github.com/kallegrens/immich-migrator/commit/fe820108e03387af06cc02339f203e52a08fe8bb))
* overhaul the readme and add AGENT.md ([7f6d997](https://github.com/kallegrens/immich-migrator/commit/7f6d9975aa3750ba17b410531bb56b1f9cc33ecc))

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
