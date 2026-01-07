"""Main CLI application using Typer."""

import asyncio
import shutil
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from immich_migrator import __version__

from ..lib.logging import configure_logging, get_logger
from ..lib.progress import ExifMetrics, LivePhotoMetrics, display_migration_summary
from ..models.album import Album
from ..models.asset import Asset
from ..models.config import Config, ImmichCredentials
from ..models.state import AlbumState, MigrationState, MigrationStatus
from ..services.downloader import Downloader, compute_file_checksum
from ..services.exif_injector import ExifInjectionError, ExifInjector
from ..services.immich_client import ImmichClient
from ..services.state_manager import StateManager
from ..services.uploader import Uploader
from .tui import display_error, select_album

app = typer.Typer(
    name="immich-migrator",
    help="CLI tool for migrating photo albums between Immich servers",
)
console = Console()


@app.command(name="migrate")
def migrate_command(
    credentials: Path | None = typer.Option(
        None,
        "--credentials",
        "-c",
        exists=True,
        readable=True,
        help=(
            "Path to unified .env file containing both OLD_IMMICH_* and NEW_IMMICH_* "
            "variables. If omitted, the tool will look for ~/.immich.env"
        ),
    ),
    batch_size: int = typer.Option(
        20,
        "--batch-size",
        min=1,
        max=100,
        help="Number of assets to download per batch",
    ),
    config: Path | None = typer.Option(
        None,
        "--config",
        exists=True,
        readable=True,
        help="Path to TOML configuration file",
    ),
    state_file: Path | None = typer.Option(
        None,
        "--state-file",
        help="Path to state persistence file",
    ),
    temp_dir: Path | None = typer.Option(
        None,
        "--temp-dir",
        help="Temporary storage directory",
    ),
    log_level: str = typer.Option(
        "INFO",
        "--log-level",
        help="Logging verbosity level",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Suppress INFO logs to console, show only warnings/errors and progress bars",
    ),
    verify_retries: int = typer.Option(
        2,
        "--verify-retries",
        min=0,
        max=10,
        help="Number of retry attempts for missing assets during verification",
    ),
    failed_output_dir: Path | None = typer.Option(
        None,
        "--failed-output-dir",
        help="Directory to save permanently failed assets (default: ./immich_failed_assets)",
    ),
) -> None:
    """Migrate photo albums between Immich servers.

    This tool connects to your old Immich server, displays an interactive menu
    for album selection, and migrates selected albums to your new server using
    batch processing with progress tracking.
    """
    try:
        # Configure logging first
        configure_logging(log_level=log_level, quiet=quiet)
        logger = get_logger()  # type: ignore[no-untyped-call]

        # Display welcome banner (only once, nicely formatted)
        console.print(
            Panel(
                f"[bold cyan]🚀 Immich Migration Tool v{__version__}[/bold cyan]",
                border_style="cyan",
            )
        )

        # Load configuration
        app_config = Config(
            batch_size=batch_size,
            log_level=log_level,  # type: ignore[arg-type]
        )

        if state_file:
            app_config.state_file = state_file
        if temp_dir:
            app_config.temp_dir = temp_dir

        # Only log configuration if non-default
        if app_config.batch_size != 20:
            logger.info(f"Configuration: batch_size={app_config.batch_size}")

        # Load server credentials
        console.print("\n[bold]🔐 Loading credentials...[/bold]")
        # Default credentials file to check when no --credentials provided
        default_cred_path = Path.home() / ".immich.env"

        cred_path_to_use: Path
        if credentials:
            cred_path_to_use = credentials
        else:
            cred_path_to_use = default_cred_path

        try:
            if not cred_path_to_use.exists():
                raise FileNotFoundError(f"Credentials file not found: {cred_path_to_use}")

            # Expect the unified env file to contain both OLD_IMMICH_* and NEW_IMMICH_* vars
            old_creds = ImmichCredentials.from_env_file(cred_path_to_use, prefix="OLD_IMMICH")
            logger.debug(f"Loaded old server credentials: {old_creds.server_url}")

            new_creds = ImmichCredentials.from_env_file(cred_path_to_use, prefix="NEW_IMMICH")
            logger.debug(f"Loaded new server credentials: {new_creds.server_url}")
        except (FileNotFoundError, KeyError) as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            logger.error(f"Failed to load credentials: {e}")
            raise typer.Exit(code=1)

        # Run async migration
        asyncio.run(
            run_migration(
                old_creds=old_creds,
                new_creds=new_creds,
                config=app_config,
                verify_retries=verify_retries,
                failed_output_dir=failed_output_dir or Path("./immich_failed_assets"),
            )
        )

    except KeyboardInterrupt:
        console.print("\n[yellow]⏸️  Migration interrupted by user[/yellow]")
        logger.info("Migration interrupted by Ctrl+C")
        raise typer.Exit(code=130)
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        logger.exception("Unexpected error during migration")
        raise typer.Exit(code=1)


async def run_migration(
    old_creds: ImmichCredentials,
    new_creds: ImmichCredentials,
    config: Config,
    verify_retries: int = 2,
    failed_output_dir: Path = Path("./immich_failed_assets"),
) -> None:
    """Run the migration process.

    Args:
        old_creds: Old server credentials
        new_creds: New server credentials
        config: Application configuration
        verify_retries: Number of retry attempts for missing assets
        failed_output_dir: Directory to save permanently failed assets
    """
    logger = get_logger()  # type: ignore[no-untyped-call]

    # Initialize state manager
    state_manager = StateManager(config.state_file)
    migration_state = state_manager.load()

    console.print("\n[bold]🌐 Connecting to Immich servers...[/bold]")

    async with ImmichClient(old_creds, config.max_concurrent_requests) as old_client:
        console.print(f"[green]✓[/green] Connected to old server: {old_creds.server_url}")
        console.print(f"[green]✓[/green] Connected to new server: {new_creds.server_url}")

        # Discover albums
        console.print("\n[bold]📂 Discovering albums...[/bold]")
        albums = await old_client.list_albums()

        # Check for unalbummed assets
        unalbummed_assets = await old_client.search_unalbummed_assets()
        if unalbummed_assets:
            virtual_album = Album.create_unalbummed_album(unalbummed_assets)
            albums.append(virtual_album)
            logger.debug(f"Created virtual album with {len(unalbummed_assets)} unalbummed assets")

        console.print(f"Found [cyan]{len(albums)}[/cyan] albums\n")

        # Update state with discovered albums
        for album in albums:
            migration_state.get_or_create_album_state(album.id, album.album_name, album.asset_count)

        # Save state after discovery
        state_manager.save(migration_state)

        # Interactive album selection
        while True:
            selected_album = await select_album(albums, migration_state)

            if selected_album is None:
                console.print("\n[yellow]Exiting...[/yellow]")
                break

            console.print(
                f"\n[bold cyan]Selected:[/bold cyan] {selected_album.album_name} "
                f"({selected_album.asset_count} assets)"
            )

            # Migrate the selected album
            await migrate_album(
                album=selected_album,
                old_client=old_client,
                new_creds=new_creds,
                config=config,
                migration_state=migration_state,
                state_manager=state_manager,
                verify_retries=verify_retries,
                failed_output_dir=failed_output_dir,
            )

            # Ask if user wants to continue
            try:
                continue_choice = typer.confirm("\nReturn to album selection?", default=True)
                if not continue_choice:
                    break
            except KeyboardInterrupt:
                console.print("\n[yellow]Exiting...[/yellow]")
                break


async def migrate_album(
    album: Album,
    old_client: ImmichClient,
    new_creds: ImmichCredentials,
    config: Config,
    migration_state: MigrationState,
    state_manager: StateManager,
    verify_retries: int = 2,
    failed_output_dir: Path = Path("./immich_failed_assets"),
    use_progress: bool = False,
) -> None:
    """Migrate a single album from old to new server.

    Args:
        album: Album to migrate
        old_client: Client for old server
        new_creds: New server credentials
        config: Application configuration
        migration_state: Current migration state
        state_manager: State persistence manager
        verify_retries: Number of retry attempts for missing assets
        failed_output_dir: Directory to save permanently failed assets
        use_progress: If True, use rich progress bars instead of console.print
    """
    import time

    logger = get_logger()  # type: ignore[no-untyped-call]

    start_time = time.time()

    # Get album state
    album_state = migration_state.get_or_create_album_state(
        album.id, album.album_name, album.asset_count
    )

    # Mark as in progress
    album_state.mark_in_progress()
    state_manager.save(migration_state)

    # Initialize uploader
    try:
        uploader = Uploader(str(new_creds.server_url), new_creds.api_key)
    except RuntimeError as e:
        display_error(str(e), "Please install Immich CLI: npm install -g @immich/cli")
        album_state.mark_failed(str(e))
        state_manager.save(migration_state)
        return

    # Initialize EXIF injector
    try:
        exif_injector = ExifInjector()
    except ExifInjectionError as e:
        display_error(str(e), "EXIF date injection will be skipped")
        logger.warning(f"ExifInjector initialization failed: {e}")
        exif_injector = None

    # Initialize downloader
    downloader = Downloader(
        old_client,
        config.temp_dir,
        max_concurrent=config.max_concurrent_downloads,
    )

    # Load full album with assets if needed
    if not album.assets:
        console.print(f"[bold]Loading assets for {album.album_name}...[/bold]")
        album = await old_client.get_album_assets(album.id)

    # === FORCE FRESH START ===
    # Always reset album state to ensure consistent counts.
    # Pre-verification below will handle detecting already-migrated assets.
    if album_state.status != MigrationStatus.PENDING or album_state.migrated_count > 0:
        console.print("[yellow]Resetting album state for fresh migration...[/yellow]")
        album_state.reset_to_pending()
        state_manager.save(migration_state)

    # Update asset_count to actual count (including live photo videos)
    # The API's assetCount excludes hidden videos, but we track them all
    actual_asset_count = len(album.assets)
    if album_state.asset_count != actual_asset_count:
        logger.info(f"Setting asset count to {actual_asset_count} (includes live photo videos)")
        album_state.asset_count = actual_asset_count
        album.asset_count = actual_asset_count

    # === PRE-MIGRATION VERIFICATION ===
    # Check which assets already exist on destination server BEFORE downloading
    # This avoids unnecessary downloads for already-migrated assets (e.g., lost state.json)
    console.print("[bold cyan]🔍 Checking existing assets on destination server...[/bold cyan]")

    # Build asset lookup map for live photo pair handling
    all_assets_by_id = {asset.id: asset for asset in album.assets}

    # Verify all assets against destination server
    pre_verified_ids, pre_missing_ids = uploader.verify_assets_exist(album.assets)

    # For live photos: if either component is missing, treat BOTH as missing
    # This ensures we don't end up with orphaned components
    adjusted_missing_ids = set(pre_missing_ids)
    for asset in album.assets:
        if asset.live_photo_video_id and asset.live_photo_video_id in all_assets_by_id:
            image_missing = asset.id in pre_missing_ids
            video_missing = asset.live_photo_video_id in pre_missing_ids
            if image_missing or video_missing:
                # Both components need to be migrated together
                adjusted_missing_ids.add(asset.id)
                adjusted_missing_ids.add(asset.live_photo_video_id)

    # Recalculate verified IDs after live photo adjustment
    adjusted_verified_ids = [
        asset_id for asset_id in pre_verified_ids if asset_id not in adjusted_missing_ids
    ]

    # Track pre-verified assets in state
    for asset_id in adjusted_verified_ids:
        album_state.add_verified_asset(asset_id)
    state_manager.save(migration_state)

    pre_verified_count = len(adjusted_verified_ids)
    pre_missing_count = len(adjusted_missing_ids)

    if pre_verified_count > 0:
        console.print(f"[green]✓ {pre_verified_count} assets already exist on destination[/green]")

        # Add pre-existing assets to target album (skip for unalbummed assets)
        if not album.is_virtual_unalbummed:
            console.print("[dim]Adding pre-existing assets to target album...[/dim]")

            # Get or create the target album on destination
            dest_album_id = uploader.get_or_create_album(album.album_name)
            if dest_album_id:
                # Get checksums for pre-verified assets, but SKIP live photo videos
                # Live photo videos are hidden and linked to their image - they're
                # not direct album members. Only add the images to the album.
                live_photo_video_ids = {
                    asset.live_photo_video_id for asset in album.assets if asset.live_photo_video_id
                }
                verified_checksums = [
                    all_assets_by_id[asset_id].checksum
                    for asset_id in adjusted_verified_ids
                    if asset_id in all_assets_by_id
                    and asset_id not in live_photo_video_ids  # Skip videos
                ]

                # Look up destination asset IDs by checksum
                checksum_to_dest_id = uploader.get_destination_asset_ids(verified_checksums)

                # Add to album
                dest_asset_ids = list(checksum_to_dest_id.values())
                if dest_asset_ids:
                    added, failed = uploader.add_assets_to_album(dest_album_id, dest_asset_ids)
                    if added > 0:
                        console.print(
                            f"[green]✓ Added {added} pre-existing assets to album[/green]"
                        )
                    if failed > 0:
                        console.print(f"[yellow]⚠ Failed to add {failed} assets to album[/yellow]")
            else:
                console.print(
                    "[yellow]⚠ Could not create target album, "
                    "pre-existing assets won't be added[/yellow]"
                )

    if pre_missing_count == 0:
        # All assets already exist - mark as completed and return early
        console.print(
            f"[bold green]✓ All {pre_verified_count} assets already migrated![/bold green]"
        )
        album_state.mark_completed()
        state_manager.save(migration_state)

        # Display summary
        duration = time.time() - start_time
        display_migration_summary(
            album_name=album.album_name,
            total=len(album.assets),
            migrated=pre_verified_count,
            failed=0,
            duration=duration,
            exif_metrics=ExifMetrics(),
            live_photo_metrics=LivePhotoMetrics(),
        )
        return

    console.print(f"[cyan]⬇ {pre_missing_count} assets need to be migrated[/cyan]\n")

    # Filter album assets to only include those that need migration
    original_asset_count = len(album.assets)
    album.assets = [asset for asset in album.assets if asset.id in adjusted_missing_ids]

    # Reorder assets so live photo images are immediately followed by their videos.
    # This ensures both components are downloaded and uploaded together in the same batch.
    assets_by_id = {asset.id: asset for asset in album.assets}
    video_ids = set()  # Track videos that will be placed after their images
    reordered_assets = []

    for asset in album.assets:
        if asset.id in video_ids:
            # Skip - this video will be added after its image
            continue
        reordered_assets.append(asset)
        if asset.live_photo_video_id and asset.live_photo_video_id in assets_by_id:
            # Add the video immediately after the image
            video_asset = assets_by_id[asset.live_photo_video_id]
            reordered_assets.append(video_asset)
            video_ids.add(asset.live_photo_video_id)

    # Add any orphan videos (videos without corresponding image in the list)
    for asset in album.assets:
        if asset.asset_type == "VIDEO" and asset.id not in video_ids:
            if asset.id not in [a.id for a in reordered_assets]:
                reordered_assets.append(asset)

    album.assets = reordered_assets
    total_assets = len(album.assets)
    batch_size = config.batch_size

    # Collect live photo pairs for linking after upload
    live_photo_pairs: list[tuple[Asset, Asset]] = []
    for asset in album.assets:
        if asset.live_photo_video_id and asset.live_photo_video_id in assets_by_id:
            video_asset = assets_by_id[asset.live_photo_video_id]
            live_photo_pairs.append((asset, video_asset))
            # Track in state for resume capability
            album_state.add_live_photo_pair(
                image_asset_id=asset.id,
                video_asset_id=video_asset.id,
                image_checksum=asset.checksum,
                video_checksum=video_asset.checksum,
            )

    if live_photo_pairs:
        console.print(
            f"[cyan]Found {len(live_photo_pairs)} live photos to link after upload[/cyan]"
        )
        state_manager.save(migration_state)

    console.print(
        f"\n[bold green]Migrating {album.album_name}[/bold green] "
        f"({total_assets} to migrate, {pre_verified_count} pre-verified, "
        f"{original_asset_count} total, batch size: {batch_size})\n"
    )

    # No resume - we always start fresh after pre-verification filtering
    # All remaining assets in album.assets need to be migrated
    remaining_assets = album.assets

    # Calculate total bytes for progress tracking
    total_bytes = sum(
        asset.file_size_bytes for asset in remaining_assets if asset.file_size_bytes is not None
    )

    # Accumulate checksum overrides for assets modified by EXIF injection
    # This will be persisted to state and used for verification
    checksum_overrides: dict[str, str] = {}

    # Track cumulative metrics
    cumulative_exif = ExifMetrics()
    # Initialize with total_pairs from discovered pairs (set once, not accumulated)
    cumulative_live_photos = LivePhotoMetrics(total_pairs=len(live_photo_pairs))

    # Display album header
    console.print(f"\n[bold green]📦 Migrating:[/bold green] {album.album_name}")
    console.print(
        f"[dim]{len(remaining_assets)} assets to download/upload • "
        f"{total_bytes / (1024**2):.1f} MB "
        f"(~{total_bytes * 2 / (1024**2):.1f} MB total with upload)[/dim]\n"
    )

    # Create album-wide progress context
    from ..lib.progress import ProgressContext

    with ProgressContext() as progress:
        # Start overall progress bar tracking download + upload bytes
        progress.start_overall(
            "Migrating",
            total_bytes=total_bytes * 2,
            total_assets=len(remaining_assets),
        )

        # Process in batches
        for batch_num, i in enumerate(range(0, len(remaining_assets), batch_size), start=1):
            batch_assets = remaining_assets[i : i + batch_size]
            batch_dir = config.temp_dir / f"batch_{album.id}_{batch_num}"

            # Download batch with progress tracking
            try:
                successful_paths, failed_ids = await downloader.download_batch(
                    batch_assets, batch_dir, on_progress=progress.update_progress
                )

                if failed_ids:
                    logger.warning(
                        f"Failed to download {len(failed_ids)} assets in batch {batch_num}"
                    )
                    for asset_id in failed_ids:
                        album_state.add_failed_asset(asset_id)

                if not successful_paths:
                    progress.console.print(
                        "[red]✗ No assets downloaded successfully, skipping upload[/red]"
                    )
                    downloader.cleanup_batch(batch_dir)
                    continue

            except Exception as e:
                logger.error(f"Batch download failed: {e}")
                progress.console.print(f"[red]✗ Download failed: {e}[/red]")
                downloader.cleanup_batch(batch_dir)
                continue

            # Inject EXIF dates for assets missing date metadata
            if exif_injector:
                # Get the successfully downloaded assets
                downloaded_assets = [asset for asset in batch_assets if asset.id not in failed_ids]
                exif_metrics, modified_ids, updated_paths, corrupted_ids = (
                    exif_injector.inject_dates_for_batch(downloaded_assets, successful_paths)
                )
                # Update successful_paths to reflect any file renames and
                # normalize to absolute strings
                successful_paths = [str(Path(p).absolute()) for p in updated_paths]  # type: ignore[misc]

                # Update cumulative metrics
                cumulative_exif += exif_metrics

                if exif_metrics.injected > 0:
                    logger.debug(f"Injected dates for {exif_metrics.injected} asset(s)")
                if exif_metrics.failed > 0:
                    logger.warning(f"Failed to inject dates for {exif_metrics.failed} asset(s)")

                # Track corrupted files as permanently failed
                if corrupted_ids:
                    # Prepare album-specific failed dir
                    safe_album_name = "".join(
                        c if c.isalnum() or c in "._-" else "_" for c in album.album_name
                    ).strip()
                    album_failed_dir = failed_output_dir / safe_album_name
                    album_failed_dir.mkdir(parents=True, exist_ok=True)

                    for asset in downloaded_assets:
                        if asset.id in corrupted_ids:
                            # Determine the file path for this asset in updated_paths
                            asset_idx = downloaded_assets.index(asset)
                            local_moved_path = None
                            original_abs_path = None
                            if asset_idx < len(updated_paths):
                                # Get absolute path of original file before moving
                                original_abs_path = str(Path(updated_paths[asset_idx]).absolute())
                                path_to_remove = Path(updated_paths[asset_idx])
                                try:
                                    dest_path = album_failed_dir / path_to_remove.name
                                    # Use shutil.move to be robust across filesystems
                                    shutil.move(str(path_to_remove), str(dest_path))
                                    local_moved_path = str(dest_path.absolute())
                                    # Replace spaces with non-breaking spaces to
                                    # avoid terminal wrapping
                                    nb_path = local_moved_path.replace(" ", "\u00a0")
                                    progress.console.print(
                                        f"[yellow]→ Moved corrupted file to: {nb_path}[/yellow]"
                                    )
                                except Exception as e:
                                    # If move fails, fallback to leaving None
                                    # but still record failure
                                    logger.warning(
                                        f"Failed to move corrupted file {path_to_remove}: {e}"
                                    )
                                    local_moved_path = None

                            album_state.add_permanently_failed_asset(
                                asset_id=asset.id,
                                original_file_name=asset.original_file_name,
                                checksum=asset.checksum,
                                failure_reason=(
                                    "Corrupted file: EXIF injection failed with "
                                    "RIFF format error or truncated data"
                                ),
                                local_path=local_moved_path,
                            )

                            # Remove from successful paths using original absolute path
                            if original_abs_path:
                                successful_paths = [
                                    p
                                    for p in successful_paths
                                    if p != original_abs_path  # type: ignore[comparison-overlap]
                                ]
                    progress.console.print(
                        f"[red]✗ {len(corrupted_ids)} corrupted file(s) excluded from upload[/red]"
                    )

                # Recompute checksums for modified files and persist to state
                # Exclude corrupted files (they've been moved to failed dir)
                if modified_ids:
                    logger.debug(f"Recomputing checksums for {len(modified_ids)} modified assets")
                    for asset, file_path in zip(downloaded_assets, updated_paths):
                        if asset.id in modified_ids and asset.id not in corrupted_ids:
                            # Check if file exists (may have been renamed/moved)
                            if not Path(file_path).exists():
                                logger.warning(
                                    f"Skipping checksum for {asset.original_file_name}: "
                                    f"file not found at {file_path}"
                                )
                                continue
                            new_checksum = compute_file_checksum(file_path)
                            checksum_overrides[asset.id] = new_checksum
                            # Persist to state for verification and future retries
                            album_state.set_checksum_override(asset.id, new_checksum)
                            logger.debug(
                                f"Asset {asset.id}: checksum changed from "
                                f"{asset.checksum[:8]}... to {new_checksum[:8]}..."
                            )
                    state_manager.save(migration_state)

            # Upload batch (skip if no files remain after exclusions)
            try:
                if not successful_paths:
                    logger.warning("No files to upload (all excluded or failed)")
                else:
                    logger.debug(f"Uploading {len(successful_paths)} file(s) via Immich CLI")

                    try:
                        upload_success = uploader.upload_batch(
                            batch_dir,
                            album_name=album.album_name
                            if not album.is_virtual_unalbummed
                            else None,
                        )

                        if upload_success:
                            logger.debug(f"Batch {batch_num} uploaded successfully")
                            album_state.increment_migrated(len(successful_paths))
                            # Update overall progress (count upload bytes and assets)
                            uploaded_bytes = sum(
                                asset.file_size_bytes or 0
                                for asset in batch_assets
                                if asset.id not in failed_ids
                            )
                            progress.update_progress(uploaded_bytes)
                            # Update asset count display
                            progress.update_assets(album_state.migrated_count)
                            state_manager.save(migration_state)

                            # Link any live photo pairs that are now ready
                            unlinked_pairs = album_state.get_unlinked_live_photos()
                            if unlinked_pairs:
                                linked_ids, live_metrics = uploader.link_ready_live_photos(
                                    unlinked_pairs
                                )
                                cumulative_live_photos += live_metrics

                                for image_id in linked_ids:
                                    album_state.mark_live_photo_linked(image_id)
                                if linked_ids:
                                    logger.debug(f"Linked {len(linked_ids)} live photo pair(s)")
                                    state_manager.save(migration_state)
                        else:
                            logger.error(f"Batch {batch_num} upload failed")

                    except Exception as e:
                        logger.error(f"Batch upload failed: {e}")
                        progress.console.print(f"[red]✗ Upload failed: {e}[/red]")

            finally:
                # Cleanup batch
                downloader.cleanup_batch(batch_dir)

    # === VERIFICATION PHASE ===
    # After all batches uploaded, verify assets exist on target and retry missing ones
    console.print("\n[bold cyan]🔍 Verifying uploaded assets...[/bold cyan]")

    await verify_and_retry_missing_assets(
        album=album,
        album_state=album_state,
        old_client=old_client,
        uploader=uploader,
        downloader=downloader,
        exif_injector=exif_injector,
        config=config,
        migration_state=migration_state,
        state_manager=state_manager,
        verify_retries=verify_retries,
        failed_output_dir=failed_output_dir,
        checksum_overrides=checksum_overrides,
    )

    # Check completion (now accounting for verification results)
    # Use original_asset_count since album.assets was filtered to only missing assets
    total_verified = len(album_state.verified_asset_ids)
    total_failed = len(album_state.permanently_failed_assets)
    total_download_failed = len(album_state.failed_asset_ids)

    if total_verified >= original_asset_count:
        album_state.mark_completed()
    elif total_verified > 0:
        if total_failed > 0 or total_download_failed > 0:
            console.print(
                f"\n[yellow]⚠️  Partial migration: "
                f"{total_verified}/{original_asset_count} verified, "
                f"{total_failed} permanently failed, "
                f"{total_download_failed} download failures[/yellow]"
            )
    else:
        album_state.mark_failed("No assets migrated successfully")
        console.print("\n[red]❌ Migration failed - no assets migrated successfully[/red]")

    # Save final state
    state_manager.save(migration_state)

    # Display comprehensive summary
    duration = time.time() - start_time
    display_migration_summary(
        album_name=album.album_name,
        total=original_asset_count,
        migrated=total_verified,
        failed=total_failed + total_download_failed,
        duration=duration,
        exif_metrics=cumulative_exif,
        live_photo_metrics=cumulative_live_photos,
    )


async def verify_and_retry_missing_assets(
    album: Album,
    album_state: AlbumState,
    old_client: ImmichClient,
    uploader: Uploader,
    downloader: Downloader,
    exif_injector: ExifInjector | None,
    config: Config,
    migration_state: MigrationState,
    state_manager: StateManager,
    verify_retries: int,
    failed_output_dir: Path,
    checksum_overrides: dict[str, str],
) -> None:
    """Verify all assets exist on target, retry missing ones, and save permanent failures.

    This function:
    1. Verifies all album assets exist on the target server by checksum
    2. Retries missing assets up to verify_retries times with full processing (batched)
    3. Downloads permanently failed assets to failed_output_dir for manual recovery

    Args:
        album: Album being migrated
        album_state: State tracking for this album
        old_client: Client for source server
        uploader: Uploader instance for target server
        downloader: Downloader instance
        exif_injector: EXIF injector (may be None)
        config: Application config
        migration_state: Root migration state
        state_manager: State persistence manager
        verify_retries: Number of retry attempts
        failed_output_dir: Directory for failed assets
        checksum_overrides: Dict mapping asset_id -> checksum for EXIF-modified assets
                           (merged with state's persisted overrides)
    """
    logger = get_logger()  # type: ignore[no-untyped-call]

    # Merge passed overrides with state's persisted overrides (passed takes precedence)
    effective_overrides = {**album_state.checksum_overrides, **checksum_overrides}

    # Build a map of all assets by ID for easy lookup
    assets_by_id = {asset.id: asset for asset in album.assets}

    # Get assets that weren't already marked as download failures
    assets_to_verify = [
        asset for asset in album.assets if asset.id not in album_state.failed_asset_ids
    ]

    if not assets_to_verify:
        console.print("[yellow]No assets to verify (all failed during download)[/yellow]")
        return

    # Initial verification using effective checksum overrides
    verified_ids, missing_ids = uploader.verify_assets_exist(
        assets_to_verify, checksum_overrides=effective_overrides
    )

    # Update state with initial verification results
    for asset_id in verified_ids:
        album_state.add_verified_asset(asset_id)

    for asset_id in missing_ids:
        album_state.add_missing_asset(asset_id)

    state_manager.save(migration_state)

    console.print(
        f"[cyan]Initial verification:[/cyan] {len(verified_ids)} verified, "
        f"{len(missing_ids)} missing"
    )

    if not missing_ids:
        console.print("[green]✓ All assets verified on target server[/green]")
        return

    # Retry missing assets in batches
    batch_size = config.batch_size

    if verify_retries > 0:
        console.print(
            f"\n[bold cyan]Retrying {len(missing_ids)} missing assets "
            f"(max {verify_retries} attempts, batch size {batch_size})...[/bold cyan]"
        )

        for attempt in range(1, verify_retries + 1):
            if not album_state.missing_asset_ids:
                break

            console.print(f"\n[cyan]Retry attempt {attempt}/{verify_retries}[/cyan]")

            # Get current missing assets
            missing_assets = [
                assets_by_id[asset_id]
                for asset_id in album_state.missing_asset_ids
                if asset_id in assets_by_id
            ]

            if not missing_assets:
                break

            # Process missing assets in batches (same batch size as main migration)
            total_retry_verified = 0
            total_retry_still_missing = 0

            for batch_start in range(0, len(missing_assets), batch_size):
                batch_assets = missing_assets[batch_start : batch_start + batch_size]
                batch_num = batch_start // batch_size + 1
                total_batches = (len(missing_assets) + batch_size - 1) // batch_size

                console.print(
                    f"  Batch {batch_num}/{total_batches}: Processing {len(batch_assets)} assets..."
                )

                retry_batch_dir = config.temp_dir / f"retry_{album.id}_{attempt}_{batch_num}"

                try:
                    # Download batch
                    successful_paths, failed_ids = await downloader.download_batch(
                        batch_assets, retry_batch_dir
                    )

                    if not successful_paths:
                        console.print("    [red]All downloads failed[/red]")
                        # Track download failures
                        for asset_id in failed_ids:
                            asset = assets_by_id.get(asset_id)
                            if asset:
                                album_state.add_permanently_failed_asset(
                                    asset_id=asset_id,
                                    original_file_name=asset.original_file_name,
                                    checksum=asset.checksum,
                                    failure_reason=f"Download failed on retry {attempt}",
                                )
                        continue

                    # EXIF injection (only for non-live-photo assets, but we handle all here)
                    if exif_injector:
                        downloaded_assets = [a for a in batch_assets if a.id not in failed_ids]
                        exif_metrics, modified_ids, updated_paths, corrupted_ids = (
                            exif_injector.inject_dates_for_batch(
                                downloaded_assets, successful_paths
                            )
                        )
                        successful_paths = [str(Path(p).absolute()) for p in updated_paths]  # type: ignore[misc]

                        if exif_metrics.injected > 0:
                            console.print(
                                f"    Injected EXIF dates for {exif_metrics.injected} asset(s)"
                            )

                        # Handle corrupted files
                        if corrupted_ids:
                            safe_album_name = "".join(
                                c if c.isalnum() or c in "._-" else "_" for c in album.album_name
                            ).strip()
                            album_failed_dir = failed_output_dir / safe_album_name
                            album_failed_dir.mkdir(parents=True, exist_ok=True)

                            for asset in downloaded_assets:
                                if asset.id in corrupted_ids:
                                    asset_idx = downloaded_assets.index(asset)
                                    local_moved_path = None
                                    original_abs_path = None
                                    if asset_idx < len(updated_paths):
                                        original_abs_path = str(
                                            Path(updated_paths[asset_idx]).absolute()
                                        )
                                        path_to_remove = Path(updated_paths[asset_idx])
                                        try:
                                            dest_path = album_failed_dir / path_to_remove.name
                                            shutil.move(str(path_to_remove), str(dest_path))
                                            local_moved_path = str(dest_path.absolute())
                                        except Exception as e:
                                            logger.warning(
                                                f"Failed to move corrupted: {path_to_remove}: {e}"
                                            )

                                    album_state.add_permanently_failed_asset(
                                        asset_id=asset.id,
                                        original_file_name=asset.original_file_name,
                                        checksum=asset.checksum,
                                        failure_reason=(
                                            "Corrupted file: EXIF injection failed during retry"
                                        ),
                                        local_path=local_moved_path,
                                    )

                                    if original_abs_path:
                                        successful_paths = [
                                            p
                                            for p in successful_paths
                                            if p != original_abs_path  # type: ignore[comparison-overlap]
                                        ]

                            console.print(
                                f"    [red]✗ {len(corrupted_ids)} corrupted file(s) excluded[/red]"
                            )

                        # Persist checksum overrides for modified files
                        # Exclude corrupted files (they've been moved to failed dir)
                        if modified_ids:
                            for asset, file_path in zip(downloaded_assets, updated_paths):
                                if asset.id in modified_ids and asset.id not in corrupted_ids:
                                    # Check if file exists (may have been renamed/moved)
                                    if not Path(file_path).exists():
                                        logger.warning(
                                            f"Skipping checksum for {asset.original_file_name}: "
                                            f"file not found at {file_path}"
                                        )
                                        continue
                                    new_checksum = compute_file_checksum(file_path)
                                    effective_overrides[asset.id] = new_checksum
                                    album_state.set_checksum_override(asset.id, new_checksum)

                    # Upload batch
                    if not successful_paths:
                        console.print("    [yellow]No files to upload[/yellow]")
                    else:
                        upload_success = uploader.upload_batch(
                            retry_batch_dir,
                            album_name=album.album_name
                            if not album.is_virtual_unalbummed
                            else None,
                        )

                        if upload_success:
                            console.print(
                                f"    [green]✓ Uploaded {len(successful_paths)} files[/green]"
                            )

                            # Link live photos
                            unlinked_pairs = album_state.get_unlinked_live_photos()
                            if unlinked_pairs:
                                linked_ids, _ = uploader.link_ready_live_photos(unlinked_pairs)
                                for image_id in linked_ids:
                                    album_state.mark_live_photo_linked(image_id)
                                if linked_ids:
                                    console.print(
                                        f"    [green]✓ Linked {len(linked_ids)} live pairs[/green]"
                                    )
                        else:
                            console.print("    [red]✗ Upload failed[/red]")

                    # Verify this batch
                    retry_assets = [a for a in batch_assets if a.id not in failed_ids]
                    newly_verified, still_missing = uploader.verify_assets_exist(
                        retry_assets, checksum_overrides=effective_overrides
                    )

                    for asset_id in newly_verified:
                        album_state.add_verified_asset(asset_id)

                    total_retry_verified += len(newly_verified)
                    total_retry_still_missing += len(still_missing)

                except Exception as e:
                    logger.error(f"Retry batch {batch_num} failed: {e}")
                    console.print(f"    [red]✗ Batch failed: {e}[/red]")

                finally:
                    downloader.cleanup_batch(retry_batch_dir)

                state_manager.save(migration_state)

            console.print(
                f"  Attempt {attempt} complete: {total_retry_verified} verified, "
                f"{total_retry_still_missing} still missing"
            )

    # Handle permanently failed assets
    permanently_missing = [
        assets_by_id[asset_id]
        for asset_id in album_state.missing_asset_ids
        if asset_id in assets_by_id
    ]

    if permanently_missing:
        console.print(
            f"\n[bold red]{len(permanently_missing)} asset(s) could not be migrated[/bold red]"
        )

        # Ask user if they want to download failed assets
        try:
            save_choice = typer.confirm("Download failed assets for manual recovery?", default=True)
        except KeyboardInterrupt:
            save_choice = False

        if save_choice:
            await save_failed_assets(
                assets=permanently_missing,
                album=album,
                album_state=album_state,
                old_client=old_client,
                failed_output_dir=failed_output_dir,
                state_manager=state_manager,
                migration_state=migration_state,
            )
        else:
            # Mark as permanently failed without saving
            for asset in permanently_missing:
                album_state.add_permanently_failed_asset(
                    asset_id=asset.id,
                    original_file_name=asset.original_file_name,
                    checksum=asset.checksum,
                    failure_reason="Upload verification failed, user declined download",
                )
            state_manager.save(migration_state)


async def save_failed_assets(
    assets: list[Asset],
    album: Album,
    album_state: AlbumState,
    old_client: ImmichClient,
    failed_output_dir: Path,
    state_manager: StateManager,
    migration_state: MigrationState,
) -> None:
    """Download and save permanently failed assets for manual recovery.

    Args:
        assets: List of Asset instances to save
        album: Album being migrated
        album_state: State tracking for this album
        old_client: Client for source server
        failed_output_dir: Base directory for failed assets
        state_manager: State persistence manager
        migration_state: Root migration state
    """
    logger = get_logger()  # type: ignore[no-untyped-call]

    # Create album-specific directory
    safe_album_name = "".join(
        c if c.isalnum() or c in "._-" else "_" for c in album.album_name
    ).strip()
    album_failed_dir = failed_output_dir / safe_album_name
    album_failed_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"\n[bold]Downloading failed assets to:[/bold] {album_failed_dir.absolute()}")

    saved_count = 0
    for asset in assets:
        dest_path = album_failed_dir / asset.original_file_name

        try:
            await old_client.download_asset(asset, dest_path)
            logger.info(f"Saved failed asset: {dest_path}")

            album_state.add_permanently_failed_asset(
                asset_id=asset.id,
                original_file_name=asset.original_file_name,
                checksum=asset.checksum,
                failure_reason="Upload verification failed after retries",
                local_path=str(dest_path.absolute()),
            )
            saved_count += 1

            console.print(f"  [green]✓[/green] {asset.original_file_name}")

        except Exception as e:
            logger.error(f"Failed to download asset {asset.original_file_name}: {e}")
            album_state.add_permanently_failed_asset(
                asset_id=asset.id,
                original_file_name=asset.original_file_name,
                checksum=asset.checksum,
                failure_reason=f"Upload failed and recovery download failed: {e}",
            )
            console.print(f"  [red]✗[/red] {asset.original_file_name}: {e}")

    state_manager.save(migration_state)

    console.print(f"\n[bold]Saved {saved_count}/{len(assets)} failed assets to:[/bold]")
    console.print(f"  [cyan]{album_failed_dir.absolute()}[/cyan]")
    logger.info(f"Failed assets saved to: {album_failed_dir.absolute()}")


@app.command()
def version() -> None:
    """Show version information."""
    console.print(f"immich-migrator version {__version__}")


if __name__ == "__main__":
    app()
