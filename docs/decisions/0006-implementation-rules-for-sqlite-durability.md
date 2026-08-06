# 0006: Implementation Rules for SQLite Durability

## Context

Neuro Core 2 relies on SQLite for persistent storage of memories and activity events. The implementation must ensure durability and restart survival.

## Decision

- Use a single SQLite database per plugin instance: `plugins/neuro_core_2/neuro_core_2.db`.
- Ensure the database:
  - Survives process restarts.
  - Remains writable after restart.
  - Preserves all memories and events without data loss.
- Protect schema compatibility with regression tests that:
  - Reopen the database after writes.
  - Append new memories and events post-restart.
  - Verify that all prior data remains intact.

## Consequences

- SQLite is treated as a durable, restart-surviving store.
- Schema changes are constrained by the need to preserve existing data.
- Tests in `test_sqlite_store.py` guard against accidental schema drift.

## References

- `docs/ARCHITECTURE.md`
- `docs/PROJECT_CONTINUITY.md`
- `docs/validation/2026-08-05-post-restart-persistence-check.md`
- `docs/decisions/0004-audit-durability-and-migration-policy.md`
- `docs/decisions/0005-concurrency-and-migration-policy.md`
