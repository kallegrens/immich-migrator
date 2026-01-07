"""EXIF metadata injection service for preserving asset dates."""

import json
import subprocess
from datetime import datetime
from enum import Enum
from pathlib import Path

from ..lib.logging import get_logger
from ..lib.progress import ExifMetrics
from ..models.asset import Asset

logger = get_logger()  # type: ignore[no-untyped-call]


class ExifInjectionError(Exception):
    """Raised when EXIF injection fails."""

    pass


class FileType(Enum):
    """File type categories for injection method dispatch."""

    IMAGE = "image"
    VIDEO = "video"  # QuickTime-based (MP4, MOV, M4V, 3GP)
    RIFF = "riff"  # AVI, WEBP
    UNKNOWN = "unknown"


class ExifInjector:
    """Service for injecting date metadata into image/video files using exiftool."""

    # Immich's date tag priority (in order checked)
    IMMICH_DATE_TAGS = [
        "SubSecDateTimeOriginal",
        "SubSecCreateDate",
        "SubSecMediaCreateDate",
        "DateTimeOriginal",
        "CreationDate",
        "CreateDate",
        "MediaCreateDate",
        "DateTimeCreated",
        "GPSDateTime",
        "DateTimeUTC",
    ]

    # File extensions by type
    VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".3gp", ".3g2"}
    RIFF_EXTENSIONS = {".avi", ".webp"}

    def __init__(self) -> None:
        """Initialize ExifInjector and verify exiftool is available."""
        self._verify_exiftool()

    def _verify_exiftool(self) -> None:
        """Verify that exiftool is installed and accessible.

        Raises:
            ExifInjectionError: If exiftool is not available
        """
        try:
            result = subprocess.run(
                ["exiftool", "-ver"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                logger.debug(f"Found exiftool version {version}")
            else:
                raise ExifInjectionError("exiftool not found or not working")
        except FileNotFoundError:
            raise ExifInjectionError(
                "exiftool is not installed. Please install it: https://exiftool.org/install.html"
            )
        except subprocess.TimeoutExpired:
            raise ExifInjectionError("exiftool command timed out")

    def _is_valid_date(self, date_value: str) -> bool:
        """Check if a date value is valid and not a placeholder.

        Args:
            date_value: Date string from EXIF/QuickTime metadata

        Returns:
            True if date is valid, False if it's a zero/placeholder date
        """
        if not date_value:
            return False
        # QuickTime files with stripped metadata show "0000:00:00 00:00:00"
        # Treat this as "no valid date"
        if date_value.startswith("0000:00:00"):
            return False
        return True

    def _has_date_metadata(self, file_path: Path) -> bool:
        """Check if file has any of Immich's priority date EXIF tags.

        Args:
            file_path: Path to image file

        Returns:
            True if any date tag exists, False otherwise

        Raises:
            ExifInjectionError: If exiftool fails to read file
        """
        try:
            # Use exiftool to extract only the date tags we care about
            result = subprocess.run(
                ["exiftool", "-json", "-G"]
                + [f"-{tag}" for tag in self.IMMICH_DATE_TAGS]
                + [str(file_path)],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                raise ExifInjectionError(
                    f"exiftool failed to read {file_path.name}: {result.stderr}"
                )

            data = json.loads(result.stdout)[0]

            # Check if any of the date tags exist and have a valid (non-zero) value
            for tag in self.IMMICH_DATE_TAGS:
                # Tags can appear with different group prefixes (e.g., EXIF:DateTimeOriginal)
                # So we check if any key ends with our tag name
                for key, value in data.items():
                    if key.endswith(tag) and self._is_valid_date(value):
                        logger.debug(f"File {file_path.name} has existing date tag: {key}={value}")
                        return True

            logger.debug(f"File {file_path.name} has no date metadata")
            return False

        except subprocess.TimeoutExpired:
            raise ExifInjectionError(f"exiftool timed out reading {file_path.name}")
        except json.JSONDecodeError as e:
            raise ExifInjectionError(f"Failed to parse exiftool output for {file_path.name}: {e}")

    def _format_datetime_for_exif(self, dt: datetime, include_timezone: bool = False) -> str:
        """Format datetime for EXIF/QuickTime tag.

        Args:
            dt: Datetime to format
            include_timezone: If True and dt has timezone, append offset (e.g., +02:00)

        Returns:
            String in EXIF format: "YYYY:MM:DD HH:MM:SS" or with timezone suffix
        """
        base = dt.strftime("%Y:%m:%d %H:%M:%S")
        if include_timezone and dt.tzinfo is not None:
            # Format timezone as +HH:MM or -HH:MM
            offset = dt.utcoffset()
            if offset is not None:
                total_seconds = int(offset.total_seconds())
                hours, remainder = divmod(abs(total_seconds), 3600)
                minutes = remainder // 60
                sign = "+" if total_seconds >= 0 else "-"
                base = f"{base}{sign}{hours:02d}:{minutes:02d}"
        return base

    def _get_file_type(self, file_path: Path) -> FileType:
        """Determine file type based on extension.

        Args:
            file_path: Path to file

        Returns:
            FileType enum value
        """
        ext = file_path.suffix.lower()
        if ext in self.VIDEO_EXTENSIONS:
            return FileType.VIDEO
        elif ext in self.RIFF_EXTENSIONS:
            return FileType.RIFF
        else:
            return FileType.IMAGE

    def _normalize_file_extension_by_mime(self, file_path: Path) -> Path:
        """Detect file MIME by content and rename suffix if it doesn't match.

        This helps avoid exiftool errors like "Not a valid PNG (looks more like a JPEG)"
        when the file extension doesn't match the actual content.

        Args:
            file_path: Path to file to check and potentially rename

        Returns:
            Path to use for exiftool operations (may be renamed file)
        """
        try:
            proc = subprocess.run(
                ["file", "--brief", "--mime-type", str(file_path)],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if proc.returncode != 0:
                logger.debug(f"file(1) failed for {file_path.name}: {proc.stderr.strip()}")
                return file_path
            mime = proc.stdout.strip()
        except FileNotFoundError:
            logger.debug("file(1) not available, skipping mime-based normalization")
            return file_path
        except subprocess.TimeoutExpired:
            logger.debug("file(1) timed out, skipping mime-based normalization")
            return file_path

        # Map MIME types to preferred extensions
        mime_to_ext = {
            # Images
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/png": ".png",
            "image/heic": ".heic",
            "image/heif": ".heif",
            "image/tiff": ".tif",
            "image/webp": ".webp",
            # Videos
            "video/mp4": ".mp4",
            "video/quicktime": ".mov",
            "video/x-m4v": ".m4v",
            "video/3gpp": ".3gp",
            "video/3gpp2": ".3g2",
            "video/x-msvideo": ".avi",
            "video/webm": ".webm",
        }

        desired_ext = mime_to_ext.get(mime)
        if desired_ext and file_path.suffix.lower() != desired_ext:
            new_path = file_path.with_suffix(desired_ext)
            try:
                file_path.rename(new_path)
                logger.debug(f"Renamed {file_path.name} -> {new_path.name} based on MIME {mime}")
                return new_path
            except Exception as e:
                logger.debug(f"Failed to rename {file_path.name} -> {new_path.name}: {e}")

        return file_path

    def _inject_date_tag(self, file_path: Path, date: datetime) -> None:
        """Inject date tags into file using exiftool.

        Dispatches to appropriate method based on file type:
        - Images: EXIF/XMP/IPTC tags
        - Videos (MP4/MOV): QuickTime tags with timezone
        - RIFF (AVI/WEBP): RIFF-specific or XMP tags

        Args:
            file_path: Path to file
            date: Date to inject

        Raises:
            ExifInjectionError: If all injection attempts fail
        """
        # Normalize file if extension doesn't match content
        work_path = self._normalize_file_extension_by_mime(file_path)

        # Determine file type AFTER normalization (extension may have changed)
        file_type = self._get_file_type(work_path)

        if file_type == FileType.VIDEO:
            self._inject_date_tag_video(work_path, date, file_path.name)
        elif file_type == FileType.RIFF:
            self._inject_date_tag_riff(work_path, date, file_path.name)
        else:
            self._inject_date_tag_image(work_path, date, file_path.name)

    def _inject_date_tag_image(self, work_path: Path, date: datetime, original_name: str) -> None:
        """Inject date tags into image file using EXIF/XMP/IPTC.

        Args:
            work_path: Path to file (possibly renamed)
            date: Date to inject
            original_name: Original filename for error messages

        Raises:
            ExifInjectionError: If all injection attempts fail
        """
        date_str = self._format_datetime_for_exif(date)

        # Prepare candidate write attempts in preferred order
        attempts = [
            (
                [
                    "exiftool",
                    f"-EXIF:CreateDate={date_str}",
                    "-overwrite_original",
                    str(work_path),
                ],
                "EXIF:CreateDate",
            ),
            (
                [
                    "exiftool",
                    f"-XMP:CreateDate={date_str}",
                    "-overwrite_original",
                    str(work_path),
                ],
                "XMP:CreateDate",
            ),
            (
                [
                    "exiftool",
                    f"-IPTC:DateCreated={date.strftime('%Y:%m:%d')}",
                    f"-IPTC:TimeCreated={date.strftime('%H:%M:%S')}",
                    "-overwrite_original",
                    str(work_path),
                ],
                "IPTC:DateCreated/IPTC:TimeCreated",
            ),
        ]

        errors = []
        for cmd, tag_name in attempts:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    logger.debug(f"Injected {tag_name}={date_str} into {work_path.name}")
                    return
                errors.append((tag_name, (result.stderr or result.stdout).strip()))
            except subprocess.TimeoutExpired:
                errors.append((tag_name, "exiftool timed out"))

        # Final attempt: try with -m to ignore minor/malformed-container issues
        try:
            cmd = [
                "exiftool",
                "-m",
                f"-EXIF:CreateDate={date_str}",
                "-overwrite_original",
                str(work_path),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                logger.debug(f"Injected EXIF:CreateDate={date_str} into {work_path.name} using -m")
                return
            errors.append(("EXIF:CreateDate (-m)", (result.stderr or result.stdout).strip()))
        except subprocess.TimeoutExpired:
            errors.append(("EXIF:CreateDate (-m)", "exiftool timed out"))

        # Nothing succeeded
        err_msgs = "; ".join(f"{t}: {e}" for t, e in errors)
        raise ExifInjectionError(
            f"exiftool failed to write any date tag to {original_name}: {err_msgs}"
        )

    def _inject_date_tag_video(self, work_path: Path, date: datetime, original_name: str) -> None:
        """Inject date tags into QuickTime-based video file (MP4/MOV).

        Uses QuickTime tags in Immich's priority order:
        - QuickTime:CreateDate (local time, no timezone)
        - Keys:CreationDate (with timezone if available)
        - QuickTime:MediaCreateDate

        Args:
            work_path: Path to file (possibly renamed)
            date: Date to inject
            original_name: Original filename for error messages

        Raises:
            ExifInjectionError: If all injection attempts fail
        """
        date_str = self._format_datetime_for_exif(date)
        date_str_tz = self._format_datetime_for_exif(date, include_timezone=True)

        # Prepare candidate write attempts in preferred order for QuickTime
        attempts = [
            # QuickTime:CreateDate - most widely recognized, local time
            (
                [
                    "exiftool",
                    f"-QuickTime:CreateDate={date_str}",
                    "-overwrite_original",
                    str(work_path),
                ],
                "QuickTime:CreateDate",
            ),
            # Keys:CreationDate - with timezone, maps to Immich's CreationDate
            (
                [
                    "exiftool",
                    f"-Keys:CreationDate={date_str_tz}",
                    "-overwrite_original",
                    str(work_path),
                ],
                "Keys:CreationDate",
            ),
            # QuickTime:MediaCreateDate - fallback
            (
                [
                    "exiftool",
                    f"-QuickTime:MediaCreateDate={date_str}",
                    "-overwrite_original",
                    str(work_path),
                ],
                "QuickTime:MediaCreateDate",
            ),
        ]

        errors = []
        for cmd, tag_name in attempts:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    logger.debug(f"Injected {tag_name} into {work_path.name}")
                    return
                errors.append((tag_name, (result.stderr or result.stdout).strip()))
            except subprocess.TimeoutExpired:
                errors.append((tag_name, "exiftool timed out"))

        # Final attempt: try with -m to ignore minor errors
        try:
            cmd = [
                "exiftool",
                "-m",
                f"-QuickTime:CreateDate={date_str}",
                "-overwrite_original",
                str(work_path),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                logger.debug(f"Injected QuickTime:CreateDate into {work_path.name} using -m")
                return
            errors.append(("QuickTime:CreateDate (-m)", (result.stderr or result.stdout).strip()))
        except subprocess.TimeoutExpired:
            errors.append(("QuickTime:CreateDate (-m)", "exiftool timed out"))

        # Nothing succeeded
        err_msgs = "; ".join(f"{t}: {e}" for t, e in errors)
        raise ExifInjectionError(
            f"exiftool failed to write any date tag to {original_name}: {err_msgs}"
        )

    def _inject_date_tag_riff(self, work_path: Path, date: datetime, original_name: str) -> None:
        """Inject date tags into RIFF-based file (AVI, WEBP).

        - AVI: Uses RIFF:DateTimeOriginal
        - WEBP: Uses XMP:DateTimeOriginal or XMP:CreateDate

        Args:
            work_path: Path to file (possibly renamed)
            date: Date to inject
            original_name: Original filename for error messages

        Raises:
            ExifInjectionError: If all injection attempts fail
        """
        date_str = self._format_datetime_for_exif(date)
        ext = work_path.suffix.lower()

        if ext == ".avi":
            # AVI uses RIFF tags
            attempts = [
                (
                    [
                        "exiftool",
                        f"-RIFF:DateTimeOriginal={date_str}",
                        "-overwrite_original",
                        str(work_path),
                    ],
                    "RIFF:DateTimeOriginal",
                ),
            ]
        else:
            # WEBP uses XMP
            attempts = [
                (
                    [
                        "exiftool",
                        f"-XMP:DateTimeOriginal={date_str}",
                        "-overwrite_original",
                        str(work_path),
                    ],
                    "XMP:DateTimeOriginal",
                ),
                (
                    [
                        "exiftool",
                        f"-XMP:CreateDate={date_str}",
                        "-overwrite_original",
                        str(work_path),
                    ],
                    "XMP:CreateDate",
                ),
            ]

        errors = []
        for cmd, tag_name in attempts:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    logger.debug(f"Injected {tag_name}={date_str} into {work_path.name}")
                    return
                errors.append((tag_name, (result.stderr or result.stdout).strip()))
            except subprocess.TimeoutExpired:
                errors.append((tag_name, "exiftool timed out"))

        # Final attempt with -m flag
        fallback_tag = "RIFF:DateTimeOriginal" if ext == ".avi" else "XMP:CreateDate"
        try:
            cmd = [
                "exiftool",
                "-m",
                f"-{fallback_tag}={date_str}",
                "-overwrite_original",
                str(work_path),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                logger.debug(f"Injected {fallback_tag}={date_str} into {work_path.name} using -m")
                return
            errors.append((f"{fallback_tag} (-m)", (result.stderr or result.stdout).strip()))
        except subprocess.TimeoutExpired:
            errors.append((f"{fallback_tag} (-m)", "exiftool timed out"))

        # Nothing succeeded
        err_msgs = "; ".join(f"{t}: {e}" for t, e in errors)
        raise ExifInjectionError(
            f"exiftool failed to write any date tag to {original_name}: {err_msgs}"
        )

    def _get_asset_date(self, asset: Asset) -> datetime | None:
        """Get the best available date for an asset.

        Priority:
        1. exif_date_time_original (from exifInfo.dateTimeOriginal)
        2. file_created_at
        3. local_date_time

        Args:
            asset: Asset to get date from

        Returns:
            Datetime if available, None otherwise
        """
        if asset.exif_date_time_original:
            return asset.exif_date_time_original
        if asset.file_created_at:
            return asset.file_created_at
        if asset.local_date_time:
            return asset.local_date_time
        return None

    def inject_dates_for_batch(
        self, assets: list[Asset], downloaded_paths: list[Path]
    ) -> tuple[ExifMetrics, set[str], list[Path], set[str]]:
        """Inject date metadata for downloaded assets that need it.

        Processes each file individually - failures are logged but do not abort the batch.
        Note: File paths may change due to extension normalization.

        Args:
            assets: List of assets that were downloaded
            downloaded_paths: Corresponding list of file paths

        Returns:
            Tuple of (metrics, modified_asset_ids, updated_paths, corrupted_asset_ids) where:
            - metrics: ExifMetrics with injected/skipped/failed counts
            - modified_asset_ids is a set of asset IDs that had EXIF data injected
            - updated_paths is the list of file paths after any renames (same order as input)
            - corrupted_asset_ids is a set of asset IDs that failed due to file corruption
        """
        if len(assets) != len(downloaded_paths):
            raise ValueError(
                f"Asset count ({len(assets)}) doesn't match path count ({len(downloaded_paths)})"
            )

        metrics = ExifMetrics()
        modified_asset_ids = set()
        updated_paths = []
        corrupted_asset_ids = set()

        for asset, file_path in zip(assets, downloaded_paths, strict=True):
            current_path = file_path  # Track current path in case of rename
            try:
                # Check if file already has date metadata
                if self._has_date_metadata(current_path):
                    logger.debug(f"Skipping {current_path.name}: has existing date metadata")
                    metrics.skipped += 1
                    updated_paths.append(current_path)
                    continue

                # Get date from asset
                date = self._get_asset_date(asset)
                if date is None:
                    logger.warning(
                        f"Skipping {current_path.name}: no date available in asset metadata"
                    )
                    metrics.skipped += 1
                    updated_paths.append(current_path)
                    continue

                # Inject date tag (may rename file)
                self._inject_date_tag(current_path, date)
                metrics.injected += 1
                modified_asset_ids.add(asset.id)

                # Check if file was renamed during normalization
                if not current_path.exists():
                    # File was renamed, find the new name
                    parent = current_path.parent

                    # Extract the base name (without ID prefix if present)
                    original_name = current_path.name
                    if "_" in original_name and original_name.split("_", 1)[0]:
                        # File has potential ID prefix (UUID format)
                        parts = original_name.split("_", 1)
                        if len(parts) == 2:
                            # Try with and without prefix
                            base_stem = Path(parts[1]).stem
                        else:
                            base_stem = current_path.stem
                    else:
                        base_stem = current_path.stem

                    # Look for files with matching stem (with or without ID prefix)
                    found = False
                    for potential_path in parent.glob(f"*{base_stem}*"):
                        if potential_path.is_file() and potential_path != current_path:
                            current_path = potential_path
                            logger.debug(f"File renamed to {current_path.name}")
                            found = True
                            break

                    if not found:
                        logger.warning(f"Could not find renamed file for {original_name}")
                        # Remove from modified since we can't find the file for checksum
                        modified_asset_ids.discard(asset.id)
                        metrics.injected -= 1
                        metrics.failed += 1

                updated_paths.append(current_path)

            except ExifInjectionError as e:
                # Check for known corruption patterns
                error_str = str(e)
                if (
                    "Truncated mdat" in error_str
                    or "RIFF format error" in error_str
                    or "Encountered empty null chunk" in error_str
                    or "Processing aborted" in error_str
                    or "Corrupted JPEG" in error_str
                    or "Corrupted" in error_str
                ):
                    logger.warning(f"Skipping corrupted file {current_path.name}: {e}")
                    corrupted_asset_ids.add(asset.id)
                else:
                    logger.warning(f"Failed to inject date into {current_path.name}: {e}")
                metrics.failed += 1
                updated_paths.append(current_path)
                # Continue processing remaining files

            except Exception as e:
                logger.warning(f"Unexpected error processing {current_path.name}: {e}")
                metrics.failed += 1
                updated_paths.append(current_path)
                # Continue processing remaining files

        logger.debug(
            f"EXIF date injection: {metrics.injected} injected, "
            f"{metrics.skipped} skipped, {metrics.failed} failed"
        )
        return metrics, modified_asset_ids, updated_paths, corrupted_asset_ids
