# ADR-0003: neuro_core_2 Identity, Install Path, and Host Validation

- **Status:** Accepted
- **Date:** 2026-08-05

## Context

The repository must be clearly distinguished from the original Neuro Core plugin while remaining installable and testable in a live Agent Zero v2.8+ container. The plugin-facing namespace and install path must avoid confusion with the original `neuro_core` plugin.

## Decision

The plugin identity is `neuro_core_2`. Host-facing plugin installation, database path, and documentation references will use `/a0/usr/plugins/neuro_core_2/` and `/a0/usr/plugins/neuro_core_2/neuro_core.db`. The repository keeps its source tree under `plugins/neuro_core/`, but all deployment-facing references inside the plugin shell and docs must use the `neuro_core_2` identity.

## Verified host evidence

- Python: 3.13.14
- Agent Zero: v2.8 commit `5ff106a2`
- Install step: confirmed no-op / same-file already in place
- Plugin discovery: tools visible (`neuro_capture.py`, `neuro_retrieve.py`, `neuro_validate.py`)
- Capture: succeeded with memory ID `b367abf8-9e78-4ae5-9d11-b54c1bd8d1b7`
- Retrieve: returned 1 result with explicit factors
- Validate: superseded successfully
- Same-scope retrieve after supersede: 0 results
- Cross-scope retrieve: 0 results
- Database: `/a0/usr/plugins/neuro_core_2/neuro_core.db` writable and populated

## Consequences

- Future session instructions should use the `neuro_core_2` install path and not the original plugin identity.
- The repository now has a durable record of the validated host workflow and scope-isolation behavior.
- Persistence across a separate restart, performance, concurrency, and security claims remain unproven and must not be asserted without additional evidence.
