# ADR-0004: Audit Durability and Migration Policy

- **Status:** Accepted
- **Date:** 2026-08-05

## Context

Neuro Core 2 now persists activity events durably in the same SQLite database used by the memory store. The project needs a minimal, explicit policy for what durability is promised now and what remains deferred.

## Decision

1. Persist activity events in SQLite when the underlying store supports `append_event(...)`.
2. Keep the in-memory `ActivityLedger` behavior unchanged for compatibility and testability.
3. Expose a tiny service-level read path (`NeuroCoreService.list_activity(...)`) rather than introducing a new tool or UI surface immediately.
4. Defer broader audit-query UX, concurrency controls, and migration tooling until a concrete consumer requires them.
5. Treat schema changes as forward-only; if the SQLite schema changes materially, add a migration note and a versioned test before claiming compatibility.

## Consequences

- Durable event history now survives restart alongside the memory store.
- The audit trail is easier to preserve, but not yet a first-class user feature.
- Future schema changes must be documented and tested before release claims are made.
