# 0002: Plugin Identity and Integration Strategy

## Context

Neuro Core 2 must integrate cleanly with Agent Zero v2.8+ while preserving host independence for core logic.

## Decision

- Use a dedicated plugin folder: `plugins/neuro_core_2/`.
- Set plugin manifest name to `neuro_core_2`.
- Expose tools: `NeuroCore2Capture`, `NeuroCore2Retrieve`, `NeuroCore2Validate`.
- Store plugin-local config in `plugins/neuro_core_2/default_config.yaml`.
- Use SQLite database at `plugins/neuro_core_2/neuro_core_2.db`.

## Consequences

- Host discovery loads `plugins/neuro_core_2/plugin.yaml`.
- Tools are invoked with explicit `project` and optional `agent` scope arguments.
- Plugin-local config is read from `plugins/neuro_core_2/default_config.yaml`.
- Core modules remain host-independent; all Agent Zero integration lives under `plugins/neuro_core_2/`.

## References

- `docs/AGENT_ZERO_CONTRACT_BASELINE.md`
- `docs/PROJECT_CONTINUITY.md`
- `docs/COMPETITION_CHARTER.md`
