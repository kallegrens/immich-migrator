# Scripts

Build, test, and maintenance scripts for the project.

## Quick Start with `just`

This project uses `just` as a task runner. You can run tasks using `uv run just <task>`.

```bash
# List available tasks
uv run just

# Install dependencies (including dev and test groups)
uv run just install

# Run the full CI pipeline locally
uv run just all

# Build the package
uv run just build

# Run checks (lint + test)
uv run just check

# Run tests only
uv run just test

# Run tests with coverage
uv run just test-cov

# Format code
uv run just fmt

# Run linters only
uv run just lint
```

## Build & Package Scripts

### `./scripts/build` (or `just build`)

Builds the Python package using `uv build`.

**Usage:**

```bash
./scripts/build
```

**Output:** Creates distribution files in `dist/` directory:

- `immich_migrator-{version}-py3-none-any.whl` (wheel)
- `immich_migrator-{version}.tar.gz` (source distribution)

### `./scripts/verify-package` (or `just verify`)

Verifies that built packages contain all required files.

**Usage:**

```bash
./scripts/verify-package
```

**Checks:**

- ✅ Wheel contains: `py.typed`, `METADATA`, `LICENSE`
- ✅ Sdist contains: `py.typed`, `README.md`, `LICENSE`, `tests/`

**Note:** Run `./scripts/build` first.

### `./scripts/test-install` (or `just test-install`)

Tests installation of the built wheel in a clean virtual environment.

**Usage:**

```bash
./scripts/test-install
```

**What it does:**

1. Creates temporary virtual environment
2. Installs the wheel
3. Verifies CLI is accessible
4. Runs `immich-migrator --help` and `immich-migrator version`
5. Cleans up test environment

**Note:** Run `./scripts/build` first.

## Maintenance Scripts

### `./scripts/clean` (or `just clean`)

Removes all build artifacts and caches.

**Usage:**

```bash
./scripts/clean
```

**Removes:**

- `dist/`, `build/`, `*.egg-info/`
- `__pycache__/`, `*.pyc`, `*.pyo`
- `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`
- Test artifacts and coverage reports

### `./scripts/check` (or `just check`)

Runs all pre-flight checks (linting, type-checking, tests).

**Usage:**

```bash
./scripts/check
```

**What it does:**

1. Runs `pre-commit` hooks on all files
2. Runs `pytest` test suite

## Complete Workflow

**Development workflow:**

```bash
# Make changes to code...

# Run checks before committing
./scripts/check

# Build and verify
./scripts/build
./scripts/verify-package
./scripts/test-install
```

**Clean rebuild:**

```bash
./scripts/clean && ./scripts/build && ./scripts/verify-package
```

## CI/CD Usage

These scripts are used by GitHub Actions workflows:

- **`build.yaml`**: Calls `build`, `verify-package`, `test-install`
- **`publish.yaml`**: Calls `build`, `verify-package`

This ensures consistency between local development and CI builds.

## Best Practices

All scripts follow these conventions:

- ✅ Use `set -euo pipefail` for safety
- ✅ Calculate paths relative to project root
- ✅ Include emoji indicators for readability
- ✅ Provide clear error messages
- ✅ Exit with non-zero code on failure
- ✅ Can be run from any directory

## Other Scripts

### `check_immich_counts.py`

Python script to verify Immich asset counts.

### `regenerate_test_assets.sh`

Regenerates test assets for the test suite.
