"""Configuration models for Immich migration tool."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator


class Config(BaseModel):
    """Application configuration loaded from file or defaults."""

    batch_size: int = Field(default=20, ge=1, le=100)
    state_file: Path = Field(
        default_factory=lambda: Path.home() / ".immich-migrator" / "state.json"
    )
    temp_dir: Path = Field(default_factory=lambda: Path.home() / ".immich-migrator" / "temp")
    max_concurrent_downloads: int = Field(default=5, ge=1, le=20)
    max_concurrent_requests: int = Field(default=50, ge=1, le=200)
    download_timeout_seconds: int = Field(default=300, gt=0)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @field_validator("state_file", "temp_dir")
    @classmethod
    def ensure_parent_exists(cls, v: Path) -> Path:
        """Ensure parent directory exists for state file and temp dir."""
        v.parent.mkdir(parents=True, exist_ok=True)
        return v


class ImmichCredentials(BaseModel):
    """Authentication credentials for Immich server."""

    server_url: HttpUrl
    api_key: str = Field(min_length=1)

    model_config = {"frozen": True}

    @classmethod
    def from_env_file(cls, path: Path, prefix: str = "IMMICH") -> "ImmichCredentials":
        """Load credentials from .env file.

        Args:
            path: Path to .env file containing credentials
            prefix: Prefix for environment variable names (e.g., 'OLD_IMMICH', 'NEW_IMMICH')
                   Will look for {prefix}_SERVER_URL and {prefix}_API_KEY

        Returns:
            ImmichCredentials instance

        Raises:
            FileNotFoundError: If env file doesn't exist
            KeyError: If required env vars are missing
        """
        env_vars = {}
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "=" in line:
                        key, value = line.split("=", 1)
                        env_vars[key.strip()] = value.strip().strip('"').strip("'")

        server_url_key = f"{prefix}_SERVER_URL"
        api_key_key = f"{prefix}_API_KEY"

        if server_url_key not in env_vars:
            raise KeyError(f"Missing {server_url_key} in {path}")
        if api_key_key not in env_vars:
            raise KeyError(f"Missing {api_key_key} in {path}")

        return cls(
            server_url=HttpUrl(env_vars[server_url_key]),
            api_key=env_vars[api_key_key],
        )
