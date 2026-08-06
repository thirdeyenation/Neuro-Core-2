## Neuro Core 2 Plugin

Agent Zero plugin providing scoped, auditable memory capture, retrieval, and validation.
Agent Zero discovers local plugins from /a0/usr/plugins/<plugin_name>/ when a root plugin.yaml is present.

### Structure

- `default_config.yaml` — plugin-local defaults (database path, etc.).
- `install.py` — copies plugin files into the Agent Zero container.
- `plugin.yaml` — Agent Zero plugin manifest (name: `neuro_core_2`).
- `tools/` — `neuro_core_2_capture.py`, `neuro_core_2_retrieve.py`, `neuro_core_2_validate.py`.

### Usage

1. Run `python install.py` from the host or container.
2. Reload plugins in Agent Zero.
3. Use `NeuroCore2Capture`, `NeuroCore2Retrieve`, and `NeuroCore2Validate` tools.

### Installation

1. Copy this neuro_core_2 directory to /a0/usr/plugins/neuro_core_2/.
2. Copy the repository's domain modules (neuro_core.py, memory_lifecycle.py, memory_store.py, sqlite_store.py, activity_ledger.py, and neuro_service.py) into the plugin directory or package them with the plugin.
3. Configure database_path in default_config.yaml for a plugin-owned persistent SQLite database.
4. Add host tool registration only after verifying the target Agent Zero release's tool callback contract.
