"""Pytest configuration and shared fixtures for immich-migrator tests.

Provides fixture factories for:
- Test asset matrix loading and filtering
- Mock Immich API responses
- Mock exiftool subprocess responses
- Mock Immich CLI subprocess responses
- Temporary directories and files
"""

import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path

import pytest
import yaml

# ============================================================================
# Constants
# ============================================================================

TESTS_DIR = Path(__file__).parent
ASSETS_DIR = TESTS_DIR / "assets"
FIXTURES_DIR = TESTS_DIR / "fixtures"
MATRIX_FILE = TESTS_DIR / "assets_matrix_template.yaml"


# ============================================================================
# Asset Matrix Fixtures
# ============================================================================


def _load_assets_matrix() -> list[dict]:
    """Load test asset matrix from YAML file."""
    with open(MATRIX_FILE) as f:
        data = yaml.safe_load(f)
    return data["test_cases"]


# Cache matrix at module load for parametrization
_ASSETS_MATRIX = _load_assets_matrix()


@pytest.fixture(scope="session")
def assets_matrix() -> list[dict]:
    """All test cases from the asset matrix."""
    return _ASSETS_MATRIX


@pytest.fixture(scope="session")
def photo_cases() -> list[dict]:
    """Photo-only test cases (P001-P004)."""
    return [c for c in _ASSETS_MATRIX if c["id"].startswith("P")]


@pytest.fixture(scope="session")
def video_cases() -> list[dict]:
    """Video-only test cases (V001-V004)."""
    return [c for c in _ASSETS_MATRIX if c["id"].startswith("V")]


@pytest.fixture(scope="session")
def live_photo_cases() -> list[dict]:
    """Live photo pair test cases (L001-L016)."""
    return [c for c in _ASSETS_MATRIX if c["id"].startswith("L")]


@pytest.fixture(scope="session")
def edge_cases() -> list[dict]:
    """Edge case test cases (E001-E006)."""
    return [c for c in _ASSETS_MATRIX if c["id"].startswith("E")]


# Parametrization helpers (functions, not fixtures, for use in decorators)
def get_photo_cases():
    """Get photo cases for parametrization."""
    return [c for c in _ASSETS_MATRIX if c["id"].startswith("P")]


def get_video_cases():
    """Get video cases for parametrization."""
    return [c for c in _ASSETS_MATRIX if c["id"].startswith("V")]


def get_live_photo_cases():
    """Get live photo cases for parametrization."""
    return [c for c in _ASSETS_MATRIX if c["id"].startswith("L")]


def get_edge_cases():
    """Get edge cases for parametrization."""
    return [c for c in _ASSETS_MATRIX if c["id"].startswith("E")]


def get_all_cases():
    """Get all test cases for parametrization."""
    return _ASSETS_MATRIX


# ============================================================================
# Asset Path Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def assets_dir() -> Path:
    """Path to test assets directory."""
    return ASSETS_DIR


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Path to test fixtures directory."""
    return FIXTURES_DIR


# ============================================================================
# UUID and Checksum Factories
# ============================================================================


class UUIDFactory:
    """Factory for generating consistent UUIDs for testing."""

    def __init__(self, seed: int = 42):
        self._counter = seed

    def __call__(self) -> str:
        """Generate a deterministic UUID."""
        self._counter += 1
        return str(uuid.UUID(int=self._counter))

    def reset(self, seed: int = 42):
        """Reset the counter."""
        self._counter = seed


@pytest.fixture
def uuid_factory() -> UUIDFactory:
    """Factory for generating deterministic UUIDs."""
    return UUIDFactory()


def compute_sha1(file_path: Path) -> str:
    """Compute SHA1 checksum of a file."""
    sha1 = hashlib.sha1()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha1.update(chunk)
    return sha1.hexdigest()


@pytest.fixture(scope="session")
def compute_checksum():
    """Fixture providing checksum computation function."""
    return compute_sha1


# ============================================================================
# Mock Response Factories
# ============================================================================


class ExiftoolResponseFactory:
    """Factory for creating realistic exiftool JSON responses."""

    @staticmethod
    def photo_with_dates(
        file_path: str,
        date_time_original: str = "2023:06:15 14:30:00",
        create_date: str = "2023:06:15 14:30:00",
    ) -> list[dict]:
        """Create exiftool response for photo with EXIF dates."""
        return [
            {
                "SourceFile": file_path,
                "ExifTool:ExifToolVersion": 12.76,
                "File:FileName": Path(file_path).name,
                "File:Directory": str(Path(file_path).parent),
                "File:FileSize": "47 kB",
                "File:FileType": "JPEG",
                "File:FileTypeExtension": "jpg",
                "File:MIMEType": "image/jpeg",
                "EXIF:DateTimeOriginal": date_time_original,
                "EXIF:CreateDate": create_date,
                "EXIF:ExifVersion": "0232",
                "Composite:ImageSize": "640x611",
                "Composite:Megapixels": 0.391,
            }
        ]

    @staticmethod
    def photo_without_dates(file_path: str) -> list[dict]:
        """Create exiftool response for photo without EXIF dates."""
        return [
            {
                "SourceFile": file_path,
                "ExifTool:ExifToolVersion": 12.76,
                "File:FileName": Path(file_path).name,
                "File:Directory": str(Path(file_path).parent),
                "File:FileSize": "47 kB",
                "File:FileType": "JPEG",
                "File:FileTypeExtension": "jpg",
                "File:MIMEType": "image/jpeg",
                "Composite:ImageSize": "640x611",
                "Composite:Megapixels": 0.391,
            }
        ]

    @staticmethod
    def video_with_dates(
        file_path: str,
        create_date: str = "2023:07:20 16:45:00",
    ) -> list[dict]:
        """Create exiftool response for video with QuickTime dates."""
        return [
            {
                "SourceFile": file_path,
                "ExifTool:ExifToolVersion": 12.76,
                "File:FileName": Path(file_path).name,
                "File:Directory": str(Path(file_path).parent),
                "File:FileSize": "56 kB",
                "File:FileType": "MOV",
                "File:FileTypeExtension": "mov",
                "File:MIMEType": "video/quicktime",
                "QuickTime:MajorBrand": "Apple QuickTime (.MOV/QT)",
                "QuickTime:CreateDate": create_date,
                "QuickTime:TrackCreateDate": create_date,
                "QuickTime:MediaCreateDate": create_date,
                "QuickTime:Duration": "3.00 s",
                "QuickTime:ImageWidth": 640,
                "QuickTime:ImageHeight": 480,
            }
        ]

    @staticmethod
    def video_without_dates(file_path: str) -> list[dict]:
        """Create exiftool response for video without QuickTime dates."""
        return [
            {
                "SourceFile": file_path,
                "ExifTool:ExifToolVersion": 12.76,
                "File:FileName": Path(file_path).name,
                "File:Directory": str(Path(file_path).parent),
                "File:FileSize": "52 kB",
                "File:FileType": "MOV",
                "File:FileTypeExtension": "mov",
                "File:MIMEType": "video/quicktime",
                "QuickTime:MajorBrand": "Apple QuickTime (.MOV/QT)",
                "QuickTime:Duration": "3.00 s",
                "QuickTime:ImageWidth": 640,
                "QuickTime:ImageHeight": 480,
            }
        ]

    @staticmethod
    def corrupted_file(file_path: str) -> list[dict]:
        """Create exiftool response for corrupted file."""
        return [
            {
                "SourceFile": file_path,
                "ExifTool:ExifToolVersion": 12.76,
                "ExifTool:Error": "File format error",
                "File:FileName": Path(file_path).name,
            }
        ]

    @staticmethod
    def version_response() -> str:
        """Create exiftool --version response."""
        return "12.76"


@pytest.fixture
def exiftool_factory() -> ExiftoolResponseFactory:
    """Factory for creating exiftool mock responses."""
    return ExiftoolResponseFactory()


class ImmichCliResponseFactory:
    """Factory for creating realistic Immich CLI responses."""

    @staticmethod
    def version_response() -> str:
        """Create immich --version response."""
        return "2.2.0"

    @staticmethod
    def upload_success(asset_count: int = 1) -> str:
        """Create successful upload response."""
        lines = [
            f"Successfully uploaded {asset_count} asset(s)",
            f"Total: {asset_count} uploaded, 0 duplicates, 0 errors",
        ]
        return "\n".join(lines)

    @staticmethod
    def upload_with_duplicates(uploaded: int = 1, duplicates: int = 1) -> str:
        """Create upload response with duplicates."""
        return f"Total: {uploaded} uploaded, {duplicates} duplicates, 0 errors"

    @staticmethod
    def upload_failure(error: str = "Connection refused") -> str:
        """Create failed upload response."""
        return f"Error: {error}"

    @staticmethod
    def login_success() -> str:
        """Create successful login test response."""
        return "Logged in as user@example.com"

    @staticmethod
    def login_failure() -> str:
        """Create failed login response."""
        return "Error: Invalid API key"


@pytest.fixture
def immich_cli_factory() -> ImmichCliResponseFactory:
    """Factory for creating Immich CLI mock responses."""
    return ImmichCliResponseFactory()


class ImmichApiResponseFactory:
    """Factory for creating realistic Immich API responses."""

    def __init__(self, uuid_factory: UUIDFactory | None = None):
        self.uuid_factory = uuid_factory or UUIDFactory()

    def album(
        self,
        album_id: str | None = None,
        album_name: str = "Test Album",
        asset_count: int = 10,
    ) -> dict:
        """Create an album response."""
        return {
            "id": album_id or self.uuid_factory(),
            "albumName": album_name,
            "assetCount": asset_count,
            "createdAt": "2023-01-01T00:00:00.000Z",
            "updatedAt": "2023-06-15T14:30:00.000Z",
            "ownerId": self.uuid_factory(),
        }

    def asset(
        self,
        asset_id: str | None = None,
        original_file_name: str = "test.jpg",
        checksum: str | None = None,
        asset_type: str = "IMAGE",
        live_photo_video_id: str | None = None,
        file_created_at: str = "2023-06-15T14:30:00.000Z",
        exif_date_time_original: str | None = "2023-06-15T14:30:00.000Z",
    ) -> dict:
        """Create an asset response."""
        # Generate a fake base64 checksum if not provided
        if checksum is None:
            import base64

            fake_sha1 = hashlib.sha1((asset_id or self.uuid_factory()).encode()).digest()
            checksum = base64.b64encode(fake_sha1).decode()

        return {
            "id": asset_id or self.uuid_factory(),
            "originalFileName": original_file_name,
            "originalMimeType": self._mime_from_filename(original_file_name),
            "checksum": checksum,
            "type": asset_type,
            "fileCreatedAt": file_created_at,
            "localDateTime": file_created_at,
            "livePhotoVideoId": live_photo_video_id,
            "exifInfo": {
                "dateTimeOriginal": exif_date_time_original,
            }
            if exif_date_time_original
            else None,
        }

    def _mime_from_filename(self, filename: str) -> str:
        """Infer MIME type from filename."""
        ext = Path(filename).suffix.lower()
        mime_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".heic": "image/heic",
            ".mov": "video/quicktime",
            ".mp4": "video/mp4",
            ".avi": "video/x-msvideo",
        }
        return mime_map.get(ext, "application/octet-stream")

    def album_with_assets(
        self,
        album_id: str | None = None,
        album_name: str = "Test Album",
        assets: list[dict] | None = None,
    ) -> dict:
        """Create album response with embedded assets."""
        album = self.album(album_id, album_name, len(assets or []))
        album["assets"] = assets or []
        return album

    def bulk_upload_check_response(
        self,
        checksums: list[str],
        existing_ids: dict[str, str] | None = None,
    ) -> dict:
        """Create bulk-upload-check API response.

        Args:
            checksums: List of checksums to check
            existing_ids: Map of checksum -> asset_id for existing assets
        """
        existing_ids = existing_ids or {}
        results = []
        for checksum in checksums:
            if checksum in existing_ids:
                results.append(
                    {
                        "id": existing_ids[checksum],
                        "checksum": checksum,
                        "action": "accept",
                    }
                )
            else:
                results.append(
                    {
                        "checksum": checksum,
                        "action": "reject",
                        "reason": "not found",
                    }
                )
        return {"results": results}

    def search_metadata_response(
        self,
        assets: list[dict] | None = None,
        next_page: str | None = None,
    ) -> dict:
        """Create search/metadata API response."""
        return {
            "assets": {"items": assets or [], "nextPage": next_page},
        }


@pytest.fixture
def immich_api_factory(uuid_factory) -> ImmichApiResponseFactory:
    """Factory for creating Immich API mock responses."""
    return ImmichApiResponseFactory(uuid_factory)


# ============================================================================
# Subprocess Mock Helpers
# ============================================================================


class SubprocessMocker:
    """Helper for setting up subprocess.run mocks."""

    def __init__(self, mocker):
        self.mocker = mocker
        self._mock = None

    def setup(self, return_values: list[tuple[int, str, str]] | None = None):
        """Setup subprocess.run mock with return values.

        Args:
            return_values: List of (returncode, stdout, stderr) tuples.
                           Will cycle through values on successive calls.
        """
        from unittest.mock import MagicMock

        return_values = return_values or [(0, "", "")]

        call_count = [0]

        def mock_run(*args, **kwargs):
            idx = call_count[0] % len(return_values)
            call_count[0] += 1
            rc, stdout, stderr = return_values[idx]

            result = MagicMock()
            result.returncode = rc
            result.stdout = stdout
            result.stderr = stderr
            return result

        self._mock = self.mocker.patch("subprocess.run", side_effect=mock_run)
        return self._mock

    def setup_exiftool(
        self,
        version_response: str = "12.76",
        json_responses: list[list[dict]] | None = None,
        inject_success: bool = True,
    ):
        """Setup mocks specifically for exiftool calls.

        Args:
            version_response: Response for exiftool -ver
            json_responses: JSON responses for -json queries
            inject_success: Whether injection calls should succeed
        """
        from unittest.mock import MagicMock

        json_responses = json_responses or []
        json_idx = [0]

        def mock_run(cmd, *args, **kwargs):
            result = MagicMock()

            if "-ver" in cmd:
                result.returncode = 0
                result.stdout = version_response
                result.stderr = ""
            elif "-json" in cmd:
                idx = json_idx[0] % max(1, len(json_responses))
                if json_responses:
                    json_idx[0] += 1
                    result.stdout = json.dumps(json_responses[idx])
                else:
                    result.stdout = "[]"
                result.returncode = 0
                result.stderr = ""
            else:
                # Injection or other command
                result.returncode = 0 if inject_success else 1
                result.stdout = "1 image files updated" if inject_success else ""
                result.stderr = "" if inject_success else "Error: File not found"

            return result

        self._mock = self.mocker.patch("subprocess.run", side_effect=mock_run)
        return self._mock

    def setup_immich_cli(
        self,
        version_response: str = "2.2.0",
        upload_success: bool = True,
        upload_response: str | None = None,
    ):
        """Setup mocks specifically for Immich CLI calls.

        Args:
            version_response: Response for immich --version
            upload_success: Whether upload should succeed
            upload_response: Custom upload response
        """
        from unittest.mock import MagicMock

        def mock_run(cmd, *args, **kwargs):
            result = MagicMock()

            if "--version" in cmd:
                result.returncode = 0
                result.stdout = version_response
                result.stderr = ""
            elif "upload" in cmd:
                if upload_success:
                    result.returncode = 0
                    result.stdout = upload_response or "Successfully uploaded 1 asset(s)"
                    result.stderr = ""
                else:
                    result.returncode = 1
                    result.stdout = ""
                    result.stderr = upload_response or "Error: Connection refused"
            else:
                result.returncode = 0
                result.stdout = ""
                result.stderr = ""

            return result

        self._mock = self.mocker.patch("subprocess.run", side_effect=mock_run)
        return self._mock


@pytest.fixture
def subprocess_mocker(mocker) -> SubprocessMocker:
    """Fixture for mocking subprocess.run calls."""
    return SubprocessMocker(mocker)


# ============================================================================
# Temporary File Fixtures
# ============================================================================


@pytest.fixture
def temp_state_file(tmp_path) -> Path:
    """Create a temporary state file path."""
    return tmp_path / "migration_state.json"


@pytest.fixture
def temp_batch_dir(tmp_path) -> Path:
    """Create a temporary batch directory."""
    batch_dir = tmp_path / "batch"
    batch_dir.mkdir()
    return batch_dir


@pytest.fixture
def temp_failed_dir(tmp_path) -> Path:
    """Create a temporary failed assets directory."""
    failed_dir = tmp_path / "failed"
    failed_dir.mkdir()
    return failed_dir


# ============================================================================
# Model Instance Factories
# ============================================================================


@pytest.fixture
def asset_factory(uuid_factory):
    """Factory for creating Asset model instances."""
    from immich_migrator.models.asset import Asset

    def _create(
        asset_id: str | None = None,
        original_file_name: str = "test.jpg",
        original_mime_type: str = "image/jpeg",
        checksum: str | None = None,
        asset_type: str = "IMAGE",
        live_photo_video_id: str | None = None,
        file_created_at: datetime | None = None,
        file_size_bytes: int | None = None,
    ) -> Asset:
        # Generate a valid hex checksum if not provided
        if checksum is None:
            checksum = hashlib.sha1((asset_id or uuid_factory()).encode()).hexdigest()

        return Asset(
            id=asset_id or uuid_factory(),
            original_file_name=original_file_name,
            original_mime_type=original_mime_type,
            checksum=checksum,
            asset_type=asset_type,
            live_photo_video_id=live_photo_video_id,
            file_created_at=file_created_at,
            file_size_bytes=file_size_bytes,
        )

    return _create


@pytest.fixture
def album_state_factory(uuid_factory):
    """Factory for creating AlbumState model instances."""
    from immich_migrator.models.state import AlbumState, MigrationStatus

    def _create(
        album_id: str | None = None,
        album_name: str = "Test Album",
        status: MigrationStatus = MigrationStatus.PENDING,
        asset_count: int = 10,
        migrated_count: int = 0,
        error_message: str | None = None,
    ) -> AlbumState:
        return AlbumState(
            album_id=album_id or uuid_factory(),
            album_name=album_name,
            status=status,
            asset_count=asset_count,
            migrated_count=migrated_count,
            error_message=error_message,
        )

    return _create


# ============================================================================
# Test Asset Helpers
# ============================================================================


@pytest.fixture(scope="session")
def real_photo_path() -> Path:
    """Path to a real photo test asset (P001)."""
    return ASSETS_DIR / "P001_photo_good.jpg"


@pytest.fixture(scope="session")
def real_video_path() -> Path:
    """Path to a real video test asset (V001)."""
    return ASSETS_DIR / "V001_video_good.mov"


@pytest.fixture(scope="session")
def real_live_photo_pair() -> tuple[Path, Path]:
    """Paths to a real live photo pair (L001)."""
    return (
        ASSETS_DIR / "L001_live_photo.jpg",
        ASSETS_DIR / "L001_live_video.mov",
    )


@pytest.fixture(scope="session")
def corrupted_photo_path() -> Path:
    """Path to a corrupted photo test asset (E002)."""
    return ASSETS_DIR / "E002_photo_corrupted.jpg"
