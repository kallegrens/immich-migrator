# Quality Gates

When to run tests, how to use linters, and what must pass before committing.

## Prerequisites

- **Python**: 3.11 or higher
- **uv**: Package manager (always use `uv run` prefix)
- **exiftool**: For EXIF metadata handling

## The Golden Rule

⚠️ **Changes to `src/immich_migrator/` MUST pass `uv run just check` before commit.**

Changes to these directories MAY skip validation if they have no functional impact:

- `docs/`
- `scripts/` (helper scripts, not source code)
- `tests/` (test-only changes)
- `agent_docs/`
- Root-level docs (README.md, CONTRIBUTING.md, etc.)

**When in doubt, run `uv run just check`.**

## What Validation Does

Runs the full validation pipeline:

1. **Pre-commit hooks**
   - ruff format (code formatting)
   - ruff check (linting)
   - mypy (type checking)
   - yamllint (YAML validation)
   - trailing whitespace, end-of-file fixes
   - merge conflict detection

2. **Test suite**
   - All pytest tests (unit + integration + contract)
   - Must pass with 0 failures

## Quick Commands

⚠️ **Always use `uv run` prefix**

```bash
# Full validation (pre-commit + tests)
uv run just check

# Only linting (fast)
uv run just lint

# Only formatting (auto-fixes)
uv run just fmt

# Only tests
uv run just test

# Tests with coverage
uv run just test-cov
```

## Linter Usage

### Let Tools Handle Style

**DO NOT** manually format code or fix style issues. Let ruff and mypy handle it:

```bash
# Auto-format and fix linting issues
uv run just fmt

# Check without fixing
uv run just lint
```

Ruff handles:

- Code formatting (PEP 8, line length, imports)
- Common code smells
- Import sorting
- Unused imports/variables

Mypy handles:

- Type checking
- Type annotation validation
- Return type verification

### Fixing Type Errors

If mypy reports type errors:

1. Fix the types (add annotations, fix return types)
2. **DO NOT** add `# type: ignore` unless absolutely necessary
3. **DO NOT** disable type checking to "fix" errors

See `pyproject.toml` for mypy config (strict mode enabled).

## Coverage Requirements

Minimum coverage: **70%**

Check coverage locally:

```bash
uv run just test-cov
```

Opens `htmlcov/index.html` with line-by-line coverage report.

### What to Cover

Prioritize:

- Core business logic (`services/`)
- API interactions (`immich_client.py`)
- Data models (`models/`)

Skip:

- CLI interface details (hard to test)
- Logging statements
- `if TYPE_CHECKING:` blocks

## Pre-commit Hooks

Installed automatically on first commit. Run manually:

```bash
uv run just lint
```

Hooks run on staged files only. To run on all files:

```bash
uv run pre-commit run --all-files
```

### Bypass (Emergency Only)

```bash
git commit --no-verify
```

Only use for:

- Hotfixes that need immediate deployment
- Documentation-only changes
- CI/CD config changes

**Never bypass for source code changes.**

## CI/CD Integration

GitHub Actions runs the full validation pipeline on every push. PRs cannot merge if:

- Linting fails
- Type checking fails
- Tests fail
- Coverage drops below 70%

Match local validation to CI by running `uv run just check` before pushing.

## Debugging Failures

### Linting Failures

```bash
# See what would be fixed
uv run just lint

# Auto-fix issues
uv run just fmt

# Check specific file
uv run ruff check src/immich_migrator/services/uploader.py
```

### Type Checking Failures

```bash
# Check specific file
uv run mypy src/immich_migrator/services/uploader.py

# See full error context
uv run mypy --show-error-context src/immich_migrator/
```

### Test Failures

```bash
# Run specific test
uv run pytest tests/unit/test_services.py::TestUploader::test_uploader_check_cli_installed -v

# Run with print statements visible
uv run pytest -s

# Run with detailed failure info
uv run pytest -vv
```

## Release Checklist

Before releasing:

```bash
# Run full pipeline
uv run just all
```

This runs the complete release pipeline: clean, check, build, verify, and test-install.
