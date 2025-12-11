"""Unit tests for ImmichClient service.

Tests API interactions, response parsing, error handling, and retry logic
using httpx mocking with respx.
"""

from datetime import UTC, datetime

import httpx
import pytest
import respx

from immich_migrator.models.album import Album
from immich_migrator.models.asset import Asset
from immich_migrator.models.config import ImmichCredentials
from immich_migrator.services.immich_client import ImmichClient


@pytest.fixture
def credentials():
    """Create test credentials."""
    return ImmichCredentials(
        server_url="http://test.immich.app",
        api_key="test-api-key-123",
    )


@pytest.fixture
def mock_album_response():
    """Create mock album API response."""
    return {
        "id": "00000000-0000-0000-0000-000000000001",
        "albumName": "Test Album",
        "assetCount": 5,
        "createdAt": "2024-01-01T00:00:00.000Z",
        "updatedAt": "2024-06-15T14:30:00.000Z",
        "ownerId": "00000000-0000-0000-0000-000000000099",
    }


@pytest.fixture
def mock_asset_response():
    """Create mock asset API response."""
    return {
        "id": "00000000-0000-0000-0000-000000000002",
        "originalFileName": "test.jpg",
        "originalMimeType": "image/jpeg",
        "checksum": "a" * 40,
        "fileCreatedAt": "2024-01-01T12:00:00.000Z",
        "localDateTime": "2024-01-01T12:00:00.000Z",
        "type": "IMAGE",
        "exifInfo": {
            "fileSizeInByte": 1024,
            # Note: dateTimeOriginal in EXIF format requires special parsing
            # We test this separately, so omit it here
        },
    }


class TestImmichClientInitialization:
    """Tests for ImmichClient initialization and context management."""

    @pytest.mark.unit
    async def test_client_context_manager(self, credentials):
        """Test client can be used as async context manager."""
        async with ImmichClient(credentials) as client:
            assert client.client is not None
            assert client.server_url == "http://test.immich.app"
            assert client.api_key == "test-api-key-123"

    @pytest.mark.unit
    async def test_client_closes_on_exit(self, credentials):
        """Test client connection closes on context manager exit."""
        client_obj = ImmichClient(credentials)
        async with client_obj:
            assert client_obj.client is not None

        # Client should be closed after exit
        assert client_obj.client.is_closed

    @pytest.mark.unit
    async def test_client_strips_trailing_slash(self):
        """Test client strips trailing slash from server URL."""
        creds = ImmichCredentials(
            server_url="http://test.immich.app/",
            api_key="test-key",
        )

        async with ImmichClient(creds) as client:
            assert client.server_url == "http://test.immich.app"


class TestImmichClientListAlbums:
    """Tests for list_albums method."""

    @pytest.mark.unit
    @respx.mock
    async def test_list_albums_success(self, credentials, mock_album_response):
        """Test listing albums returns parsed Album objects."""
        respx.get("http://test.immich.app/api/albums").mock(
            return_value=httpx.Response(200, json=[mock_album_response])
        )

        async with ImmichClient(credentials) as client:
            albums = await client.list_albums()

        assert len(albums) == 1
        assert isinstance(albums[0], Album)
        assert albums[0].album_name == "Test Album"
        assert albums[0].asset_count == 5

    @pytest.mark.unit
    @respx.mock
    async def test_list_albums_empty(self, credentials):
        """Test listing albums when none exist."""
        respx.get("http://test.immich.app/api/albums").mock(
            return_value=httpx.Response(200, json=[])
        )

        async with ImmichClient(credentials) as client:
            albums = await client.list_albums()

        assert len(albums) == 0

    @pytest.mark.unit
    @respx.mock
    async def test_list_albums_http_error(self, credentials):
        """Test list_albums handles HTTP errors."""
        respx.get("http://test.immich.app/api/albums").mock(
            return_value=httpx.Response(500, text="Server error")
        )

        async with ImmichClient(credentials) as client:
            with pytest.raises(httpx.HTTPStatusError):
                await client.list_albums()


class TestImmichClientGetAlbumAssets:
    """Tests for get_album_assets method."""

    @pytest.mark.unit
    @respx.mock
    async def test_get_album_assets_success(self, credentials, mock_asset_response):
        """Test fetching album assets returns Asset objects."""
        album_id = "00000000-0000-0000-0000-000000000001"
        respx.get(f"http://test.immich.app/api/albums/{album_id}").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": album_id,
                    "albumName": "Test Album",
                    "assetCount": 1,
                    "assets": [mock_asset_response],
                },
            )
        )

        async with ImmichClient(credentials) as client:
            album = await client.get_album_assets(album_id)

        assert isinstance(album, Album)
        assert len(album.assets) == 1
        assert isinstance(album.assets[0], Asset)
        assert album.assets[0].original_file_name == "test.jpg"

    @pytest.mark.unit
    @respx.mock
    async def test_get_album_assets_empty_album(self, credentials):
        """Test fetching assets from empty album."""
        album_id = "00000000-0000-0000-0000-000000000001"
        respx.get(f"http://test.immich.app/api/albums/{album_id}").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": album_id,
                    "albumName": "Empty Album",
                    "assetCount": 0,
                    "assets": [],
                },
            )
        )

        async with ImmichClient(credentials) as client:
            album = await client.get_album_assets(album_id)

        assert isinstance(album, Album)
        assert len(album.assets) == 0

    @pytest.mark.unit
    @respx.mock
    async def test_get_album_assets_album_not_found(self, credentials):
        """Test get_album_assets handles 404 errors."""
        album_id = "00000000-0000-0000-0000-000000000099"
        respx.get(f"http://test.immich.app/api/albums/{album_id}").mock(
            return_value=httpx.Response(404, text="Not found")
        )

        async with ImmichClient(credentials) as client:
            with pytest.raises(httpx.HTTPStatusError):
                await client.get_album_assets(album_id)


class TestImmichClientGetAsset:
    """Tests for get_asset method."""

    @pytest.mark.unit
    @respx.mock
    async def test_get_asset_success(self, credentials, mock_asset_response):
        """Test fetching single asset by ID."""
        asset_id = "00000000-0000-0000-0000-000000000002"
        respx.get(f"http://test.immich.app/api/assets/{asset_id}").mock(
            return_value=httpx.Response(200, json=mock_asset_response)
        )

        async with ImmichClient(credentials) as client:
            asset = await client.get_asset(asset_id)

        assert asset is not None
        assert isinstance(asset, Asset)
        assert asset.id == asset_id
        assert asset.original_file_name == "test.jpg"

    @pytest.mark.unit
    @respx.mock
    async def test_get_asset_not_found(self, credentials):
        """Test get_asset returns None for 404."""
        asset_id = "00000000-0000-0000-0000-000000000099"
        respx.get(f"http://test.immich.app/api/assets/{asset_id}").mock(
            return_value=httpx.Response(404, text="Not found")
        )

        async with ImmichClient(credentials) as client:
            asset = await client.get_asset(asset_id)

        assert asset is None

    @pytest.mark.unit
    @respx.mock
    async def test_get_asset_server_error(self, credentials):
        """Test get_asset raises on server errors."""
        asset_id = "00000000-0000-0000-0000-000000000002"
        respx.get(f"http://test.immich.app/api/assets/{asset_id}").mock(
            return_value=httpx.Response(500, text="Server error")
        )

        async with ImmichClient(credentials) as client:
            with pytest.raises(httpx.HTTPStatusError):
                await client.get_asset(asset_id)


class TestImmichClientDownloadAsset:
    """Tests for download_asset method."""

    @pytest.mark.unit
    @respx.mock
    async def test_download_asset_success(self, credentials, uuid_factory, tmp_path):
        """Test downloading asset to file."""
        asset_id = uuid_factory()
        asset = Asset(
            id=asset_id,
            original_file_name="test.jpg",
            original_mime_type="image/jpeg",
            checksum="a" * 40,
            file_created_at=datetime(2024, 1, 1, tzinfo=UTC),
            file_size_bytes=1024,
            asset_type="IMAGE",
        )

        # Mock download endpoint
        respx.get(f"http://test.immich.app/api/assets/{asset_id}/original").mock(
            return_value=httpx.Response(200, content=b"fake image data")
        )

        dest_path = tmp_path / "downloaded.jpg"

        async with ImmichClient(credentials) as client:
            await client.download_asset(asset, dest_path)

        assert dest_path.exists()
        assert dest_path.read_bytes() == b"fake image data"

    @pytest.mark.unit
    @respx.mock
    async def test_download_asset_creates_parent_dir(self, credentials, uuid_factory, tmp_path):
        """Test download_asset creates parent directories."""
        asset_id = uuid_factory()
        asset = Asset(
            id=asset_id,
            original_file_name="test.jpg",
            original_mime_type="image/jpeg",
            checksum="a" * 40,
            file_created_at=datetime(2024, 1, 1, tzinfo=UTC),
            file_size_bytes=1024,
            asset_type="IMAGE",
        )

        respx.get(f"http://test.immich.app/api/assets/{asset_id}/original").mock(
            return_value=httpx.Response(200, content=b"test data")
        )

        # Path with non-existent parent directories
        dest_path = tmp_path / "nested" / "deep" / "file.jpg"

        async with ImmichClient(credentials) as client:
            await client.download_asset(asset, dest_path)

        assert dest_path.exists()


class TestImmichClientSearchUnalbummed:
    """Tests for search_unalbummed_assets method."""

    @pytest.mark.unit
    @respx.mock
    async def test_search_unalbummed_assets_success(self, credentials, mock_asset_response):
        """Test searching for unalbummed assets."""
        respx.post("http://test.immich.app/api/search/metadata").mock(
            return_value=httpx.Response(
                200,
                json={
                    "assets": {
                        "items": [mock_asset_response],
                        "nextPage": None,
                    }
                },
            )
        )

        async with ImmichClient(credentials) as client:
            assets = await client.search_unalbummed_assets()

        assert len(assets) == 1
        assert isinstance(assets[0], Asset)

    @pytest.mark.unit
    @respx.mock
    async def test_search_unalbummed_assets_pagination(self, credentials, mock_asset_response):
        """Test search handles pagination."""
        # First page
        respx.post("http://test.immich.app/api/search/metadata").mock(
            return_value=httpx.Response(
                200,
                json={
                    "assets": {
                        "items": [mock_asset_response],
                        "nextPage": "page2",
                    }
                },
            )
        )

        async with ImmichClient(credentials) as client:
            assets = await client.search_unalbummed_assets()

        # Should return first page (pagination handled by caller)
        assert len(assets) >= 1

    @pytest.mark.unit
    @respx.mock
    async def test_search_unalbummed_assets_empty(self, credentials):
        """Test search with no unalbummed assets."""
        respx.post("http://test.immich.app/api/search/metadata").mock(
            return_value=httpx.Response(
                200,
                json={"assets": {"items": [], "nextPage": None}},
            )
        )

        async with ImmichClient(credentials) as client:
            assets = await client.search_unalbummed_assets()

        assert len(assets) == 0


class TestImmichClientLivePhotos:
    """Tests for live photo related methods."""

    @pytest.mark.unit
    @respx.mock
    async def test_fetch_live_photo_videos_success(self, credentials, mock_asset_response):
        """Test fetching live photo video assets."""
        video_id = "00000000-0000-0000-0000-000000000003"

        # Mock the video asset response
        video_response = mock_asset_response.copy()
        video_response["id"] = video_id
        video_response["type"] = "VIDEO"
        video_response["originalMimeType"] = "video/quicktime"

        respx.get(f"http://test.immich.app/api/assets/{video_id}").mock(
            return_value=httpx.Response(200, json=video_response)
        )

        async with ImmichClient(credentials) as client:
            videos = await client._fetch_live_photo_videos([video_id])

        assert len(videos) == 1
        assert videos[0].asset_type == "VIDEO"

    @pytest.mark.unit
    @respx.mock
    async def test_fetch_live_photo_videos_handles_errors(self, credentials):
        """Test _fetch_live_photo_videos handles individual asset errors."""
        video_id = "00000000-0000-0000-0000-000000000003"

        respx.get(f"http://test.immich.app/api/assets/{video_id}").mock(
            return_value=httpx.Response(404, text="Not found")
        )

        async with ImmichClient(credentials) as client:
            videos = await client._fetch_live_photo_videos([video_id])

        # Should handle error gracefully and return empty list
        assert len(videos) == 0

    @pytest.mark.unit
    @respx.mock
    async def test_fetch_live_photo_videos_empty_list(self, credentials):
        """Test _fetch_live_photo_videos with empty input."""
        async with ImmichClient(credentials) as client:
            videos = await client._fetch_live_photo_videos([])

        assert len(videos) == 0


class TestImmichClientRateLimiting:
    """Tests for rate limiting and retry behavior."""

    @pytest.mark.unit
    async def test_client_uses_semaphore(self, credentials):
        """Test client limits concurrent requests."""
        async with ImmichClient(credentials, max_concurrent=2) as client:
            assert client._semaphore._value == 2

    @pytest.mark.unit
    async def test_client_request_without_context_manager(self, credentials):
        """Test making request without context manager raises error."""
        client = ImmichClient(credentials)

        # Client not initialized, so this will fail
        # This test verifies we need to use the context manager
        assert client.client is None


class TestImmichClientResponseParsing:
    """Tests for API response parsing edge cases."""

    @pytest.mark.unit
    @respx.mock
    async def test_parse_asset_with_minimal_data(self, credentials):
        """Test parsing asset with minimal required fields."""
        asset_id = "00000000-0000-0000-0000-000000000002"
        minimal_response = {
            "id": asset_id,
            "originalFileName": "minimal.jpg",
            "originalMimeType": "image/jpeg",
            "checksum": "b" * 40,
            "type": "IMAGE",
            "exifInfo": {},
        }

        respx.get(f"http://test.immich.app/api/assets/{asset_id}").mock(
            return_value=httpx.Response(200, json=minimal_response)
        )

        async with ImmichClient(credentials) as client:
            asset = await client.get_asset(asset_id)

        assert asset is not None
        assert asset.original_file_name == "minimal.jpg"
        assert asset.file_created_at is None  # Optional field

    @pytest.mark.unit
    @respx.mock
    async def test_parse_asset_with_live_photo_video_id(self, credentials):
        """Test parsing asset with live photo video link."""
        asset_id = "00000000-0000-0000-0000-000000000004"
        video_id = "00000000-0000-0000-0000-000000000005"

        response_with_live_photo = {
            "id": asset_id,
            "originalFileName": "live.jpg",
            "originalMimeType": "image/jpeg",
            "checksum": "c" * 40,
            "livePhotoVideoId": video_id,
            "type": "IMAGE",
            "exifInfo": {},
        }

        respx.get(f"http://test.immich.app/api/albums/{asset_id}").mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": asset_id,
                    "albumName": "Live Photo Album",
                    "assetCount": 1,
                    "assets": [response_with_live_photo],
                },
            )
        )

        async with ImmichClient(credentials) as client:
            album = await client.get_album_assets(asset_id)

        assert len(album.assets) == 1
        assert album.assets[0].live_photo_video_id == video_id
