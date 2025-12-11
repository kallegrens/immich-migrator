# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
