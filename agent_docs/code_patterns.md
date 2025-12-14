# Code Patterns

Architecture patterns and conventions used in immich-migrator.

## Service Layer Architecture

All business logic lives in `src/immich_migrator/services/`:

```text
services/
├── immich_client.py    # Async HTTP client for Immich API
├── downloader.py       # Batch asset downloads with checksums
├── uploader.py         # Subprocess wrapper for immich CLI
├── exif_injector.py    # ExifTool wrapper for metadata
└── state_manager.py    # JSON state persistence
```

Services are **injected** into CLI commands, not instantiated globally.

## Async Patterns

### ImmichClient: Async Context Manager

**Location**: `src/immich_migrator/services/immich_client.py:45`

```python
class ImmichClient:
    async def __aenter__(self) -> "ImmichClient":
        self.client = httpx.AsyncClient(...)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.client:
            await self.client.aclose()
```

**Usage**:

```python
async with ImmichClient(credentials=creds) as client:
    albums = await client.list_albums()
```

### Concurrent Operations with Semaphore

**Location**: `src/immich_migrator/services/immich_client.py:260`

Rate limiting with `asyncio.Semaphore`:

```python
self._semaphore = asyncio.Semaphore(max_concurrent)

async def download_asset(self, asset: Asset, dest_path: Path) -> Path:
    async with self._semaphore:
        # Only N concurrent downloads
        url = f"{self.server_url}/api/assets/{asset.id}/original"
        ...
```

### Retry Logic with Tenacity

**Location**: `src/immich_migrator/services/immich_client.py:256`

Exponential backoff for transient failures:

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
async def download_asset(self, asset: Asset, dest_path: Path) -> Path:
    ...
```

## Subprocess Patterns

### Uploader: Immich CLI Wrapper

**Location**: `src/immich_migrator/services/uploader.py:60`

Always set environment variables for subprocess:

```python
env = os.environ.copy()
env["IMMICH_INSTANCE_URL"] = self.server_url
env["IMMICH_API_KEY"] = self.api_key

result = subprocess.run(
    ["immich", "upload", str(batch_dir), "--recursive"],
    env=env,
    capture_output=True,
    text=True,
    timeout=600,
)
```

**Key points**:

- Always use `capture_output=True` for logging
- Set timeouts to prevent hangs
- Check `returncode` for success/failure
- Log `stdout` and `stderr` for debugging

## Pydantic Model Patterns

### Config Validation

**Location**: `src/immich_migrator/models/config.py:1`

Use Pydantic for validation and type safety:

```python
class ImmichCredentials(BaseModel):
    server_url: HttpUrl
    api_key: str

    @field_validator("server_url")
    @classmethod
    def validate_url(cls, v: HttpUrl) -> HttpUrl:
        # Custom validation
        return v
```

### Asset/Album Models

**Location**: `src/immich_migrator/models/asset.py`, `models/album.py`

Map API responses directly to Pydantic models:

```python
class Asset(BaseModel):
    id: str
    original_file_name: str
    checksum: str
    type: Literal["IMAGE", "VIDEO"]
    # ... other fields
```

## CLI Structure

### Typer Application

**Location**: `src/immich_migrator/cli/app.py:1`

Single command CLI with options:

```python
app = typer.Typer(
    name="immich-migrator",
    help="CLI tool for migrating photo albums between Immich servers",
)

@app.command()
def main(
    credentials: Path | None = typer.Option(...),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    # Main logic
```

Entry point in `__main__.py`:

```python
def main() -> None:
    app()
```

### Interactive Selection

Use `questionary` for user prompts:

```python
from questionary import checkbox

selected = checkbox(
    "Select albums to migrate:",
    choices=[Choice(title=album.name, value=album) for album in albums],
).ask()
```

## Error Handling

### Custom Exceptions

**Location**: `src/immich_migrator/services/exif_injector.py`

Create domain-specific exceptions:

```python
class ExifInjectionError(Exception):
    """Raised when EXIF injection fails."""
```

### Logging Patterns

**Location**: `src/immich_migrator/lib/logging.py`

Use loguru for structured logging:

```python
from immich_migrator.lib.logging import get_logger

logger = get_logger()  # type: ignore[no-untyped-call]

logger.info(f"Processing {len(assets)} assets")
logger.error(f"Failed to download asset {asset.id}: {e}")
logger.debug(f"API response: {response.json()}")
```

Log levels:

- `DEBUG`: API responses, file operations
- `INFO`: Progress updates, success messages
- `ERROR`: Failures, exceptions

## Progress Tracking

**Location**: `src/immich_migrator/lib/progress.py`

Use Rich for progress bars:

```python
from immich_migrator.lib.progress import ProgressContext

with ProgressContext() as progress:
    task_id = progress.add_task("Downloading...", total=len(assets))
    for asset in assets:
        # ... do work ...
        progress.update(task_id, advance=1)
```

## File Organization

Follow existing structure when adding features:

1. **Models** (`models/`) — Data structures, validation
2. **Services** (`services/`) — Business logic, API calls
3. **CLI** (`cli/`) — User interface, command handlers
4. **Lib** (`lib/`) — Shared utilities (logging, progress)

Don't mix concerns across layers.
