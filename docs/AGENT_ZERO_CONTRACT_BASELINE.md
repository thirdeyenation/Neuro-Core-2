# Agent Zero Contract Baseline

This document records the minimal contract Neuro Core 2 requires from the Agent Zero host to operate correctly.

## Plugin identity

- Plugin name in manifest: `neuro_core_2`.
- Plugin folder: `plugins/neuro_core_2/`.
- Tools: `NeuroCore2Capture`, `NeuroCore2Retrieve`, `NeuroCore2Validate` (modules `neuro_core_2_capture`, `neuro_core_2_retrieve`, `neuro_core_2_validate`).

## File layout

- `plugins/neuro_core_2/plugin.yaml` — plugin manifest.
- `plugins/neuro_core_2/default_config.yaml` — plugin-local defaults.
- `plugins/neuro_core_2/install.py` — installer script.
- `plugins/neuro_core_2/tools/` — tool implementations.
- `plugins/neuro_core_2/neuro_core_2.db` — SQLite database (created at runtime).

## Runtime expectations

- Plugin discovery loads `plugins/neuro_core_2/plugin.yaml`.
- Tools are invoked with explicit `project` and optional `agent` scope arguments.
- Plugin-local config is read from `plugins/neuro_core_2/default_config.yaml`.

## Versioning

- Neuro Core 2 targets Agent Zero v2.8+.
- The plugin identity `neuro_core_2` is fixed; do not rename to `neuro_core`.

## Validation checklist

- [ ] Plugin appears in Agent Zero with name `neuro_core_2`.
- [ ] Tools `NeuroCore2Capture`, `NeuroCore2Retrieve`, `NeuroCore2Validate` are callable.
- [ ] A captured memory is persisted to `plugins/neuro_core_2/neuro_core_2.db`.
- [ ] Retrieval for the same scope returns the memory with factors.
- [ ] Validating to `superseded` removes the memory from retrieval but not from storage.
- [ ] Restarting the host preserves the database and allows new captures/retrievals.
- [ ] Activity events are appended for captured, retrieved, and validation-changed memories.
