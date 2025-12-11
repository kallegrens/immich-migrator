"""Progress bar utilities using Rich."""

from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)


def create_migration_progress() -> Progress:
    """Create progress bar for overall migration tracking.

    Returns:
        Progress instance with overall migration columns
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("{task.completed}/{task.total}"),
        TimeRemainingColumn(),
        console=Console(stderr=True),
    )


def create_download_progress() -> Progress:
    """Create progress bar for download operations with speed tracking.

    Returns:
        Progress instance with download-specific columns
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold green]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=Console(stderr=True),
    )


def create_batch_progress() -> Progress:
    """Create progress bar for batch processing.

    Returns:
        Progress instance for batch operations
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("{task.completed}/{task.total}"),
        console=Console(stderr=True),
    )


class ProgressContext:
    """Context manager for managing multiple progress bars."""

    def __init__(self) -> None:
        """Initialize progress context with three progress bars."""
        self.overall_progress = create_migration_progress()
        self.batch_progress = create_batch_progress()
        self.download_progress = create_download_progress()

        self.overall_task: TaskID | None = None
        self.batch_task: TaskID | None = None
        self.download_task: TaskID | None = None

    def __enter__(self) -> "ProgressContext":
        """Start all progress bars."""
        self.overall_progress.start()
        self.batch_progress.start()
        self.download_progress.start()
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Stop all progress bars."""
        self.overall_progress.stop()
        self.batch_progress.stop()
        self.download_progress.stop()

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

    def start_download(self, description: str, total: int) -> TaskID:
        """Start download tracking.

        Args:
            description: Download description
            total: Total bytes to download

        Returns:
            Task ID for updating progress
        """
        self.download_task = self.download_progress.add_task(description, total=total)
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
