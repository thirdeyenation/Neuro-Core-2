# ADR-0005: Concurrency and Migration Policy

- **Status:** Accepted
- **Date:** 2026-08-05

## Context

Neuro Core 2 now persists memories and activity events in SQLite. The codebase needs a minimal policy for how concurrent access and schema changes are handled so that verified behavior remains stable without promising unsupported guarantees.

## Decision

1. Treat SQLite as the durable source of truth for a single active writer process at a time.
2. Open and close database connections per tool/service invocation, as the current architecture already does.
3. Keep writes synchronous and commit immediately after each memory/event mutation.
4. Do not claim concurrent multi-writer safety, WAL tuning, or cross-process locking until those behaviors are explicitly implemented and tested.
5. Treat schema changes as forward-only: when a table shape changes materially, add a versioned migration note and a regression test before release claims are updated.
6. Prefer additive schema changes and preserve prior evidence rather than destructive rewrites.

## Consequences

- The current verified runtime remains simple and deterministic.
- Restart persistence and small-surface durability are preserved.
- The project can evolve toward migrations and stronger concurrency only when a concrete need and test coverage exist.
