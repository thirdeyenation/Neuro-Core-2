# Neuro Core 2 Benchmark Plan

## Purpose

Define a minimal, repeatable benchmark harness for Neuro Core 2 once the core slice is stable.

## Metrics

- Capture latency (p50, p95) for typical memory sizes.
- Retrieve latency and result quality (top-k precision/recall against a labeled set).
- Storage size growth per N memories and M activity events.
- Restart survival: DB remains readable/writable after process restart.

## Harness

- Synthetic memory generator with configurable size and vocabulary.
- Fixed query set for retrieval quality measurement.
- SQLite DB path: `plugins/neuro_core_2/neuro_core_2.db`.
- Scripted runs producing CSV logs and summary stats.

## Status

Not implemented. This is a placeholder for future work after host-contract and deployment-path findings are resolved.
