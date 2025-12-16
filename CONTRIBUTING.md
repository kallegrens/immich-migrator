# Contributing to immich-migrator

Thank you for your interest in contributing to immich-migrator! This document provides guidelines and instructions for contributing.

## Development Setup

### Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- git
- exiftool (`libimage-exiftool-perl` on Ubuntu/Debian)

### Getting Started

1. **Fork and clone the repository**

```bash
git clone https://github.com/kallegrens/immich-migrator.git
cd immich-migrator
```

2. **Install dependencies**

```bash
uv sync --all-groups
```

3. **Install pre-commit hooks**

```bash
uv run pre-commit install
```

This will automatically run linting and type checking before each commit.

## Development Workflow

### Running Tests

We have three types of tests:

```bash
# Run unit tests (fast, no I/O)
uv run pytest tests/unit -v -m unit

# Run integration tests (may use real files)
uv run pytest tests/integration -v -m integration

# Run contract tests (API/CLI compliance)
uv run pytest tests/contract -v -m contract

# Run all tests with coverage
uv run pytest tests/ -v --cov=src/immich_migrator --cov-report=term-missing
```

### Code Quality

#### Linting with Ruff

```bash
# Check for issues
uv run ruff check src/ tests/

# Auto-fix issues
uv run ruff check --fix src/ tests/

# Format code
uv run ruff format src/ tests/
```

#### Type Checking with mypy

```bash
uv run mypy src/immich_migrator
```

#### Pre-commit Hooks

All checks run automatically on commit. To run manually:

```bash
uv run pre-commit run --all-files
```

## Code Style

- **Line length**: 100 characters
- **Python version**: 3.12+
- **Type hints**: Required for all functions and methods
- **Docstrings**: Use for public APIs and complex logic
- **Imports**: Sorted and organized by ruff

## Testing Guidelines

- Write tests for all new features
- Maintain minimum 70% coverage
- Use appropriate markers (`@pytest.mark.unit`, `@pytest.mark.integration`)
- Mock external dependencies (Immich API, filesystem)
- Follow AAA pattern: Arrange, Act, Assert

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `test:` Test additions or changes
- `refactor:` Code refactoring
- `chore:` Maintenance tasks
- `ci:` CI/CD changes

Examples:

```text
feat: add support for video migration
fix: handle missing EXIF data gracefully
docs: update installation instructions
```

## Pull Request Process

1. **Create a feature branch**

   ```bash
   git checkout -b feat/your-feature-name
   ```

2. **Make your changes**
   - Write code
   - Add tests
   - Update documentation

3. **Ensure all checks pass**

   ```bash
   uv run pytest tests/ -v --cov=src/immich_migrator --cov-fail-under=70
   uv run ruff check src/ tests/
   uv run ruff format --check src/ tests/
   uv run mypy src/immich_migrator
   ```

4. **Commit your changes**
   - Pre-commit hooks will run automatically
   - Fix any issues before committing

5. **Push and create PR**

   ```bash
   git push origin feat/your-feature-name
   ```

6. **PR requirements**
   - Clear description of changes
   - Tests pass on CI
   - Coverage maintained or improved
   - Documentation updated if needed
   - Follows code style guidelines

## Project Structure

```text
immich-migrator/
├── src/immich_migrator/
│   ├── cli/           # CLI interface and TUI
│   ├── lib/           # Shared utilities
│   ├── models/        # Data models
│   └── services/      # Business logic
├── tests/
│   ├── unit/          # Unit tests
│   ├── integration/   # Integration tests
│   └── contract/      # API/CLI contract tests
├── specs/             # Project specifications
└── scripts/           # Helper scripts
```

## Getting Help

- **Issues**: Check existing issues or create a new one
- **Discussions**: For questions and feature requests
- **Documentation**: See README.md and specs/

## Code of Conduct

Be respectful, inclusive, and constructive. We're all here to build something useful together.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
