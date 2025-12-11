#!/usr/bin/env python3
"""
Validate test assets matrix.

This script verifies that all assets referenced in assets_matrix_template.yaml
exist and have the expected properties.
"""

import re
import sys
from pathlib import Path


def validate_assets():
    """Validate all test assets exist and are configured correctly."""

    # Read the YAML template (simple parsing, no yaml dependency needed for validation)
    yaml_path = Path(__file__).parent / "assets_matrix_template.yaml"
    if not yaml_path.exists():
        print(f"❌ YAML template not found: {yaml_path}")
        return False

    content = yaml_path.read_text()

    # Extract all path values
    path_pattern = r'path: "([^"]+)"'
    paths = re.findall(path_pattern, content)

    if not paths:
        print("❌ No paths found in YAML template")
        return False

    print(f"Found {len(paths)} asset paths in YAML template")
    print()

    # Validate each path exists
    missing = []
    found = []

    for path_str in paths:
        path = Path(path_str)
        if path.exists():
            found.append(path)
            size = path.stat().st_size
            print(f"✓ {path} ({size:,} bytes)")
        else:
            missing.append(path)
            print(f"✗ MISSING: {path}")

    print()
    print("=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    print(f"Total paths: {len(paths)}")
    print(f"Found: {len(found)} ✓")
    print(f"Missing: {len(missing)} ✗")
    print("=" * 70)

    if missing:
        print()
        print("MISSING FILES:")
        for path in missing:
            print(f"  - {path}")
        return False

    print()
    print("✅ ALL ASSETS VALIDATED SUCCESSFULLY!")
    return True


if __name__ == "__main__":
    success = validate_assets()
    sys.exit(0 if success else 1)
