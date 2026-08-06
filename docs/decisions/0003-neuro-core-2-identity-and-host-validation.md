# 0003: Neuro Core 2 Identity and Host Validation

## Context

The project previously used unversioned "neuro core" / `neuro_core` identifiers. To avoid ambiguity and support future versions, the identity must be versioned and validated in a real host.

## Decision

- Standardize all references to `neuro_core_2` / "Neuro Core 2".
- Use plugin folder `plugins/neuro_core_2/` and manifest name `neuro_core_2`.
- Tools are named `NeuroCore2Capture`, `NeuroCore2Retrieve`, `NeuroCore2Validate`.
- Validate identity and behavior in an actual Agent Zero host:
  - 2026-08-05 host validation with plugin identity `neuro_core_2`.
  - 2026-08-05 post-restart persistence check confirming DB survival and writability.

## Consequences

- Docs, configs, and code consistently use `neuro_core_2`.
- Validation artifacts in `docs/validation/` record exact host version/commit, install command, and observed behavior.
- Future versions can coexist (e.g. `neuro_core_3`) without confusing current evidence.

## References

- `docs/validation/2026-08-05-agent-zero-host-validation.md`
- `docs/validation/2026-08-05-post-restart-persistence-check.md`
- `docs/AGENT_ZERO_CONTRACT_BASELINE.md`
- `docs/PROJECT_CONTINUITY.md`
