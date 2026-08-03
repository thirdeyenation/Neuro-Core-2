# Neuro Core 2 Product Specification

## Product definition

Neuro Core 2 is an explainable agent-memory plugin. It provides scoped memory capture, episode-aware retrieval, trust and freshness signals, contradiction review, and an operator-facing Memory Workbench.

## Core user loop

1. An agent or user action creates a memory candidate.
2. Neuro Core 2 classifies the candidate with visible provenance and confidence.
3. Related memories form an episode when the evidence supports a shared task narrative.
4. A later task retrieves scoped context using an explicit retrieval plan.
5. The agent receives compact context plus source references.
6. The user can inspect why each item appeared, its trust state, and its relationship to the current task.
7. A user or authorized agent may validate, dispute, supersede, relate, defer, or resolve memory state; the prior record remains available.

## Memory Workbench

The primary interface answers three questions: **What did Neuro Core 2 do? What needs attention? What context is helping now?**

### Activity

A chronological feed of capture, retrieval, episode, reflection, contradiction, policy, and resolution events. Each event displays a plain-language summary and links to its evidence.

### Context view

A task-scoped view lists selected memories and a retrieval explanation: query intent, candidate source, ranking factors, relationship path, freshness, and confidence.

### Semantic map

A graph is optional navigation, not the only interface. It uses accessible visual encodings for type, validation state, episode membership, relationships, and attention state. Selecting a node opens an evidence card.

### Review queue

A queue prioritizes disputed claims, stale high-impact memories, unresolved contradictions, and failed/low-confidence reflections.

### Controls

Users can inspect effective capture, retrieval, episode, reflection, contradiction, and observability policy by project and agent scope. Disabling visibility must not silently disable memory, and vice versa.

## Trust model

A memory record has separate fields for importance, confidence, stability, freshness, validation state, provenance, scope, and lineage. A single composite score may assist ranking but never replaces the component explanation.

## Retrieval contract

A retrieval result contains selected memories and a machine-readable explanation. At minimum, each selected memory records its source, selection reason, ranking factors, graph/episode support where applicable, and applicable policy.

## Contradiction workflow

Detection creates a reviewable candidate, not a silent overwrite. The review view displays both sources, detection rationale, confidence, timestamps, scope, and permitted resolution actions. Resolution creates a new immutable event.

## Accessibility and safety

All meaning encoded by color has a text, shape, pattern, or label equivalent. Loading, empty, degraded, and error states are explicit. The plugin distinguishes unknown, unavailable, and disabled behavior rather than presenting a generic success state.