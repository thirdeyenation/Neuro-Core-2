# Neuro Core 2 Benchmark Plan

## Purpose

Define a minimal, repeatable benchmark harness for Neuro Core 2 once the core slice is stable and host-contract findings are resolved.

## Goals

- Quantify **latency** and **throughput** for capture and retrieval under realistic workloads.
- Measure **retrieval quality** (precision/recall) against a labeled test set.
- Track **storage growth** per N memories and M activity events.
- Confirm **restart survival**: database remains readable/writable after process restart.

## Metrics

### Capture

- p50 and p95 latency for `NeuroCore2Capture` calls.
- Throughput (captures/second) under sustained load.
- Write amplification (bytes written per captured memory + activity event).

### Retrieve

- p50 and p95 latency for `NeuroCore2Retrieve` calls with varying corpus sizes.
- Top-k precision and recall against a labeled query set.
- Result diversity and stability across repeated runs.

### Storage

- Database size growth as a function of:
  - Number of memories.
  - Number of activity events.
  - Average memory/event payload size.
- Index size and fragmentation over time.

### Restart

- Time to reopen database and restore service.
- Verification that all memories and events remain intact after restart.

## Harness

- **Synthetic memory generator**: configurable distribution of memory sizes, vocabularies, and scopes.
- **Labeled query set**: fixed queries with known relevant memories for precision/recall measurement.
- **Configuration**:
  - SQLite DB path: `plugins/neuro_core_2/neuro_core_2.db`.
  - Configurable batch sizes and run durations.
- **Output**:
  - CSV logs with per-operation timestamps, latencies, and result sizes.
  - Summary stats (mean, p50, p95, p99) and plots (generated offline).

## Status

Not implemented. This is a placeholder for future work after:
- Host-contract and deployment-path findings are resolved.
- Tool configuration is fully driven by `default_config.yaml`.
- The core API and behavior are stable.

## Design notes

- Keep benchmarks separate from core logic; do not pollute production code.
- Use scripts under `scripts/` or a dedicated `bench/` directory.
- Document exact environment (Agent Zero version, OS, hardware) for each benchmark run.
- Store benchmark artifacts in `docs/benchmarks/` with dated logs and summaries.
