# Test Assets Matrix Overview

## Dimension Analysis

### Photo-Only Cases (P001-P004)

2D matrix: `missing_exif × wrong_extension`

| ID | Missing EXIF | Wrong Extension | Description |
|----|--------------|-----------------|-------------|
| P001 | ❌ No | ❌ No | Baseline good photo |
| P002 | ✅ Yes | ❌ No | EXIF injection needed |
| P003 | ❌ No | ✅ Yes | Extension normalization needed |
| P004 | ✅ Yes | ✅ Yes | Both injection and normalization |

**Total: 4 cases (2² = 4)**

---

### Video-Only Cases (V001-V004)

2D matrix: `missing_exif × wrong_extension`

| ID | Missing EXIF | Wrong Extension | Description |
|----|--------------|-----------------|-------------|
| V001 | ❌ No | ❌ No | Baseline good video |
| V002 | ✅ Yes | ❌ No | Metadata injection needed |
| V003 | ❌ No | ✅ Yes | Extension normalization needed |
| V004 | ✅ Yes | ✅ Yes | Both injection and normalization |

**Total: 4 cases (2² = 4)**

---

### Live Photo Pairs (L001-L016)

4D matrix: `photo_missing_exif × photo_wrong_ext × video_missing_exif × video_wrong_ext`

| ID | Photo EXIF | Photo Ext | Video EXIF | Video Ext | Description |
|----|------------|-----------|------------|-----------|-------------|
| L001 | ❌ | ❌ | ❌ | ❌ | Both components good (baseline) |
| L002 | ✅ | ❌ | ❌ | ❌ | Photo needs EXIF injection |
| L003 | ❌ | ✅ | ❌ | ❌ | Photo needs extension fix |
| L004 | ✅ | ✅ | ❌ | ❌ | Photo needs both |
| L005 | ❌ | ❌ | ✅ | ❌ | Video needs EXIF injection |
| L006 | ✅ | ❌ | ✅ | ❌ | Both need EXIF injection |
| L007 | ❌ | ❌ | ❌ | ✅ | Video needs extension fix |
| L008 | ✅ | ❌ | ❌ | ✅ | Photo EXIF + video ext |
| L009 | ❌ | ❌ | ✅ | ✅ | Video needs both |
| L010 | ✅ | ✅ | ✅ | ✅ | All 4 issues present |
| L011 | ❌ | ✅ | ✅ | ❌ | Photo ext + video EXIF |
| L012 | ✅ | ✅ | ❌ | ✅ | Photo both + video ext |
| L013 | ✅ | ❌ | ✅ | ✅ | Photo EXIF + video both |
| L014 | ❌ | ❌ | ✅ | ✅ | Video needs both |
| L015 | ❌ | ✅ | ❌ | ❌ | Photo ext only |
| L016 | ✅ | ❌ | ✅ | ✅ | Photo EXIF + video both |

**Total: 16 cases (2⁴ = 16 permutations)**

Legend:

- ✅ = Issue present (missing/wrong)
- ❌ = No issue (present/correct)

---

### Edge Cases (E001-E006)

Special scenarios not part of systematic permutations

| ID | Type | Scenario | Purpose |
|----|------|----------|---------|
| E001 | Photo | Checksum mismatch | Test retry/recovery on download corruption |
| E002 | Photo | Truncated file | Test graceful EXIF injection failure |
| E003 | Video | Orphan live video | Test handling video without pair |
| E004 | Photo | Special chars in filename | Test filesystem edge cases |
| E005 | Photo+XMP | External metadata sidecar | Test sidecar date extraction |
| E006 | Photo | Exiftool failure | Test tool unavailability handling |

**Total: 6 cases (+1 sidecar file)**

---

## Complete Matrix Summary

| Category | Files | Test Cases | Dimensions |
|----------|-------|------------|------------|
| Photos | 4 | 4 | 2D (2×2) |
| Videos | 4 | 4 | 2D (2×2) |
| Live Photos | 32 | 16 | 4D (2×2×2×2) |
| Edge Cases | 7 | 6 | N/A (special) |
| **TOTAL** | **47** | **30** | - |

---

## Coverage Analysis

### What's Tested

✅ **EXIF Date Handling**

- Presence detection
- Injection into photos (EXIF:CreateDate, XMP:CreateDate)
- Injection into videos (QuickTime:CreateDate, MediaCreateDate)
- Checksum recomputation after injection
- Checksum override tracking

✅ **File Extension Normalization**

- MIME type detection
- Extension correction
- Path tracking after rename
- Extension preservation after EXIF injection

✅ **Live Photo Management**

- Image+video pairing
- Batch reordering for adjacency
- State tracking for pairs
- Linking on destination server
- Orphan handling (video without image)

✅ **Error Scenarios**

- Download checksum verification
- Retry logic (network failures)
- Corrupted file handling
- Tool availability (exiftool)
- Special character filenames
- External metadata sources (XMP)

✅ **State Management**

- Progress tracking per album
- Resume from interruption
- Failed asset tracking
- Verification state persistence

### What's NOT Tested (Mocked in Unit Tests)

These require mocking as they depend on external servers:

🔶 **Immich API Interactions**

- Album listing (mocked with fixture data)
- Asset download (return local test assets)
- Upload verification (bulk-upload-check)
- Live photo linking API
- Unalbummed asset search

🔶 **Immich CLI**

- Upload subprocess (mock with success/failure)
- Availability check
- Connection test

🔶 **Network Failures**

- Timeout handling (simulated with mock delays)
- Rate limiting (simulated with mock throttling)
- Retry exponential backoff (verify call counts)

---

## Test Data Integrity

All assets are **real files** with actual:

- JPEG/PNG image data (downloaded from public sources)
- MOV/MP4 video data (ffmpeg-generated or real Live Photo)
- Valid/invalid EXIF metadata (manipulated with exiftool)
- Correct/incorrect file extensions (intentional mismatches)
- Corrupted data (intentionally truncated)

This ensures tests catch **real-world issues** that might be missed with synthetic mocks.

---

## Usage in Tests

```python
import pytest
import yaml
from pathlib import Path

@pytest.fixture(scope='session')
def assets_matrix():
    """Load test asset matrix from YAML."""
    yaml_path = Path(__file__).parent / 'assets_matrix_template.yaml'
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    return data['test_cases']

# Parametrize over all test cases
@pytest.mark.parametrize('case', assets_matrix(), ids=lambda c: c['id'])
def test_asset_handling(case):
    asset_type = case['type']  # 'photo', 'video', 'live_photo'

    if asset_type == 'photo':
        photo_path = Path(case['photo']['path'])
        assert photo_path.exists()
        # Test photo handling...

    elif asset_type == 'live_photo':
        photo_path = Path(case['photo']['path'])
        video_path = Path(case['video']['path'])
        # Test live photo pair handling...

# Filter by category
@pytest.mark.parametrize(
    'case',
    [c for c in assets_matrix() if c['id'].startswith('L')],
    ids=lambda c: c['id']
)
def test_live_photos_only(case):
    # Test only live photo cases...
    pass
```

---

## Maintenance

To add new test cases:

1. Create asset file(s) in `tests/assets/`
2. Manipulate with exiftool/dd/etc. as needed
3. Add entry to `assets_matrix_template.yaml`
4. Run `python tests/validate_assets.py` to verify
5. Update this overview document with new dimensions

To regenerate all assets:

- See `tests/assets/README.md` for manipulation commands
- Original sources documented in README
- Live photo from user's real device preserved as base
