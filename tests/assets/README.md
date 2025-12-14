# Test Assets Directory

This directory contains 47 generated test assets for comprehensive testing of the Immich Migrator tool.

## Asset Generation

**Base files** (tracked in git):

- `base_photo.jpg` - Stripped JPEG photo (no EXIF metadata)
- `base_video.mov` - Stripped MOV video (no timestamps)
- `base_live_photo.jpg` - Stripped live photo JPEG
- `base_live_video.mov` - Stripped live photo MOV component
- `base_sidecar.xmp` - XMP sidecar file template

**Generated files** (created from base files, gitignored):

- `P001-P004` - Photo variants
- `V001-V004` - Video variants
- `L001-L016` - Live photo pairs (32 files)
- `E001-E006` - Edge cases (7 files)

To generate/regenerate assets:

```bash
python scripts/generate_test_assets.py
# or
just generate-assets
```

To verify assets exist with correct checksums:

```bash
python scripts/verify_test_assets.py
# or
just verify-assets
```

## Asset Categories

### Photo Variants (P001-P004) - 4 files

Tests basic photo handling with different conditions:

- **P001_photo_good.jpg**: Valid JPEG with EXIF date tags (baseline)
- **P002_photo_missing_exif.jpg**: JPEG with all date metadata removed
- **P003_photo_wrong_ext.png**: JPEG file with wrong extension (.png)
- **P004_photo_missing_exif_wrong_ext.png**: JPEG with wrong extension AND missing EXIF

### Video Variants (V001-V004) - 4 files

Tests basic video handling:

- **V001_video_good.mov**: MOV file with QuickTime creation metadata
- **V002_video_missing_exif.mov**: MOV without creation timestamps
- **V003_video_wrong_ext.avi**: MOV file with wrong extension (.avi)
- **V004_video_missing_exif_wrong_ext.mp4**: MOV with wrong extension AND missing metadata

### Live Photo Pairs (L001-L016) - 32 files (16 pairs)

Complete permutation matrix testing all combinations of:

- Photo: missing_exif (yes/no) × wrong_extension (yes/no)
- Video: missing_exif (yes/no) × wrong_extension (yes/no)

Each Lxxx case includes both a photo and video component:

- **L001**: Both good (baseline)
- **L002**: Photo missing EXIF, video good
- **L003**: Photo wrong extension, video good
- **L004**: Photo missing EXIF + wrong extension, video good
- **L005**: Video missing EXIF, photo good
- **L006**: Both missing EXIF
- **L007**: Video wrong extension, photo good
- **L008**: Photo missing EXIF, video wrong extension
- **L009**: Video missing EXIF + wrong extension, photo good
- **L010**: Both missing EXIF + both wrong extensions
- **L011**: Photo wrong extension, video missing EXIF
- **L012**: Photo wrong extension + missing EXIF, video wrong extension
- **L013**: Photo missing EXIF, video wrong extension + missing EXIF
- **L014**: Photo good, video wrong extension + missing EXIF
- **L015**: Photo wrong extension, video good
- **L016**: Photo missing EXIF, video wrong extension + missing EXIF

### Edge Cases (E001-E006) - 7 files

Special scenarios for robustness testing:

- **E001_photo_checksum_mismatch.jpg**: Normal photo (checksum mismatch simulated in tests)
- **E002_photo_corrupted.jpg**: Truncated/corrupted JPEG file (20KB truncated)
- **E003_orphan_live_video.mov**: Live photo video without matching image
- **E004_photo_ünícødé_@_#.jpg**: Filename with special/unicode characters
- **E005_photo_with_sidecar.jpg**: Photo with accompanying XMP sidecar file
- **E005_photo_with_sidecar.xmp**: XMP sidecar containing date metadata
- **E006_photo_exiftool_fail.jpg**: Normal photo (exiftool failure simulated in tests)

## Asset Sources

- **Base photos**: Downloaded from Wikimedia Commons (public domain)
- **Base videos**: Generated using ffmpeg test sources
- **Live photo pair**: User-provided real Apple Live Photo (IMG_2950.HEIC/MOV)

## File Sizes

- Photos: ~46KB each (JPEG), ~20KB (corrupted)
- Videos: ~50-55KB (generated test videos), ~3.2MB (live photo video)
- Total assets directory: ~15MB

## Usage in Tests

All assets are referenced in `tests/assets_matrix_template.yaml` which serves as:

1. Test case documentation
2. Pytest fixture data source
3. Parametrized test inputs

Example pytest fixture usage:

```python
import yaml
import pytest
from pathlib import Path

@pytest.fixture(scope='session')
def assets_matrix():
    p = Path(__file__).parent / 'assets_matrix_template.yaml'
    return yaml.safe_load(p.read_text())['test_cases']

@pytest.mark.parametrize('case', assets_matrix(), ids=lambda c: c['id'])
def test_asset_handling(case):
    # Test logic using case['photo']['path'], case['expected'], etc.
    pass
```

## Maintenance

To update the test asset generation:

1. Modify `scripts/generate_test_assets.py` with new logic
2. Run `python scripts/generate_test_assets.py` to regenerate
3. Update `scripts/verify_test_assets.py` with matching checksums
4. Update `assets_matrix_template.yaml` with any new test cases
5. Verify tests pass: `uv run pytest tests/`

To add new base files:

1. Add stripped versions (no EXIF/timestamps) to `tests/assets/base_*.ext`
2. Update the generator script to use the new base file
3. Commit the base file (generated files are gitignored)

## Notes

- All paths in the YAML are relative to the project root: `tests/assets/filename`
- Assets are generated files, not checked into git (except base files)
- EXIF manipulation done with exiftool 12.76+
- File extension mismatches intentionally test MIME-based normalization logic
- CI workflow generates assets before running tests
