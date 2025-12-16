"""Downloader service for batch asset downloads with progress tracking."""

import asyncio
import hashlib
from collections.abc import Callable
from pathlib import Path

from ..lib.logging import get_logger
from ..models.asset import Asset
from ..services.immich_client import ImmichClient

logger = get_logger()  # type: ignore[no-untyped-call]


def compute_file_checksum(file_path: Path) -> str:
    """Compute SHA1 checksum of a file.

    Args:
        file_path: Path to file

    Returns:
        SHA1 checksum as lowercase hex string (40 characters)
    """
    sha1 = hashlib.sha1()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha1.update(chunk)
    return sha1.hexdigest()


class Downloader:
    """Handles batched async downloads with checksum verification."""

    def __init__(
        self,
        client: ImmichClient,
        temp_dir: Path,
        max_concurrent: int = 5,
    ):
        """Initialize downloader.

        Args:
            client: Immich API client
            temp_dir: Temporary directory for downloads
            max_concurrent: Maximum concurrent downloads
        """
        self.client = client
        self.temp_dir = temp_dir
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)

        # Ensure temp directory exists
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    async def download_batch(
        self,
        assets: list[Asset],
        batch_dir: Path,
        on_progress: Callable[[int], None] | None = None,
    ) -> tuple[list[Path], list[str]]:
        """Download a batch of assets concurrently.

        Args:
            assets: List of assets to download
            batch_dir: Directory to save downloads
            on_progress: Optional callback for progress updates (bytes downloaded)

        Returns:
            Tuple of (successful_paths, failed_asset_ids)
        """
        batch_dir.mkdir(parents=True, exist_ok=True)

        logger.debug(f"Starting batch download of {len(assets)} assets to {batch_dir}")

        # Pre-detect filename collisions to determine which assets need ID prefix
        filename_counts: dict[str, int] = {}
        for asset in assets:
            filename_counts[asset.original_file_name] = (
                filename_counts.get(asset.original_file_name, 0) + 1
            )

        needs_prefix = {asset.id: filename_counts[asset.original_file_name] > 1 for asset in assets}

        if any(needs_prefix.values()):
            collision_count = sum(1 for v in needs_prefix.values() if v)
            logger.debug(
                f"Detected {collision_count} assets with duplicate filenames, will add ID prefix"
            )

        successful_paths = []
        failed_asset_ids = []

        # Create tasks for concurrent downloads
        tasks = []
        for asset in assets:
            task = self._download_with_retry(asset, batch_dir, needs_prefix[asset.id], on_progress)
            tasks.append(task)

        # Execute downloads concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for asset, result in zip(assets, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to download {asset.original_file_name}: {result}")
                failed_asset_ids.append(asset.id)
            elif result is None:
                failed_asset_ids.append(asset.id)
            else:
                successful_paths.append(result)

        logger.debug(
            f"Batch download complete: {len(successful_paths)} successful, "
            f"{len(failed_asset_ids)} failed"
        )

        return successful_paths, failed_asset_ids  # type: ignore[return-value]

    async def _download_with_retry(
        self,
        asset: Asset,
        batch_dir: Path,
        needs_prefix: bool = False,
        on_progress: Callable[[int], None] | None = None,
        max_retries: int = 3,
    ) -> Path | None:
        """Download single asset with retry logic.

        Args:
            asset: Asset to download
            batch_dir: Directory to save download
            needs_prefix: Whether to add ID prefix to avoid collision
            on_progress: Optional callback for progress updates
            max_retries: Maximum retry attempts

        Returns:
            Path to downloaded file or None on failure
        """
        async with self.semaphore:
            # Only add ID prefix if there are duplicate filenames in this batch
            if needs_prefix:
                dest_path = batch_dir / f"{asset.id}_{asset.original_file_name}"
                logger.debug(f"Using prefixed filename for collision: {dest_path.name}")
            else:
                dest_path = batch_dir / asset.original_file_name

            for attempt in range(max_retries):
                try:
                    # Download asset
                    await self.client.download_asset(asset, dest_path)

                    # Verify checksum
                    if await self._verify_checksum(dest_path, asset.checksum):
                        logger.debug(f"✓ Downloaded and verified: {asset.original_file_name}")
                        # Report progress after successful download
                        if on_progress and asset.file_size_bytes:
                            on_progress(asset.file_size_bytes)
                        return dest_path
                    else:
                        logger.warning(
                            f"Checksum mismatch for {asset.original_file_name}, "
                            f"attempt {attempt + 1}/{max_retries}"
                        )
                        if dest_path.exists():
                            dest_path.unlink()

                except Exception as e:
                    logger.warning(
                        f"Download failed for {asset.original_file_name}: {e}, "
                        f"attempt {attempt + 1}/{max_retries}"
                    )

                    if attempt < max_retries - 1:
                        # Exponential backoff
                        await asyncio.sleep(2**attempt)

            # All retries exhausted
            logger.error(
                f"Failed to download {asset.original_file_name} after {max_retries} attempts"
            )
            return None

    async def _verify_checksum(self, file_path: Path, expected_checksum: str) -> bool:
        """Verify file checksum matches expected SHA1.

        Args:
            file_path: Path to file to verify
            expected_checksum: Expected SHA1 checksum

        Returns:
            True if checksum matches, False otherwise
        """
        sha1 = hashlib.sha1()

        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):
                    sha1.update(chunk)

            actual_checksum = sha1.hexdigest()
            return actual_checksum == expected_checksum

        except Exception as e:
            logger.error(f"Failed to verify checksum for {file_path}: {e}")
            return False

    def cleanup_batch(self, batch_dir: Path) -> None:
        """Delete downloaded batch files.

        Args:
            batch_dir: Directory containing downloaded files
        """
        if not batch_dir.exists():
            return

        try:
            for file_path in batch_dir.iterdir():
                if file_path.is_file():
                    file_path.unlink()

            batch_dir.rmdir()
            logger.debug(f"Cleaned up batch directory: {batch_dir}")

        except Exception as e:
            logger.warning(f"Failed to cleanup batch directory {batch_dir}: {e}")

    def cleanup_all(self) -> None:
        """Clean up all temporary downloads."""
        if not self.temp_dir.exists():
            return

        try:
            for batch_dir in self.temp_dir.iterdir():
                if batch_dir.is_dir():
                    self.cleanup_batch(batch_dir)

            logger.debug(f"Cleaned up temp directory: {self.temp_dir}")

        except Exception as e:
            logger.warning(f"Failed to cleanup temp directory {self.temp_dir}: {e}")
