"""Minimal, framework-independent Neuro Core foundation."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Scope:
    project: str
    agent: str | None = None

@dataclass(frozen=True)
class Memory:
    text: str
    source: str
    scope: Scope
    importance: float = 0.5
    confidence: float = 0.5

def retrieve(query: str, scope: Scope, memories: list[Memory]) -> list[dict]:
    terms = set(query.lower().split())
    results = []
    for memory in memories:
        if memory.scope != scope:
            continue
        overlap = len(terms & set(memory.text.lower().split())) / max(len(terms), 1)
        score = round(.5 * overlap + .25 * memory.importance + .25 * memory.confidence, 6)
        results.append({"memory": memory, "score": score, "factors": {"overlap": overlap, "importance": memory.importance, "confidence": memory.confidence}})
    return sorted(results, key=lambda item: item["score"], reverse=True)
