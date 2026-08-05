# ADR-0006: Implementation Rules for SQLite Durability

- **Status:** Accepted
- **Date:** 2026-08-05

## Context

Neuro Core 2 now relies on SQLite for durable memory and activity-event storage. The runtime is intentionally small and verified, so the implementation rules should preserve the current behavior without promising unsupported concurrency or migration features.

## Decision

1. Treat SQLite as a single-writer durability layer for the currently verified runtime slice.
2. Keep writes synchronous and immediately committed.
3. Prefer additive schema changes over destructive rewrites.
4. Require a versioned migration note and regression test before any table shape changes are considered release-ready.
5. Do not introduce WAL tuning, cross-process locking, or multi-writer guarantees unless they are explicitly implemented, tested, and documented.
6. Keep activity-event persistence and memory persistence aligned in the same SQLite database until a concrete need justifies splitting them.

## Consequences

- The current runtime remains simple, deterministic, and evidence-backed.
- Future schema evolution must be test-first.
- Concurrency claims remain intentionally narrow until expanded by measured implementation work.
