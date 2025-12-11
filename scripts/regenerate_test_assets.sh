#!/bin/bash
# Script to regenerate test assets with correct EXIF states
# This ensures the test matrix matches actual asset metadata

set -e

ASSETS_DIR="$(dirname "$0")/../tests/assets"
cd "$ASSETS_DIR"

echo "=== Regenerating Test Assets ==="
echo "Assets directory: $PWD"

# Check if exiftool is installed
if ! command -v exiftool &> /dev/null; then
    echo "ERROR: exiftool is required but not installed"
    echo "Install: sudo apt-get install libimage-exiftool-perl"
    exit 1
fi

# ==============================================================================
# Helper Functions
# ==============================================================================

# Strip all EXIF/metadata from a file
strip_exif() {
    local file="$1"
    echo "  Stripping EXIF from: $file"
    exiftool -all= -overwrite_original "$file"
}

# Add date EXIF to a photo
add_photo_exif() {
    local file="$1"
    local date="${2:-2024:01:15 10:30:00}"
    echo "  Adding photo EXIF to: $file (date: $date)"
    exiftool \
        -DateTimeOriginal="$date" \
        -CreateDate="$date" \
        -ModifyDate="$date" \
        -overwrite_original "$file"
}

# Add QuickTime metadata to a video
add_video_exif() {
    local file="$1"
    local date="${2:-2024:01:15 10:30:00}"
    echo "  Adding video metadata to: $file (date: $date)"
    exiftool \
        -QuickTime:CreateDate="$date" \
        -QuickTime:ModifyDate="$date" \
        -QuickTime:TrackCreateDate="$date" \
        -QuickTime:TrackModifyDate="$date" \
        -QuickTime:MediaCreateDate="$date" \
        -QuickTime:MediaModifyDate="$date" \
        -overwrite_original "$file"
}

# Verify EXIF presence
has_exif() {
    local file="$1"
    local tag="$2"
    exiftool -s -"$tag" "$file" 2>/dev/null | grep -q "$tag"
}

# Strip video metadata with fallback for read-only QuickTime atoms
# Some QuickTime files have dates in read-only atoms that can't be modified.
# If stripping fails, we copy from V002 which has successfully stripped metadata.
strip_video_with_fallback() {
    local file="$1"

    echo "  Stripping video metadata from: $file"
    strip_exif "$file"

    # Check if dates are actually zeroed (QuickTime stripped files show 0000:00:00)
    local create_date=$(exiftool -s -QuickTime:CreateDate "$file" 2>/dev/null | awk '{print $3}')

    if [ -n "$create_date" ] && [ "$create_date" != "0000:00:00" ]; then
        echo "  WARNING: Could not strip $file (read-only QuickTime atoms), using V002 as base"
        cp "V002_video_missing_exif.mov" "$file"
    fi
}

# ==============================================================================
# Photo-only assets (P001-P004)
# ==============================================================================

echo ""
echo "=== Processing Photo-only Assets ==="

# P001: Good photo (has EXIF, correct extension)
echo "P001: Good photo with EXIF"
add_photo_exif "P001_photo_good.jpg" "2024:01:01 12:00:00"

# P002: Missing EXIF
echo "P002: Photo without EXIF"
strip_exif "P002_photo_missing_exif.jpg"

# P003: Wrong extension (but has EXIF)
# Note: exiftool can't write to files with wrong extension, so we work around it
echo "P003: Photo with wrong extension (.png) but has EXIF"
if [ -f "P003_photo_wrong_ext.png" ]; then
    # Temporarily rename to correct extension, add EXIF, rename back
    mv "P003_photo_wrong_ext.png" "P003_photo_wrong_ext.jpg.tmp"
    add_photo_exif "P003_photo_wrong_ext.jpg.tmp" "2024:01:03 12:00:00"
    mv "P003_photo_wrong_ext.jpg.tmp" "P003_photo_wrong_ext.png"
fi

# P004: Missing EXIF + wrong extension
echo "P004: Photo without EXIF and wrong extension"
if [ -f "P004_photo_missing_exif_wrong_ext.png" ]; then
    mv "P004_photo_missing_exif_wrong_ext.png" "P004_photo_missing_exif_wrong_ext.jpg.tmp"
    strip_exif "P004_photo_missing_exif_wrong_ext.jpg.tmp"
    mv "P004_photo_missing_exif_wrong_ext.jpg.tmp" "P004_photo_missing_exif_wrong_ext.png"
fi

# ==============================================================================
# Video-only assets (V001-V004)
# ==============================================================================

echo ""
echo "=== Processing Video-only Assets ==="

# V001: Good video (has metadata, correct extension)
echo "V001: Good video with metadata"
add_video_exif "V001_video_good.mov" "2024:02:01 14:00:00"

# V002: Missing metadata
echo "V002: Video without metadata"
strip_exif "V002_video_missing_exif.mov"

# V003: Wrong extension (but has metadata)
echo "V003: Video with wrong extension (.avi) but has metadata"
if [ -f "V003_video_wrong_ext.avi" ]; then
    mv "V003_video_wrong_ext.avi" "V003_video_wrong_ext.mov.tmp"
    add_video_exif "V003_video_wrong_ext.mov.tmp" "2024:02:03 14:00:00"
    mv "V003_video_wrong_ext.mov.tmp" "V003_video_wrong_ext.avi"
fi

# V004: Missing metadata + wrong extension
echo "V004: Video without metadata and wrong extension"
if [ -f "V004_video_missing_exif_wrong_ext.mp4" ]; then
    mv "V004_video_missing_exif_wrong_ext.mp4" "V004_video_missing_exif_wrong_ext.mov.tmp"
    strip_exif "V004_video_missing_exif_wrong_ext.mov.tmp"
    mv "V004_video_missing_exif_wrong_ext.mov.tmp" "V004_video_missing_exif_wrong_ext.mp4"
fi

# ==============================================================================
# Live Photo pairs (L001-L016)
# ==============================================================================

echo ""
echo "=== Processing Live Photo Pairs ==="

# L001: Both good (photo has EXIF, video has metadata)
echo "L001: Both components good"
add_photo_exif "L001_live_photo.jpg" "2024:03:01 10:00:00"
add_video_exif "L001_live_video.mov" "2024:03:01 10:00:01"

# L002: Photo missing EXIF, video good
echo "L002: Photo missing EXIF, video good"
strip_exif "L002_live_photo.jpg"
add_video_exif "L002_live_video.mov" "2024:03:02 10:00:00"

# L003: Photo wrong ext (but has EXIF), video good
echo "L003: Photo wrong extension, video good"
if [ -f "L003_live_photo.png" ]; then
    mv "L003_live_photo.png" "L003_live_photo.jpg.tmp"
    add_photo_exif "L003_live_photo.jpg.tmp" "2024:03:03 10:00:00"
    mv "L003_live_photo.jpg.tmp" "L003_live_photo.png"
fi
add_video_exif "L003_live_video.mov" "2024:03:03 10:00:01"

# L004: Photo missing EXIF + wrong ext, video good
echo "L004: Photo missing EXIF + wrong ext, video good"
if [ -f "L004_live_photo.png" ]; then
    mv "L004_live_photo.png" "L004_live_photo.jpg.tmp"
    strip_exif "L004_live_photo.jpg.tmp"
    mv "L004_live_photo.jpg.tmp" "L004_live_photo.png"
fi
add_video_exif "L004_live_video.mov" "2024:03:04 10:00:00"

# L005: Photo good, video missing metadata
echo "L005: Photo good, video missing metadata"
add_photo_exif "L005_live_photo.jpg" "2024:03:05 10:00:00"
strip_exif "L005_live_video.mov"

# L006: Both missing metadata
echo "L006: Both components missing metadata"
strip_exif "L006_live_photo.jpg"
strip_exif "L006_live_video.mov"

# L007: Photo good, video wrong ext (but has metadata)
echo "L007: Photo good, video wrong extension"
add_photo_exif "L007_live_photo.jpg" "2024:03:07 10:00:00"
if [ -f "L007_live_video.avi" ]; then
    mv "L007_live_video.avi" "L007_live_video.mov.tmp"
    add_video_exif "L007_live_video.mov.tmp" "2024:03:07 10:00:01"
    mv "L007_live_video.mov.tmp" "L007_live_video.avi"
fi

# L008: Photo missing EXIF, video wrong ext (but has metadata)
echo "L008: Photo missing EXIF, video wrong extension"
strip_exif "L008_live_photo.jpg"
if [ -f "L008_live_video.mp4" ]; then
    mv "L008_live_video.mp4" "L008_live_video.mov.tmp"
    add_video_exif "L008_live_video.mov.tmp" "2024:03:08 10:00:00"
    mv "L008_live_video.mov.tmp" "L008_live_video.mp4"
fi

# L009: Photo good, video missing metadata + wrong ext
echo "L009: Photo good, video missing metadata + wrong ext"
add_photo_exif "L009_live_photo.jpg" "2024:03:09 10:00:00"
if [ -f "L009_live_video.avi" ]; then
    mv "L009_live_video.avi" "L009_live_video.mov.tmp"
    strip_video_with_fallback "L009_live_video.mov.tmp"
    mv "L009_live_video.mov.tmp" "L009_live_video.avi"
fi

# L010: Both missing metadata + both wrong ext
echo "L010: Both missing metadata + both wrong ext"
if [ -f "L010_live_photo.png" ]; then
    mv "L010_live_photo.png" "L010_live_photo.jpg.tmp"
    strip_exif "L010_live_photo.jpg.tmp"
    mv "L010_live_photo.jpg.tmp" "L010_live_photo.png"
fi
if [ -f "L010_live_video.mp4" ]; then
    mv "L010_live_video.mp4" "L010_live_video.mov.tmp"
    strip_exif "L010_live_video.mov.tmp"
    mv "L010_live_video.mov.tmp" "L010_live_video.mp4"
fi

# L011: Photo wrong ext (but has EXIF), video missing metadata
echo "L011: Photo wrong ext, video missing metadata"
if [ -f "L011_live_photo.png" ]; then
    mv "L011_live_photo.png" "L011_live_photo.jpg.tmp"
    add_photo_exif "L011_live_photo.jpg.tmp" "2024:03:11 10:00:00"
    mv "L011_live_photo.jpg.tmp" "L011_live_photo.png"
fi
strip_exif "L011_live_video.mov"

# L012: Photo wrong ext + missing EXIF, video wrong ext (but has metadata)
echo "L012: Photo wrong ext + missing EXIF, video wrong ext"
if [ -f "L012_live_photo.png" ]; then
    mv "L012_live_photo.png" "L012_live_photo.jpg.tmp"
    strip_exif "L012_live_photo.jpg.tmp"
    mv "L012_live_photo.jpg.tmp" "L012_live_photo.png"
fi
if [ -f "L012_live_video.avi" ]; then
    mv "L012_live_video.avi" "L012_live_video.mov.tmp"
    add_video_exif "L012_live_video.mov.tmp" "2024:03:12 10:00:00"
    mv "L012_live_video.mov.tmp" "L012_live_video.avi"
fi

# L013: Photo missing EXIF, video wrong ext + missing metadata
echo "L013: Photo missing EXIF, video wrong ext + missing metadata"
strip_exif "L013_live_photo.jpg"
if [ -f "L013_live_video.mp4" ]; then
    mv "L013_live_video.mp4" "L013_live_video.mov.tmp"
    strip_exif "L013_live_video.mov.tmp"
    mv "L013_live_video.mov.tmp" "L013_live_video.mp4"
fi

# L014: Photo good, video wrong ext + missing metadata
echo "L014: Photo good, video wrong ext + missing metadata"
add_photo_exif "L014_live_photo.jpg" "2024:03:14 10:00:00"
if [ -f "L014_live_video.avi" ]; then
    mv "L014_live_video.avi" "L014_live_video.mov.tmp"
    strip_video_with_fallback "L014_live_video.mov.tmp"
    mv "L014_live_video.mov.tmp" "L014_live_video.avi"
fi

# L015: Photo wrong ext (but has EXIF), video good
echo "L015: Photo wrong ext, video good"
if [ -f "L015_live_photo.png" ]; then
    mv "L015_live_photo.png" "L015_live_photo.jpg.tmp"
    add_photo_exif "L015_live_photo.jpg.tmp" "2024:03:15 10:00:00"
    mv "L015_live_photo.jpg.tmp" "L015_live_photo.png"
fi
add_video_exif "L015_live_video.mov" "2024:03:15 10:00:01"

# L016: Photo missing EXIF, video wrong ext + missing metadata
echo "L016: Photo missing EXIF, video wrong ext + missing metadata"
strip_exif "L016_live_photo.jpg"
if [ -f "L016_live_video.mp4" ]; then
    mv "L016_live_video.mp4" "L016_live_video.mov.tmp"
    strip_exif "L016_live_video.mov.tmp"
    mv "L016_live_video.mov.tmp" "L016_live_video.mp4"
fi

# ==============================================================================
# Edge case assets (E001-E006)
# ==============================================================================

echo ""
echo "=== Processing Edge Case Assets ==="

# E001: Checksum mismatch (has EXIF)
echo "E001: Photo for checksum mismatch testing"
add_photo_exif "E001_photo_checksum_mismatch.jpg" "2024:04:01 12:00:00"

# E002: Corrupted photo (already corrupted, don't modify)
echo "E002: Corrupted photo (leaving as-is)"
# Don't modify - it's intentionally corrupted

# E003: Orphan live video (has metadata)
echo "E003: Orphan live video"
add_video_exif "E003_orphan_live_video.mov" "2024:04:03 12:00:00"

# E004: Unicode filename (has EXIF)
echo "E004: Photo with unicode filename"
add_photo_exif "E004_photo_ünícødé_@_#.jpg" "2024:04:04 12:00:00"

# E005: Photo with XMP sidecar (strip EXIF from photo)
echo "E005: Photo with XMP sidecar (photo has no EXIF, sidecar has metadata)"
strip_exif "E005_photo_with_sidecar.jpg"
# XMP sidecar already has metadata

# E006: Exiftool failure test (has no EXIF - for testing injection failure)
echo "E006: Photo for exiftool failure testing"
strip_exif "E006_photo_exiftool_fail.jpg"

# ==============================================================================
# Verification
# ==============================================================================

echo ""
echo "=== Verification Summary ==="

verify_photo() {
    local file="$1"
    local should_have_exif="$2"

    if has_exif "$file" "DateTimeOriginal" || has_exif "$file" "CreateDate"; then
        if [ "$should_have_exif" = "yes" ]; then
            echo "✓ $file: Has EXIF (expected)"
        else
            echo "✗ $file: Has EXIF (should be stripped!)"
            return 1
        fi
    else
        if [ "$should_have_exif" = "no" ]; then
            echo "✓ $file: No EXIF (expected)"
        else
            echo "✗ $file: No EXIF (should have it!)"
            return 1
        fi
    fi
}

verify_video() {
    local file="$1"
    local should_have_meta="$2"

    # Check if video has a valid (non-zero) CreateDate
    local create_date=$(exiftool -s -QuickTime:CreateDate "$file" 2>/dev/null | awk '{print $3}')

    if [ -n "$create_date" ] && [ "$create_date" != "0000:00:00" ] && [ "$create_date" != "" ]; then
        if [ "$should_have_meta" = "yes" ]; then
            echo "✓ $file: Has metadata (expected)"
        else
            echo "✗ $file: Has metadata (should be stripped!)"
            return 1
        fi
    else
        if [ "$should_have_meta" = "no" ]; then
            echo "✓ $file: No metadata (expected)"
        else
            echo "✗ $file: No metadata (should have it!)"
            return 1
        fi
    fi
}

# Verify photos
verify_photo "P001_photo_good.jpg" "yes"
verify_photo "P002_photo_missing_exif.jpg" "no"
verify_photo "P003_photo_wrong_ext.png" "yes"
verify_photo "P004_photo_missing_exif_wrong_ext.png" "no"

# Verify videos
verify_video "V001_video_good.mov" "yes"
verify_video "V002_video_missing_exif.mov" "no"
verify_video "V003_video_wrong_ext.avi" "yes"
verify_video "V004_video_missing_exif_wrong_ext.mp4" "no"

# Verify live photos (sample)
verify_photo "L001_live_photo.jpg" "yes"
verify_video "L001_live_video.mov" "yes"
verify_photo "L002_live_photo.jpg" "no"
verify_video "L002_live_video.mov" "yes"
verify_photo "L006_live_photo.jpg" "no"
verify_video "L006_live_video.mov" "no"

echo ""
echo "=== Asset Regeneration Complete ==="
echo "Run tests with: uv run pytest tests/ -v"
