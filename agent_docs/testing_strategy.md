# Testing Strategy

immich-migrator uses three test types: unit, integration, and contract tests.

## Test Categories

### Unit Tests (`tests/unit/`)

**Purpose**: Test individual functions/classes in isolation with mocks.

**Characteristics**:

- Fast (no I/O, no network)
- Use pytest fixtures and mocks (pytest-mock, respx)
- Mark with `@pytest.mark.unit`

**Run**:

```bash
just test
# or specifically:
uv run pytest tests/unit -v -m unit
```

**Examples**:

- `tests/unit/test_services.py:206` — Uploader service tests
- `tests/unit/test_immich_client.py:254` — ImmichClient async tests
- `tests/unit/test_models.py` — Pydantic model validation

### Integration Tests (`tests/integration/`)

**Purpose**: Test multiple components working together with real I/O.

**Characteristics**:

- May use real files (tmp_path fixture)
- May use actual subprocess calls
- Mark with `@pytest.mark.integration`

**Run**:

```bash
uv run pytest tests/integration -v -m integration
```

**Examples**:

- `tests/integration/test_migration_workflow.py:155` — Full workflow tests
- `tests/integration/test_exif_injection.py` — ExifTool integration
- `tests/integration/test_live_photos.py` — Live photo pairing

### Contract Tests (`tests/contract/`)

**Purpose**: Verify API/CLI behavior matches expected contracts.

**Characteristics**:

- Test external interfaces (Immich API, CLI)
- Ensure backward compatibility
- Mark with `@pytest.mark.contract`

**Run**:

```bash
uv run pytest tests/contract -v -m contract
```

**Examples**:

- `tests/contract/test_immich_api.py` — Immich API endpoint contracts

## Running Tests

### Quick Commands

```bash
# All tests
uv run just test

# With coverage report
uv run just test-cov

# Specific test file
uv run pytest tests/unit/test_services.py -v

# Specific test function
uv run pytest tests/unit/test_services.py::TestUploader::test_uploader_check_cli_installed -v

# Run only fast tests
uv run pytest -m "not slow"
```

### Test Selection

Use markers to filter:

```bash
uv run pytest -m unit              # Only unit tests
uv run pytest -m integration       # Only integration tests
uv run pytest -m "unit or integration"  # Both
```

## Writing Tests

### Use Fixtures

See `tests/conftest.py` for shared fixtures:

- `asset_factory` — Create test Asset objects
- `album_factory` — Create test Album objects
- `uuid_factory` — Generate UUIDs
- `subprocess_mocker` — Mock subprocess calls
- `immich_cli_factory` — Mock Immich CLI

**Example** (from `tests/unit/test_services.py:206`):

```python
@pytest.mark.unit
def test_uploader_check_cli_installed(self, subprocess_mocker, immich_cli_factory):
    """Uploader can verify Immich CLI is installed."""
    subprocess_mocker.setup_immich_cli(version_response="2.2.0")
    uploader = Uploader(server_url="https://immich.example.com", api_key="test-key")
    assert uploader is not None
```

### Mocking Patterns

- **HTTP requests**: Use `respx` for httpx mocking
- **Subprocess**: Use `pytest-mock` and `subprocess_mocker` fixture
- **Files**: Use `tmp_path` fixture for temporary directories

**HTTP mock example** (`tests/unit/test_immich_client.py:254`):

```python
@pytest.mark.unit
@respx.mock
async def test_download_asset_success(self, credentials, uuid_factory, tmp_path):
    # respx automatically mocks httpx requests
```

## Coverage Requirements

Minimum coverage: **70%**

Check coverage:

```bash
just test-cov
# Opens htmlcov/index.html
```

Exclude from coverage:

- `if TYPE_CHECKING:` blocks
- `if __name__ == "__main__":` blocks
- Abstract methods

See `pyproject.toml` for coverage config.

## Test Assets

Some tests require generated assets:

```bash
# Verify test assets exist
uv run just verify-assets

# Generate missing assets
uv run just generate-assets

# Run tests with asset generation
uv run just test-with-assets
```

See `tests/ASSETS_COMPLETION_SUMMARY.md` for details.
