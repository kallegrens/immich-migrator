# 📸 Immich Migration Tool

[![Tests](https://github.com/kallegrens/immich-migrator/actions/workflows/test.yaml/badge.svg)](https://github.com/kallegrens/immich-migrator/actions/workflows/test.yaml)
[![Build](https://github.com/kallegrens/immich-migrator/actions/workflows/build.yaml/badge.svg)](https://github.com/kallegrens/immich-migrator/actions/workflows/build.yaml)
[![Lint](https://github.com/kallegrens/immich-migrator/actions/workflows/lint.yaml/badge.svg)](https://github.com/kallegrens/immich-migrator/actions/workflows/lint.yaml)
[![Publish](https://github.com/kallegrens/immich-migrator/actions/workflows/publish.yaml/badge.svg)](https://github.com/kallegrens/immich-migrator/actions/workflows/publish.yaml)
[![codecov](https://codecov.io/gh/kallegrens/immich-migrator/branch/main/graph/badge.svg)](https://codecov.io/gh/kallegrens/immich-migrator)
[![PyPI version](https://badge.fury.io/py/immich-migrator.svg)](https://badge.fury.io/py/immich-migrator)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: AGPLv3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

CLI tool for migrating photo albums between Immich servers with interactive selection, progress tracking, and state persistence.

## Installation

### Recommended: Run directly with uvx (no installation needed)

```bash
uvx immich-migrator
```

This is the fastest way to try the tool without installing anything. Perfect for one-time migrations!

### Install with uv (persistent)

```bash
uv tool install immich-migrator
```

### Traditional pip install

```bash
pip install immich-migrator
```

### From Source

```bash
git clone https://github.com/kallegrens/immich-migrator.git
cd immich-migrator
uv sync
```

## Quick Start

### Prerequisites

- **Python**: 3.12 or higher (if not using uvx)
- **Disk Space**: At least 5GB free for temporary storage
- **ExifTool**: For EXIF metadata handling

  ```bash
  # Ubuntu/Debian
  sudo apt-get install libimage-exiftool-perl

  # macOS
  brew install exiftool
  ```

### 1. Prepare a unified credentials file

The tool now expects a single, unified credentials file that contains credentials for both the old and new Immich servers. By default the CLI will look for `~/.immich.env` if you don't pass a credentials path explicitly.

Create a file at `~/.immich.env` (or copy the example `.immich.env.example`):

```bash
# ~/.immich.env
# OLD server
OLD_IMMICH_SERVER_URL=https://old.immich.example.com
OLD_IMMICH_API_KEY=your-old-server-api-key-here

# NEW server
NEW_IMMICH_SERVER_URL=https://new.immich.example.com
NEW_IMMICH_API_KEY=your-new-server-api-key-here
```

You can also provide an explicit path with `--credentials` (or `-c`). If `--credentials` is supplied, the default lookup at `~/.immich.env` is skipped.

### 2. Run migration

Using the default credentials file (`~/.immich.env`):

```bash
immich-migrator
```

Or provide an explicit credentials file (skips default lookup):

```bash
immich-migrator -c /path/to/your/credentials.env
```

This will:

1. Connect to your old Immich server
2. Discover all albums (including unalbummed assets)
3. Display an interactive menu for album selection
4. Migrate selected albums to the new server with progress tracking
5. Save state for resume capability

## Usage

### Basic Migration

Using the default credentials file (`~/.immich.env`):

```bash
immich-migrator
```

Or explicitly specify credentials file:

```bash
immich-migrator -c /path/to/credentials.env
```

### Custom Batch Size

```bash
immich-migrator -c /path/to/credentials.env --batch-size 30
```

### Custom Configuration

```bash
immich-migrator -c /path/to/credentials.env --config config.toml
```

### Debug Mode

```bash
immich-migrator -c /path/to/credentials.env --log-level DEBUG
```

## Configuration

Create a `config.toml` file for advanced configuration:

```toml
[migration]
batch_size = 25
max_concurrent_downloads = 5
rate_limit_rps = 10.0
download_timeout_seconds = 300

[storage]
state_file = "~/.immich-migrator/state.json"
temp_dir = "~/.immich-migrator/temp"

[logging]
level = "INFO"
```

## Features

- **Interactive Album Selection**: TUI for choosing albums to migrate
- **Batch Processing**: Downloads and uploads in configurable batches
- **Progress Tracking**: Real-time progress bars for downloads and uploads
- **State Persistence**: Resume interrupted migrations
- **Checksum Verification**: SHA1 verification for data integrity
- **Error Handling**: Graceful recovery from network failures
- **Unalbummed Assets**: Migrate photos not in any album

## Troubleshooting

### Authentication Errors

If you see authentication errors:

- Verify your API key is correct
- Check that the server URL is accessible
- Ensure you have the necessary permissions

### Storage Errors

If you see insufficient storage errors:

- Reduce batch size with `--batch-size`
- Specify a different temp directory with `--temp-dir`
- Free up disk space

### Network Errors

The tool automatically retries failed downloads with exponential backoff. If errors persist:

- Check your network connection
- Verify both servers are accessible
- Try reducing concurrent downloads in config

## Development

### Setup

```bash
uv sync
```

### Run Tests

```bash
uv run pytest
```

### Linting

```bash
uv run ruff check .
uv run ruff format .
```

## License

MIT License - see LICENSE file for details

## Contributing

Contributions welcome! Please read CONTRIBUTING.md for details.
