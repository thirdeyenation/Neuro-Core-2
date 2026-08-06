# Clean Room Protocol for Neuro Core 2

## Purpose

Ensure Neuro Core 2 code and docs are written without copying from external codebases or proprietary specs.

## Rules

- No copy-paste from external sources.
- Cite public docs by URL when needed; paraphrase in your own words.
- Keep third-party code out of the repo; use imports instead.
- Record any external inspiration in `docs/decisions/`.

## Scope

Applies to all Neuro Core 2 code, tests, and documentation in this repo.

## Identity

- Plugin folder: `plugins/neuro_core_2/`.
- Manifest name: `neuro_core_2`.
- Tools: `NeuroCore2Capture`, `NeuroCore2Retrieve`, `NeuroCore2Validate`.

## Relation to other docs

- See `docs/PROJECT_CONTINUITY.md` for change discipline and onboarding.
- See `docs/COMPETITION_CHARTER.md` for entry claims and evidence rules.
- See `docs/decisions/` for recorded architectural and policy decisions.
