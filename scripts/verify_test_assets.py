#!/usr/bin/env python3
"""Verify test assets exist and have correct checksums.

This script verifies that all generated test assets exist and match
their expected SHA256 checksums. Use this before running tests to
ensure assets are properly generated.

Usage:
    python scripts/verify_test_assets.py
    # or via justfile:
    just verify-assets
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
ASSETS_DIR = PROJECT_ROOT / "tests" / "assets"

# fmt: off
# Expected checksums for verification (SHA256)
# These must match generate_test_assets.py
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


def verify_assets() -> bool:
    """Verify all test assets exist and have correct checksums.

    Returns:
        True if all assets verified, False otherwise
    """
    print("=" * 60)
    print("Test Asset Verification")
    print("=" * 60)
    print()

    # Check if assets directory exists
    if not ASSETS_DIR.exists():
        print(f"ERROR: Assets directory not found: {ASSETS_DIR}")
        return False

    passed = 0
    failed = 0
    missing = 0

    print("=== Verifying Generated Assets ===")
    for filename, expected in sorted(EXPECTED_CHECKSUMS.items()):
        filepath = ASSETS_DIR / filename
        if not filepath.exists():
            print(f"  ✗ {filename} (MISSING)")
            missing += 1
            continue

        actual = sha256_file(filepath)
        if actual == expected:
            print(f"  ✓ {filename}")
            passed += 1
        else:
            print(f"  ✗ {filename}")
            print(f"      Expected: {expected}")
            print(f"      Actual:   {actual}")
            failed += 1

    print()
    print("=" * 60)
    total = passed + failed + missing
    print(f"Summary: {passed}/{total} passed", end="")
    if failed > 0:
        print(f", {failed} checksum failures", end="")
    if missing > 0:
        print(f", {missing} missing", end="")
    print()
    print("=" * 60)

    if failed > 0 or missing > 0:
        print()
        print("Run 'python scripts/generate_test_assets.py' to regenerate assets.")
        return False

    print()
    print("✓ All assets verified successfully!")
    return True


def main() -> int:
    """Main entry point."""
    success = verify_assets()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
