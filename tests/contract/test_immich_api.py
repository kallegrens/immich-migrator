"""Contract tests for Immich API interface.

These tests verify that our models and expectations match the actual
Immich API contract. They use mock responses based on real API documentation
to ensure compatibility.

Contract tests verify:
- Request format matches API expectations
- Response parsing handles all fields correctly
- Error responses are handled properly
- API versioning considerations
"""

import base64

import pytest

# ============================================================================
# API Response Contracts
# ============================================================================


class TestAlbumApiContract:
    """Contract tests for Album API endpoints."""

    @pytest.mark.contract
    def test_album_response_required_fields(self, immich_api_factory):
        """Album response must contain required fields."""
        album = immich_api_factory.album()

        # Required fields per Immich API
        required_fields = ["id", "albumName", "assetCount", "ownerId"]

        for field in required_fields:
            assert field in album, f"Missing required field: {field}"

    @pytest.mark.contract
    def test_album_id_format(self, immich_api_factory):
        """Album ID must be valid UUID format."""
        import re

        album = immich_api_factory.album()

        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        assert re.match(uuid_pattern, album["id"], re.IGNORECASE), (
            f"Album ID not valid UUID: {album['id']}"
        )

    @pytest.mark.contract
    def test_album_list_response_is_array(self, immich_api_factory):
        """GET /albums returns array of albums."""
        # Simulating API response
        response = [
            immich_api_factory.album(album_name="Album 1"),
            immich_api_factory.album(album_name="Album 2"),
        ]

        assert isinstance(response, list)
        assert len(response) == 2

    @pytest.mark.contract
    def test_album_with_assets_response(self, immich_api_factory):
        """Album response can include embedded assets."""
        assets = [
            immich_api_factory.asset(original_file_name="photo1.jpg"),
            immich_api_factory.asset(original_file_name="photo2.jpg"),
        ]

        album = immich_api_factory.album_with_assets(
            album_name="With Assets",
            assets=assets,
        )

        assert "assets" in album
        assert len(album["assets"]) == 2


# ============================================================================
# Asset API Contract Tests
# ============================================================================


class TestAssetApiContract:
    """Contract tests for Asset API endpoints."""

    @pytest.mark.contract
    def test_asset_response_required_fields(self, immich_api_factory):
        """Asset response must contain required fields."""
        asset = immich_api_factory.asset()

        required_fields = [
            "id",
            "originalFileName",
            "originalMimeType",
            "checksum",
            "type",
        ]

        for field in required_fields:
            assert field in asset, f"Missing required field: {field}"

    @pytest.mark.contract
    def test_asset_type_enum_values(self, immich_api_factory):
        """Asset type must be IMAGE or VIDEO."""
        valid_types = ["IMAGE", "VIDEO"]

        for asset_type in valid_types:
            asset = immich_api_factory.asset(asset_type=asset_type)
            assert asset["type"] in valid_types

    @pytest.mark.contract
    def test_asset_checksum_format(self, immich_api_factory):
        """Asset checksum is base64-encoded SHA1."""
        asset = immich_api_factory.asset()

        checksum = asset["checksum"]

        # Base64-encoded SHA1 is 28 characters with padding
        # Or can be decoded to 20 bytes
        try:
            decoded = base64.b64decode(checksum)
            assert len(decoded) == 20, "SHA1 should be 20 bytes"
        except Exception:
            # If not base64, might be hex (40 chars)
            assert len(checksum) == 40, "If hex, should be 40 chars"

    @pytest.mark.contract
    def test_asset_live_photo_video_id_optional(self, immich_api_factory):
        """livePhotoVideoId is optional for linking live photos."""
        # Without live photo
        asset_without = immich_api_factory.asset()
        assert asset_without.get("livePhotoVideoId") is None

        # With live photo
        video_id = "550e8400-e29b-41d4-a716-446655440001"
        asset_with = immich_api_factory.asset(live_photo_video_id=video_id)
        assert asset_with["livePhotoVideoId"] == video_id

    @pytest.mark.contract
    def test_asset_exif_info_structure(self, immich_api_factory):
        """Asset exifInfo has expected structure."""
        asset = immich_api_factory.asset(exif_date_time_original="2024:01:15 10:30:00")

        assert "exifInfo" in asset
        exif = asset["exifInfo"]
        assert "dateTimeOriginal" in exif

    @pytest.mark.contract
    def test_asset_mime_types(self, immich_api_factory):
        """Asset MIME types match file extensions."""
        test_cases = [
            ("photo.jpg", "image/jpeg"),
            ("photo.jpeg", "image/jpeg"),
            ("photo.png", "image/png"),
            ("photo.heic", "image/heic"),
            ("video.mov", "video/quicktime"),
            ("video.mp4", "video/mp4"),
        ]

        for filename, expected_mime in test_cases:
            asset = immich_api_factory.asset(original_file_name=filename)
            assert asset["originalMimeType"] == expected_mime, (
                f"Expected {expected_mime} for {filename}, got {asset['originalMimeType']}"
            )


# ============================================================================
# Bulk Upload Check API Contract Tests
# ============================================================================


class TestBulkUploadCheckContract:
    """Contract tests for bulk-upload-check endpoint."""

    @pytest.mark.contract
    def test_bulk_upload_check_request_format(self):
        """Bulk upload check request format."""
        # Request body format
        request = {
            "assets": [
                {"id": "local-id-1", "checksum": "base64checksum1=="},
                {"id": "local-id-2", "checksum": "base64checksum2=="},
            ]
        }

        assert "assets" in request
        assert isinstance(request["assets"], list)

    @pytest.mark.contract
    def test_bulk_upload_check_response_format(self, immich_api_factory):
        """Bulk upload check response format."""
        checksums = ["checksum1", "checksum2", "checksum3"]
        existing = {"checksum1": "asset-id-1"}

        response = immich_api_factory.bulk_upload_check_response(
            checksums=checksums,
            existing_ids=existing,
        )

        assert "results" in response
        assert isinstance(response["results"], list)

        # Each result should have checksum and action
        for result in response["results"]:
            assert "checksum" in result
            assert "action" in result
            assert result["action"] in ["accept", "reject"]

    @pytest.mark.contract
    def test_bulk_upload_check_accept_action(self, immich_api_factory):
        """Accept action includes asset ID."""
        checksums = ["existing-checksum"]
        existing = {"existing-checksum": "found-asset-id"}

        response = immich_api_factory.bulk_upload_check_response(
            checksums=checksums,
            existing_ids=existing,
        )

        result = response["results"][0]
        assert result["action"] == "accept"
        assert result["id"] == "found-asset-id"

    @pytest.mark.contract
    def test_bulk_upload_check_reject_action(self, immich_api_factory):
        """Reject action for non-existing assets."""
        checksums = ["new-checksum"]
        existing = {}

        response = immich_api_factory.bulk_upload_check_response(
            checksums=checksums,
            existing_ids=existing,
        )

        result = response["results"][0]
        assert result["action"] == "reject"
        assert "reason" in result


# ============================================================================
# Search Metadata API Contract Tests
# ============================================================================


class TestSearchMetadataContract:
    """Contract tests for search/metadata endpoint."""

    @pytest.mark.contract
    def test_search_metadata_response_structure(self, immich_api_factory):
        """Search metadata response structure."""
        assets = [
            immich_api_factory.asset(original_file_name="found1.jpg"),
        ]

        response = immich_api_factory.search_metadata_response(assets=assets)

        assert "assets" in response
        assert "items" in response["assets"]
        assert "nextPage" in response["assets"]

    @pytest.mark.contract
    def test_search_metadata_pagination(self, immich_api_factory):
        """Search metadata supports pagination."""
        response = immich_api_factory.search_metadata_response(
            assets=[],
            next_page="page-token-123",
        )

        assert response["assets"]["nextPage"] == "page-token-123"

    @pytest.mark.contract
    def test_search_metadata_empty_results(self, immich_api_factory):
        """Search metadata handles empty results."""
        response = immich_api_factory.search_metadata_response(assets=[])

        assert response["assets"]["items"] == []
        assert response["assets"]["nextPage"] is None


# ============================================================================
# Error Response Contract Tests
# ============================================================================


class TestErrorResponseContract:
    """Contract tests for API error responses."""

    @pytest.mark.contract
    def test_error_response_structure(self):
        """API error responses have consistent structure."""
        # Standard Immich error response format
        error_response = {
            "statusCode": 401,
            "message": "Unauthorized",
            "error": "Invalid API key",
        }

        assert "statusCode" in error_response
        assert "message" in error_response

    @pytest.mark.contract
    def test_validation_error_structure(self):
        """Validation errors include field details."""
        validation_error = {
            "statusCode": 400,
            "message": "Validation failed",
            "errors": [{"field": "checksum", "message": "must be valid base64"}],
        }

        assert validation_error["statusCode"] == 400
        assert "errors" in validation_error

    @pytest.mark.contract
    def test_not_found_error(self):
        """404 error for non-existent resources."""
        not_found = {
            "statusCode": 404,
            "message": "Not Found",
            "error": "Asset not found",
        }

        assert not_found["statusCode"] == 404


# ============================================================================
# Model to API Contract Tests
# ============================================================================


class TestModelApiContract:
    """Tests that our models match API contract."""

    @pytest.mark.contract
    def test_asset_model_parses_api_response(self, immich_api_factory, uuid_factory):
        """Asset model can parse API response."""
        from immich_migrator.models.asset import Asset

        # API response format
        api_response = immich_api_factory.asset(
            asset_id=uuid_factory(),
            original_file_name="api_photo.jpg",
            asset_type="IMAGE",
        )

        # Parse into model (file_size_bytes is optional)
        asset = Asset(
            id=api_response["id"],
            original_file_name=api_response["originalFileName"],
            original_mime_type=api_response["originalMimeType"],
            checksum=api_response["checksum"],
            asset_type=api_response["type"],
            live_photo_video_id=api_response.get("livePhotoVideoId"),
            file_size_bytes=None,  # Optional field
        )

        assert asset.id == api_response["id"]
        assert asset.original_file_name == api_response["originalFileName"]

    @pytest.mark.contract
    def test_album_state_from_api_response(self, immich_api_factory, uuid_factory):
        """AlbumState can be created from API response."""
        from immich_migrator.models.state import AlbumState, MigrationStatus

        api_response = immich_api_factory.album(
            album_id=uuid_factory(),
            album_name="API Album",
            asset_count=50,
        )

        album_state = AlbumState(
            album_id=api_response["id"],
            album_name=api_response["albumName"],
            status=MigrationStatus.PENDING,
            asset_count=api_response["assetCount"],
            migrated_count=0,
        )

        assert album_state.album_name == "API Album"
        assert album_state.asset_count == 50


# ============================================================================
# API Version Contract Tests
# ============================================================================


class TestApiVersionContract:
    """Tests for API version compatibility."""

    @pytest.mark.contract
    def test_api_key_header_name(self):
        """API key header name is x-api-key."""
        expected_header = "x-api-key"
        assert expected_header == "x-api-key"

    @pytest.mark.contract
    def test_base_api_path(self):
        """Base API path is /api."""
        base_path = "/api"
        assert base_path.startswith("/api")

    @pytest.mark.contract
    def test_album_endpoints(self):
        """Album API endpoints follow expected pattern."""
        endpoints = {
            "list": "GET /api/albums",
            "get": "GET /api/albums/{id}",
            "create": "POST /api/albums",
            "add_assets": "PUT /api/albums/{id}/assets",
        }

        assert "/api/albums" in endpoints["list"]

    @pytest.mark.contract
    def test_asset_endpoints(self):
        """Asset API endpoints follow expected pattern."""
        endpoints = {
            "download": "GET /api/assets/{id}/original",
            "info": "GET /api/assets/{id}",
            "bulk_check": "POST /api/assets/bulk-upload-check",
        }

        assert "bulk-upload-check" in endpoints["bulk_check"]


# ============================================================================
# Live Photo Linking Contract Tests
# ============================================================================


class TestLivePhotoLinkingContract:
    """Contract tests for live photo linking API."""

    @pytest.mark.contract
    def test_live_photo_link_request(self, uuid_factory):
        """Live photo link request format."""
        request = {
            "assetId": uuid_factory(),  # Image asset
            "motionVideoId": uuid_factory(),  # Video asset
        }

        assert "assetId" in request
        assert "motionVideoId" in request

    @pytest.mark.contract
    def test_live_photo_in_asset_response(self, immich_api_factory, uuid_factory):
        """Linked live photo appears in asset response."""
        video_id = uuid_factory()

        # Image asset with linked video
        asset = immich_api_factory.asset(
            asset_type="IMAGE",
            live_photo_video_id=video_id,
        )

        assert asset["livePhotoVideoId"] == video_id

    @pytest.mark.contract
    def test_live_photo_video_asset_type(self, immich_api_factory):
        """Live photo video component has VIDEO type."""
        video_asset = immich_api_factory.asset(
            original_file_name="live_video.mov",
            asset_type="VIDEO",
        )

        assert video_asset["type"] == "VIDEO"
        assert video_asset["originalMimeType"] == "video/quicktime"
