"""Integration tests for CLI commands.

Tests the CLI entry points with mocked API calls to verify:
- Command parsing and validation
- Credential loading
- State management
- Error handling
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from immich_migrator.cli.app import app
from immich_migrator.models.album import Album
from immich_migrator.models.asset import Asset

runner = CliRunner()


def _mock_asyncio_run(coro):
    """Mock asyncio.run that properly closes coroutines to avoid warnings."""
    coro.close()
    return None


@pytest.fixture
def mock_credentials_file(tmp_path):
    """Create a temporary credentials file."""
    creds_file = tmp_path / ".immich.env"
    creds_file.write_text(
        """OLD_IMMICH_SERVER_URL=http://old.server
OLD_IMMICH_API_KEY=old-key-123
NEW_IMMICH_SERVER_URL=http://new.server
NEW_IMMICH_API_KEY=new-key-456
"""
    )
    return creds_file


@pytest.fixture
def mock_immich_client():
    """Create a mocked ImmichClient."""
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)

    # Mock album listing
    client.list_albums = AsyncMock(
        return_value=[
            Album(
                id="album-1",
                album_name="Test Album",
                asset_count=5,
                created_at=datetime(2024, 1, 1, tzinfo=UTC),
            )
        ]
    )

    # Mock unalbummed assets search
    client.search_unalbummed_assets = AsyncMock(return_value=[])

    # Mock asset fetching
    client.get_album_assets = AsyncMock(
        return_value=[
            Asset(
                id="asset-1",
                asset_type="IMAGE",
                original_file_name="test.jpg",
                original_mime_type="image/jpeg",
                checksum="abc123def456" * 4,  # SHA1 is 40 chars
                file_created_at=datetime(2024, 1, 1, tzinfo=UTC),
                file_size_bytes=1024,
            )
        ]
    )

    return client


class TestCliCredentials:
    """Tests for credential loading and validation."""

    def test_default_credentials_file_used(self, tmp_path, mock_credentials_file):
        """Test that ~/.immich.env is used by default."""
        # Move creds to home directory location
        home_creds = tmp_path / "home" / ".immich.env"
        home_creds.parent.mkdir(parents=True)
        home_creds.write_text(mock_credentials_file.read_text())

        with patch("immich_migrator.cli.app.Path.home", return_value=tmp_path / "home"):
            with patch("immich_migrator.cli.app.asyncio.run", side_effect=_mock_asyncio_run):
                result = runner.invoke(app, ["migrate"])
                # Should attempt to load credentials and run migration
                assert result.exit_code == 0

    def test_custom_credentials_file(self, mock_credentials_file):
        """Test loading credentials from custom path."""
        with patch("immich_migrator.cli.app.asyncio.run", side_effect=_mock_asyncio_run):
            result = runner.invoke(app, ["migrate", "--credentials", str(mock_credentials_file)])
            # Should load credentials successfully
            assert result.exit_code == 0
            assert "Loading credentials" in result.stdout

    def test_missing_credentials_file_error(self, tmp_path):
        """Test error when credentials file doesn't exist."""
        nonexistent = tmp_path / "missing.env"
        result = runner.invoke(app, ["migrate", "--credentials", str(nonexistent)])
        assert result.exit_code == 2  # Typer validation error
        # Typer outputs validation errors to stderr, but CliRunner captures both
        output = result.stdout + (result.stderr or "")
        assert "does not exist" in output.lower()

    def test_invalid_credentials_format(self, tmp_path):
        """Test error when credentials file has wrong format."""
        bad_creds = tmp_path / ".immich.env"
        bad_creds.write_text("INVALID=content\n")

        with patch(
            "immich_migrator.models.config.ImmichCredentials.from_env_file"
        ) as mock_from_env:
            mock_from_env.side_effect = KeyError("Missing required key")
            result = runner.invoke(app, ["migrate", "--credentials", str(bad_creds)])
            assert result.exit_code == 1


class TestCliOptions:
    """Tests for CLI option parsing."""

    def test_batch_size_option(self, mock_credentials_file):
        """Test --batch-size option is parsed."""
        with patch("immich_migrator.cli.app.asyncio.run", side_effect=_mock_asyncio_run):
            result = runner.invoke(
                app,
                ["migrate", "--credentials", str(mock_credentials_file), "--batch-size", "50"],
            )
            assert result.exit_code == 0

    def test_log_level_option(self, mock_credentials_file):
        """Test --log-level option is parsed."""
        with patch("immich_migrator.cli.app.asyncio.run", side_effect=_mock_asyncio_run):
            result = runner.invoke(
                app,
                [
                    "migrate",
                    "--credentials",
                    str(mock_credentials_file),
                    "--log-level",
                    "DEBUG",
                ],
            )
            assert result.exit_code == 0
            # Should not error on valid log level
            output = result.stdout + (result.stderr or "")
            assert "invalid" not in output.lower()

    def test_state_file_option(self, mock_credentials_file, tmp_path):
        """Test --state-file option is parsed."""
        state_file = tmp_path / "custom_state.json"
        with patch("immich_migrator.cli.app.asyncio.run", side_effect=_mock_asyncio_run):
            result = runner.invoke(
                app,
                [
                    "migrate",
                    "--credentials",
                    str(mock_credentials_file),
                    "--state-file",
                    str(state_file),
                ],
            )
            assert result.exit_code == 0

    def test_temp_dir_option(self, mock_credentials_file, tmp_path):
        """Test --temp-dir option is parsed."""
        temp_dir = tmp_path / "custom_temp"
        temp_dir.mkdir()
        with patch("immich_migrator.cli.app.asyncio.run", side_effect=_mock_asyncio_run):
            result = runner.invoke(
                app,
                [
                    "migrate",
                    "--credentials",
                    str(mock_credentials_file),
                    "--temp-dir",
                    str(temp_dir),
                ],
            )
            assert result.exit_code == 0

    def test_batch_size_validation_min(self, mock_credentials_file):
        """Test batch size minimum validation."""
        result = runner.invoke(
            app,
            ["migrate", "--credentials", str(mock_credentials_file), "--batch-size", "0"],
        )
        assert result.exit_code == 2  # Validation error

    def test_batch_size_validation_max(self, mock_credentials_file):
        """Test batch size maximum validation."""
        result = runner.invoke(
            app,
            ["migrate", "--credentials", str(mock_credentials_file), "--batch-size", "101"],
        )
        assert result.exit_code == 2  # Validation error


class TestCliErrorHandling:
    """Tests for CLI error handling."""

    def test_keyboard_interrupt_handling(self, mock_credentials_file):
        """Test graceful handling of Ctrl+C."""

        def _raise_keyboard_interrupt(coro):
            coro.close()
            raise KeyboardInterrupt()

        with patch("immich_migrator.cli.app.asyncio.run") as mock_run:
            mock_run.side_effect = _raise_keyboard_interrupt
            result = runner.invoke(app, ["migrate", "--credentials", str(mock_credentials_file)])
            assert result.exit_code == 130  # Unix convention for SIGINT
            output = result.stdout + (result.stderr or "")
            assert "interrupted" in output.lower()

    def test_general_exception_handling(self, mock_credentials_file):
        """Test handling of unexpected exceptions."""

        def _raise_runtime_error(coro):
            coro.close()
            raise RuntimeError("Something went wrong")

        with patch("immich_migrator.cli.app.asyncio.run") as mock_run:
            mock_run.side_effect = _raise_runtime_error
            result = runner.invoke(app, ["migrate", "--credentials", str(mock_credentials_file)])
            assert result.exit_code == 1
            output = result.stdout + (result.stderr or "")
            assert "error" in output.lower()


class TestCliOutput:
    """Tests for CLI output formatting."""

    def test_version_display(self, mock_credentials_file):
        """Test that version is displayed on startup."""
        with patch("immich_migrator.cli.app.asyncio.run", side_effect=_mock_asyncio_run):
            result = runner.invoke(app, ["migrate", "--credentials", str(mock_credentials_file)])
            assert result.exit_code == 0
            assert "Migration Tool" in result.stdout

    def test_credentials_loading_message(self, mock_credentials_file):
        """Test credentials loading message is displayed."""
        with patch("immich_migrator.cli.app.asyncio.run", side_effect=_mock_asyncio_run):
            result = runner.invoke(app, ["migrate", "--credentials", str(mock_credentials_file)])
            assert result.exit_code == 0
            assert "Loading credentials" in result.stdout
