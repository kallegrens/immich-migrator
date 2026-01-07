# 📸 Immich Migration Tool

[![uv][uv-badge]][uv]
[![PyPI][pypi-badge]][pypi]
[![Python Version][python-badge]][pypi]
[![Tests][tests-badge]][tests]
[![Coverage][coverage-badge]][coverage]
[![License][license-badge]][license]
[![Conventional Commits][cc-badge]][cc]

[uv]: https://github.com/astral-sh/uv
[uv-badge]: https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json
[pypi-badge]: https://img.shields.io/pypi/v/immich-migrator
[pypi]: https://pypi.org/project/immich-migrator/
[python-badge]: https://img.shields.io/pypi/pyversions/immich-migrator
[tests-badge]: https://github.com/kallegrens/immich-migrator/actions/workflows/test.yaml/badge.svg
[tests]: https://github.com/kallegrens/immich-migrator/actions/workflows/test.yaml
[coverage-badge]: https://codecov.io/gh/kallegrens/immich-migrator/branch/main/graph/badge.svg
[coverage]: https://codecov.io/gh/kallegrens/immich-migrator
[license-badge]: https://img.shields.io/github/license/kallegrens/immich-migrator
[license]: ./LICENSE
[cc-badge]: https://img.shields.io/badge/Conventional%20Commits-1.0.0-yellow.svg
[cc]: https://www.conventionalcommits.org/en/v1.0.0/
[release-page]: https://github.com/kallegrens/immich-migrator/releases

Migrate your photo library between **Immich** servers with confidence.

---

## ✨ Features

- 🎯 **Interactive Album Selection**: TUI for choosing albums to migrate
- 📦 **Batch Processing**: Downloads and uploads in configurable batches
- 📊 **Progress Tracking**: Real-time progress bars for downloads and uploads
- 💾 **State Persistence**: Resume interrupted migrations seamlessly (state saved to `~/.immich-migrator/state.json`)
- ✅ **Checksum Verification**: SHA1 verification for data integrity with configurable retry attempts
- 🔄 **Error Handling**: Graceful recovery from network failures with retry logic
- 📷 **Unalbummed Assets**: Migrate photos not organized in albums (presented as virtual album in selection)
- 📝 **EXIF Preservation**: Maintains all photo metadata; original capture dates are injected into downloaded files before upload
- 📸 **Live Photo Support**: Automatically detects and links iPhone Live Photos (image + video pairs)
- 🗂️ **Failed Assets Recovery**: Assets that fail verification are saved to `./immich_failed_assets` (configurable) for manual review

---

## 📦 Installation

> [!TIP]
> Use **uvx** to run the tool instantly without installation — perfect for one-time migrations:
>
> ```bash
> uvx immich-migrator migrate
> ```

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

---

## 🚀 Quick Start

### Prerequisites

Before you begin, ensure you have:

- **Python**: 3.11 or higher ✅
- **Disk Space**: At least 5GB free for temporary storage of downloaded batches 💾
- **ExifTool**: For EXIF metadata handling 📝

  ```bash
  # Ubuntu/Debian
  sudo apt-get install libimage-exiftool-perl

  # macOS
  brew install exiftool
  ```

### 1. Prepare a unified credentials file

The tool expects a single credentials file containing both old and new server details. By default, it looks for `~/.immich.env`.

Create `~/.immich.env` (or copy from `.immich.env.example`):

```bash
# ~/.immich.env
# OLD server
OLD_IMMICH_SERVER_URL=https://old.immich.example.com
OLD_IMMICH_API_KEY=your-old-server-api-key-here

# NEW server
NEW_IMMICH_SERVER_URL=https://new.immich.example.com
NEW_IMMICH_API_KEY=your-new-server-api-key-here
```

> [!NOTE]
> You can provide an explicit path with `--credentials` (or `-c`). When specified, the default `~/.immich.env` lookup is skipped.

### 2. Run migration

Run with the default credentials file (`~/.immich.env`):

```bash
uv run immich-migrator migrate
```

Or specify a custom credentials path:

```bash
uv run immich-migrator migrate -c /path/to/your/credentials.env
```

**What happens next?** 🎬

1. 🔍 Connects to your old Immich server
2. 📚 Discovers all albums (including unalbummed assets)
3. 🎯 Displays an interactive menu for album selection
4. ⬇️ Downloads selected albums with progress tracking
5. ⬆️ Uploads to the new server with album organization intact
6. 💾 Saves state for resume capability

---

## 🎯 Usage Examples

### View Available Commands

```bash
immich-migrator --help
immich-migrator migrate --help
```

### Basic Migration

```bash
immich-migrator migrate
```

### Custom Batch Size

```bash
immich-migrator migrate --batch-size 30
```

### Custom Configuration

```bash
immich-migrator migrate --config config.toml
```

### Debug Mode

```bash
immich-migrator migrate --log-level DEBUG
```

### Quiet Mode (Warnings/Errors Only)

```bash
immich-migrator migrate --quiet
```

### Custom Failed Assets Directory

```bash
immich-migrator migrate --failed-output-dir /path/to/failed/assets
```

### Adjust Verification Retries

```bash
immich-migrator migrate --verify-retries 5
```

---

## ⚙️ Configuration

Create a `config.toml` file for advanced configuration. All settings are optional and have sensible defaults.

### Available Configuration Options

```toml
# Batch processing
batch_size = 20                      # Assets per batch (1-100, default: 20)

# Performance tuning
max_concurrent_downloads = 5         # Parallel downloads (1-20, default: 5)
max_concurrent_requests = 50         # Parallel API requests (1-200, default: 50)
download_timeout_seconds = 300       # Download timeout in seconds (default: 300)

# Storage locations
state_file = "~/.immich-migrator/state.json"  # Migration state persistence
temp_dir = "~/.immich-migrator/temp"          # Temporary download directory

# Logging
log_level = "INFO"                   # DEBUG | INFO | WARNING | ERROR (default: INFO)
```

### Using Configuration File

```bash
immich-migrator migrate --config /path/to/config.toml
```

> [!NOTE]
> CLI flags take precedence over config file settings. For example, `--batch-size 30` overrides the config file value.

---

## ✅ Compatibility

- **Python**: 3.11, 3.12, 3.13
- **Operating Systems**: Linux, macOS, Windows (WSL recommended)
- **Immich**: Tested with Immich v1.119 – v2.x.x servers

---

## 🔧 Troubleshooting

### 🔐 Authentication Errors

> [!WARNING]
> If you encounter authentication errors:
>
> - ✅ Verify your API key is correct and has not expired
> - ✅ Check that the server URL is accessible (include https://)
> - ✅ Ensure you have the necessary permissions on both servers

### 💾 Storage Errors

> [!NOTE]
> If you see insufficient storage errors:
>
> - Reduce batch size: `--batch-size 10`
> - Specify a different temp directory: `--temp-dir /path/to/large/disk`
> - Free up disk space before retrying

### 🌐 Network Errors

The tool automatically retries failed downloads with exponential backoff.

> [!TIP]
> If errors persist:
>
> - Check your network connection stability
> - Verify both servers are accessible from your location
> - Try reducing `max_concurrent_downloads` in `config.toml`
> - Use `--log-level DEBUG` to see detailed error messages

---

## 🛠️ Development

### Setup

```bash
uv sync
```

> [!CAUTION]
> Never commit your `.immich.env` file to version control! Add it to `.gitignore` to protect your API keys.
>

### Run Tests

```bash
uv run pytest
```

### Linting

```bash
uv run ruff check .
uv run ruff format .
```

---

## 📖 Changelog

See [CHANGELOG.md](./CHANGELOG.md) for release history and breaking changes.

### Latest Release

> [!NOTE]
> [Version 0.4.7][release-page] is the current stable release. <!-- {x-release-please-version} -->

---

## 🙌 Contributing

Contributions welcome! Please read [CONTRIBUTING.md](./CONTRIBUTING.md) for:

- 📋 Development workflow
- ✅ Testing requirements
- 🎨 Code style guidelines
- 🔒 Security practices

---

## 📄 License

[GNU Affero General Public License v3.0](./LICENSE) — see LICENSE file for details.

This ensures that any modifications to this tool, especially if hosted as a service, remain open source.
