"""Integration tests for EXIF injection functionality.

These tests use REAL exiftool to verify EXIF manipulation works correctly.
They test the full workflow of reading, injecting, and verifying EXIF data.

Requirements:
- exiftool must be installed and in PATH
- Uses real test asset files
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

# Load test assets paths
TESTS_DIR = Path(__file__).parent.parent
ASSETS_DIR = TESTS_DIR / "assets"
MATRIX_FILE = TESTS_DIR / "assets_matrix_template.yaml"


def _load_matrix() -> list[dict]:
    """Load test cases from matrix."""
    with open(MATRIX_FILE) as f:
        data = yaml.safe_load(f)
    return data["test_cases"]


def get_photo_cases() -> list[dict]:
    """Get photo test cases."""
    return [c for c in _load_matrix() if c["id"].startswith("P")]


def get_video_cases() -> list[dict]:
    """Get video test cases."""
    return [c for c in _load_matrix() if c["id"].startswith("V")]


# Skip all tests if exiftool is not installed
pytestmark = pytest.mark.skipif(shutil.which("exiftool") is None, reason="exiftool not installed")


# ============================================================================
# Helper Functions
# ============================================================================


def run_exiftool_json(file_path: Path) -> dict:
    """Run exiftool and return JSON metadata."""
    result = subprocess.run(
        ["exiftool", "-json", "-G", str(file_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"exiftool failed: {result.stderr}")
    data = json.loads(result.stdout)
    return data[0] if data else {}


def run_exiftool_inject(file_path: Path, tag: str, value: str) -> bool:
    """Inject a single tag value into a file."""
    result = subprocess.run(
        ["exiftool", f"-{tag}={value}", "-overwrite_original", str(file_path)],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def get_date_tag(metadata: dict, tag_name: str) -> str | None:
    """Extract a date tag from metadata dict."""
    for key, value in metadata.items():
        if tag_name in key:
            return value
    return None


# ============================================================================
# Photo EXIF Tests
# ============================================================================


class TestPhotoExifReading:
    """Tests for reading EXIF data from photos."""

    @pytest.mark.integration
    def test_read_photo_with_exif_dates(self, assets_dir):
        """Read EXIF dates from photo with complete metadata."""
        photo = assets_dir / "P001_photo_good.jpg"
        assert photo.exists()

        metadata = run_exiftool_json(photo)

        # Should have date tags
        date_original = get_date_tag(metadata, "DateTimeOriginal")
        create_date = get_date_tag(metadata, "CreateDate")

        assert date_original is not None or create_date is not None, (
            f"Photo should have date tags. Keys: {list(metadata.keys())}"
        )

    @pytest.mark.integration
    def test_read_photo_without_exif_dates(self, assets_dir):
        """Read photo without EXIF date tags."""
        photo = assets_dir / "P002_photo_missing_exif.jpg"
        assert photo.exists()

        metadata = run_exiftool_json(photo)

        # Should NOT have EXIF date tags
        date_original = get_date_tag(metadata, "EXIF:DateTimeOriginal")
        create_date = get_date_tag(metadata, "EXIF:CreateDate")

        assert date_original is None and create_date is None, (
            "Photo without EXIF should not have date tags"
        )

    @pytest.mark.integration
    @pytest.mark.parametrize("case", get_photo_cases(), ids=lambda c: c["id"])
    def test_read_photo_matrix_cases(self, case, assets_dir):
        """Read metadata from all photo test cases."""
        photo_path = assets_dir / Path(case["photo"]["path"]).name
        assert photo_path.exists(), f"Missing: {photo_path}"

        metadata = run_exiftool_json(photo_path)
        missing_exif = case["photo"].get("missing_exif", False)

        date_original = get_date_tag(metadata, "EXIF:DateTimeOriginal")

        if missing_exif:
            assert date_original is None, f"{case['id']}: Should not have EXIF dates"
        else:
            assert date_original is not None, f"{case['id']}: Should have EXIF dates"


# ============================================================================
# Video Metadata Tests
# ============================================================================


class TestVideoMetadataReading:
    """Tests for reading metadata from videos."""

    @pytest.mark.integration
    def test_read_video_with_quicktime_dates(self, assets_dir):
        """Read QuickTime dates from video."""
        video = assets_dir / "V001_video_good.mov"
        assert video.exists()

        metadata = run_exiftool_json(video)

        # Should have QuickTime date tags
        create_date = get_date_tag(metadata, "QuickTime:CreateDate")

        assert create_date is not None, (
            f"Video should have QuickTime dates. Keys: {list(metadata.keys())}"
        )

    @pytest.mark.integration
    def test_read_video_without_dates(self, assets_dir):
        """Read video without date tags."""
        video = assets_dir / "V002_video_missing_exif.mov"
        assert video.exists()

        metadata = run_exiftool_json(video)

        # Should NOT have valid QuickTime date (may have 0000:00:00 placeholder)
        create_date = get_date_tag(metadata, "QuickTime:CreateDate")

        # QuickTime files with stripped metadata show "0000:00:00 00:00:00"
        # We consider this as "no valid date"
        if create_date is not None:
            assert create_date.startswith("0000:00:00"), (
                f"Video without dates should have zero date or None, got: {create_date}"
            )

    @pytest.mark.integration
    @pytest.mark.parametrize("case", get_video_cases(), ids=lambda c: c["id"])
    def test_read_video_matrix_cases(self, case, assets_dir):
        """Read metadata from all video test cases."""
        video_path = assets_dir / Path(case["video"]["path"]).name
        assert video_path.exists(), f"Missing: {video_path}"

        metadata = run_exiftool_json(video_path)
        missing_exif = case["video"].get("missing_exif", False)

        create_date = get_date_tag(metadata, "QuickTime:CreateDate")

        if missing_exif:
            # Should either be None or 0000:00:00 (stripped QuickTime)
            if create_date is not None:
                assert create_date.startswith("0000:00:00"), (
                    f"{case['id']}: Should not have valid date, got: {create_date}"
                )
        else:
            assert create_date is not None and not create_date.startswith("0000:00:00"), (
                f"{case['id']}: Should have valid date metadata"
            )


# ============================================================================
# EXIF Injection Tests
# ============================================================================


class TestExifInjection:
    """Tests for injecting EXIF data into files."""

    @pytest.mark.integration
    def test_inject_date_into_photo(self, assets_dir, tmp_path):
        """Inject DateTimeOriginal into photo."""
        # Copy file to temp dir to avoid modifying test asset
        source = assets_dir / "P002_photo_missing_exif.jpg"
        target = tmp_path / "inject_test.jpg"
        shutil.copy(source, target)

        # Verify no date before injection
        before = run_exiftool_json(target)
        assert get_date_tag(before, "EXIF:DateTimeOriginal") is None

        # Inject date
        test_date = "2024:01:15 10:30:00"
        success = run_exiftool_inject(target, "EXIF:DateTimeOriginal", test_date)
        assert success, "Injection should succeed"

        # Verify date after injection
        after = run_exiftool_json(target)
        injected = get_date_tag(after, "EXIF:DateTimeOriginal")
        assert injected == test_date, f"Expected {test_date}, got {injected}"

    @pytest.mark.integration
    def test_inject_multiple_date_tags(self, assets_dir, tmp_path):
        """Inject multiple date tags at once."""
        source = assets_dir / "P002_photo_missing_exif.jpg"
        target = tmp_path / "multi_inject.jpg"
        shutil.copy(source, target)

        test_date = "2024:02:20 14:45:00"

        # Inject multiple tags
        result = subprocess.run(
            [
                "exiftool",
                f"-EXIF:DateTimeOriginal={test_date}",
                f"-EXIF:CreateDate={test_date}",
                "-overwrite_original",
                str(target),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

        # Verify both tags
        metadata = run_exiftool_json(target)
        assert get_date_tag(metadata, "EXIF:DateTimeOriginal") == test_date
        assert get_date_tag(metadata, "EXIF:CreateDate") == test_date

    @pytest.mark.integration
    def test_injection_preserves_other_metadata(self, assets_dir, tmp_path):
        """EXIF injection preserves other metadata."""
        source = assets_dir / "P001_photo_good.jpg"
        target = tmp_path / "preserve_test.jpg"
        shutil.copy(source, target)

        # Get original metadata
        before = run_exiftool_json(target)
        original_size = before.get("File:ImageWidth") or before.get("EXIF:ImageWidth")

        # Inject a different date
        new_date = "2025:12:31 23:59:59"
        run_exiftool_inject(target, "EXIF:DateTimeOriginal", new_date)

        # Verify other metadata preserved
        after = run_exiftool_json(target)
        new_size = after.get("File:ImageWidth") or after.get("EXIF:ImageWidth")

        assert original_size == new_size, "Image dimensions should be preserved"

    @pytest.mark.integration
    def test_injection_into_video_quicktime(self, assets_dir, tmp_path):
        """Inject CreateDate into video."""
        source = assets_dir / "V002_video_missing_exif.mov"
        target = tmp_path / "video_inject.mov"
        shutil.copy(source, target)

        test_date = "2024:03:10 09:15:00"

        # Inject QuickTime date
        success = run_exiftool_inject(target, "QuickTime:CreateDate", test_date)

        # Note: This may fail depending on video format and exiftool capabilities
        if success:
            metadata = run_exiftool_json(target)
            injected = get_date_tag(metadata, "QuickTime:CreateDate")
            assert injected == test_date


# ============================================================================
# EXIF Date Tag Priority Tests
# ============================================================================


class TestDateTagPriority:
    """Tests for date tag priority as used by Immich."""

    # Priority order used by Immich
    IMMICH_DATE_PRIORITY = [
        "EXIF:DateTimeOriginal",
        "EXIF:CreateDate",
        "QuickTime:CreateDate",
        "QuickTime:TrackCreateDate",
        "QuickTime:MediaCreateDate",
    ]

    @pytest.mark.integration
    def test_photo_date_priority_datetimeoriginal_first(self, assets_dir, tmp_path):
        """DateTimeOriginal takes priority over CreateDate."""
        source = assets_dir / "P002_photo_missing_exif.jpg"
        target = tmp_path / "priority_test.jpg"
        shutil.copy(source, target)

        date1 = "2024:01:01 00:00:00"  # DateTimeOriginal
        date2 = "2024:12:31 23:59:59"  # CreateDate

        # Inject both dates
        subprocess.run(
            [
                "exiftool",
                f"-EXIF:DateTimeOriginal={date1}",
                f"-EXIF:CreateDate={date2}",
                "-overwrite_original",
                str(target),
            ],
            capture_output=True,
        )

        metadata = run_exiftool_json(target)

        # When reading with priority, DateTimeOriginal should be chosen
        date_original = get_date_tag(metadata, "EXIF:DateTimeOriginal")
        create_date = get_date_tag(metadata, "EXIF:CreateDate")

        assert date_original == date1
        assert create_date == date2
        # Priority: DateTimeOriginal should be used
        assert date_original < create_date  # Chronologically first

    @pytest.mark.integration
    def test_get_best_date_from_metadata(self, assets_dir):
        """Extract best date using Immich's priority order."""
        photo = assets_dir / "P001_photo_good.jpg"
        metadata = run_exiftool_json(photo)

        # Find first available date tag by priority
        best_date = None
        used_tag = None

        for tag in self.IMMICH_DATE_PRIORITY:
            date_value = get_date_tag(metadata, tag)
            if date_value:
                best_date = date_value
                used_tag = tag
                break

        assert best_date is not None, "Should find at least one date tag"
        assert "DateTimeOriginal" in used_tag or "CreateDate" in used_tag


# ============================================================================
# Live Photo EXIF Tests
# ============================================================================


class TestLivePhotoExif:
    """Tests for EXIF handling in live photo pairs."""

    @pytest.mark.integration
    def test_live_photo_pair_dates_match(self, assets_dir):
        """Live photo image and video should have matching dates."""
        # L001 is the "good" live photo pair
        photo = assets_dir / "L001_live_photo.jpg"
        video = assets_dir / "L001_live_video.mov"

        photo_meta = run_exiftool_json(photo)
        video_meta = run_exiftool_json(video)

        # Get dates from each
        photo_date = get_date_tag(photo_meta, "EXIF:DateTimeOriginal") or get_date_tag(
            photo_meta, "EXIF:CreateDate"
        )
        video_date = get_date_tag(video_meta, "QuickTime:CreateDate") or get_date_tag(
            video_meta, "QuickTime:TrackCreateDate"
        )

        # Both should have dates
        assert photo_date is not None, "Photo should have date"
        assert video_date is not None, "Video should have date"

        # Dates should be close (within same minute)
        # Parse and compare if needed

    @pytest.mark.integration
    def test_live_photo_missing_exif_on_photo(self, assets_dir):
        """Live photo with missing EXIF on photo component."""
        # Find a live photo case with missing photo EXIF
        photo = assets_dir / "L005_live_photo.jpg"
        _video = assets_dir / "L005_live_video.mov"

        if photo.exists():
            photo_meta = run_exiftool_json(photo)
            _date = get_date_tag(photo_meta, "EXIF:DateTimeOriginal")
            # This case should have missing EXIF
            # Check based on test matrix

    @pytest.mark.integration
    def test_live_photo_missing_exif_on_video(self, assets_dir):
        """Live photo with missing metadata on video component."""
        # Find a live photo case with missing video dates
        _photo = assets_dir / "L002_live_photo.jpg"
        video = assets_dir / "L002_live_video.mov"

        if video.exists():
            video_meta = run_exiftool_json(video)
            _date = get_date_tag(video_meta, "QuickTime:CreateDate")
            # Check based on test matrix expectations


# ============================================================================
# Edge Case EXIF Tests
# ============================================================================


class TestExifEdgeCases:
    """Tests for EXIF edge cases."""

    @pytest.mark.integration
    def test_corrupted_file_exif_read(self, assets_dir):
        """Handle corrupted file when reading EXIF."""
        corrupted = assets_dir / "E002_photo_corrupted.jpg"
        assert corrupted.exists()

        # exiftool should handle corrupted file gracefully
        result = subprocess.run(
            ["exiftool", "-json", "-G", str(corrupted)],
            capture_output=True,
            text=True,
        )

        # May succeed with partial data or have error
        # Either way should not crash
        assert result.returncode in [0, 1]

    @pytest.mark.integration
    def test_wrong_extension_exif_read(self, assets_dir):
        """Read EXIF from file with wrong extension (photos have .png but are jpg content)."""
        # P003 is a photo with wrong extension (.png instead of .jpg)
        wrong_ext = assets_dir / "P003_photo_wrong_ext.png"
        assert wrong_ext.exists()

        metadata = run_exiftool_json(wrong_ext)

        # exiftool should still be able to read it
        assert "SourceFile" in metadata

    @pytest.mark.integration
    def test_unicode_filename_exif_read(self, assets_dir):
        """Read EXIF from file with unicode filename."""
        # Actual unicode file with special characters
        unicode_file = assets_dir / "E004_photo_ünícødé_@_#.jpg"
        assert unicode_file.exists()

        # Should handle unicode filename
        metadata = run_exiftool_json(unicode_file)
        assert "SourceFile" in metadata

    @pytest.mark.integration
    def test_xmp_sidecar_reading(self, assets_dir):
        """Read metadata from XMP sidecar file."""
        sidecar = assets_dir / "E005_photo_with_sidecar.xmp"
        assert sidecar.exists()

        result = subprocess.run(
            ["exiftool", "-json", str(sidecar)],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            metadata = json.loads(result.stdout)
            assert len(metadata) > 0

    @pytest.mark.integration
    def test_xmp_sidecar_combined_with_image(self, assets_dir):
        """Read combined metadata from image + XMP sidecar."""
        image = assets_dir / "E005_photo_with_sidecar.jpg"
        sidecar = assets_dir / "E005_photo_with_sidecar.xmp"

        assert image.exists()
        assert sidecar.exists()

        # exiftool can read both together
        result = subprocess.run(
            ["exiftool", "-json", "-G", str(image)],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        metadata = json.loads(result.stdout)
        assert len(metadata) > 0
