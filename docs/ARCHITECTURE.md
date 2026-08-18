# Neuro Core 2 Architecture

Neuro Core 2 is a scoped, auditable memory capability for Agent Zero v2.8+. It provides capture, retrieval, validation, and audit tools backed by SQLite, with explicit memory lifecycle and activity logging.

## Components

- **Domain** (`neuro_core_2.py`): `Memory`, `Scope`, and retrieval with factor-level explanations.
- **Lifecycle** (`memory_lifecycle.py`): states `unreviewed`, `validated`, `disputed`, `superseded`.
- **Storage port** (`memory_store.py`): `MemoryStore` interface.
- **SQLite adapter** (`sqlite_store.py`): durable `MemoryStore` implementation.
- **Activity ledger** (`activity_ledger.py`): append-only event log.
- **Service** (`neuro_core_2_service.py`): composes capture, retrieve, validate, store, and activity.
- **Plugin** (`plugins/neuro_core_2/`): Agent Zero tools `NeuroCore2Capture`, `NeuroCore2Retrieve`, `NeuroCore2Validate`, `NeuroCore2Audit`.

## Data flow

1. Tools call `NeuroCore2Service` with explicit `Scope(project, agent)`.
2. Service writes to `MemoryStore` and appends to `ActivityLedger`.
3. Retrieval ranks candidates lexically and by trust, returning factors.
4. Superseded memories remain stored but are excluded from retrieval.
5. The audit tool (`NeuroCore2Audit`) constructs `Scope(project, agent)` explicitly, calls `NeuroCoreService.list_activity(scope)`, applies optional filters (`event_type`, `memory_id`, `start_date`, `end_date`) in the tool layer, orders results by `occurred_at` DESC, enforces the limit (default 100, max 1000), and serializes each `ActivityEvent` to a dict.

## Persistence

- SQLite database path is configured in `plugins/neuro_core_2/default_config.yaml`.
- Schema is intentionally simple; migrations are out of scope for v1.
- Activity events are durably stored alongside memories.

## Boundaries

- Core modules (`neuro_core_2.py`, `memory_lifecycle.py`, `memory_store.py`, `sqlite_store.py`, `activity_ledger.py`, `neuro_core_2_service.py`) are host-independent.
- All Agent Zero integration lives under `/a0/usr/plugins/neuro_core_2/`.
- Scope isolation is strict: `Scope(project, agent)` is a hard boundary.

## Non-goals (for now)

- Semantic/vector retrieval (replaceable behind the ranking port).
- Concurrency beyond single-writer SQLite.
- Authorization, input-size controls, or observability.
- Benchmark or competition claims.
