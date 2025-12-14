# AGENTS.md

AI agent onboarding guide for immich-migrator codebase.

## What is immich-migrator?

CLI tool for migrating photo albums between Immich servers. Downloads assets from old server, preserves EXIF metadata, uploads to new server with album organization intact.

**Tech Stack**: Python 3.11+, async I/O (httpx), Typer CLI, Pydantic models, pytest, loguru, rich and questionary.

## Architecture

```text
src/immich_migrator/
├── cli/           # Typer CLI app + interactive TUI (questionary)
├── models/        # Pydantic data models (Asset, Album, Config, State)
├── services/      # Business logic (ImmichClient, Downloader, Uploader, StateManager)
└── lib/           # Shared utilities (logging, progress tracking)
```

**Data flow**: CLI → Services → ImmichClient (async API) → Immich API
**Upload**: Uses official `immich` CLI (subprocess) for reliability

## Development Tooling

- **uv**: Package manager and virtual environment manager
- **justfile**: Task automation (run `uv run just help` to see available commands)
- **pre-commit**: Runs ruff + mypy on commit

⚠️ **Always prefix commands with `uv run`** to use the project's virtual environment.

## Critical Testing Rule

⚠️ **Changes to `src/immich_migrator/` MUST pass `uv run just check` before commit.**

This runs pre-commit hooks and the full test suite.

Documentation, tooling, or script changes MAY skip if no functional impact.

## Task-Specific Guides

Read these files when relevant to your task (progressive disclosure):

- **`agent_docs/development_workflow.md`** — uv commands, justfile tasks, pre-commit setup
- **`agent_docs/testing_strategy.md`** — Unit/integration/contract tests, when to use each
- **`agent_docs/code_patterns.md`** — Service architecture, async patterns, error handling
- **`agent_docs/quality_gates.md`** — When to run tests, linter usage, coverage requirements
