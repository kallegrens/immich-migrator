"""Terminal UI for album selection using Questionary."""

import questionary
from rich.console import Console

from ..models.album import Album
from ..models.state import MigrationState, MigrationStatus

console = Console()


async def select_album(albums: list[Album], state: MigrationState) -> Album | None:
    """Display interactive TUI for album selection.

    Args:
        albums: List of available albums
        state: Current migration state

    Returns:
        Selected Album or None if user cancels
    """
    if not albums:
        console.print("[yellow]No albums found[/yellow]")
        return None

    # Build choices with status indicators
    choices = []
    for album in albums:
        album_state = state.get_or_create_album_state(album.id, album.album_name, album.asset_count)

        # Status icon
        if album_state.status == MigrationStatus.COMPLETED:
            icon = "✅"
        elif album_state.status == MigrationStatus.IN_PROGRESS:
            icon = "🔄"
        elif album_state.status == MigrationStatus.FAILED:
            icon = "❌"
        else:
            icon = "⏳"

        # Progress info
        if album_state.migrated_count > 0:
            progress = f"{album_state.migrated_count}/{album_state.asset_count}"
        else:
            progress = f"{album_state.asset_count} assets"

        label = f"{icon} {album.album_name} ({progress}) - {album_state.status.value}"
        choices.append({"name": label, "value": album})

    # Show selection menu
    console.print(
        "\n[bold cyan]╭─────────────────────────────────────────────────────╮[/bold cyan]"
    )
    console.print("[bold cyan]│ Select an album to migrate:                         │[/bold cyan]")
    console.print(
        "[bold cyan]╰─────────────────────────────────────────────────────╯[/bold cyan]\n"
    )

    try:
        selected = await questionary.select(
            "",
            choices=choices,
            instruction="(Use ↑/↓ arrows, Enter to select, Ctrl+C to exit)",
        ).ask_async()

        if selected is None:
            return None

        # Check if selected album is already completed
        album_state = state.get_or_create_album_state(
            selected.id, selected.album_name, selected.asset_count
        )

        if album_state.status == MigrationStatus.COMPLETED:
            # Show warning message using Rich console
            console.print(
                f"\n[bold yellow]⚠ Album '{selected.album_name}' already completed.[/bold yellow]"
            )

            # Prompt user for action on completed album
            action = await questionary.select(
                "What would you like to do?",
                choices=[
                    {"name": "Re-migrate (start fresh)", "value": "remigrate"},
                    {"name": "Skip (return to menu)", "value": "skip"},
                    {"name": "Cancel", "value": "cancel"},
                ],
            ).ask_async()

            if action == "remigrate":
                album_state.reset_to_pending()
                console.print(
                    f"[green]Album state reset. Will re-migrate all "
                    f"{selected.asset_count} assets.[/green]"
                )
                return selected  # type: ignore[no-any-return]
            elif action == "skip":
                console.print("[yellow]Returning to album selection...[/yellow]")
                return None
            else:  # cancel
                return None

        return selected  # type: ignore[no-any-return]

    except KeyboardInterrupt:
        return None


def display_error(message: str, details: str | None = None) -> None:
    """Display error message with optional details.

    Args:
        message: Error message
        details: Optional detailed error information
    """
    console.print(f"\n[bold red]Error:[/bold red] {message}")
    if details:
        console.print(f"[dim]{details}[/dim]")
