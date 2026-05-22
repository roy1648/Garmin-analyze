# AGENTS.md

## Scope

These instructions apply to the entire repository.

This project is a personal Garmin TCX to AI-ready data converter. The current phase is specification-first. Do not add implementation code unless the user explicitly asks for implementation.

## Required Reading

Before making changes, read the relevant spec documents:

- `docs/00_project_brief.md`
- `docs/01_requirements.md`
- `docs/02_data_contract.md`
- `docs/03_acceptance_tests.md`
- `docs/04_architecture.md`
- `docs/05_task_breakdown.md`

For implementation tasks, treat `docs/02_data_contract.md` and `docs/03_acceptance_tests.md` as the primary source of truth.

## Project Constraints

- Keep the project maintainable by one developer.
- Prefer simple modules and explicit data contracts.
- Do not introduce heavy frameworks without explicit user approval.
- Do not modify raw TCX files.
- Treat GPS and health data as sensitive.
- Keep MVP scope focused on Garmin Connect exported Running TCX files.

## Python Standards

Future Python code must follow:

- PEP8 style.
- Type hints for public functions and data structures.
- Docstrings for modules, classes, and public functions.
- Clear variable and function names.
- Small functions with focused responsibilities.

Avoid:

- One-letter variable names.
- Hidden side effects.
- Overly broad utility modules.
- Premature abstractions.

## Privacy Rules

Raw TCX files are read-only inputs.

Any work involving GPS or health data must preserve these guarantees:

- The selected GPS policy is explicit.
- AI-ready output records the GPS policy used.
- No cloud upload is added without explicit user approval.
- No direct AI API upload is added without explicit user approval.
- No Garmin Connect authentication is added during MVP work.

Supported GPS policies are:

- `keep`
- `remove`
- `redact_start_end`

The default policy is `keep`, but changes involving output must avoid accidental coordinate leaks when another policy is selected.

## MVP Boundaries

Do not add these in MVP implementation unless the user explicitly requests a scope change:

- Web UI
- Database storage
- GarminDB dependency
- python-garminconnect dependency
- Garmin Connect login flow
- Cloud sync
- Multi-user support
- Full AI coaching platform

GarminDB and python-garminconnect may be referenced in documentation or future roadmap notes only.

## Collaboration Workflow

When asked to implement:

1. Restate the concrete task briefly if useful.
2. Inspect relevant files before editing.
3. Make small, focused changes.
4. Update docs when behavior or contracts change.
5. Add or update tests when implementation exists.
6. Run the narrowest useful validation first.
7. Report changed files and validation results.

Do not commit changes unless explicitly asked.

## Documentation Style

Documentation should be:

- Practical for a solo developer.
- Direct enough for Codex Agent handoff.
- Specific about inputs, outputs, constraints, and done criteria.
- Clear about MVP versus future roadmap.

Avoid marketing language and vague platform claims.

