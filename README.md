# Neuro Core 2

**Explainable memory for Agent Zero.**

Neuro Core 2 is an independent competition entry for an Agent Zero memory plugin. It is designed as a clean-room successor concept: it does not copy the existing Neuro Core implementation, and it will earn adoption through measurable improvement in reliability, explainability, control, and task outcomes.

## Product promise

Neuro Core 2 makes agent memory useful without making it opaque. A user can see what was captured, why context was retrieved, how trustworthy it is, what conflict exists, and what action changed memory state.

## The memory loop

`Capture → Understand → Retrieve → Explain → Resolve → Learn`

The product is successful only when each meaningful stage leaves scoped, inspectable evidence.

## Competition win condition

In controlled multi-step tasks, Neuro Core 2 must outperform a no-memory baseline and a basic retrieval baseline on correct context recall, redundant work avoided, unsupported-memory claims avoided, and user ability to inspect or correct behavior. See [the benchmark plan](docs/BENCHMARK_PLAN.md).

## Repository boundaries

- This repository is an independent implementation and product design.
- The existing Neuro Core repository is a read-only competitor/reference for comparative analysis; its source is not copied here.
- Framework integration is implemented only after the relevant Agent Zero contract is independently verified.

## Initial documents

- [Competition charter](docs/COMPETITION_CHARTER.md)
- [Clean-room protocol](docs/CLEAN_ROOM_PROTOCOL.md)
- [Product specification](docs/PRODUCT_SPEC.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Benchmark plan](docs/BENCHMARK_PLAN.md)
- [ADR-0001](docs/decisions/0001-product-and-architecture.md)

## Status

Foundation phase. No Agent Zero runtime behavior is claimed or implemented by this commit.