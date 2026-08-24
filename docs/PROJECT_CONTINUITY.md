# Neuro Core 2 Continuity Guide

## Mission

Neuro Core 2 is an evidence-first, scoped memory capability for Agent
Zero v2.8+. Its core promise is explainable retrieval: selected memories
expose scoring factors; memory lifecycle is explicit; meaningful
operations are auditable. This document is the authoritative status and
continuation guide. Use existing architecture, product, benchmark, and
competition documents for detail.

---

## What is implemented

- Framework-independent domain: immutable `Memory`, `Scope`,
  lexical/trust ranking, and factor-level retrieval explanations.
- Lifecycle policy: `unreviewed`, `validated`, `disputed`, and terminal
  `superseded`; superseded memories are excluded, not deleted.
- Append-only in-process activity ledger.
- `MemoryStore` port with in-memory and SQLite adapters.
- `NeuroCoreService` composing capture, retrieve, validation, storage,
  and activity events.
- Standard-library tests for scope isolation, lifecycle, storage,
  SQLite persistence, and service flow.
- Agent Zero plugin shell, installer, and `NeuroCore2Capture`,
  `NeuroCore2Retrieve`, and `NeuroCore2Validate` tools.
- Verified Agent Zero host run on 2026-08-05 with plugin identity
  `neuro_core_2`, capture/retrieve/validate/supersede flow, cross-scope
  isolation, and writable SQLite store evidence. See
  `docs/validation/2026-08-05-agent-zero-host-validation.md`.
- Verified post-restart persistence check on 2026-08-05: database
  survived restart, remained writable, and capture/retrieve worked
  after restart. See
  `docs/validation/2026-08-05-post-restart-persistence-check.md`.
- Durable activity-event persistence now stored in SQLite alongside
  memories, with a tiny read path exposed through
  `NeuroCoreService.list_activity(...)`.
- `NeuroCoreService.list_activity(...)` is now covered by a unit test
  for scope-filtered in-memory activity access.
- SQLite schema compatibility is now protected by a regression test
  that exercises restart plus additive activity writes.
- Schema versioning and migration: `PRAGMA user_version` tracks the
  schema version; `migrations.py` runs on every `SQLiteStore` open,
  applies pending migrations in ascending order inside `BEGIN IMMEDIATE`
  transactions, and is idempotent by construction. Fresh and legacy
  databases both converge on version 2 with all existing rows preserved.
- Concurrency strategy: every write and migration uses `BEGIN IMMEDIATE`
  plus a bounded `PRAGMA busy_timeout` (default 5000 ms, configurable via
  the `busy_timeout_ms` constructor argument). This provides a
  single-writer serialization guarantee only.
- Lifecycle hook and extension integration: `hooks.py` implements `register_plugin` (plugin metadata: name=`neuro_core_2`, version=`0.1.0`, tools=`[NeuroCore2Capture, NeuroCore2Retrieve, NeuroCore2Validate]`), `on_plugin_load` (service initialization from `default_config.yaml`), and `on_plugin_activate` (database accessibility check, startup validation, activation logging); `extensions/__init__.py` registers a `SessionLifecycleExtension` at `agent_init` that appends a `session_initialized` `ActivityEvent`. Verified in-process only — host-level firing against a real Agent Zero host is not yet verified.
- Inverted-term retrieval index: a `memory_terms` table (schema version 2)
  is maintained on capture and used as a pure candidate pre-filter before
  domain scoring. Tokenization is exactly `text.lower().split()`;
  scoring, ranking, and the inspectable-factors explanation contract are
  unchanged.
- Bounded retrieval results: `NeuroCore2Retrieve` returns at most
  `max_results` results (default 100, configurable via `max_results` in
  `default_config.yaml`; the optional `max_results` tool argument
  overrides the config value for a single call). The cap is applied AFTER
  scoring and sorting. When the full match count exceeds the cap, the
  payload includes `count_exceeded: true` and `total_matches: <int>` so
  callers can distinguish truncation from exhaustion — silent truncation
  is prohibited.

---

## What is not proven

- Performance, multi-writer, distributed, or security claims. Do not
  claim these as completed. The only concurrency guarantee is
  single-writer serialization via `BEGIN IMMEDIATE` plus
  `busy_timeout`; no throughput, latency, multi-writer, or distributed
  behavior is claimed or implied.
- Durable cross-session audit querying surface beyond the service
  method.
- Tool configuration sourced from `default_config.yaml` instead of
  hardcoded paths.
- Actual Agent Zero host lifecycle firing (the real framework calling `on_plugin_load`/`on_plugin_activate`/`register_extension` as part of its own plugin loading sequence) is not exercised. Only in-process code-path verification was performed.

---

## Non-negotiable decisions

1. Keep Agent Zero imports in `plugins/neuro_core_2/`; root modules
   must remain host-independent.
2. Treat `Scope(project, agent)` as a hard isolation boundary.
3. Preserve inspectable ranking factors when replacing lexical
   retrieval with semantic/vector retrieval.
4. Preserve superseded records for audit; do not retrieve them.
5. Add storage backends behind `MemoryStore`, not directly in the
   service.
6. Keep explicit tool scope inputs unless a documented host-session
   mapping is proven.

---

## Known debt

- Ranking is a correctness baseline, not semantic retrieval.
- The unindexed linear scan is resolved by the inverted-term index
  (`memory_terms`, schema version 2). Remaining honest limits:
  concurrency is untested at host level, WebUI surfaces are unexercised,
  and the full default-scale benchmark suite has not yet been re-run
  (only a bounded 5000-memory, n=5 latency diagnostic was measured).
- SQLite opens per invocation; the single-writer serialization model is
  implemented, but multi-writer, distributed, and performance behavior
  remain unproven and out of scope.
- Tool code should load the plugin-local database path from
  `default_config.yaml` at runtime.
- Activity events are now durably appended when the underlying store
  supports it, but cross-invocation audit querying is not yet exposed
  as a tool.
- The installer copies files but does not validate imports, discovery,
  permissions, or manifest behavior.
- There is no authorization policy, input-size control, observability,
  or evaluation harness.
- Lifecycle integration code is implemented, but host-level firing (real Agent Zero framework load/activate/agent_init invocation) remains unverified.

---

## Completion sequence

1. Run `python scripts/verify.py` (if present in the runtime plugin
   directory).
2. In the target Agent Zero container, run
   `python plugins/neuro_core_2/install.py`, reload plugins, and record
   the exact Agent Zero version/commit.
3. Smoke-test capture, retrieve, and validate with one project/agent
   scope; confirm superseded records disappear from retrieval.
4. Resolve all host-contract and deployment-path findings before
   feature expansion.
5. Make tool configuration real and persist activity events.
6. Add a benchmark harness before production or competition claims.
   (Schema migrations and the single-writer concurrency/failure policy
   are implemented as of 2026-08-18.)
7. Verify host-level lifecycle firing: confirm the real Agent Zero
   framework calls `on_plugin_load`/`on_plugin_activate`/`register_extension`
   as part of its own plugin loading sequence. Lifecycle integration code
   is implemented (in-process verified); host-level firing verification
   is the remaining step.

---

## Change discipline

Every behavior change needs a `unittest` update. Record lifecycle,
ranking, or public-contract decisions in `docs/decisions/`. Preserve
constructor and port compatibility or provide a deliberate migration.
Keep implemented, planned, and unverified behavior clearly separated.

---

## Onboarding for new contributors

Before touching code:
1. Read this file, `docs/ARCHITECTURE.md`, and
   `docs/AGENT_ZERO_CONTRACT_BASELINE.md`.
2. Run the tests locally and ensure they pass.
3. Reproduce the host validation steps in `docs/validation/` using the
   recorded Agent Zero version/commit.

When proposing changes:
- State the objective and why it matters.
- Identify affected modules, tests, and ADRs.
- Call out any assumptions, risks, and downstream effects.
- Preserve backward compatibility or provide a migration note.

---

## Acceptance evidence

For deployment work, record the Agent Zero version/commit, install
command, plugin discovery result, capture/retrieve/validate inputs and
outputs, database path, test output, and deviations in a dated issue,
PR, or `docs/validation/` artifact.

---

## Environment variables

**No environment variable is currently required.** All configuration is
read from the plugin-local `default_config.yaml`. See `README.md` for
the full environment-variable policy.
