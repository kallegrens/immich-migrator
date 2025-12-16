"""Logging configuration using loguru."""

import sys
from pathlib import Path

from loguru import logger


def configure_logging(
    log_level: str = "INFO", log_file: Path | None = None, quiet: bool = False
) -> None:
    """Configure loguru logging with file rotation.

    Args:
        log_level: Logging verbosity level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional path to log file. If None, uses default location.
        quiet: If True, suppress INFO logs to console (still write to file)
    """
    # Remove default handler
    logger.remove()

    # Add console handler with formatting (only if not quiet, or show warnings/errors)
    console_level = "WARNING" if quiet else log_level
    logger.add(
        sys.stderr,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | <level>{message}</level>"
        ),
        level=console_level,
        colorize=True,
    )

    # Add file handler if specified or use default
    if log_file is None:
        log_file = Path.home() / ".immich-migrator" / "logs" / "migration.log"

    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        level=log_level,
        rotation="10 MB",
        retention="1 week",
        compression="zip",
    )

    logger.debug(f"Logging configured: level={log_level}, file={log_file}, quiet={quiet}")


def get_logger():  # type: ignore[no-untyped-def]
    """Get the configured logger instance.

    Returns:
        Logger instance
    """
    return logger
