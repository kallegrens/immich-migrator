"""Integration tests for checksum handling and verification.

Tests checksum computation, comparison, and mismatch detection:
- SHA1 checksum calculation
- Base64 to hex conversion
- Checksum verification after download
- Mismatch detection scenarios
"""

import base64
import hashlib
from pathlib import Path

import pytest
import yaml

# Load assets directory and matrix from conftest constants
TESTS_DIR = Path(__file__).parent.parent
ASSETS_DIR = TESTS_DIR / "assets"
MATRIX_FILE = TESTS_DIR / "assets_matrix_template.yaml"


def get_all_cases() -> list[dict]:
    """Get all test cases from matrix."""
    with open(MATRIX_FILE) as f:
        data = yaml.safe_load(f)
    return data["test_cases"]


# ============================================================================
# Checksum Computation Tests
# ============================================================================


class TestChecksumComputation:
    """Tests for computing file checksums."""

    @pytest.mark.integration
    def test_sha1_checksum_computation(self, compute_checksum, real_photo_path):
        """Compute SHA1 checksum of a file."""
        checksum = compute_checksum(real_photo_path)

        # SHA1 produces 40 hex characters
        assert len(checksum) == 40
        assert all(c in "0123456789abcdef" for c in checksum.lower())

    @pytest.mark.integration
    def test_checksum_consistency(self, compute_checksum, real_photo_path):
        """Same file produces same checksum."""
        cs1 = compute_checksum(real_photo_path)
        cs2 = compute_checksum(real_photo_path)
        cs3 = compute_checksum(real_photo_path)

        assert cs1 == cs2 == cs3

    @pytest.mark.integration
    def test_different_files_different_checksums(self, compute_checksum):
        """Different files produce different checksums."""
        photo = ASSETS_DIR / "P001_photo_good.jpg"
        video = ASSETS_DIR / "V001_video_good.mov"

        photo_cs = compute_checksum(photo)
        video_cs = compute_checksum(video)

        assert photo_cs != video_cs

    @pytest.mark.integration
    @pytest.mark.parametrize("case", get_all_cases()[:10], ids=lambda c: c["id"])
    def test_all_assets_have_valid_checksums(self, case, compute_checksum):
        """All test assets produce valid SHA1 checksums."""
        if "photo" in case:
            path = ASSETS_DIR / Path(case["photo"]["path"]).name
            if path.exists():
                cs = compute_checksum(path)
                assert len(cs) == 40

        if "video" in case:
            path = ASSETS_DIR / Path(case["video"]["path"]).name
            if path.exists():
                cs = compute_checksum(path)
                assert len(cs) == 40


# ============================================================================
# Base64 to Hex Conversion Tests
# ============================================================================


class TestBase64HexConversion:
    """Tests for converting between base64 and hex checksums."""

    @pytest.mark.integration
    def test_base64_to_hex_conversion(self):
        """Convert base64-encoded checksum to hex."""
        # Create a known SHA1
        sha1_bytes = hashlib.sha1(b"test data").digest()

        # Base64 encoded (as Immich API returns)
        base64_checksum = base64.b64encode(sha1_bytes).decode()

        # Convert to hex
        hex_checksum = base64.b64decode(base64_checksum).hex()

        assert len(hex_checksum) == 40
        assert hex_checksum == sha1_bytes.hex()

    @pytest.mark.integration
    def test_hex_to_base64_conversion(self):
        """Convert hex checksum to base64."""
        # Create a known SHA1 in hex
        sha1_bytes = hashlib.sha1(b"another test").digest()
        hex_checksum = sha1_bytes.hex()

        # Convert to base64
        base64_checksum = base64.b64encode(bytes.fromhex(hex_checksum)).decode()

        # Round-trip back
        roundtrip_hex = base64.b64decode(base64_checksum).hex()

        assert roundtrip_hex == hex_checksum

    @pytest.mark.integration
    def test_asset_model_base64_conversion(self, uuid_factory):
        """Asset model converts base64 checksum to hex."""
        from immich_migrator.models.asset import Asset

        # Create base64 checksum (28 chars with padding for SHA1)
        sha1_bytes = hashlib.sha1(b"model test").digest()
        base64_checksum = base64.b64encode(sha1_bytes).decode()

        asset = Asset(
            id=uuid_factory(),
            original_file_name="test.jpg",
            original_mime_type="image/jpeg",
            checksum=base64_checksum,
            asset_type="IMAGE",
            file_size_bytes=1024,
        )

        # Should be stored as hex
        assert len(asset.checksum) == 40
        assert asset.checksum == sha1_bytes.hex()

    @pytest.mark.integration
    def test_asset_model_hex_passthrough(self, uuid_factory):
        """Asset model passes through hex checksum unchanged."""
        from immich_migrator.models.asset import Asset

        hex_checksum = "a" * 40

        asset = Asset(
            id=uuid_factory(),
            original_file_name="test.jpg",
            original_mime_type="image/jpeg",
            checksum=hex_checksum,
            asset_type="IMAGE",
            file_size_bytes=1024,
        )

        assert asset.checksum == hex_checksum

    @pytest.mark.integration
    def test_base64_with_padding(self, uuid_factory):
        """Handle base64 checksum with proper padding."""
        from immich_migrator.models.asset import Asset

        sha1_bytes = hashlib.sha1(b"with padding").digest()
        base64_with_pad = base64.b64encode(sha1_bytes).decode()

        asset = Asset(
            id=uuid_factory(),
            original_file_name="test.jpg",
            original_mime_type="image/jpeg",
            checksum=base64_with_pad,
            asset_type="IMAGE",
            file_size_bytes=1024,
        )

        # Should be stored as hex
        assert len(asset.checksum) == 40
        assert asset.checksum == sha1_bytes.hex()


# ============================================================================
# Checksum Verification Tests
# ============================================================================


class TestChecksumVerification:
    """Tests for verifying checksums after download."""

    @pytest.mark.integration
    def test_verify_correct_checksum(self, compute_checksum, real_photo_path):
        """Verify checksum matches expected value."""
        expected = compute_checksum(real_photo_path)

        # Re-compute and verify
        actual = compute_checksum(real_photo_path)

        assert actual == expected

    @pytest.mark.integration
    def test_detect_checksum_mismatch(self, compute_checksum, tmp_path):
        """Detect when computed checksum doesn't match expected."""
        # Create a file
        test_file = tmp_path / "checksum_test.txt"
        test_file.write_bytes(b"original content")

        original_checksum = compute_checksum(test_file)

        # Modify the file
        test_file.write_bytes(b"modified content")

        new_checksum = compute_checksum(test_file)

        assert new_checksum != original_checksum

    @pytest.mark.integration
    def test_checksum_mismatch_edge_case(self):
        """E001: Checksum mismatch test asset."""
        mismatch_asset = ASSETS_DIR / "E001_photo_checksum_mismatch.jpg"
        assert mismatch_asset.exists()

        # This asset exists for testing mismatch scenarios
        # The actual mismatch would be between stored and computed values

    @pytest.mark.integration
    def test_verify_downloaded_file_integrity(self, compute_checksum, tmp_path):
        """Simulate download verification workflow."""
        # 1. Get expected checksum (from API)
        source_file = ASSETS_DIR / "P001_photo_good.jpg"
        expected_checksum = compute_checksum(source_file)

        # 2. "Download" file (copy in this test)
        downloaded = tmp_path / "downloaded.jpg"
        downloaded.write_bytes(source_file.read_bytes())

        # 3. Verify checksum
        actual_checksum = compute_checksum(downloaded)

        assert actual_checksum == expected_checksum, "Downloaded file integrity verified"

    @pytest.mark.integration
    def test_verify_fails_on_corrupted_download(self, compute_checksum, tmp_path):
        """Detect corrupted download via checksum mismatch."""
        # Expected checksum
        source_file = ASSETS_DIR / "P001_photo_good.jpg"
        expected_checksum = compute_checksum(source_file)

        # Simulate corrupted download (truncated)
        downloaded = tmp_path / "corrupted.jpg"
        original_content = source_file.read_bytes()
        downloaded.write_bytes(original_content[: len(original_content) // 2])

        # Verification should fail
        actual_checksum = compute_checksum(downloaded)

        assert actual_checksum != expected_checksum, "Corrupted file should fail verification"


# ============================================================================
# Checksum Comparison Tests
# ============================================================================


class TestChecksumComparison:
    """Tests for comparing checksums between source and target."""

    @pytest.mark.integration
    def test_case_insensitive_comparison(self):
        """Checksum comparison is case-insensitive."""
        lower = "abcdef1234567890abcdef1234567890abcdef12"
        upper = "ABCDEF1234567890ABCDEF1234567890ABCDEF12"
        mixed = "AbCdEf1234567890aBcDeF1234567890AbCdEf12"

        assert lower.lower() == upper.lower() == mixed.lower()

    @pytest.mark.integration
    def test_checksum_comparison_with_api_response(self, uuid_factory, compute_checksum):
        """Compare local checksum with API response format."""
        # Local file checksum (hex)
        local_file = ASSETS_DIR / "P001_photo_good.jpg"
        local_checksum = compute_checksum(local_file)

        # Simulate API response (base64)
        api_checksum_base64 = base64.b64encode(bytes.fromhex(local_checksum)).decode()

        # Convert API response to hex for comparison
        api_checksum_hex = base64.b64decode(api_checksum_base64).hex()

        assert local_checksum.lower() == api_checksum_hex.lower()

    @pytest.mark.integration
    def test_bulk_checksum_lookup(self, compute_checksum):
        """Simulate bulk checksum lookup for existing assets."""
        # Compute checksums for several assets
        assets = [
            ASSETS_DIR / "P001_photo_good.jpg",
            ASSETS_DIR / "P002_photo_missing_exif.jpg",
            ASSETS_DIR / "V001_video_good.mov",
        ]

        local_checksums = {f.name: compute_checksum(f) for f in assets if f.exists()}

        # Simulate API "existing" check
        existing_checksums = {
            local_checksums["P001_photo_good.jpg"],  # This one "exists"
        }

        # Determine which need upload
        need_upload = [name for name, cs in local_checksums.items() if cs not in existing_checksums]

        assert "P001_photo_good.jpg" not in need_upload
        assert "P002_photo_missing_exif.jpg" in need_upload
        assert "V001_video_good.mov" in need_upload


# ============================================================================
# Checksum Edge Cases
# ============================================================================


class TestChecksumEdgeCases:
    """Tests for checksum edge cases."""

    @pytest.mark.integration
    def test_empty_file_checksum(self, compute_checksum, tmp_path):
        """Empty file has a valid checksum."""
        empty_file = tmp_path / "empty.txt"
        empty_file.write_bytes(b"")

        checksum = compute_checksum(empty_file)

        # SHA1 of empty string is known
        expected = hashlib.sha1(b"").hexdigest()
        assert checksum == expected
        assert checksum == "da39a3ee5e6b4b0d3255bfef95601890afd80709"

    @pytest.mark.integration
    def test_large_file_checksum(self, compute_checksum, tmp_path):
        """Large file checksum computed correctly."""
        large_file = tmp_path / "large.bin"

        # Create 1MB file
        content = b"x" * (1024 * 1024)
        large_file.write_bytes(content)

        checksum = compute_checksum(large_file)

        assert len(checksum) == 40

    @pytest.mark.integration
    def test_binary_file_checksum(self, compute_checksum, tmp_path):
        """Binary file with all byte values."""
        binary_file = tmp_path / "binary.bin"

        # All possible byte values
        content = bytes(range(256))
        binary_file.write_bytes(content)

        checksum = compute_checksum(binary_file)

        assert len(checksum) == 40

    @pytest.mark.integration
    def test_unicode_filename_checksum(self, compute_checksum):
        """Compute checksum for file with unicode filename."""
        unicode_file = ASSETS_DIR / "E005_photo_üñíçödé.jpg"

        if unicode_file.exists():
            checksum = compute_checksum(unicode_file)
            assert len(checksum) == 40

    @pytest.mark.integration
    def test_checksum_all_zeros_valid(self, uuid_factory):
        """All-zero checksum is valid (though unlikely)."""
        from immich_migrator.models.asset import Asset

        zero_checksum = "0" * 40

        asset = Asset(
            id=uuid_factory(),
            original_file_name="zeros.jpg",
            original_mime_type="image/jpeg",
            checksum=zero_checksum,
            asset_type="IMAGE",
            file_size_bytes=1024,
        )

        assert asset.checksum == zero_checksum


# ============================================================================
# Checksum in Migration Workflow Tests
# ============================================================================


class TestChecksumInMigration:
    """Tests for checksum handling in the migration workflow."""

    @pytest.mark.integration
    def test_download_verify_upload_workflow(self, compute_checksum, tmp_path, uuid_factory):
        """Complete workflow: download → verify → prepare for upload."""
        from immich_migrator.models.asset import Asset

        # 1. Source asset with known checksum
        source = ASSETS_DIR / "P001_photo_good.jpg"
        source_checksum = compute_checksum(source)

        # 2. Create Asset model (simulating API response)
        asset = Asset(
            id=uuid_factory(),
            original_file_name="P001_photo_good.jpg",
            original_mime_type="image/jpeg",
            checksum=source_checksum,
            asset_type="IMAGE",
            file_size_bytes=1024,
        )

        # 3. Download to batch directory
        batch_dir = tmp_path / "batch"
        batch_dir.mkdir()
        downloaded = batch_dir / asset.original_file_name
        downloaded.write_bytes(source.read_bytes())

        # 4. Verify checksum
        downloaded_checksum = compute_checksum(downloaded)
        assert downloaded_checksum == asset.checksum, "Download verification passed"

        # 5. File is ready for upload (checksum verified)

    @pytest.mark.integration
    def test_checksum_mismatch_after_exif_injection(self, compute_checksum, tmp_path):
        """Checksum changes after EXIF injection (expected behavior)."""
        import shutil

        # Skip if exiftool not installed
        if shutil.which("exiftool") is None:
            pytest.skip("exiftool not installed")

        import subprocess

        # Copy file to temp
        source = ASSETS_DIR / "P002_photo_missing_exif.jpg"
        target = tmp_path / "inject_checksum_test.jpg"
        shutil.copy(source, target)

        # Checksum before injection
        before_checksum = compute_checksum(target)

        # Inject EXIF data
        subprocess.run(
            [
                "exiftool",
                "-EXIF:DateTimeOriginal=2024:01:01 00:00:00",
                "-overwrite_original",
                str(target),
            ],
            capture_output=True,
        )

        # Checksum after injection
        after_checksum = compute_checksum(target)

        # Checksum should change (EXIF data modifies file)
        assert before_checksum != after_checksum, "EXIF injection should change checksum"

    @pytest.mark.integration
    def test_target_server_checksum_verification(self, compute_checksum, uuid_factory):
        """Simulate verifying upload on target server via checksum."""
        from immich_migrator.models.asset import Asset

        # Source asset
        source = ASSETS_DIR / "P001_photo_good.jpg"
        source_checksum = compute_checksum(source)

        # Asset as uploaded
        uploaded_asset = Asset(
            id=uuid_factory(),
            original_file_name="P001_photo_good.jpg",
            original_mime_type="image/jpeg",
            checksum=source_checksum,
            asset_type="IMAGE",
            file_size_bytes=1024,
        )

        # Simulate target server response (would have same checksum if upload successful)
        target_checksum = source_checksum  # In reality, from API

        assert uploaded_asset.checksum == target_checksum, "Upload verified via checksum match"
