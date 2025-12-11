"""Integration tests for migration workflow.

Tests the complete migration workflow with services working together:
- Download → EXIF injection → Upload pipeline
- State management and persistence
- Error handling and recovery
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from immich_migrator.models.album import Album
from immich_migrator.models.asset import Asset
from immich_migrator.models.config import Config
from immich_migrator.models.state import MigrationState, MigrationStatus
from immich_migrator.services.downloader import Downloader
from immich_migrator.services.exif_injector import ExifInjector
from immich_migrator.services.state_manager import StateManager
from immich_migrator.services.uploader import Uploader


@pytest.fixture
def sample_asset(uuid_factory):
    """Create a sample asset for testing."""
    return Asset(
        id=uuid_factory(),
        original_file_name="test.jpg",
        original_mime_type="image/jpeg",
        checksum="a" * 40,  # Valid SHA1 checksum format
        file_created_at=datetime(2024, 1, 1, tzinfo=UTC),
        file_size_bytes=1024,
        asset_type="IMAGE",
    )


@pytest.fixture
def sample_album(sample_asset, uuid_factory):
    """Create a sample album for testing."""
    return Album(
        id=uuid_factory(),
        album_name="Test Album",
        asset_count=1,
        assets=[sample_asset],
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
    )


@pytest.fixture
def config(tmp_path):
    """Create a test configuration."""
    return Config(
        batch_size=5,
        temp_dir=tmp_path / "temp",
        state_file=tmp_path / "state.json",
    )


class TestDownloadWorkflow:
    """Tests for download workflow."""

    @pytest.mark.integration
    def test_downloader_initialization(self, tmp_path):
        """Test downloader can be initialized."""
        # Create mock ImmichClient
        mock_client = AsyncMock()

        # Create downloader
        downloader = Downloader(client=mock_client, temp_dir=tmp_path)

        assert downloader.client == mock_client
        assert downloader.temp_dir == tmp_path
        assert tmp_path.exists()  # Temp dir should be created


class TestExifInjectionWorkflow:
    """Tests for EXIF injection workflow."""

    @pytest.mark.integration
    def test_exif_injector_initialization(self):
        """Test EXIF injector can be initialized."""
        injector = ExifInjector()
        assert injector is not None


class TestStateManagementWorkflow:
    """Tests for state management workflow."""

    @pytest.mark.integration
    def test_state_manager_creates_file(self, tmp_path):
        """Test state manager creates state file."""
        state_file = tmp_path / "state.json"
        manager = StateManager(state_file)

        state = MigrationState()
        manager.save(state)

        assert state_file.exists()
        assert state_file.read_text()  # Should contain JSON

    @pytest.mark.integration
    def test_state_manager_persists_album_progress(self, tmp_path, uuid_factory):
        """Test state manager persists album progress."""
        state_file = tmp_path / "state.json"
        manager = StateManager(state_file)

        # Create and save initial state
        state = MigrationState()
        album_id = uuid_factory()
        album_state = state.get_or_create_album_state(
            album_id=album_id,
            album_name="Test Album",
            asset_count=10,
        )
        album_state.status = MigrationStatus.IN_PROGRESS
        album_state.migrated_count = 5
        manager.save(state)

        # Load state and verify persistence
        loaded_state = manager.load()
        loaded_album = loaded_state.albums[album_id]

        assert loaded_album.status == MigrationStatus.IN_PROGRESS
        assert loaded_album.migrated_count == 5
        assert loaded_album.album_name == "Test Album"

    @pytest.mark.integration
    def test_state_manager_handles_corrupted_file(self, tmp_path):
        """Test state manager handles corrupted state file."""
        state_file = tmp_path / "state.json"
        state_file.write_text("invalid json {{{")

        manager = StateManager(state_file)
        state = manager.load()

        # Should return new empty state
        assert isinstance(state, MigrationState)
        assert len(state.albums) == 0

    @pytest.mark.integration
    def test_state_manager_atomic_save(self, tmp_path):
        """Test state manager uses atomic saves."""
        state_file = tmp_path / "state.json"
        manager = StateManager(state_file)

        state = MigrationState()
        manager.save(state)

        # Verify temp file was used (atomicity)
        assert state_file.exists()
        assert not (tmp_path / "state.json.tmp").exists()  # Temp file cleaned up


class TestUploadWorkflow:
    """Tests for upload workflow."""

    @pytest.mark.integration
    def test_uploader_checks_cli_availability(self, tmp_path):
        """Test uploader checks if Immich CLI is available."""
        # This will check for immich-cli
        with patch("immich_migrator.services.uploader.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1  # CLI not found
            with pytest.raises(RuntimeError, match="Immich CLI"):
                Uploader(
                    server_url="http://test.com",
                    api_key="test-key",
                )


class TestEndToEndWorkflow:
    """Tests for end-to-end workflow scenarios."""

    @pytest.mark.integration
    def test_failed_asset_tracking(self, tmp_path, uuid_factory):
        """Test failed assets are tracked in state."""
        state_file = tmp_path / "state.json"
        manager = StateManager(state_file)

        state = MigrationState()
        album_id = uuid_factory()
        album_state = state.get_or_create_album_state(album_id, "Test Album", 10)

        # Add failed asset to album state
        failed_asset_id = uuid_factory()
        album_state.add_permanently_failed_asset(
            asset_id=failed_asset_id,
            original_file_name="failed.jpg",
            checksum="a" * 40,
            failure_reason="Download failed",
            local_path=str(tmp_path / "failed.jpg"),
        )

        manager.save(state)

        # Verify failed asset recorded
        loaded_state = manager.load()
        loaded_album = loaded_state.albums[album_id]
        assert len(loaded_album.permanently_failed_assets) == 1
        failed = loaded_album.permanently_failed_assets[0]
        assert failed.asset_id == failed_asset_id
        assert "Download failed" in failed.failure_reason

    @pytest.mark.integration
    def test_resume_from_saved_state(self, tmp_path, sample_album):
        """Test migration can resume from saved state."""
        state_file = tmp_path / "state.json"
        manager = StateManager(state_file)

        # Simulate partial migration
        state = MigrationState()
        album_state = state.get_or_create_album_state(
            album_id=sample_album.id,
            album_name=sample_album.album_name,
            asset_count=100,
        )
        album_state.migrated_count = 50
        album_state.status = MigrationStatus.IN_PROGRESS
        manager.save(state)

        # Load and verify we can resume
        resumed_state = manager.load()
        resumed_album = resumed_state.albums[sample_album.id]

        assert resumed_album.migrated_count == 50
        assert resumed_album.status == MigrationStatus.IN_PROGRESS
        assert resumed_album.asset_count == 100

    @pytest.mark.integration
    def test_complete_album_workflow(self, tmp_path, uuid_factory):
        """Test complete album migration workflow."""
        state_file = tmp_path / "state.json"
        manager = StateManager(state_file)

        state = MigrationState()
        album_id = uuid_factory()

        # Start migration
        album_state = state.get_or_create_album_state(
            album_id=album_id,
            album_name="Test Album",
            asset_count=10,
        )
        assert album_state.status == MigrationStatus.PENDING

        # Mark in progress
        album_state.status = MigrationStatus.IN_PROGRESS
        album_state.migrated_count = 0
        manager.save(state)

        # Process assets
        album_state.migrated_count = 10
        manager.save(state)

        # Mark complete
        album_state.status = MigrationStatus.COMPLETED
        manager.save(state)

        # Verify final state
        final_state = manager.load()
        final_album = final_state.albums[album_id]
        assert final_album.status == MigrationStatus.COMPLETED
        assert final_album.migrated_count == 10
