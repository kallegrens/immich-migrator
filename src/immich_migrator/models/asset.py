"""Asset model representing a photo or video from Immich."""

import base64
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class Asset(BaseModel):
    """Represents a single photo/video asset from Immich."""

    id: str = Field(pattern=r"^[0-9a-f-]{36}$")  # UUID format
    original_file_name: str = Field(min_length=1)
    original_mime_type: str = Field(pattern=r"^[\w\-]+/[\w\.\-\+]+$")
    checksum: str = Field(pattern=r"^[0-9a-f]{40}$")  # SHA1
    file_created_at: datetime | None = None
    file_size_bytes: int | None = Field(None, ge=0)
    download_url: str | None = None
    exif_date_time_original: datetime | None = None
    local_date_time: datetime | None = None
    # Live photo support (Apple Live Photos)
    asset_type: str = Field(default="IMAGE", pattern=r"^(IMAGE|VIDEO|AUDIO|OTHER)$")
    live_photo_video_id: str | None = Field(default=None, pattern=r"^[0-9a-f-]{36}$")

    model_config = {"frozen": True}

    @field_validator("checksum", mode="before")
    @classmethod
    def convert_checksum(cls, v: str | None) -> str | None:
        """Convert base64 checksum to hex format if needed."""
        if v is None:
            return v

        # If already in hex format, return as-is
        if len(v) == 40 and all(c in "0123456789abcdef" for c in v.lower()):
            return v.lower()

        # Try to decode from base64
        try:
            # Immich returns base64-encoded checksums
            decoded = base64.b64decode(v)
            # Convert to hex string
            return decoded.hex()
        except Exception:
            # If conversion fails, return as-is and let validation fail
            return v

    @field_validator("download_url", mode="before")
    @classmethod
    def compute_download_url(cls, v: str | None, info: Any) -> str | None:
        """Compute download URL from asset ID if not provided."""
        if v is None and "id" in info.data:
            # Will be completed by ImmichClient with server URL
            return f"/assets/{info.data['id']}/original"
        return v
