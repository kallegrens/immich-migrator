"""Uploader service using official Immich CLI."""

import os
import subprocess
from pathlib import Path

import httpx

from ..lib.logging import get_logger
from ..lib.progress import LivePhotoMetrics
from ..models.asset import Asset
from ..models.state import LivePhotoPair

logger = get_logger()


class Uploader:
    """Handles asset uploads using official Immich CLI tool."""

    def __init__(self, server_url: str, api_key: str):
        """Initialize uploader.

        Args:
            server_url: New Immich server URL
            api_key: New Immich server API key

        Raises:
            RuntimeError: If Immich CLI is not available
        """
        self.server_url = server_url.rstrip("/")  # Remove trailing slash
        self.api_key = api_key

        # Check Immich CLI availability
        if not self._check_immich_cli():
            raise RuntimeError("Immich CLI not found. Please install: npm install -g @immich/cli")

        logger.debug("Immich CLI detected and ready")

    def _check_immich_cli(self) -> bool:
        """Check if Immich CLI is installed and available.

        Returns:
            True if Immich CLI is available, False otherwise
        """
        try:
            result = subprocess.run(
                ["immich", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def upload_batch(
        self,
        batch_dir: Path,
        album_name: str | None = None,
    ) -> bool:
        """Upload batch of assets using Immich CLI.

        Args:
            batch_dir: Directory containing assets to upload
            album_name: Optional album name for uploads

        Returns:
            True if upload successful, False otherwise
        """
        if not batch_dir.exists() or not batch_dir.is_dir():
            logger.error(f"Batch directory does not exist: {batch_dir}")
            return False

        logger.debug(f"Uploading batch from {batch_dir} to {self.server_url}")

        # Prepare environment variables for Immich CLI
        env = os.environ.copy()
        env["IMMICH_INSTANCE_URL"] = self.server_url
        env["IMMICH_API_KEY"] = self.api_key

        # Build command
        cmd = ["immich", "upload", str(batch_dir), "--recursive"]

        if album_name:
            cmd.extend(["--album-name", album_name])

        try:
            # Execute upload
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
            )

            if result.returncode == 0:
                logger.debug("Batch uploaded successfully")
                logger.debug(f"Upload output: {result.stdout}")
                return True
            else:
                logger.error(f"Upload failed with exit code {result.returncode}")
                logger.error(f"Upload stderr: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"Upload timed out for batch {batch_dir}")
            return False

        except Exception as e:
            logger.error(f"Upload failed with exception: {e}")
            return False

    def test_connection(self) -> bool:
        """Test connection to Immich server using CLI.

        Returns:
            True if connection successful, False otherwise
        """
        env = os.environ.copy()
        env["IMMICH_INSTANCE_URL"] = self.server_url
        env["IMMICH_API_KEY"] = self.api_key

        try:
            result = subprocess.run(
                ["immich", "server-info"],
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                logger.debug("✓ Immich CLI connection test successful")
                return True
            else:
                logger.error(f"Immich CLI connection test failed: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Immich CLI connection test failed: {e}")
            return False

    def link_live_photos(
        self,
        live_photo_pairs: list[tuple[Asset, Asset]],
    ) -> tuple[int, int]:
        """Link live photo images to their video counterparts on destination server.

        After CLI upload, we need to find the uploaded assets by checksum and
        link them via the API. This establishes the live photo relationship.

        Args:
            live_photo_pairs: List of (image_asset, video_asset) pairs from source

        Returns:
            Tuple of (successful_links, failed_links)
        """
        if not live_photo_pairs:
            return 0, 0

        logger.debug(f"Linking {len(live_photo_pairs)} live photo pairs")
        successful = 0
        failed = 0

        for image_asset, video_asset in live_photo_pairs:
            try:
                # Find assets on destination by checksum
                dest_image_id = self._find_asset_by_checksum(image_asset.checksum)
                dest_video_id = self._find_asset_by_checksum(video_asset.checksum)

                if not dest_image_id:
                    logger.warning(
                        f"Could not find uploaded image for {image_asset.original_file_name}"
                    )
                    failed += 1
                    continue

                if not dest_video_id:
                    logger.warning(
                        f"Could not find uploaded video for {video_asset.original_file_name}"
                    )
                    failed += 1
                    continue

                # Link the live photo
                if self._link_live_photo_pair(dest_image_id, dest_video_id):
                    logger.debug(
                        f"Linked live photo: {image_asset.original_file_name} -> "
                        f"{video_asset.original_file_name}"
                    )
                    successful += 1
                else:
                    failed += 1

            except Exception as e:
                logger.error(f"Failed to link live photo {image_asset.original_file_name}: {e}")
                failed += 1

        logger.debug(f"Live photo linking complete: {successful} linked, {failed} failed")
        return successful, failed

    def verify_assets_exist(
        self,
        assets: list[Asset],
        checksum_overrides: dict[str, str] | None = None,
    ) -> tuple[list[str], list[str]]:
        """Verify which assets exist on the destination server by checksum.

        Uses the bulk-upload-check endpoint to efficiently verify multiple
        assets in a single request. Assets are checked by their checksum.

        Args:
            assets: List of Asset instances to verify
            checksum_overrides: Optional dict mapping asset_id -> checksum for assets
                that were modified (e.g., EXIF injection) and have different checksums
                than their original values

        Returns:
            Tuple of (verified_asset_ids, missing_asset_ids)
            - verified_asset_ids: Source asset IDs found on destination
            - missing_asset_ids: Source asset IDs NOT found on destination
        """
        if not assets:
            return [], []

        checksum_overrides = checksum_overrides or {}
        logger.debug(f"Verifying {len(assets)} assets exist on destination server")

        # Build checksum -> asset mapping, using overrides where available
        checksum_to_asset = {}
        for asset in assets:
            checksum = checksum_overrides.get(asset.id, asset.checksum)
            checksum_to_asset[checksum] = asset
        checksums = list(checksum_to_asset.keys())

        # Batch lookup all checksums (use existing method)
        found_checksums = self._find_assets_by_checksums(checksums)

        verified_ids = []
        missing_ids = []

        for asset in assets:
            # Use override checksum if available, otherwise use original
            checksum_to_check = checksum_overrides.get(asset.id, asset.checksum)
            if checksum_to_check in found_checksums:
                verified_ids.append(asset.id)
            else:
                missing_ids.append(asset.id)

        logger.debug(
            f"Verification complete: {len(verified_ids)} verified, {len(missing_ids)} missing"
        )

        return verified_ids, missing_ids

    def _find_asset_by_checksum(self, checksum: str) -> str | None:
        """Find asset ID on destination server by checksum.

        Args:
            checksum: SHA1 checksum (hex format, 40 chars)

        Returns:
            Asset ID if found, None otherwise
        """
        try:
            # Use bulk-upload-check endpoint - it returns assetId for duplicates
            response = httpx.post(
                f"{self.server_url}/api/assets/bulk-upload-check",
                headers={"x-api-key": self.api_key},
                json={"assets": [{"id": "lookup", "checksum": checksum}]},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            if results and results[0].get("action") == "reject":
                # "reject" means duplicate exists, assetId is the existing asset
                asset_id = results[0].get("assetId")
                if asset_id:
                    logger.debug(f"Found asset by checksum {checksum[:8]}...: {asset_id}")
                    return str(asset_id)
            return None

        except Exception as e:
            logger.warning(f"Failed to find asset by checksum {checksum[:8]}...: {e}")
            return None

    def _find_assets_by_checksums(self, checksums: list[str]) -> dict[str, str]:
        """Find asset IDs on destination server by checksums (batched).

        Args:
            checksums: List of SHA1 checksums (hex format, 40 chars)

        Returns:
            Dict mapping checksum -> asset_id for found assets
        """
        if not checksums:
            return {}

        try:
            # Use bulk-upload-check endpoint with multiple checksums
            assets_payload = [{"id": checksum, "checksum": checksum} for checksum in checksums]
            response = httpx.post(
                f"{self.server_url}/api/assets/bulk-upload-check",
                headers={"x-api-key": self.api_key},
                json={"assets": assets_payload},
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()

            result = {}
            for item in data.get("results", []):
                if item.get("action") == "reject" and item.get("assetId"):
                    # "reject" means duplicate exists, use the id field as our checksum key
                    checksum = item.get("id")
                    if checksum:
                        result[checksum] = item["assetId"]
                        logger.debug(
                            f"Found asset by checksum {checksum[:8]}...: {item['assetId']}"
                        )

            return result

        except Exception as e:
            logger.warning(f"Failed to find assets by checksums: {e}")
            return {}

    def link_ready_live_photos(
        self,
        unlinked_pairs: list[LivePhotoPair],
    ) -> tuple[list[str], LivePhotoMetrics]:
        """Link live photo pairs where both components exist on destination.

        Checks each unlinked pair to see if both image and video have been
        uploaded to the destination server. Links any pairs that are ready.

        Args:
            unlinked_pairs: List of LivePhotoPair from state that haven't been linked

        Returns:
            Tuple of (linked_image_ids, metrics)
            - linked_image_ids: List of image_asset_ids that were successfully linked
            - metrics: LivePhotoMetrics with detailed statistics
        """
        metrics = LivePhotoMetrics(total_pairs=len(unlinked_pairs))

        if not unlinked_pairs:
            return [], metrics

        logger.debug(f"Checking {len(unlinked_pairs)} unlinked live photo pair(s) for linking")

        # Collect all checksums we need to look up
        checksums_to_check = set()
        for pair in unlinked_pairs:
            checksums_to_check.add(pair.image_checksum)
            checksums_to_check.add(pair.video_checksum)

        # Batch lookup all checksums
        checksum_to_asset_id = self._find_assets_by_checksums(list(checksums_to_check))
        logger.debug(f"Found {len(checksum_to_asset_id)} asset(s) on destination by checksum")

        # Analyze which components are found
        for pair in unlinked_pairs:
            has_image = pair.image_checksum in checksum_to_asset_id
            has_video = pair.video_checksum in checksum_to_asset_id
            if has_image:
                metrics.found_images += 1
            if has_video:
                metrics.found_videos += 1
            if has_image and has_video:
                metrics.ready_pairs += 1

        metrics.pending = len(unlinked_pairs) - metrics.ready_pairs

        logger.debug(
            f"Live photo component analysis: {metrics.found_images} images found, "
            f"{metrics.found_videos} videos found, {metrics.ready_pairs} pairs with both, "
            f"{metrics.pending} pairs with neither"
        )

        # Log sample checksums for debugging format issues
        if unlinked_pairs:
            sample = unlinked_pairs[0]
            logger.debug(
                f"Sample pair checksums - image: {sample.image_checksum[:16]}... "
                f"video: {sample.video_checksum[:16]}..."
            )
            if checksum_to_asset_id:
                sample_key = next(iter(checksum_to_asset_id.keys()))
                logger.debug(f"Sample found checksum key: {sample_key[:16]}...")

        # Link pairs where both components are found
        linked_image_ids = []
        for pair in unlinked_pairs:
            dest_image_id = checksum_to_asset_id.get(pair.image_checksum)
            dest_video_id = checksum_to_asset_id.get(pair.video_checksum)

            if not dest_image_id or not dest_video_id:
                # One or both components not yet uploaded, skip
                continue

            # Both exist, attempt to link
            if self._link_live_photo_pair(dest_image_id, dest_video_id):
                logger.debug(
                    f"Linked live photo pair: image={pair.image_asset_id}, "
                    f"video={pair.video_asset_id}"
                )
                linked_image_ids.append(pair.image_asset_id)
                metrics.linked += 1
            else:
                logger.warning(f"Failed to link live photo pair: image={pair.image_asset_id}")

        logger.debug(
            f"Live photo linking: {metrics.ready_pairs} pair(s) ready, "
            f"{metrics.linked} linked successfully"
        )

        return linked_image_ids, metrics

    def _link_live_photo_pair(self, image_id: str, video_id: str) -> bool:
        """Link a live photo image to its video on destination server.

        Args:
            image_id: Destination image asset ID
            video_id: Destination video asset ID

        Returns:
            True if linking successful, False otherwise
        """
        try:
            response = httpx.put(
                f"{self.server_url}/api/assets/{image_id}",
                headers={"x-api-key": self.api_key},
                json={"livePhotoVideoId": video_id},
                timeout=30,
            )
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            logger.warning(f"Failed to link live photo {image_id} -> {video_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error linking live photo: {e}")
            return False
