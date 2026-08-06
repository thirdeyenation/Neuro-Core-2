# 0005: Concurrency and Migration Policy

## Context

Neuro Core 2 uses SQLite for durability. The project must clarify concurrency assumptions and migration expectations.

## Decision

- Treat SQLite as a single-writer, file-based store for v1.
- Do not claim concurrency guarantees beyond what the current implementation provides.
- For schema changes:
  - Prefer additive columns/tables.
  - Provide migration notes or scripts when behavior changes.
  - Preserve backward compatibility where feasible or document breaking changes explicitly.

## Consequences

- No concurrency claims in competition materials.
- Schema compatibility is protected by tests (e.g. restart + additive writes).
- Future work may introduce a more formal migration mechanism or concurrency model.

## References

- `docs/ARCHITECTURE.md`
- `docs/PROJECT_CONTINUITY.md`
- `docs/COMPETITION_CHARTER.md`
- `docs/decisions/0004-audit-durability-and-migration-policy.md`
- `docs/decisions/0006-implementation-rules-for-sqlite-durability.md`
