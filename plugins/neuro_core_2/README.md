## Neuro Core 2 Plugin

Agent Zero plugin providing scoped, auditable memory capture, retrieval, and validation.

### Structure

- `default_config.yaml` — plugin-local defaults (database path, etc.).
- `install.py` — copies plugin files into the Agent Zero container.
- `plugin.yaml` — Agent Zero plugin manifest (name: `neuro_core_2`).
- `tools/` — `neuro_core_2_capture.py`, `neuro_core_2_retrieve.py`, `neuro_core_2_validate.py`.

### Usage

1. Run `python install.py` from the host or container.
2. Reload plugins in Agent Zero.
3. Use `NeuroCore2Capture`, `NeuroCore2Retrieve`, and `NeuroCore2Validate` tools.
