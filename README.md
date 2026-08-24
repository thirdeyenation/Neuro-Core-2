# Neuro Core 2

Evidence-first, scoped memory for Agent Zero v2.8+. This repository implements the Neuro Core 2 plugin: capture, retrieval, validation, and audit tools backed by SQLite, with explicit memory lifecycle and audit.

## Quick start

1. Run `python scripts/verify.py` (if present) to sanity-check the core modules.
2. In the target Agent Zero container, run:
   ```bash
   python plugins/neuro_core_2/install.py
   ```
   then reload plugins and record the exact Agent Zero version/commit.
3. Smoke-test with one project/agent scope:
   - Capture a memory via `neuro_core_2_capture.py`.
   - Retrieve it via `neuro_core_2_retrieve.py`.
   - Validate or supersede it via `neuro_core_2_validate.py`.
   - Query activity events via `neuro_core_2_audit.py`.
   - Confirm superseded memories no longer appear in retrieval.

### Structure

- `default_config.yaml` — plugin-local defaults (database path, etc.).
- `install.py` — copies plugin files into the Agent Zero container.
- `plugin.yaml` — Agent Zero plugin manifest (name: `neuro_core_2`).
- `tools/` — `neuro_core_2_capture.py`, `neuro_core_2_retrieve.py`, `neuro_core_2_validate.py`, `neuro_core_2_audit.py`.
- `hooks.py` — Agent Zero lifecycle hooks: `register_plugin` (registers plugin metadata: name=`neuro_core_2`, version=`0.1.0`, tools=`[NeuroCore2Capture, NeuroCore2Retrieve, NeuroCore2Validate]`), `on_plugin_load` (loads `default_config.yaml`, resolves `database_path`, constructs `SQLiteStore` and `NeuroCoreService`, registers the lifecycle extension), and `on_plugin_activate` (verifies database accessibility with `SELECT 1`, runs startup validation via `PRAGMA user_version`, logs activation status, returns a status dict).
- `extensions/` — lifecycle extension modules: `extensions/__init__.py` registers a functional `SessionLifecycleExtension` (subclass of `helpers.extension.Extension`) at the `agent_init` session-lifecycle point that appends an `ActivityEvent` (kind=`session_initialized`) to the Neuro Core 2 service ledger and store.
- `scripts/` — verify to sanity-check the core modules.
- `docs/` — contains `decisions/` folder, `validation/` folder, and loose markdown files that provide critical information   and context that should be read and followed prior to beginning any continued development of the Neuro Core 2 plugin.
- `tests/` — contains all existing and future test scripts 

## What's implemented

- Framework-independent domain: immutable `Memory`, `Scope`, lexical/trust ranking, and factor-level retrieval explanations.
- Lifecycle policy: `unreviewed`, `validated`, `disputed`, and terminal `superseded`; superseded memories are excluded from retrieval, not deleted.
- Append-only in-process activity ledger (`activity_ledger.py`).
- `memory_store.py` port with in-memory and SQLite adapters.
- `neuro_core_2_service.py` composing capture, retrieve, validation, storage, and activity events.
- Standard-library tests for scope isolation, lifecycle, storage, SQLite persistence, and service flow.
- Agent Zero plugin (`neuro_core_2`) with `neuro_core_2_capture.py`, `neuro_core_2_retrieve.py`, `neuro_core_2_validate.py`, and `neuro_core_2_audit.py` tools (under `tools/`).
- `NeuroCore2Audit` tool exposing durable cross-session audit queries via `NeuroCoreService.list_activity(...)`, with explicit scope construction, optional filters (`event_type`, `memory_id`, `start_date`, `end_date`), `occurred_at` DESC ordering, and limit enforcement (default 100, max 1000).
- Verified Agent Zero host run on 2026-08-05 with plugin identity `neuro_core_2`, capture/retrieve/validate/supersede flow, cross-scope isolation, and writable SQLite store evidence. See `docs/validation/2026-08-05-agent-zero-host-validation.md`.
- Verified post-restart persistence check on 2026-08-05: database survived restart, remained writable, and capture/retrieve worked after restart. See `docs/validation/2026-08-05-post-restart-persistence-check.md`.
- Durable activity-event persistence in SQLite alongside memories, with a tiny read path via `NeuroCoreService.list_activity(...)`.
- `NeuroCoreService.list_activity(...)` covered by a unit test for scope-filtered in-memory activity access.
- SQLite schema compatibility protected by a regression test that exercises restart plus additive activity writes.
- Lifecycle hook and extension integration: `hooks.py` implements `register_plugin` (plugin metadata: name=`neuro_core_2`, version=`0.1.0`, tools=`[NeuroCore2Capture, NeuroCore2Retrieve, NeuroCore2Validate]`), `on_plugin_load` (service initialization from `default_config.yaml`), and `on_plugin_activate` (database accessibility check, startup validation, activation logging); `extensions/__init__.py` registers a `SessionLifecycleExtension` at `agent_init` that appends a `session_initialized` `ActivityEvent`. Verified in-process only (39 unit tests pass; integration scenarios passed) — host-level firing against a real Agent Zero host is not yet verified.
- Inverted-term retrieval index: a `memory_terms` table (schema version 2) is maintained on capture and used as a pure candidate pre-filter before domain scoring. Tokenization is exactly `text.lower().split()`; scoring, ranking, and the inspectable-factors explanation contract are unchanged.
- Bounded retrieval results: `NeuroCore2Retrieve` returns at most `max_results` results (default 100, configurable via `max_results` in `default_config.yaml`; the optional `max_results` tool argument overrides the config value for a single call). The cap is applied AFTER scoring and sorting. When the full match count exceeds the cap, the payload includes `count_exceeded: true` and `total_matches: <int>` so callers can distinguish truncation from exhaustion — silent truncation is prohibited.

## What is not proven

- Performance, concurrency, security, benchmark, or competition claims. Do not assert these as completed.
- Tool configuration sourced from `default_config.yaml` instead of hardcoded paths (design intent; implementation may still be evolving).
- Actual Agent Zero host lifecycle firing (the real framework calling `on_plugin_load`/`on_plugin_activate`/`register_extension` as part of its own plugin loading sequence) is not exercised. Only in-process code-path verification was performed.

## Non-negotiable decisions

1. Keep Agent Zero imports in `plugins/neuro_core_2/`; root modules must remain host-independent.
2. Treat `Scope(project, agent)` as a hard isolation boundary.
3. Preserve inspectable ranking factors when replacing lexical retrieval with semantic/vector retrieval.
4. Preserve superseded records for audit; do not retrieve them.
5. Add storage backends behind `MemoryStore`, not directly in the service.
6. Keep explicit tool scope inputs unless a documented host-session mapping is proven.

## Known debt

- Ranking is a correctness baseline, not semantic retrieval.
- SQLite opens per invocation and has no migration or concurrency strategy.
- Tool code should load the plugin-local database path from `default_config.yaml` at runtime.
- Activity events are durably appended when the underlying store supports it.
- The installer copies files but does not validate imports, discovery, permissions, or manifest behavior.
- There is no authorization policy, input-size control, observability, or evaluation harness.
- Lifecycle integration code is implemented, but host-level firing (real Agent Zero framework load/activate/agent_init invocation) remains unverified.


## Known limitations

- The audit tool's date-range filters (`start_date`, `end_date`) are implemented but not covered by dedicated unit tests.
- Offset-based pagination for audit queries is not implemented (deferred).
- Host-level behavior of the audit tool (Agent Zero tool dispatcher registration, runtime tool invocation, WebUI integration) is not verified at unit level.

## Completion sequence

1. Run `python scripts/verify.py`.
2. In the target Agent Zero container, run `python plugins/neuro_core_2/install.py`, reload plugins, and record the exact Agent Zero version/commit.
3. Smoke-test capture, retrieve, validate, and audit with one project/agent scope; confirm superseded records disappear from retrieval and audit returns expected activity events.
4. Resolve all host-contract and deployment-path findings before feature expansion.
5. Make tool configuration real and persist activity events.
6. Add schema migrations, concurrency/failure policy, and a benchmark harness before production or competition claims.

## Change discipline

Every behavior change needs a `unittest` update. Record lifecycle, ranking, or public-contract decisions in `docs/decisions/`. Preserve constructor and port compatibility or provide a deliberate migration. Keep implemented, planned, and unverified behavior clearly separated.

## Acceptance evidence

For deployment work, record the Agent Zero version/commit, install command, plugin discovery result, capture/retrieve/validate inputs and outputs, database path, test output, and deviations in a dated issue, PR, or `docs/validation/` artifact.
