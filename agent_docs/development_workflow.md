# Development Workflow

How to work with immich-migrator using uv, justfile, and pre-commit.

## Package Management: uv

We use [uv](https://github.com/astral-sh/uv) for fast, reliable Python package management.

### Common Commands

```bash
# Install all dependencies (dev, test, main)
uv run just install
# or manually:
uv sync --all-groups

# Add a new dependency
uv add <package>

# Add a dev/test dependency
uv add --group dev <package>
uv add --group test <package>

# Run commands in the project environment (always use uv run)
uv run python script.py
uv run pytest
uv run just check
```

## Task Automation: justfile

Central task runner for all operations. View available tasks:

```bash
uv run just help
```

⚠️ **Critical**: Always prefix commands with `uv run` to use the project's virtual environment.

```bash
# Correct
uv run just check
uv run just test
uv run pytest tests/unit

# Wrong (will use wrong Python/packages)
just check
pytest tests/unit
```

The justfile wraps common operations for consistency with CI/CD. Prefer justfile tasks over running tools directly when available.

## Pre-commit Hooks

Automatically runs on `git commit`:

- **ruff**: Format + lint Python code
- **mypy**: Type checking
- **yamllint**: YAML validation
- Other file checks (trailing whitespace, merge conflicts, etc.)

### Setup

```bash
# Install hooks (one-time)
uv run pre-commit install

# Run manually on all files
uv run just lint
```

### Bypass (use sparingly)

```bash
git commit --no-verify
```

Only bypass for docs/config changes that don't affect code.

## File Structure Reference

See authoritative examples:

- **Async patterns**: `src/immich_migrator/services/immich_client.py:45` (async context manager)
- **Subprocess handling**: `src/immich_migrator/services/uploader.py:60` (immich CLI wrapper)
- **CLI structure**: `src/immich_migrator/cli/app.py:1` (Typer app setup)
- **Pydantic models**: `src/immich_migrator/models/config.py:1` (validation patterns)

## Making Changes

1. Create feature branch: `git checkout -b feature/name`
2. Make changes
3. Run `uv run just check` (pre-commit + tests)
4. Commit (pre-commit runs automatically)
5. Push and create PR

Pre-commit will block commits that fail linting or type checking. Fix issues before committing.
