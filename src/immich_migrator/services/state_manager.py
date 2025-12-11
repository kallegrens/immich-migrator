"""State management for migration progress persistence."""

import json
from pathlib import Path

from ..lib.logging import get_logger
from ..models.state import MigrationState

logger = get_logger()  # type: ignore[no-untyped-call]


class StateManager:
    """Manages loading and saving migration state with atomic writes."""

    def __init__(self, state_file: Path):
        """Initialize state manager.

        Args:
            state_file: Path to JSON state file
        """
        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> MigrationState:
        """Load migration state from file.

        Returns:
            MigrationState instance (new if file doesn't exist)
        """
        if not self.state_file.exists():
            logger.info(f"No existing state file found at {self.state_file}, creating new state")
            return MigrationState()

        try:
            with open(self.state_file) as f:
                data = json.load(f)

            state = MigrationState.model_validate(data)
            logger.info(
                f"Loaded state from {self.state_file}: "
                f"{len(state.albums)} albums, "
                f"{state.get_completed_count()} completed"
            )
            return state

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to load state file {self.state_file}: {e}")
            logger.info("Creating new state")
            return MigrationState()

    def save(self, state: MigrationState) -> None:
        """Save migration state with atomic write.

        Uses temp file + rename pattern to ensure atomicity.

        Args:
            state: MigrationState to persist
        """
        # Serialize to JSON
        data = state.model_dump(mode="json")

        # Write to temporary file
        temp_file = self.state_file.with_suffix(".tmp")
        try:
            with open(temp_file, "w") as f:
                json.dump(data, f, indent=2, default=str)

            # Atomic rename
            temp_file.replace(self.state_file)

            logger.debug(
                f"Saved state to {self.state_file}: "
                f"{len(state.albums)} albums, "
                f"{state.get_completed_count()} completed"
            )

        except Exception as e:
            logger.error(f"Failed to save state to {self.state_file}: {e}")
            if temp_file.exists():
                temp_file.unlink()
            raise

    def backup(self) -> Path | None:
        """Create backup of current state file.

        Returns:
            Path to backup file or None if no state file exists
        """
        if not self.state_file.exists():
            return None

        backup_file = self.state_file.with_suffix(".backup.json")
        try:
            backup_file.write_bytes(self.state_file.read_bytes())
            logger.info(f"Created backup at {backup_file}")
            return backup_file
        except Exception as e:
            logger.warning(f"Failed to create backup: {e}")
            return None
