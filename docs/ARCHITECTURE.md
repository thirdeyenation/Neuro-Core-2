# Neuro Core 2 Architecture

Neuro Core 2 is a scoped, auditable memory capability for Agent Zero v2.8+. It provides capture, retrieval, and validation tools backed by SQLite, with explicit memory lifecycle and activity logging.

## Components

- **Domain** (`neuro_core.py`): `Memory`, `Scope`, and retrieval with factor-level explanations.
- **Lifecycle** (`memory_lifecycle.py`): states `unreviewed`, `validated`, `disputed`, `superseded`.
- **Storage port** (`memory_store.py`): `MemoryStore` interface.
- **SQLite adapter** (`sqlite_store.py`): durable `MemoryStore` implementation.
- **Activity ledger** (`activity_ledger.py`): append-only event log.
- **Service** (`neuro_service.py`): composes capture, retrieve, validate, store, and activity.
- **Plugin** (`plugins/neuro_core_2/`): Agent Zero tools `NeuroCore2Capture`, `NeuroCore2Retrieve`, `NeuroCore2Validate`.

## Data flow

1. Tools call `NeuroCoreService` with explicit `Scope(project, agent)`.
2. Service writes to `MemoryStore` and appends to `ActivityLedger`.
3. Retrieval ranks candidates lexically and by trust, returning factors.
4. Superseded memories remain stored but are excluded from retrieval.

## Persistence

- SQLite database path is configured in `plugins/neuro_core_2/default_config.yaml`.
- Schema is intentionally simple; migrations are out of scope for v1.
- Activity events are durably stored alongside memories.

## Boundaries

- Core modules (`neuro_core.py`, `memory_lifecycle.py`, `memory_store.py`, `sqlite_store.py`, `activity_ledger.py`, `neuro_service.py`) are host-independent.
- All Agent Zero integration lives under `plugins/neuro_core_2/`.
- Scope isolation is strict: `Scope(project, agent)` is a hard boundary.

## Non-goals (for now)

- Semantic/vector retrieval (replaceable behind the ranking port).
- Concurrency beyond single-writer SQLite.
- Authorization, input-size controls, or observability.
- Benchmark or competition claims.
