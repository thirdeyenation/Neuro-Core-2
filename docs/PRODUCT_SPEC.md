# Neuro Core 2 Product Specification

## Problem

Agents need scoped, auditable memory that survives restarts and explains why items were selected.

## Solution

Neuro Core 2 provides:
- Capture, retrieval, and validation tools scoped by `(project, agent)`.
- Explicit lifecycle (`unreviewed` → `validated`/`disputed` → `superseded`).
- Factor-level retrieval explanations.
- Durable SQLite storage and append-only activity logging.

## User stories

- As a developer, I can capture a memory with a project/agent scope.
- As a developer, I can retrieve memories for a scope and see why they were selected.
- As a developer, I can validate or supersede memories and see audit events.

## Scope

- In-scope: core domain, lifecycle, storage port, SQLite adapter, service, plugin tools, basic tests.
- Out-of-scope (v1): semantic retrieval, concurrency, authorization, benchmarks.

## Acceptance criteria

- `NeuroCore2Capture`, `NeuroCore2Retrieve`, `NeuroCore2Validate` tools work in Agent Zero v2.8+.
- Superseded memories are not retrieved but remain in storage.
- Activity events are durably stored and queryable via `NeuroCoreService.list_activity(...)`.
- SQLite database survives restart and remains writable.
- Schema compatibility is protected by a regression test.

## Configuration

- Plugin config in `plugins/neuro_core_2/default_config.yaml`.
- Database path: `plugins/neuro_core_2/neuro_core_2.db`.

## Risks

- Semantic retrieval gap: mitigated by preserving factor explanations.
- No concurrency model: mitigated by single-writer posture and explicit ADRs.
- No authorization: mitigated by scope isolation and explicit non-goals.
