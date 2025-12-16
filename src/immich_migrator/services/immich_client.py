"""Immich API client with async HTTP operations."""

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ..lib.logging import get_logger
from ..models.album import Album
from ..models.asset import Asset
from ..models.config import ImmichCredentials

logger = get_logger()  # type: ignore[no-untyped-call]


class ImmichClient:
    """HTTP client for Immich API with rate limiting and retry logic."""

    def __init__(
        self,
        credentials: ImmichCredentials,
        max_concurrent: int = 50,
        timeout_seconds: int = 300,
    ):
        """Initialize Immich API client.

        Args:
            credentials: Server URL and API key
            max_concurrent: Maximum concurrent HTTP requests
            timeout_seconds: Timeout for HTTP requests
        """
        self.server_url = str(credentials.server_url).rstrip("/")
        self.api_key = credentials.api_key
        self.max_concurrent = max_concurrent
        self.timeout_seconds = timeout_seconds

        # Concurrency control semaphore
        self._semaphore = asyncio.Semaphore(max_concurrent)

        # HTTP client
        self.client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "ImmichClient":
        """Async context manager entry."""
        self.client = httpx.AsyncClient(
            headers={"x-api-key": self.api_key},
            timeout=httpx.Timeout(self.timeout_seconds),
            follow_redirects=True,
        )
        logger.debug(f"Connected to Immich server: {self.server_url}")
        return self

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()
        logger.debug("Closed Immich client connection")

    async def _rate_limited_request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Make concurrent HTTP request with semaphore control.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API endpoint path
            **kwargs: Additional arguments for httpx request

        Returns:
            HTTP response

        Raises:
            httpx.HTTPError: On HTTP errors
        """
        if not self.client:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")

        async with self._semaphore:
            url = f"{self.server_url}/api{path}"
            logger.debug(f"{method} {url}")

            response = await self.client.request(method, url, **kwargs)
            response.raise_for_status()

            return response

    @retry(  # type: ignore[untyped-decorator]
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def list_albums(self) -> list[Album]:
        """List all albums from Immich server.

        Returns:
            List of Album instances (without full asset lists)

        Raises:
            httpx.HTTPError: On API errors
        """
        logger.debug("Fetching album list from Immich server")

        response = await self._rate_limited_request("GET", "/albums")
        data = response.json()

        albums = []
        for album_data in data:
            album = Album(
                id=album_data["id"],
                album_name=album_data["albumName"],
                asset_count=album_data["assetCount"],
                created_at=album_data.get("createdAt"),
                shared=album_data.get("shared", False),
            )
            albums.append(album)

        logger.debug(f"Found {len(albums)} albums")
        return albums

    @retry(  # type: ignore[untyped-decorator]
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def get_album_assets(self, album_id: str) -> Album:
        """Get album with full asset list.

        Args:
            album_id: Album identifier

        Returns:
            Album instance with populated assets list

        Raises:
            httpx.HTTPError: On API errors
        """
        logger.debug(f"Fetching assets for album {album_id}")

        response = await self._rate_limited_request(
            "GET", f"/albums/{album_id}", params={"withoutAssets": False}
        )
        data = response.json()

        # Parse assets
        assets = []
        live_photo_video_ids = []  # Collect IDs of linked live photo videos
        for asset_data in data.get("assets", []):
            exif_info = asset_data.get("exifInfo", {})
            live_photo_video_id = asset_data.get("livePhotoVideoId")
            asset = Asset(
                id=asset_data["id"],
                original_file_name=asset_data["originalFileName"],
                original_mime_type=asset_data["originalMimeType"],
                checksum=asset_data["checksum"],
                file_created_at=asset_data.get("fileCreatedAt"),
                file_size_bytes=exif_info.get("fileSizeInByte"),
                exif_date_time_original=exif_info.get("dateTimeOriginal"),
                local_date_time=asset_data.get("localDateTime"),
                asset_type=asset_data.get("type", "IMAGE"),
                live_photo_video_id=live_photo_video_id,
            )
            assets.append(asset)
            if live_photo_video_id:
                live_photo_video_ids.append(live_photo_video_id)

        # Fetch live photo video assets (they're hidden and not in album list)
        if live_photo_video_ids:
            logger.debug(f"Fetching {len(live_photo_video_ids)} live photo videos")
            video_assets = await self._fetch_live_photo_videos(live_photo_video_ids)
            assets.extend(video_assets)

        album = Album(
            id=data["id"],
            album_name=data["albumName"],
            asset_count=data["assetCount"],
            assets=assets,
            created_at=data.get("createdAt"),
            shared=data.get("shared", False),
        )

        logger.debug(f"Loaded {len(assets)} assets for album '{album.album_name}'")
        return album

    async def _fetch_live_photo_videos(self, video_ids: list[str]) -> list[Asset]:
        """Fetch live photo video assets by their IDs.

        Live photo videos are hidden assets not returned in album listings,
        so we need to fetch them individually. Uses parallel requests for speed.

        Args:
            video_ids: List of video asset IDs to fetch

        Returns:
            List of video Asset instances
        """
        if not video_ids:
            return []

        # Fetch all videos in parallel for speed
        tasks = [self.get_asset(video_id) for video_id in video_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        video_assets = []
        for video_id, result in zip(video_ids, results):
            if isinstance(result, Exception):
                logger.warning(f"Failed to fetch live photo video {video_id}: {result}")
            elif result is not None:
                video_assets.append(result)

        return video_assets  # type: ignore[return-value]

    @retry(  # type: ignore[untyped-decorator]
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def get_asset(self, asset_id: str) -> Asset | None:
        """Fetch a single asset by ID.

        Args:
            asset_id: Asset identifier

        Returns:
            Asset instance or None if not found

        Raises:
            httpx.HTTPError: On API errors (except 404)
        """
        logger.debug(f"Fetching asset {asset_id}")

        try:
            response = await self._rate_limited_request("GET", f"/assets/{asset_id}")
            data = response.json()

            exif_info = data.get("exifInfo", {})
            return Asset(
                id=data["id"],
                original_file_name=data["originalFileName"],
                original_mime_type=data["originalMimeType"],
                checksum=data["checksum"],
                file_created_at=data.get("fileCreatedAt"),
                file_size_bytes=exif_info.get("fileSizeInByte"),
                exif_date_time_original=exif_info.get("dateTimeOriginal"),
                local_date_time=data.get("localDateTime"),
                asset_type=data.get("type", "VIDEO"),
                live_photo_video_id=None,  # Videos don't have linked videos
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Asset {asset_id} not found")
                return None
            raise

    @retry(  # type: ignore[untyped-decorator]
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def download_asset(
        self,
        asset: Asset,
        dest_path: Path,
        progress_callback: Callable[[int], None] | None = None,
    ) -> Path:
        """Download asset to local file with streaming.

        Args:
            asset: Asset to download
            dest_path: Destination file path
            progress_callback: Optional callback to report bytes downloaded

        Returns:
            Path to downloaded file

        Raises:
            httpx.HTTPError: On download errors
            IOError: On file write errors
        """
        logger.debug(f"Downloading asset {asset.id}: {asset.original_file_name}")

        dest_path.parent.mkdir(parents=True, exist_ok=True)

        async with self._semaphore:
            url = f"{self.server_url}/api/assets/{asset.id}/original"

            async with self.client.stream("GET", url) as response:  # type: ignore[union-attr]
                response.raise_for_status()

                with open(dest_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
                        if progress_callback:
                            progress_callback(len(chunk))

        logger.debug(f"Downloaded {asset.original_file_name} to {dest_path}")
        return dest_path

    @retry(  # type: ignore[untyped-decorator]
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def search_unalbummed_assets(self) -> list[Asset]:
        """Search for assets not in any album.

        Note: Live photo videos linked to images ARE considered "in album" even
        though they're hidden, so we need to fetch them separately based on
        livePhotoVideoId references.

        Returns:
            List of Asset instances without album membership

        Raises:
            httpx.HTTPError: On API errors
        """
        logger.debug("Searching for unalbummed assets")

        all_assets = []
        live_photo_video_ids = []
        page = 1
        page_size = 1000  # Use max page size for efficiency

        while True:
            response = await self._rate_limited_request(
                "POST",
                "/search/metadata",
                json={"isNotInAlbum": True, "page": page, "size": page_size},
            )
            data = response.json()

            assets_data = data.get("assets", {}).get("items", [])
            if not assets_data:
                break

            for asset_data in assets_data:
                live_photo_video_id = asset_data.get("livePhotoVideoId")
                asset = Asset(
                    id=asset_data["id"],
                    original_file_name=asset_data["originalFileName"],
                    original_mime_type=asset_data["originalMimeType"],
                    checksum=asset_data["checksum"],
                    file_created_at=asset_data.get("fileCreatedAt"),
                    file_size_bytes=asset_data.get("exifInfo", {}).get("fileSizeInByte"),
                    asset_type=asset_data.get("type", "IMAGE"),
                    live_photo_video_id=live_photo_video_id,
                )
                all_assets.append(asset)
                if live_photo_video_id:
                    live_photo_video_ids.append(live_photo_video_id)

            logger.debug(f"Fetched page {page}: {len(assets_data)} unalbummed assets")

            # Check if we've reached the end
            if len(assets_data) < page_size:
                break

            page += 1

        # Fetch live photo video assets in parallel (they're hidden so not in search results)
        if live_photo_video_ids:
            logger.debug(f"Fetching {len(live_photo_video_ids)} live photo videos")
            video_assets = await self._fetch_live_photo_videos(live_photo_video_ids)
            all_assets.extend(video_assets)

        logger.debug(f"Found {len(all_assets)} unalbummed assets")
        return all_assets
