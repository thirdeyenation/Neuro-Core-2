# Neuro Core 2 Validation Artifacts

This folder holds dated evidence that Neuro Core 2 works as claimed in a real Agent Zero host.

## Contents

- `2026-08-05-agent-zero-host-validation.md` — first end-to-end host run with plugin identity `neuro_core_2`, capture/retrieve/validate/supersede flow, cross-scope isolation, and writable SQLite store evidence.
- `2026-08-05-post-restart-persistence-check.md` — confirms the SQLite database survived restart, remained writable, and supported capture/retrieve after restart.
- `SCHEMA_TEST_SKETCH.md` — notes leading to the schema compatibility regression test.

## How to add a new validation log

1. Create a new file named `YYYY-MM-DD-<short-description>.md`.
2. Record:
   - Agent Zero version/commit and environment details.
   - Install command (e.g. `python plugins/neuro_core_2/install.py`).
   - Plugin discovery result and tool names observed.
   - Concrete capture/retrieve/validate inputs and outputs.
   - Database path and any schema notes.
   - Test output and any deviations from expected behavior.
3. Link the new file from this README.

## Use in competition

When citing evidence, reference the specific dated log and the exact claims it supports (e.g. "restart survival" or "supersession behavior"). Do not extrapolate beyond what the log demonstrates.
