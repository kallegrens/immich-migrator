<!--

Sync Impact Report

Version change: template (unspecified) -> 1.0.0

Modified principles:
- PRINCIPLE_1 (template placeholder) -> Code Quality (NON-NEGOTIABLE)
- PRINCIPLE_2 (template placeholder) -> Testing Standards (NON-NEGOTIABLE)
- PRINCIPLE_3 (template placeholder) -> User Experience Consistency (GUIDING)
- PRINCIPLE_4 (template placeholder) -> Performance Requirements (NON-NEGOTIABLE)
- PRINCIPLE_5 (template placeholder) -> Simplicity & Observability (CROSS-CUTTING)

Added sections:
- Constraints & Standards
- Development Workflow & Quality Gates

Removed sections:
- None

Templates requiring updates:
- `.specify/templates/plan-template.md`: ✅ updated
- `.specify/templates/tasks-template.md`: ✅ updated
- `.specify/templates/spec-template.md`: ⚠ pending (reviewed — no mandatory changes)
- `.specify/templates/commands/*`: ⚠ pending (directory not found; verify external command docs)

Follow-up TODOs:
- RATIFICATION_DATE is unknown — TODO(RATIFICATION_DATE): confirm original adoption date
-->

# Immich Migrator Constitution

## Core Principles

### Code Quality (NON-NEGOTIABLE)

All production code MUST be clear, maintainable, and reviewable. Code quality rules:

- MUST follow the repository's style and linting rules; formatting tools MUST run in CI.
- MUST include meaningful names, limited function length, and a single responsibility per unit.
- MUST include automated static analysis where applicable (linters, type checks).

Rationale: High-quality code reduces defects and long-term maintenance cost; it is testable and enables confident refactors.

### Testing Standards (NON-NEGOTIABLE)

Testing is mandatory and test-first where practical. Rules:

- For every user-impacting change, automated tests MUST be added: unit tests for logic, integration/contract tests for public interfaces, and end-to-end tests for critical user journeys.
- Tests MUST be written before or alongside implementation and MUST fail initially (Red-Green-Refactor cycle). CI MUST run tests on every PR and block merges on failing critical tests (P1/P2 as defined in specs).
- Test coverage goals: critical paths MUST have high coverage; coverage thresholds for new code MUST be defined in the feature spec.

Rationale: Requiring tests prevents regressions and documents expected behavior; failing tests provide a safety net for maintainers.

### User Experience Consistency (GUIDING)

User-facing behaviors and CLI/UX flows MUST be consistent across features. Rules:

- UX patterns, CLI flags, and output formats MUST follow documented conventions in `docs/quickstart.md` or plan/spec files.
- API and CLI outputs intended for machine consumption MUST provide stable structured formats (JSON) and semantic versioning for breaking changes.

Rationale: Consistency reduces user friction and support burden; it enables predictable integrations for downstream consumers.

### Performance Requirements (NON-NEGOTIABLE)

Performance constraints are part of the spec and MUST be treated as first-class requirements. Rules:

- Every feature spec MUST state performance goals (latency, throughput, memory) and acceptable p95/p99 targets.
- Performance tests or benchmarks for measurable goals MUST be included and executed in CI for performance-sensitive changes.
- Any optimizations that add complexity MUST be justified with metrics and have corresponding tests to prevent regressions.

Rationale: Explicit performance goals ensure features meet user expectations and avoid costly rework after release.

### Simplicity & Observability (CROSS-CUTTING)

Prefer simple, well-instrumented solutions. Rules:

- Choose the simplest design that satisfies requirements (YAGNI applied with cautious engineering judgment).
- Instrument critical flows with structured logging and metrics; tracing recommended for cross-service flows.
- Observability artifacts (logs, metrics, traces) MUST be documented in the feature plan and available to reviewers.

Rationale: Simplicity reduces bugs; observability shortens diagnosis time.

## Constraints & Standards

This section lists cross-cutting constraints that all features MUST consider:

- **Technology Stack**: Use the languages and frameworks documented in `plan.md` for the feature. Any deviation requires a documented justification and approval from maintainers.
- **Security & Privacy**: All code handling user data MUST follow secure handling practices and relevant privacy regulations; sensitive data MUST be encrypted in transit and at rest where applicable.
- **Performance Budgets**: Each feature MUST declare performance budgets for p95/p99 latency and memory; these budgets are validated in CI for critical paths.
- **Accessibility & UX**: Public-facing CLI and UIs MUST follow accessibility and usability conventions; where applicable, include examples in `quickstart.md`.

## Development Workflow & Quality Gates

Processes enforced across the project:

- **Pull Requests**: All changes MUST be submitted via PRs with clear descriptions, linked specs/plans, and test evidence.
- **Reviews**: PRs MUST be reviewed by at least one maintainer and one peer with familiarity of the affected area. Critical or large changes (per the plan's complexity section) MAY require two approvals.
- **CI Gates**: CI MUST run linters, type checks, unit tests, integration tests, and any feature-specific performance/benchmark checks. The PR gateway MUST block merges on failing critical gates.
- **Constitution Check**: Feature plans (plan.md) MUST include a Constitution Check section that documents how the feature meets the principles: Code Quality, Testing Standards, UX Consistency, Performance, and Observability. The plan MUST list any deviations and justifications.
- **Release & Versioning**: Breaking changes MUST follow semantic versioning and include migration guidance in the spec and changelog.

## Governance

Constitution scope and amendment rules:

- **Authority**: This constitution defines the non-negotiable engineering principles for the Immich Migrator project. Where it conflicts with other project documents, this constitution governs until formally amended.
- **Amendments**: Any amendment MUST be proposed as a PR that updates this file. The PR MUST include: rationale, migration plan for affected artifacts, and a list of templates or docs to be updated. Amendments require approval from at least two maintainers or owners and MUST pass the CI constitution-check gates.
- **Versioning Policy**: The constitution uses semantic versioning MAJOR.MINOR.PATCH where:

- MAJOR: incompatible governance or principle removals/redefinitions.
- MINOR: addition of new principle/section or material expansion.
- PATCH: clarifications, wording fixes, or typo corrections.
- **Compliance Reviews**: Significant changes to architecture or public interfaces MUST include a constitution compliance review in the plan and be explicitly signed off in the PR description.

**Version**: 1.0.0 | **Ratified**: TODO(RATIFICATION_DATE): confirm adoption date | **Last Amended**: 2025-12-08
