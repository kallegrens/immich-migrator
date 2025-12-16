"""Integration tests for critical download/upload/EXIF workflows.

These tests focus on realistic end-to-end scenarios that exercise
the core functionality users depend on for photo migration.
"""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from immich_migrator.models.asset import Asset
from immich_migrator.services.downloader import Downloader, compute_file_checksum
from immich_migrator.services.exif_injector import ExifInjector
from immich_migrator.services.uploader import Uploader


class TestDownloadWorkflows:
    """Integration tests for download workflows."""

    @pytest.mark.integration
    async def test_download_batch_successful_workflow(self, uuid_factory, tmp_path):
        """Test successful batch download with checksum verification."""
        # Setup
        mock_client = AsyncMock()
        downloader = Downloader(client=mock_client, temp_dir=tmp_path, max_concurrent=2)

        assets = [
            Asset(
                id=uuid_factory(),
                original_file_name="photo1.jpg",
                original_mime_type="image/jpeg",
                checksum="da39a3ee5e6b4b0d3255bfef95601890afd80709",  # SHA1 of empty content
                file_size_bytes=0,
                asset_type="IMAGE",
            ),
            Asset(
                id=uuid_factory(),
                original_file_name="photo2.jpg",
                original_mime_type="image/jpeg",
                checksum="da39a3ee5e6b4b0d3255bfef95601890afd80709",
                file_size_bytes=0,
                asset_type="IMAGE",
            ),
        ]

        # Mock download to write empty file (matches checksum above)
        async def mock_download(asset, dest_path, progress_callback=None):
            dest_path.write_bytes(b"")

        mock_client.download_asset = mock_download

        batch_dir = tmp_path / "batch_001"

        # Execute
        successful, failed = await downloader.download_batch(assets, batch_dir)

        # Verify
        assert len(successful) == 2
        assert len(failed) == 0
        assert all(path.exists() for path in successful)

    @pytest.mark.integration
    async def test_download_batch_with_failures(self, uuid_factory, tmp_path):
        """Test batch download handles individual asset failures."""
        mock_client = AsyncMock()
        downloader = Downloader(client=mock_client, temp_dir=tmp_path)

        assets = [
            Asset(
                id=uuid_factory(),
                original_file_name="success.jpg",
                original_mime_type="image/jpeg",
                checksum="da39a3ee5e6b4b0d3255bfef95601890afd80709",
                file_size_bytes=0,
                asset_type="IMAGE",
            ),
            Asset(
                id=uuid_factory(),
                original_file_name="failure.jpg",
                original_mime_type="image/jpeg",
                checksum="b" * 40,  # Valid checksum format
                file_size_bytes=100,
                asset_type="IMAGE",
            ),
        ]

        call_count = 0

        async def mock_download(asset, dest_path, progress_callback=None):
            nonlocal call_count
            call_count += 1
            if "failure" in asset.original_file_name:
                raise httpx.HTTPError("Network error")
            dest_path.write_bytes(b"")

        mock_client.download_asset = mock_download

        batch_dir = tmp_path / "batch_mixed"

        # Execute
        successful, failed = await downloader.download_batch(assets, batch_dir)

        # Verify
        assert len(successful) == 1
        assert len(failed) == 1
        assert failed[0] == assets[1].id

    @pytest.mark.integration
    async def test_download_checksum_verification(self, uuid_factory, tmp_path):
        """Test checksum verification rejects corrupted downloads."""
        mock_client = AsyncMock()
        downloader = Downloader(client=mock_client, temp_dir=tmp_path)

        asset = Asset(
            id=uuid_factory(),
            original_file_name="test.jpg",
            original_mime_type="image/jpeg",
            checksum="a" * 40,  # Wrong checksum
            file_size_bytes=100,
            asset_type="IMAGE",
        )

        # Mock download writes wrong content
        async def mock_download(a, dest_path, progress_callback=None):
            dest_path.write_bytes(b"wrong content")

        mock_client.download_asset = mock_download

        batch_dir = tmp_path / "batch_checksum"

        # Execute
        successful, failed = await downloader.download_batch([asset], batch_dir)

        # Verify - should fail due to checksum mismatch
        assert len(successful) == 0
        assert len(failed) == 1

    @pytest.mark.integration
    def test_cleanup_batch_removes_files(self, tmp_path):
        """Test cleanup removes batch directory and files."""
        mock_client = AsyncMock()
        downloader = Downloader(client=mock_client, temp_dir=tmp_path)

        batch_dir = tmp_path / "batch_cleanup"
        batch_dir.mkdir()
        (batch_dir / "file1.jpg").write_text("test")
        (batch_dir / "file2.jpg").write_text("test")

        downloader.cleanup_batch(batch_dir)

        assert not batch_dir.exists()

    @pytest.mark.integration
    def test_cleanup_all_removes_all_batches(self, tmp_path):
        """Test cleanup_all removes all batch directories."""
        mock_client = AsyncMock()
        temp_dir = tmp_path / "downloads"
        downloader = Downloader(client=mock_client, temp_dir=temp_dir)

        # Create multiple batch dirs
        for i in range(3):
            batch_dir = temp_dir / f"batch_{i}"
            batch_dir.mkdir(parents=True)
            (batch_dir / "file.jpg").write_text("test")

        downloader.cleanup_all()

        # Temp dir should still exist but be empty
        assert temp_dir.exists()
        assert len(list(temp_dir.iterdir())) == 0


class TestExifInjectionWorkflows:
    """Integration tests for EXIF metadata injection."""

    @pytest.mark.integration
    def test_format_datetime_for_exif(self):
        """Test datetime formatting for EXIF tags."""
        injector = ExifInjector()

        dt = datetime(2024, 6, 15, 14, 30, 45, tzinfo=UTC)

        formatted = injector._format_datetime_for_exif(dt)
        assert formatted == "2024:06:15 14:30:45"

        formatted_tz = injector._format_datetime_for_exif(dt, include_timezone=True)
        assert formatted_tz == "2024:06:15 14:30:45+00:00"

    @pytest.mark.integration
    def test_is_valid_date_validation(self):
        """Test EXIF date validation."""
        injector = ExifInjector()

        # Valid dates
        assert injector._is_valid_date("2024:06:15 10:30:00")
        assert injector._is_valid_date("2020:01:01 00:00:00")

        # Invalid dates
        assert not injector._is_valid_date("0000:00:00 00:00:00")
        assert not injector._is_valid_date("")
        # Note: _is_valid_date is lenient and may return True for some invalid formats

    @pytest.mark.integration
    def test_get_file_type_detection(self):
        """Test file type detection by extension."""
        injector = ExifInjector()

        from immich_migrator.services.exif_injector import FileType

        # Images
        assert injector._get_file_type(Path("photo.jpg")) == FileType.IMAGE
        assert injector._get_file_type(Path("photo.PNG")) == FileType.IMAGE
        assert injector._get_file_type(Path("photo.heic")) == FileType.IMAGE

        # Videos
        assert injector._get_file_type(Path("video.mp4")) == FileType.VIDEO
        assert injector._get_file_type(Path("video.MOV")) == FileType.VIDEO
        assert injector._get_file_type(Path("video.m4v")) == FileType.VIDEO

        # RIFF
        assert injector._get_file_type(Path("video.avi")) == FileType.RIFF
        assert injector._get_file_type(Path("image.webp")) == FileType.RIFF


class TestUploadWorkflows:
    """Integration tests for upload workflows."""

    @pytest.mark.integration
    def test_uploader_test_connection_success(self):
        """Test uploader connection verification."""
        with patch("immich_migrator.services.uploader.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            uploader = Uploader(
                server_url="http://test.immich.app",
                api_key="test-key",
            )

            assert uploader.test_connection() is True

    @pytest.mark.integration
    def test_uploader_test_connection_failure(self):
        """Test uploader handles connection failures."""
        with patch("immich_migrator.services.uploader.subprocess.run") as mock_run:
            # First call for init check, second for actual test
            mock_run.side_effect = [
                MagicMock(returncode=0),  # Init check passes
                MagicMock(returncode=1, stderr="Connection failed"),  # Test fails
            ]

            uploader = Uploader(
                server_url="http://test.immich.app",
                api_key="test-key",
            )

            assert uploader.test_connection() is False

    @pytest.mark.integration
    def test_uploader_strips_trailing_slash_from_url(self):
        """Test uploader normalizes server URL."""
        with patch("immich_migrator.services.uploader.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            uploader = Uploader(
                server_url="http://test.immich.app/",
                api_key="test-key",
            )

            assert uploader.server_url == "http://test.immich.app"

    @pytest.mark.integration
    async def test_upload_batch_success(self, tmp_path):
        """Test successful batch upload."""
        with patch("immich_migrator.services.uploader.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            uploader = Uploader(
                server_url="http://test.immich.app",
                api_key="test-key",
            )

            # Create test directory with files
            batch_dir = tmp_path / "batch"
            batch_dir.mkdir()
            for i in range(2):
                file_path = batch_dir / f"photo{i}.jpg"
                file_path.write_bytes(b"fake image")

            result = uploader.upload_batch(batch_dir)

            assert result is True
            assert mock_run.called

    @pytest.mark.integration
    async def test_upload_batch_with_album(self, tmp_path):
        """Test batch upload to specific album."""
        with patch("immich_migrator.services.uploader.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            uploader = Uploader(
                server_url="http://test.immich.app",
                api_key="test-key",
            )

            batch_dir = tmp_path / "batch"
            batch_dir.mkdir()
            file_path = batch_dir / "photo.jpg"
            file_path.write_bytes(b"image")

            result = uploader.upload_batch(batch_dir, album_name="Test Album")

            assert result is True
            # Verify album name was passed to CLI
            call_args = str(mock_run.call_args)
            assert "Test Album" in call_args or "--album" in call_args


class TestComputeFileChecksum:
    """Tests for checksum computation utility."""

    @pytest.mark.integration
    def test_compute_checksum_empty_file(self, tmp_path):
        """Test checksum of empty file."""
        file_path = tmp_path / "empty.txt"
        file_path.write_bytes(b"")

        checksum = compute_file_checksum(file_path)

        # SHA1 of empty content
        assert checksum == "da39a3ee5e6b4b0d3255bfef95601890afd80709"

    @pytest.mark.integration
    def test_compute_checksum_with_content(self, tmp_path):
        """Test checksum of file with content."""
        file_path = tmp_path / "test.txt"
        file_path.write_bytes(b"test content")

        checksum = compute_file_checksum(file_path)

        assert len(checksum) == 40  # SHA1 is 40 hex chars
        assert checksum.islower()
        assert all(c in "0123456789abcdef" for c in checksum)

    @pytest.mark.integration
    def test_compute_checksum_large_file(self, tmp_path):
        """Test checksum computation handles large files."""
        file_path = tmp_path / "large.bin"
        # Create 10MB file
        file_path.write_bytes(b"x" * (10 * 1024 * 1024))

        checksum = compute_file_checksum(file_path)

        assert len(checksum) == 40
        assert checksum.islower()

    @pytest.mark.integration
    def test_compute_checksum_binary_file(self, tmp_path):
        """Test checksum works with binary content."""
        file_path = tmp_path / "binary.dat"
        file_path.write_bytes(bytes(range(256)))

        checksum = compute_file_checksum(file_path)

        assert len(checksum) == 40
