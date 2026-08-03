# ADR-0001: Explainable Memory Loop and Clean-Room Architecture

- **Status:** Accepted
- **Date:** 2026-08-03

## Context

The competition entry must be developed independently from an existing memory-plugin repository while producing demonstrably stronger user outcomes. A storage-first or dashboard-first design risks reproducing opaque automation rather than solving it.

## Decision

Neuro Core 2 will be designed around an explainable memory loop: capture, understand, retrieve, explain, resolve, and learn. It will use a canonical memory record, append-only activity events, transparent retrieval explanations, episode-first workflows, and a reviewable contradiction process. Agent Zero integration is isolated behind a verified adapter.

## Consequences

- The repository starts with product, architecture, and benchmark contracts before runtime implementation.
- Features that cannot produce inspectable evidence are deferred.
- The graph is a supporting navigation view, not the product's sole explanation surface.
- The implementation can change storage or framework adapters without abandoning its user-facing evidence contract.
- Competitive claims require benchmark evidence rather than subjective feature comparison.