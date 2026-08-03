# ADR-0002: Independent Plugin Identity and Adapter-First Integration

- **Status:** Accepted
- **Date:** 2026-08-03

## Context

Neuro Core 2 must be a separate competition entry that can later be installed and published as an Agent Zero plugin without modifying framework-owned files or inheriting the original Neuro Core implementation.

## Decision

The plugin identifier is `neuro_core_2`. The repository will use a root `plugin.yaml` with project- and agent-scoped configuration. Framework-specific integration is deferred behind an adapter boundary. The initial core remains framework-independent, while each later integration surface requires a targeted contract verification.

## Consequences

- The package can meet the naming requirement for future Plugin Index submission.
- Core tests can run against deterministic synthetic fixtures without an Agent Zero container.
- Integration progress is gated by verified contracts rather than assumptions derived from a competing plugin.
- The first implementation slice will favor a visible, frontend-oriented Workbench over invisible automatic memory behavior.
