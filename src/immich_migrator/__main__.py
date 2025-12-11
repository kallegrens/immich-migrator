"""Main entry point for immich-migrator CLI."""

from .cli.app import app


def main() -> None:
    """Entry point for console script."""
    app()


if __name__ == "__main__":
    main()
