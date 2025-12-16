"""Progress bar utilities using Rich."""

from dataclasses import dataclass

from rich.console import Console
from rich.live import Live
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TaskID,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.table import Table


@dataclass
class ExifMetrics:
    """Metrics for EXIF date injection operations."""

    injected: int = 0  # Successfully injected date metadata
    skipped: int = 0  # Already had valid date metadata
    failed: int = 0  # Failed injection (corrupted files)

    def __add__(self, other: "ExifMetrics") -> "ExifMetrics":
        """Add two ExifMetrics together."""
        return ExifMetrics(
            injected=self.injected + other.injected,
            skipped=self.skipped + other.skipped,
            failed=self.failed + other.failed,
        )


@dataclass
class LivePhotoMetrics:
    """Metrics for live photo linking operations."""

    total_pairs: int = 0  # Total expected pairs from source
    found_images: int = 0  # Images found on destination
    found_videos: int = 0  # Videos found on destination
    ready_pairs: int = 0  # Pairs with both components found
    linked: int = 0  # Successfully linked pairs
    pending: int = 0  # Pairs still missing one or both components

    def __add__(self, other: "LivePhotoMetrics") -> "LivePhotoMetrics":
        """Add two LivePhotoMetrics together.

        Note: total_pairs is not accumulated - it represents the total expected pairs
        from the source album, which is constant throughout the migration.
        """
        return LivePhotoMetrics(
            total_pairs=self.total_pairs,  # Keep original total, don't accumulate
            found_images=self.found_images + other.found_images,
            found_videos=self.found_videos + other.found_videos,
            ready_pairs=self.ready_pairs + other.ready_pairs,
            linked=self.linked + other.linked,
            pending=self.pending + other.pending,
        )


class ProgressContext:
    """Context manager for managing overall migration progress."""

    def __init__(self) -> None:
        """Initialize progress context with shared console and Live display."""
        self.console = Console()  # Shared console for progress bar

        # Single overall progress bar tracking bytes with comprehensive metrics
        self.overall_progress = Progress(
            TextColumn("📊 Progress"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            DownloadColumn(),
            TransferSpeedColumn(),
            TextColumn("•"),
            TextColumn("{task.fields[assets_done]}/{task.fields[assets_total]} assets"),
            TimeRemainingColumn(),
        )

        self.live: Live | None = None
        self.overall_task: TaskID | None = None
        self.total_bytes: int = 0
        self.completed_bytes: int = 0
        self.total_assets: int = 0
        self.completed_assets: int = 0

    def __enter__(self) -> "ProgressContext":
        """Start Live display with overall progress bar."""
        # Start Live display with just the overall progress
        self.live = Live(self.overall_progress, console=self.console, refresh_per_second=10)
        self.live.start()
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Stop Live display."""
        if self.live:
            self.live.stop()

    def start_overall(self, description: str, total_bytes: int, total_assets: int) -> TaskID:
        """Start overall migration tracking.

        Args:
            description: Task description
            total_bytes: Total bytes to process (download + upload = 2x file sizes)
            total_assets: Total number of assets to migrate

        Returns:
            Task ID for updating progress
        """
        self.total_bytes = total_bytes
        self.total_assets = total_assets
        self.overall_task = self.overall_progress.add_task(
            description,
            total=total_bytes,
            assets_done=0,
            assets_total=total_assets,
        )
        return self.overall_task

    def update_progress(self, bytes_advanced: int) -> None:
        """Update overall progress by bytes.

        Args:
            bytes_advanced: Number of bytes to advance
        """
        if self.overall_task is not None:
            self.completed_bytes += bytes_advanced
            self.overall_progress.update(self.overall_task, advance=bytes_advanced)

    def update_assets(self, assets_completed: int) -> None:
        """Update completed asset count display.

        Args:
            assets_completed: Number of assets completed (for display only)
        """
        if self.overall_task is not None:
            self.completed_assets = assets_completed
            self.overall_progress.update(
                self.overall_task,
                assets_done=assets_completed,
            )


def display_migration_summary(
    album_name: str,
    total: int,
    migrated: int,
    failed: int,
    duration: float,
    exif_metrics: ExifMetrics | None = None,
    live_photo_metrics: LivePhotoMetrics | None = None,
) -> None:
    """Display migration summary table with all metrics.

    Args:
        album_name: Name of migrated album
        total: Total assets in album
        migrated: Successfully migrated count
        failed: Failed asset count
        duration: Migration duration in seconds
        exif_metrics: EXIF injection metrics (optional)
        live_photo_metrics: Live photo linking metrics (optional)
    """
    console = Console()

    # Determine status based on results
    if failed == 0:
        status_icon = "✅"
        status_text = "Migration Completed"
        title_style = "bold green"
    elif migrated == 0:
        status_icon = "❌"
        status_text = "Migration Failed"
        title_style = "bold red"
    else:
        status_icon = "⚠️"
        status_text = "Partial Migration"
        title_style = "bold yellow"

    table = Table(
        title=f"\n{status_icon} {status_text}: {album_name}",
        show_header=True,
        title_style=title_style,
    )

    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    # Asset metrics
    table.add_row("📷 Total Assets", str(total))
    table.add_row("✅ Migrated", str(migrated))
    table.add_row("❌ Failed", str(failed))

    # EXIF metrics
    if exif_metrics:
        exif_summary = f"{exif_metrics.injected} injected, {exif_metrics.failed} failed"
        table.add_row("📝 EXIF Injected", exif_summary)

    # Live photo metrics
    if live_photo_metrics:
        live_photo_summary = f"{live_photo_metrics.linked}/{live_photo_metrics.total_pairs} linked"
        table.add_row("🔗 Live Photos", live_photo_summary)

    # Duration
    table.add_row("⏱  Duration", f"{duration:.1f}s")

    console.print(table)
