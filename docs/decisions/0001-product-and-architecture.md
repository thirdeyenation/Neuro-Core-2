# 0001: Product and Architecture

## Context

Neuro Core 2 is scoped, auditable memory for Agent Zero v2.8+. The project needed a clean separation between domain logic and host integration, with explicit lifecycle and audit.

## Decision

- Implement a framework-independent domain:
  - `Memory` and `Scope` as core types.
  - Lexical/trust ranking with factor-level explanations.
- Define an explicit lifecycle policy:
  - States: `unreviewed`, `validated`, `disputed`, `superseded`.
  - Superseded memories are excluded from retrieval but preserved for audit.
- Introduce a `MemoryStore` port with in-memory and SQLite adapters.
- Compose capabilities in `NeuroCoreService` (capture, retrieve, validate, store, activity).
- Keep all Agent Zero integration under `plugins/neuro_core_2/`.

## Consequences

- Core modules (`neuro_core.py`, `memory_lifecycle.py`, `memory_store.py`, `sqlite_store.py`, `activity_ledger.py`, `neuro_service.py`) remain host-independent.
- Plugin identity is `neuro_core_2` with tools `NeuroCore2Capture`, `NeuroCore2Retrieve`, `NeuroCore2Validate`.
- Documentation distinguishes implemented, planned, and unverified behavior (see `docs/PROJECT_CONTINUITY.md`).

## References

- `docs/ARCHITECTURE.md`
- `docs/PRODUCT_SPEC.md`
- `docs/PROJECT_CONTINUITY.md`
- `docs/COMPETITION_CHARTER.md`
