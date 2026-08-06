# Agent Zero Contract Baseline

This document records the minimal contract Neuro Core 2 requires from the Agent Zero host to operate correctly.

## Plugin identity

- Plugin name in manifest: `neuro_core_2`.
- Plugin folder: `plugins/neuro_core_2/`.
- Tools: `neuro_core_2_capture`, `neuro_core_2_retrieve`, `neuro_core_2_validate`.

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
