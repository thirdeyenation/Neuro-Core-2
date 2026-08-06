# 0004: Audit Durability and Migration Policy

## Context

Neuro Core 2 appends activity events for meaningful operations (capture, retrieve, validation changes). These must be durable and aligned with memory storage.

## Decision

- Store activity events durably in SQLite alongside memories.
- Expose a minimal read path via `NeuroCoreService.list_activity(scope)`.
- Do not delete audit records; treat them as append-only.
- For schema evolution, prefer additive changes and migration scripts over breaking changes.

## Consequences

- Audit is now a first-class, durable concern.
- Cross-invocation audit querying is possible in principle, though not yet exposed as a tool.
- Schema changes must consider migration of both memories and events.

## References

- `docs/ARCHITECTURE.md`
- `docs/PROJECT_CONTINUITY.md`
- `docs/decisions/0005-concurrency-and-migration-policy.md`
- `docs/decisions/0006-implementation-rules-for-sqlite-durability.md`
