# immich-migrator task runner
#
# This file delegates complex logic to shell scripts in ./scripts/
# to ensure consistency between local development and CI/CD workflows.

set shell := ["bash", "-c"]

# List available commands
default:
    @just --list

# List available commands
help:
    @just --list

# Clean all build artifacts and caches
clean:
    ./scripts/clean

# Run pre-commit hooks and tests
check:
    ./scripts/check

# Build the package (sdist and wheel)
build:
    ./scripts/build

# Verify the package contents
verify:
    ./scripts/verify-package

# Test installation in a fresh environment
test-install:
    ./scripts/test-install

# Install dependencies and set up the environment
install:
    uv sync --all-groups

# Run linters (pre-commit hooks)
lint:
    uv tool run pre-commit run --all-files --show-diff-on-failure

# Format code
fmt:
    uv run ruff format .
    uv run ruff check --fix .

# Run tests
test:
    uv run pytest

# Run tests with coverage
test-cov:
    uv run pytest --cov=src/immich_migrator --cov-report=html --cov-report=term

# Generate test assets from base files
generate-assets:
    uv run python scripts/generate_test_assets.py

# Verify test assets exist and have correct checksums
verify-assets:
    uv run python scripts/verify_test_assets.py

# Verify assets, generate if needed, then run tests
test-with-assets:
    @just verify-assets || just generate-assets
    uv run pytest

# Run the full release pipeline locally
all: clean check build verify test-install
    @echo "✅ All checks passed!"
