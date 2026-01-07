"""State models for tracking migration progress."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class MigrationStatus(str, Enum):
    """Status of album migration."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class FailedAsset(BaseModel):
    """Tracks a permanently failed asset with details for manual recovery."""

    asset_id: str = Field(pattern=r"^[0-9a-f-]{36}$")
    original_file_name: str
    checksum: str = Field(pattern=r"^[0-9a-f]{40}$")
    failure_reason: str
    local_path: str | None = None  # Path where asset was saved for recovery


class LivePhotoPair(BaseModel):
    """Tracks a live photo pair (image + video) for linking after upload."""

    image_asset_id: str = Field(pattern=r"^[0-9a-f-]{36}$")
    video_asset_id: str = Field(pattern=r"^[0-9a-f-]{36}$")
    image_checksum: str = Field(pattern=r"^[0-9a-f]{40}$")
    video_checksum: str = Field(pattern=r"^[0-9a-f]{40}$")
    linked: bool = False


class AlbumState(BaseModel):
    """Tracks migration state for a single album."""

    album_id: str = Field(pattern=r"^[0-9a-f-]{36}$|^UNALBUMMED_ASSETS$")
    album_name: str = Field(min_length=1)
    status: MigrationStatus = MigrationStatus.PENDING
    asset_count: int = Field(ge=0)
    migrated_count: int = Field(default=0, ge=0)
    failed_asset_ids: list[str] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.now)
    error_message: str | None = None
    # Live photo tracking
    live_photo_pairs: list[LivePhotoPair] = Field(default_factory=list)
    live_photos_linked: int = Field(default=0, ge=0)
    # Verification tracking
    verified_asset_ids: list[str] = Field(default_factory=list)
    missing_asset_ids: list[str] = Field(default_factory=list)
    permanently_failed_assets: list[FailedAsset] = Field(default_factory=list)
    # Checksum overrides for EXIF-injected assets (asset_id -> new_checksum)
    # These are used during verification to check for the modified checksum on destination
    checksum_overrides: dict[str, str] = Field(default_factory=dict)

    @field_validator("migrated_count")
    @classmethod
    def validate_migrated_count(cls, v: int, info: Any) -> int:
        """Ensure migrated_count doesn't exceed asset_count."""
        if "asset_count" in info.data and v > info.data["asset_count"]:
            raise ValueError("migrated_count cannot exceed asset_count")
        return v

    @model_validator(mode="after")
    def validate_completion_state(self) -> "AlbumState":
        """Validate state consistency for COMPLETED and FAILED statuses."""
        if self.status == MigrationStatus.COMPLETED:
            # Album is valid if either:
            # 1. migrated_count == asset_count (traditional completion)
            # 2. len(verified_asset_ids) >= asset_count (pre-verification completion)
            verified_count = len(self.verified_asset_ids)
            if self.migrated_count != self.asset_count and verified_count < self.asset_count:
                raise ValueError(
                    "COMPLETED albums must have migrated_count == asset_count "
                    "or verified_asset_ids >= asset_count"
                )
        if self.status == MigrationStatus.FAILED:
            if not self.error_message:
                raise ValueError("FAILED albums must have error_message set")
        return self

    def mark_in_progress(self) -> None:
        """Transition to IN_PROGRESS status."""
        self.status = MigrationStatus.IN_PROGRESS
        self.last_updated = datetime.now()

    def increment_migrated(self, count: int = 1) -> None:
        """Increment migrated count after successful batch upload.

        Args:
            count: Number of assets successfully migrated
        """
        self.migrated_count += count
        self.last_updated = datetime.now()

    def mark_completed(self) -> None:
        """Transition to COMPLETED status."""
        self.status = MigrationStatus.COMPLETED
        self.last_updated = datetime.now()

    def mark_failed(self, error: str) -> None:
        """Transition to FAILED status with error message.

        Args:
            error: Error message describing the failure
        """
        self.status = MigrationStatus.FAILED
        self.error_message = error
        self.last_updated = datetime.now()

    def add_failed_asset(self, asset_id: str) -> None:
        """Track a failed asset ID.

        Args:
            asset_id: ID of asset that failed to migrate
        """
        if asset_id not in self.failed_asset_ids:
            self.failed_asset_ids.append(asset_id)
        self.last_updated = datetime.now()

    def reset_to_pending(self) -> None:
        """Reset album state to pending for re-migration.

        Clears migrated count and failed assets, useful for re-migrating
        completed albums to a different server.
        """
        self.status = MigrationStatus.PENDING
        self.migrated_count = 0
        self.failed_asset_ids = []
        self.error_message = None
        self.live_photo_pairs = []
        self.live_photos_linked = 0
        self.verified_asset_ids = []
        self.missing_asset_ids = []
        self.permanently_failed_assets = []
        self.checksum_overrides = {}
        self.last_updated = datetime.now()

    def add_live_photo_pair(
        self,
        image_asset_id: str,
        video_asset_id: str,
        image_checksum: str,
        video_checksum: str,
    ) -> None:
        """Track a live photo pair for linking after upload.

        Args:
            image_asset_id: Source image asset ID
            video_asset_id: Source video asset ID
            image_checksum: SHA1 checksum of image
            video_checksum: SHA1 checksum of video
        """
        # Check if pair already exists
        for pair in self.live_photo_pairs:
            if pair.image_asset_id == image_asset_id:
                return

        self.live_photo_pairs.append(
            LivePhotoPair(
                image_asset_id=image_asset_id,
                video_asset_id=video_asset_id,
                image_checksum=image_checksum,
                video_checksum=video_checksum,
            )
        )
        self.last_updated = datetime.now()

    def mark_live_photo_linked(self, image_asset_id: str) -> None:
        """Mark a live photo pair as successfully linked.

        Args:
            image_asset_id: Source image asset ID
        """
        for pair in self.live_photo_pairs:
            if pair.image_asset_id == image_asset_id and not pair.linked:
                pair.linked = True
                self.live_photos_linked += 1
                self.last_updated = datetime.now()
                return

    def get_unlinked_live_photos(self) -> list[LivePhotoPair]:
        """Get live photo pairs that haven't been linked yet.

        Returns:
            List of unlinked LivePhotoPair instances
        """
        return [pair for pair in self.live_photo_pairs if not pair.linked]

    def add_verified_asset(self, asset_id: str) -> None:
        """Track a verified asset ID.

        Args:
            asset_id: ID of asset verified on target server
        """
        if asset_id not in self.verified_asset_ids:
            self.verified_asset_ids.append(asset_id)
        # Remove from missing if it was there
        if asset_id in self.missing_asset_ids:
            self.missing_asset_ids.remove(asset_id)
        self.last_updated = datetime.now()

    def add_missing_asset(self, asset_id: str) -> None:
        """Track a missing asset ID.

        Args:
            asset_id: ID of asset not found on target server
        """
        if asset_id not in self.missing_asset_ids:
            self.missing_asset_ids.append(asset_id)
        self.last_updated = datetime.now()

    def add_permanently_failed_asset(
        self,
        asset_id: str,
        original_file_name: str,
        checksum: str,
        failure_reason: str,
        local_path: str | None = None,
    ) -> None:
        """Track a permanently failed asset.

        Args:
            asset_id: ID of the failed asset
            original_file_name: Original filename
            checksum: Asset checksum
            failure_reason: Reason for failure
            local_path: Path where asset was saved for recovery
        """
        # Remove from missing list
        if asset_id in self.missing_asset_ids:
            self.missing_asset_ids.remove(asset_id)

        # Check if already tracked
        for failed in self.permanently_failed_assets:
            if failed.asset_id == asset_id:
                failed.failure_reason = failure_reason
                failed.local_path = local_path
                self.last_updated = datetime.now()
                return

        self.permanently_failed_assets.append(
            FailedAsset(
                asset_id=asset_id,
                original_file_name=original_file_name,
                checksum=checksum,
                failure_reason=failure_reason,
                local_path=local_path,
            )
        )
        self.last_updated = datetime.now()

    def clear_verification_state(self) -> None:
        """Clear verification tracking for re-verification.

        Note: Preserves checksum_overrides since those reflect actual file changes.
        """
        self.verified_asset_ids = []
        self.missing_asset_ids = []
        self.permanently_failed_assets = []
        self.last_updated = datetime.now()

    def set_checksum_override(self, asset_id: str, new_checksum: str) -> None:
        """Record an overridden checksum for an EXIF-modified asset.

        Args:
            asset_id: ID of the asset that was modified
            new_checksum: The new SHA1 checksum after EXIF injection
        """
        self.checksum_overrides[asset_id] = new_checksum
        self.last_updated = datetime.now()

    def get_checksum_for_asset(self, asset_id: str, original_checksum: str) -> str:
        """Get the checksum to use for verification.

        Returns the overridden checksum if the asset was EXIF-injected,
        otherwise returns the original checksum.

        Args:
            asset_id: ID of the asset
            original_checksum: The original checksum from source server

        Returns:
            The checksum to look for on the destination server
        """
        return self.checksum_overrides.get(asset_id, original_checksum)


class MigrationState(BaseModel):
    """Root state tracking all album migrations."""

    albums: dict[str, AlbumState] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def get_or_create_album_state(
        self, album_id: str, album_name: str, asset_count: int
    ) -> AlbumState:
        """Get existing album state or create new one.

        Args:
            album_id: Unique album identifier
            album_name: Album display name
            asset_count: Total number of assets in album

        Returns:
            AlbumState for the album
        """
        if album_id not in self.albums:
            self.albums[album_id] = AlbumState(
                album_id=album_id,
                album_name=album_name,
                asset_count=asset_count,
            )
            self.updated_at = datetime.now()
        return self.albums[album_id]

    def update_album_state(self, album_state: AlbumState) -> None:
        """Update album state and refresh timestamp.

        Args:
            album_state: Updated album state
        """
        self.albums[album_state.album_id] = album_state
        self.updated_at = datetime.now()

    def get_pending_albums(self) -> list[AlbumState]:
        """Get all albums with PENDING status.

        Returns:
            List of pending album states
        """
        return [state for state in self.albums.values() if state.status == MigrationStatus.PENDING]

    def get_completed_count(self) -> int:
        """Get count of completed albums.

        Returns:
            Number of albums with COMPLETED status
        """
        return sum(1 for state in self.albums.values() if state.status == MigrationStatus.COMPLETED)
