#!/usr/bin/env python3
"""Generate test assets from base files with specific EXIF states.

This script creates 47 test asset variants from a minimal set of base files.
Base files are tracked in git; generated files are gitignored.

Base files required in tests/assets/:
  - base_photo.jpg       (JPEG photo with EXIF data)
  - base_video.mov       (QuickTime video with metadata)
  - base_live_photo.jpg  (JPEG for live photo pairs)
  - base_live_video.mov  (MOV for live photo pairs)
  - base_sidecar.xmp     (XMP sidecar template)

Generated assets:
  - P001-P004: Photo-only variants
  - V001-V004: Video-only variants
  - L001-L016: Live photo pairs (32 files)
  - E001-E006: Edge cases (7 files)

Usage:
    python scripts/generate_test_assets.py
    # or via justfile:
    just generate-assets
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
ASSETS_DIR = PROJECT_ROOT / "tests" / "assets"

# Base files (minimal set tracked in git)
BASE_PHOTO = ASSETS_DIR / "base_photo.jpg"
BASE_VIDEO = ASSETS_DIR / "base_video.mov"
BASE_LIVE_PHOTO = ASSETS_DIR / "base_live_photo.jpg"
BASE_LIVE_VIDEO = ASSETS_DIR / "base_live_video.mov"
BASE_SIDECAR = ASSETS_DIR / "base_sidecar.xmp"

# fmt: off
# Expected checksums for verification (SHA256)
# These are generated from pre-stripped base files with exiftool adding metadata
EXPECTED_CHECKSUMS: dict[str, str] = {
    # Photo-only
    "P001_photo_good.jpg":
        "200703c6ec0179e47794259f23484f0bc7740a46af489153bc3844b71cca79fc",
    "P002_photo_missing_exif.jpg":
        "21cfef36cd8b6ac0934b399bdff5c2c4492dcabac659ceef17be3d0c52dbd69a",
    "P003_photo_wrong_ext.png":
        "959a32efdf482907e069d75048e0e23cb948c51f7a779d71a6372affc2326938",
    "P004_photo_missing_exif_wrong_ext.png":
        "21cfef36cd8b6ac0934b399bdff5c2c4492dcabac659ceef17be3d0c52dbd69a",
    # Video-only
    "V001_video_good.mov":
        "926ad125324266bcc439151ad3794b90a5231be44e2c63b7fe06cf75beb23343",
    "V002_video_missing_exif.mov":
        "9f822797577b16989e4790094222c528c62a41e4ba797dc4d876cb03dedda38d",
    "V003_video_wrong_ext.avi":
        "04bfc765c04a6c4e6ea81af021086a8cffa7e3ed6c35283cb9004cacbe6b18ba",
    "V004_video_missing_exif_wrong_ext.mp4":
        "9f822797577b16989e4790094222c528c62a41e4ba797dc4d876cb03dedda38d",
    # Live photos
    "L001_live_photo.jpg":
        "a02bd258f3173551e576cc66d65f051c204cdd6b1d3c7b4d6a08d0ad31ca45cd",
    "L001_live_video.mov":
        "30f7dc149797933ba346432481e953a40140cbea153b081fba8d58ee9b044ee6",
    "L002_live_photo.jpg":
        "7992add02c82d5265db3d840976ffa7d5fce47eb8982f079f0dc64ef3989e719",
    "L002_live_video.mov":
        "e70e25404a777ce28682b446e87167b1766e21e68968f1427508284d35395a68",
    "L003_live_photo.png":
        "99f162c71e495f2e0799f2582bf6c2f5e1d21acea53e81deb2d51d5a2b9eea68",
    "L003_live_video.mov":
        "08a369ae209c98a3040e2aaa24d01c0b17f1570bb71cf3b3493f966f9925662b",
    "L004_live_photo.png":
        "7992add02c82d5265db3d840976ffa7d5fce47eb8982f079f0dc64ef3989e719",
    "L004_live_video.mov":
        "a5a0f0982ffc5893c7e0c134fa342fb52a5256cb2774aea706416b4a6ab893d5",
    "L005_live_photo.jpg":
        "f8c0bf62f4d818a2e05817787494f16ffe8099c018794af4194593226b42e4a2",
    "L005_live_video.mov":
        "a0c97da99266230f3d930b69512b74edaacf2423d41a18a40b2a4c5cd56bd655",
    "L006_live_photo.jpg":
        "7992add02c82d5265db3d840976ffa7d5fce47eb8982f079f0dc64ef3989e719",
    "L006_live_video.mov":
        "a0c97da99266230f3d930b69512b74edaacf2423d41a18a40b2a4c5cd56bd655",
    "L007_live_photo.jpg":
        "d1f474bcd215309fac2d78289d2914da934eef52fcf79bc2289eb71434914ea8",
    "L007_live_video.avi":
        "a7721c85595af458c1fd72fc7e5ed2010824606cd6bb9fa53921b2c9f2123138",
    "L008_live_photo.jpg":
        "7992add02c82d5265db3d840976ffa7d5fce47eb8982f079f0dc64ef3989e719",
    "L008_live_video.mp4":
        "0bdd0d8b57ba1bdc6c50f87ad961b819c6526891f6c016803a128995bd170db6",
    "L009_live_photo.jpg":
        "7ed73a19bf4c19ce477d3002419ab83ec1c575c62f89539b6e43537434daaa3a",
    "L009_live_video.avi":
        "a0c97da99266230f3d930b69512b74edaacf2423d41a18a40b2a4c5cd56bd655",
    "L010_live_photo.png":
        "7992add02c82d5265db3d840976ffa7d5fce47eb8982f079f0dc64ef3989e719",
    "L010_live_video.mp4":
        "a0c97da99266230f3d930b69512b74edaacf2423d41a18a40b2a4c5cd56bd655",
    "L011_live_photo.png":
        "c276e4ba1a0142231a24cc80bc8c956ee9362bc1d96e914fbbe6428cf1ce4d0d",
    "L011_live_video.mov":
        "a0c97da99266230f3d930b69512b74edaacf2423d41a18a40b2a4c5cd56bd655",
    "L012_live_photo.png":
        "7992add02c82d5265db3d840976ffa7d5fce47eb8982f079f0dc64ef3989e719",
    "L012_live_video.avi":
        "1d0337a1e1f6bc042ff580f81423622fde1c79393b48fa7eb8ffdbcc734a2c43",
    "L013_live_photo.jpg":
        "7992add02c82d5265db3d840976ffa7d5fce47eb8982f079f0dc64ef3989e719",
    "L013_live_video.mp4":
        "a0c97da99266230f3d930b69512b74edaacf2423d41a18a40b2a4c5cd56bd655",
    "L014_live_photo.jpg":
        "bbcbdf2cb7546c46ae2e4b38581956acc8de7f11a4e9b7d1dc32e796ea26193d",
    "L014_live_video.avi":
        "a0c97da99266230f3d930b69512b74edaacf2423d41a18a40b2a4c5cd56bd655",
    "L015_live_photo.png":
        "b4d60682c8a78190920794a878eb6efda1e4c29ae349cf79838c50d9ee04debc",
    "L015_live_video.mov":
        "9147c033c216031c8eeb9136145e73e07526fefd9b44cc5be1fc1f22535b4583",
    "L016_live_photo.jpg":
        "7992add02c82d5265db3d840976ffa7d5fce47eb8982f079f0dc64ef3989e719",
    "L016_live_video.mp4":
        "a0c97da99266230f3d930b69512b74edaacf2423d41a18a40b2a4c5cd56bd655",
    # Edge cases
    "E001_photo_checksum_mismatch.jpg":
        "79311f03aea547e94a5fc14be74bc9ddc8342b97a2c1a89290391c79e79347fc",
    "E002_photo_corrupted.jpg":
        "31c202b82dbda28eb8d4845d005fa6ca5f3286a8e24c9d04614fba4e4ad5b096",
    "E003_orphan_live_video.mov":
        "f641fe551af55860fd390429eccb4abc37ccb98efd4373c156eaab9d68209267",
    "E004_photo_ünícødé_@_#.jpg":
        "ffc548b4db4b879911361dcfb94e2387998afe55c40751ac4dcbdb5afc87a1e0",
    "E005_photo_with_sidecar.jpg":
        "21cfef36cd8b6ac0934b399bdff5c2c4492dcabac659ceef17be3d0c52dbd69a",
    "E005_photo_with_sidecar.xmp":
        "209c3cb1ebfce440055d769f1a73232f193e31f8a7b4921d6f4070beb556dc6d",
    "E006_photo_exiftool_fail.jpg":
        "21cfef36cd8b6ac0934b399bdff5c2c4492dcabac659ceef17be3d0c52dbd69a",
}
# fmt: on


def sha256_file(path: Path) -> str:
    """Compute SHA256 checksum of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def check_exiftool() -> bool:
    """Check if exiftool is available."""
    return shutil.which("exiftool") is not None


def run_exiftool(*args: str) -> subprocess.CompletedProcess[str]:
    """Run exiftool with given arguments."""
    result = subprocess.run(
        ["exiftool", *args],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result


def strip_exif(file_path: Path) -> None:
    """Strip all EXIF/metadata from a file."""
    print(f"  Stripping EXIF: {file_path.name}")
    result = run_exiftool("-all=", "-overwrite_original", str(file_path))
    if result.returncode != 0:
        print(f"    WARNING: {result.stderr.strip()}")


def add_photo_exif(file_path: Path, date: str = "2024:01:15 10:30:00") -> None:
    """Add date EXIF to a photo."""
    print(f"  Adding photo EXIF: {file_path.name} (date: {date})")
    result = run_exiftool(
        f"-DateTimeOriginal={date}",
        f"-CreateDate={date}",
        f"-ModifyDate={date}",
        "-overwrite_original",
        str(file_path),
    )
    if result.returncode != 0:
        print(f"    WARNING: {result.stderr.strip()}")


def add_video_exif(file_path: Path, date: str = "2024:01:15 10:30:00") -> None:
    """Add QuickTime metadata to a video."""
    print(f"  Adding video metadata: {file_path.name} (date: {date})")
    result = run_exiftool(
        f"-QuickTime:CreateDate={date}",
        f"-QuickTime:ModifyDate={date}",
        f"-QuickTime:TrackCreateDate={date}",
        f"-QuickTime:TrackModifyDate={date}",
        f"-QuickTime:MediaCreateDate={date}",
        f"-QuickTime:MediaModifyDate={date}",
        "-overwrite_original",
        str(file_path),
    )
    if result.returncode != 0:
        print(f"    WARNING: {result.stderr.strip()}")


def copy_and_rename(src: Path, dst: Path) -> None:
    """Copy file from src to dst."""
    print(f"  Copying: {src.name} -> {dst.name}")
    shutil.copy2(src, dst)


def process_with_temp_extension(
    file_path: Path,
    correct_ext: str,
    processor: Callable[[Path], None] | Callable[[Path, str], None],
    date: str | None = None,
) -> None:
    """Process a file that has wrong extension by temporarily renaming.

    Some tools (like exiftool) need correct extension to work properly.
    """
    temp_path = file_path.with_suffix(correct_ext + ".tmp")
    file_path.rename(temp_path)
    if date is not None:
        processor(temp_path, date)  # type: ignore[call-arg]
    else:
        processor(temp_path)  # type: ignore[call-arg]
    temp_path.rename(file_path)


def generate_photo_assets() -> None:
    """Generate P001-P004 photo-only assets.

    Base file (base_photo.jpg) is pre-stripped (no EXIF).
    """
    print("\n=== Generating Photo-only Assets (P001-P004) ===")

    # P001: Good photo (has EXIF, correct extension)
    p001 = ASSETS_DIR / "P001_photo_good.jpg"
    copy_and_rename(BASE_PHOTO, p001)
    add_photo_exif(p001, "2024:01:01 12:00:00")

    # P002: Missing EXIF (base is already stripped, just copy)
    p002 = ASSETS_DIR / "P002_photo_missing_exif.jpg"
    copy_and_rename(BASE_PHOTO, p002)
    # No stripping needed - base is already stripped

    # P003: Wrong extension (but has EXIF)
    p003 = ASSETS_DIR / "P003_photo_wrong_ext.png"
    copy_and_rename(BASE_PHOTO, p003)
    process_with_temp_extension(p003, ".jpg", add_photo_exif, "2024:01:03 12:00:00")

    # P004: Missing EXIF + wrong extension (base is already stripped, just copy)
    p004 = ASSETS_DIR / "P004_photo_missing_exif_wrong_ext.png"
    copy_and_rename(BASE_PHOTO, p004)
    # No stripping needed - base is already stripped


def generate_video_assets() -> None:
    """Generate V001-V004 video-only assets.

    Base file (base_video.mov) is pre-stripped (no metadata).
    """
    print("\n=== Generating Video-only Assets (V001-V004) ===")

    # V001: Good video (has metadata, correct extension)
    v001 = ASSETS_DIR / "V001_video_good.mov"
    copy_and_rename(BASE_VIDEO, v001)
    add_video_exif(v001, "2024:02:01 14:00:00")

    # V002: Missing metadata (base is already stripped, just copy)
    v002 = ASSETS_DIR / "V002_video_missing_exif.mov"
    copy_and_rename(BASE_VIDEO, v002)
    # No stripping needed - base is already stripped

    # V003: Wrong extension (but has metadata)
    v003 = ASSETS_DIR / "V003_video_wrong_ext.avi"
    copy_and_rename(BASE_VIDEO, v003)
    process_with_temp_extension(v003, ".mov", add_video_exif, "2024:02:03 14:00:00")

    # V004: Missing metadata + wrong extension (base is already stripped, just copy)
    v004 = ASSETS_DIR / "V004_video_missing_exif_wrong_ext.mp4"
    copy_and_rename(BASE_VIDEO, v004)
    # No stripping needed - base is already stripped


def generate_live_photo_assets() -> None:
    """Generate L001-L016 live photo pair assets.

    Base files (base_live_photo.jpg, base_live_video.mov) are pre-stripped (no EXIF).
    """
    print("\n=== Generating Live Photo Pairs (L001-L016) ===")

    # L001: Both good
    l001_photo = ASSETS_DIR / "L001_live_photo.jpg"
    l001_video = ASSETS_DIR / "L001_live_video.mov"
    copy_and_rename(BASE_LIVE_PHOTO, l001_photo)
    copy_and_rename(BASE_LIVE_VIDEO, l001_video)
    add_photo_exif(l001_photo, "2024:03:01 10:00:00")
    add_video_exif(l001_video, "2024:03:01 10:00:01")

    # L002: Photo missing EXIF, video good (photo base already stripped)
    l002_photo = ASSETS_DIR / "L002_live_photo.jpg"
    l002_video = ASSETS_DIR / "L002_live_video.mov"
    copy_and_rename(BASE_LIVE_PHOTO, l002_photo)
    copy_and_rename(BASE_LIVE_VIDEO, l002_video)
    # No strip needed - base is already stripped
    add_video_exif(l002_video, "2024:03:02 10:00:00")

    # L003: Photo wrong ext, video good
    l003_photo = ASSETS_DIR / "L003_live_photo.png"
    l003_video = ASSETS_DIR / "L003_live_video.mov"
    copy_and_rename(BASE_LIVE_PHOTO, l003_photo)
    copy_and_rename(BASE_LIVE_VIDEO, l003_video)
    process_with_temp_extension(l003_photo, ".jpg", add_photo_exif, "2024:03:03 10:00:00")
    add_video_exif(l003_video, "2024:03:03 10:00:01")

    # L004: Photo missing EXIF + wrong ext, video good (photo base already stripped)
    l004_photo = ASSETS_DIR / "L004_live_photo.png"
    l004_video = ASSETS_DIR / "L004_live_video.mov"
    copy_and_rename(BASE_LIVE_PHOTO, l004_photo)
    copy_and_rename(BASE_LIVE_VIDEO, l004_video)
    # No strip needed - base is already stripped
    add_video_exif(l004_video, "2024:03:04 10:00:00")

    # L005: Photo good, video missing metadata (video base already stripped)
    l005_photo = ASSETS_DIR / "L005_live_photo.jpg"
    l005_video = ASSETS_DIR / "L005_live_video.mov"
    copy_and_rename(BASE_LIVE_PHOTO, l005_photo)
    copy_and_rename(BASE_LIVE_VIDEO, l005_video)
    add_photo_exif(l005_photo, "2024:03:05 10:00:00")
    # No strip needed - base is already stripped

    # L006: Both missing metadata (both bases already stripped)
    l006_photo = ASSETS_DIR / "L006_live_photo.jpg"
    l006_video = ASSETS_DIR / "L006_live_video.mov"
    copy_and_rename(BASE_LIVE_PHOTO, l006_photo)
    copy_and_rename(BASE_LIVE_VIDEO, l006_video)
    # No strip needed - bases are already stripped

    # L007: Photo good, video wrong ext
    l007_photo = ASSETS_DIR / "L007_live_photo.jpg"
    l007_video = ASSETS_DIR / "L007_live_video.avi"
    copy_and_rename(BASE_LIVE_PHOTO, l007_photo)
    copy_and_rename(BASE_LIVE_VIDEO, l007_video)
    add_photo_exif(l007_photo, "2024:03:07 10:00:00")
    process_with_temp_extension(l007_video, ".mov", add_video_exif, "2024:03:07 10:00:01")

    # L008: Photo missing EXIF, video wrong ext (photo base already stripped)
    l008_photo = ASSETS_DIR / "L008_live_photo.jpg"
    l008_video = ASSETS_DIR / "L008_live_video.mp4"
    copy_and_rename(BASE_LIVE_PHOTO, l008_photo)
    copy_and_rename(BASE_LIVE_VIDEO, l008_video)
    # No strip needed - base is already stripped
    process_with_temp_extension(l008_video, ".mov", add_video_exif, "2024:03:08 10:00:00")

    # L009: Photo good, video missing metadata + wrong ext (video base already stripped)
    l009_photo = ASSETS_DIR / "L009_live_photo.jpg"
    l009_video = ASSETS_DIR / "L009_live_video.avi"
    copy_and_rename(BASE_LIVE_PHOTO, l009_photo)
    copy_and_rename(BASE_LIVE_VIDEO, l009_video)
    add_photo_exif(l009_photo, "2024:03:09 10:00:00")
    # No strip needed - base is already stripped

    # L010: Both missing metadata + both wrong ext (both bases already stripped)
    l010_photo = ASSETS_DIR / "L010_live_photo.png"
    l010_video = ASSETS_DIR / "L010_live_video.mp4"
    copy_and_rename(BASE_LIVE_PHOTO, l010_photo)
    copy_and_rename(BASE_LIVE_VIDEO, l010_video)
    # No strip needed - bases are already stripped

    # L011: Photo wrong ext, video missing metadata (video base already stripped)
    l011_photo = ASSETS_DIR / "L011_live_photo.png"
    l011_video = ASSETS_DIR / "L011_live_video.mov"
    copy_and_rename(BASE_LIVE_PHOTO, l011_photo)
    copy_and_rename(BASE_LIVE_VIDEO, l011_video)
    process_with_temp_extension(l011_photo, ".jpg", add_photo_exif, "2024:03:11 10:00:00")
    # No strip needed - base is already stripped

    # L012: Photo wrong ext + missing EXIF, video wrong ext (photo base already stripped)
    l012_photo = ASSETS_DIR / "L012_live_photo.png"
    l012_video = ASSETS_DIR / "L012_live_video.avi"
    copy_and_rename(BASE_LIVE_PHOTO, l012_photo)
    copy_and_rename(BASE_LIVE_VIDEO, l012_video)
    # No strip needed - base is already stripped
    process_with_temp_extension(l012_video, ".mov", add_video_exif, "2024:03:12 10:00:00")

    # L013: Photo missing EXIF, video wrong ext + missing metadata (both bases stripped)
    l013_photo = ASSETS_DIR / "L013_live_photo.jpg"
    l013_video = ASSETS_DIR / "L013_live_video.mp4"
    copy_and_rename(BASE_LIVE_PHOTO, l013_photo)
    copy_and_rename(BASE_LIVE_VIDEO, l013_video)
    # No strip needed - bases are already stripped

    # L014: Photo good, video wrong ext + missing metadata (video base already stripped)
    l014_photo = ASSETS_DIR / "L014_live_photo.jpg"
    l014_video = ASSETS_DIR / "L014_live_video.avi"
    copy_and_rename(BASE_LIVE_PHOTO, l014_photo)
    copy_and_rename(BASE_LIVE_VIDEO, l014_video)
    add_photo_exif(l014_photo, "2024:03:14 10:00:00")
    # No strip needed - base is already stripped

    # L015: Photo wrong ext, video good
    l015_photo = ASSETS_DIR / "L015_live_photo.png"
    l015_video = ASSETS_DIR / "L015_live_video.mov"
    copy_and_rename(BASE_LIVE_PHOTO, l015_photo)
    copy_and_rename(BASE_LIVE_VIDEO, l015_video)
    process_with_temp_extension(l015_photo, ".jpg", add_photo_exif, "2024:03:15 10:00:00")
    add_video_exif(l015_video, "2024:03:15 10:00:01")

    # L016: Photo missing EXIF, video wrong ext + missing metadata (both bases stripped)
    l016_photo = ASSETS_DIR / "L016_live_photo.jpg"
    l016_video = ASSETS_DIR / "L016_live_video.mp4"
    copy_and_rename(BASE_LIVE_PHOTO, l016_photo)
    copy_and_rename(BASE_LIVE_VIDEO, l016_video)
    # No strip needed - bases are already stripped


def generate_edge_case_assets() -> None:
    """Generate E001-E006 edge case assets.

    Base files are pre-stripped (no EXIF).
    """
    print("\n=== Generating Edge Case Assets (E001-E006) ===")

    # E001: Checksum mismatch (has EXIF)
    e001 = ASSETS_DIR / "E001_photo_checksum_mismatch.jpg"
    copy_and_rename(BASE_PHOTO, e001)
    add_photo_exif(e001, "2024:04:01 12:00:00")

    # E002: Corrupted photo (truncate to 20KB)
    e002 = ASSETS_DIR / "E002_photo_corrupted.jpg"
    copy_and_rename(BASE_PHOTO, e002)
    print(f"  Truncating: {e002.name} to 20KB")
    with open(e002, "r+b") as f:
        f.truncate(20 * 1024)

    # E003: Orphan live video (has metadata)
    e003 = ASSETS_DIR / "E003_orphan_live_video.mov"
    copy_and_rename(BASE_LIVE_VIDEO, e003)
    add_video_exif(e003, "2024:04:03 12:00:00")

    # E004: Unicode filename (has EXIF)
    e004 = ASSETS_DIR / "E004_photo_ünícødé_@_#.jpg"
    copy_and_rename(BASE_PHOTO, e004)
    add_photo_exif(e004, "2024:04:04 12:00:00")

    # E005: Photo with XMP sidecar (photo has no EXIF - base already stripped)
    e005_photo = ASSETS_DIR / "E005_photo_with_sidecar.jpg"
    e005_xmp = ASSETS_DIR / "E005_photo_with_sidecar.xmp"
    copy_and_rename(BASE_PHOTO, e005_photo)
    copy_and_rename(BASE_SIDECAR, e005_xmp)
    # No strip needed - base is already stripped

    # E006: Exiftool failure test (no EXIF - base already stripped)
    e006 = ASSETS_DIR / "E006_photo_exiftool_fail.jpg"
    copy_and_rename(BASE_PHOTO, e006)
    # No strip needed - base is already stripped


def clean_generated_assets() -> None:
    """Remove all generated assets before regeneration."""
    print("\n=== Cleaning Generated Assets ===")
    patterns = [
        "P0*.jpg",
        "P0*.png",
        "V0*.mov",
        "V0*.avi",
        "V0*.mp4",
        "L0*.jpg",
        "L0*.png",
        "L0*.mov",
        "L0*.avi",
        "L0*.mp4",
        "E0*.jpg",
        "E0*.mov",
        "E0*.xmp",
    ]
    for pattern in patterns:
        for f in ASSETS_DIR.glob(pattern):
            print(f"  Removing: {f.name}")
            f.unlink()


def verify_base_files() -> bool:
    """Verify all required base files exist."""
    print("\n=== Verifying Base Files ===")
    base_files = [BASE_PHOTO, BASE_VIDEO, BASE_LIVE_PHOTO, BASE_LIVE_VIDEO, BASE_SIDECAR]
    missing: list[Path] = []
    for bf in base_files:
        if bf.exists():
            print(f"  ✓ {bf.name}")
        else:
            print(f"  ✗ {bf.name} (MISSING)")
            missing.append(bf)

    if missing:
        print("\nERROR: Missing base files. Cannot generate assets.")
        print("Required base files:")
        for bf in base_files:
            print(f"  - {bf.name}")
        return False
    return True


def verify_checksums() -> tuple[int, int]:
    """Verify checksums of generated assets."""
    print("\n=== Verifying Checksums ===")
    passed = 0
    failed = 0

    for filename, expected in sorted(EXPECTED_CHECKSUMS.items()):
        file_path = ASSETS_DIR / filename
        if not file_path.exists():
            print(f"  ✗ {filename} (MISSING)")
            failed += 1
            continue

        actual = sha256_file(file_path)
        if actual == expected:
            print(f"  ✓ {filename}")
            passed += 1
        else:
            print(f"  ✗ {filename}")
            print(f"      Expected: {expected}")
            print(f"      Actual:   {actual}")
            failed += 1

    return passed, failed


def main() -> int:
    """Main entry point."""
    print("=" * 60)
    print("Test Asset Generator")
    print("=" * 60)

    # Check exiftool
    if not check_exiftool():
        print("\nERROR: exiftool is not installed.")
        print("Install: sudo apt-get install libimage-exiftool-perl")
        return 1

    # Verify base files
    if not verify_base_files():
        return 1

    # Clean existing generated assets
    clean_generated_assets()

    # Generate all assets
    generate_photo_assets()
    generate_video_assets()
    generate_live_photo_assets()
    generate_edge_case_assets()

    # Verify checksums
    passed, failed = verify_checksums()

    print("\n" + "=" * 60)
    print(f"Summary: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed > 0:
        print("\nWARNING: Some checksums do not match expected values.")
        print("This may indicate changes in exiftool behavior or base files.")
        return 1

    print("\n✓ All assets generated successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
