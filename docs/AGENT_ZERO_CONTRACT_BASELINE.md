# Agent Zero Contract Baseline

This document records the minimal contract Neuro Core 2 requires from
the Agent Zero host to operate correctly. It is the authoritative
newcomer entry point for the **install-plugin** onboarding journey.

---

## Plugin identity

- Plugin name in manifest: `neuro_core_2`.
- Plugin folder: `/a0/usr/plugins/neuro_core_2/`.
- Tools: `NeuroCore2Capture`, `NeuroCore2Retrieve`,
  `NeuroCore2Validate` (modules `neuro_core_2_capture`,
  `neuro_core_2_retrieve`, `neuro_core_2_validate`).

---

## File layout

The runtime plugin source lives at `/a0/usr/plugins/neuro_core_2/`:

- `plugin.yaml` — plugin manifest.
- `default_config.yaml` — plugin-local defaults.
- `install.py` — installer script.
- `hooks.py` — Agent Zero lifecycle hooks: `register_plugin` (registers plugin metadata: name=`neuro_core_2`, version=`0.1.0`, tools=`[NeuroCore2Capture, NeuroCore2Retrieve, NeuroCore2Validate]`), `on_plugin_load` (loads `default_config.yaml`, resolves `database_path`, constructs `SQLiteStore` and `NeuroCoreService`, registers the lifecycle extension), and `on_plugin_activate` (verifies database accessibility with `SELECT 1`, runs startup validation via `PRAGMA user_version`, logs activation status, returns a status dict).
- `extensions/` — lifecycle extension modules: `extensions/__init__.py` registers a functional `SessionLifecycleExtension` (subclass of `helpers.extension.Extension`) at the `agent_init` session-lifecycle point that appends an `ActivityEvent` (kind=`session_initialized`) to the Neuro Core 2 service ledger and store.
- `tools/` — tool implementations.
- `neuro_core_2.db` — SQLite database (created at runtime).

---

## Runtime expectations

- Plugin discovery loads `/a0/usr/plugins/neuro_core_2/plugin.yaml`.
- Tools are invoked with explicit `project` and optional `agent` scope
  arguments.
- Plugin-local config is read from
  `/a0/usr/plugins/neuro_core_2/default_config.yaml`.
- `hooks.py` registers plugin metadata (`neuro_core_2`, `0.1.0`, the three tools) via `register_plugin`, initializes the service from `default_config.yaml` via `on_plugin_load`, and verifies database accessibility and startup validation via `on_plugin_activate`.
- `extensions/__init__.py` registers a `SessionLifecycleExtension` at the `agent_init` session-lifecycle point that appends a `session_initialized` `ActivityEvent`.
- Lifecycle hook firing and extension registration are verified in-process only; actual Agent Zero host lifecycle firing is not yet verified.
- `NeuroCore2Retrieve` results are bounded: at most `max_results` results
  are returned (default 100, configurable via `max_results` in
  `default_config.yaml`; the optional `max_results` tool argument
  overrides the config value for a single call). The cap is applied AFTER
  scoring and sorting. When the full match count exceeds the cap, the
  payload includes `count_exceeded: true` and `total_matches: <int>` so
  callers can distinguish truncation from exhaustion — silent truncation
  is prohibited.
- Retrieval uses an inverted-term index: a `memory_terms` table (schema
  version 2) is maintained on capture and used as a pure candidate
  pre-filter before domain scoring. Tokenization is exactly
  `text.lower().split()`; scoring, ranking, and the inspectable-factors
  explanation contract are unchanged.

---

## Environment variables

**No environment variable is currently required** to install,
configure, or run Neuro Core 2. A read-only inspection of the runtime
plugin source for `os.environ`, `getenv`, and `environ[...]`
references returned no matches. All configuration is read from the
plugin-local `default_config.yaml`.

If a future change introduces an environment-variable prerequisite, it
must be:
1. Documented in this file with its exact name, purpose, and safe
   provisioning instructions.
2. Documented in `README.md` under the "Environment variables"
   section.
3. Recorded as a durable decision in `docs/decisions/`.

---

## Versioning

- Neuro Core 2 targets Agent Zero v2.8+.
- The plugin identity `neuro_core_2` is fixed; do not rename to
  `neuro_core`.

---

## Validation checklist

A newcomer or operator can verify the install-plugin journey by
confirming each of the following:

- [ ] Plugin appears in Agent Zero with name `neuro_core_2`.
- [ ] Tools `NeuroCore2Capture`, `NeuroCore2Retrieve`,
      `NeuroCore2Validate` are callable.
- [ ] A captured memory is persisted to
      `/a0/usr/plugins/neuro_core_2/neuro_core_2.db`.
- [ ] Retrieval for the same scope returns the memory with factors.
- [ ] Validating to `superseded` removes the memory from retrieval but
      not from storage.
- [ ] Restarting the host preserves the database and allows new
      captures/retrievals.
- [ ] Activity events are appended for captured, retrieved, and
      validation-changed memories.
- Lifecycle hook firing and extension registration are verified in-process (unit/integration). Host-level firing against a real Agent Zero host is not yet verified.
- [ ] Retrieval results are bounded at `max_results` (default 100); when
      the full match count exceeds the cap, the payload includes
      `count_exceeded: true` and `total_matches: <int>` — no silent
      truncation.
- [ ] Index effectiveness: retrieval latency at 5000-memory corpus scale
      is sub-second (bounded diagnostic, n=5 queries, synthetic corpus,
      median ~657ms). This is a bounded diagnostic, not a full benchmark.

---

## References

- `README.md` — project entry point.
- `docs/ARCHITECTURE.md` — component boundaries.
- `docs/PROJECT_CONTINUITY.md` — current state and known debt.
- `docs/validation/README.md` — index of validation evidence.
- `docs/decisions/ADR-001-record-format.md` — durable decision records.
