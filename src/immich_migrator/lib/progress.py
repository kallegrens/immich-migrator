"""Progress bar utilities using Rich."""

from dataclasses import dataclass

from rich.console import Console, Group
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
    """Context manager for managing multiple progress bars with unified Live display."""

    def __init__(self) -> None:
        """Initialize progress context with shared console and Live display."""
        self.console = Console()  # Shared console for all progress bars

        # Create progress bars without separate consoles
        self.download_progress = Progress(
            TextColumn("⬇️  Download"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
        )

        self.batch_progress = Progress(
            TextColumn("📦 Batch"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("{task.completed}/{task.total}"),
        )

        self.overall_progress = Progress(
            TextColumn("📊 Overall"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("{task.completed}/{task.total}"),
            TimeRemainingColumn(),
        )

        self.live: Live | None = None
        self.overall_task: TaskID | None = None
        self.batch_task: TaskID | None = None
        self.download_task: TaskID | None = None

    def __enter__(self) -> "ProgressContext":
        """Start Live display with all progress bars."""
        # Create group of all progress bars
        progress_group = Group(
            self.download_progress,
            self.batch_progress,
            self.overall_progress,
        )

        # Start Live display with the group
        self.live = Live(progress_group, console=self.console, refresh_per_second=10)
        self.live.start()
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Stop Live display."""
        if self.live:
            self.live.stop()

    def start_overall(self, description: str, total: int) -> TaskID:
        """Start overall migration tracking.

        Args:
            description: Task description
            total: Total number of items

        Returns:
            Task ID for updating progress
        """
        self.overall_task = self.overall_progress.add_task(description, total=total)
        return self.overall_task

    def start_batch(self, description: str, total: int) -> TaskID:
        """Start batch processing tracking.

        Args:
            description: Batch description
            total: Total items in batch

        Returns:
            Task ID for updating progress
        """
        self.batch_task = self.batch_progress.add_task(description, total=total)
        return self.batch_task

    def start_download(self, total: int) -> TaskID:
        """Start download tracking.

        Args:
            total: Total bytes to download

        Returns:
            Task ID for updating progress
        """
        self.download_task = self.download_progress.add_task("", total=total)
        return self.download_task

    def update_overall(self, advance: int = 1) -> None:
        """Update overall progress.

        Args:
            advance: Number of items to advance
        """
        if self.overall_task is not None:
            self.overall_progress.update(self.overall_task, advance=advance)

    def update_batch(self, advance: int = 1) -> None:
        """Update batch progress.

        Args:
            advance: Number of items to advance
        """
        if self.batch_task is not None:
            self.batch_progress.update(self.batch_task, advance=advance)

    def update_download(self, advance: int) -> None:
        """Update download progress.

        Args:
            advance: Number of bytes downloaded
        """
        if self.download_task is not None:
            self.download_progress.update(self.download_task, advance=advance)

    def complete_batch(self) -> None:
        """Complete and remove current batch task."""
        if self.batch_task is not None:
            self.batch_progress.remove_task(self.batch_task)
            self.batch_task = None

    def complete_download(self) -> None:
        """Complete and remove current download task."""
        if self.download_task is not None:
            self.download_progress.remove_task(self.download_task)
            self.download_task = None


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
    table = Table(title=f"\n✅ Migration Completed: {album_name}", show_header=True)

    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    # Asset metrics
    table.add_row("📷 Total Assets", str(total))
    table.add_row("✅ Migrated", str(migrated))
    if failed > 0:
        table.add_row("❌ Failed", str(failed))

    # EXIF metrics
    if exif_metrics and (exif_metrics.injected + exif_metrics.skipped + exif_metrics.failed > 0):
        exif_summary = (
            f"{exif_metrics.injected} injected, "
            f"{exif_metrics.skipped} skipped, "
            f"{exif_metrics.failed} failed"
        )
        table.add_row("📝 EXIF Injected", exif_summary)

    # Live photo metrics
    if live_photo_metrics and live_photo_metrics.linked > 0:
        table.add_row(
            "🔗 Live Photos", f"{live_photo_metrics.linked}/{live_photo_metrics.total_pairs} linked"
        )

    # Duration
    table.add_row("⏱️ Duration", f"{duration:.1f}s")

    console.print(table)
