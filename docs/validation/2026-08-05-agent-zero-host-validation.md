# Agent Zero Host Validation Evidence

**Date:** 2026-08-05
**Repository:** thirdeyenation/Neuro-Core-2
**Plugin identity:** neuro_core_2
**Agent Zero version:** v2.8 commit 5ff106a2
**Python:** 3.13.14

## Verified actions

- Installed or confirmed installed the Neuro Core 2 plugin at `/a0/usr/plugins/neuro_core_2`.
- Restarted Agent Zero successfully.
- Confirmed tools were present: `neuro_capture.py`, `neuro_retrieve.py`, `neuro_validate.py`.
- Captured memory `b367abf8-9e78-4ae5-9d11-b54c1bd8d1b7`.
- Retrieved 1 result with score `0.75` and factors `{overlap: 1.0, importance: 0.5, confidence: 0.5, validation: unreviewed}`.
- Superseded the captured memory successfully.
- Re-retrieval in the same scope returned 0 results.
- Cross-scope retrieval in `beta` returned 0 results.
- Confirmed writable database at `/a0/usr/plugins/neuro_core_2/neuro_core.db` with size 12288 bytes.

## Notes

- The initial install step reported `SameFileError` because the plugin files were already in place; this was a no-op and not a failure.
- These results verify host integration and scope isolation for the current plugin identity.
