"""Storage boundary for Neuro Core; durable backends implement this port."""
from collections.abc import Iterable
from typing import Protocol
from neuro_core_2 import Memory, Scope


class MemoryStore(Protocol):
    def put(self, memory: Memory) -> Memory: ...
    def get(self, memory_id: str) -> Memory | None: ...
    def list(self, scope: Scope) -> Iterable[Memory]: ...
    def candidate_ids(self, terms, scope) -> Iterable[str]: ...


class InMemoryStore:
    def __init__(self) -> None:
        self._items: dict[str, Memory] = {}

    def put(self, memory: Memory) -> Memory:
        self._items[memory.memory_id] = memory
        return memory

    def get(self, memory_id: str) -> Memory | None:
        return self._items.get(memory_id)

    def list(self, scope: Scope) -> tuple[Memory, ...]:
        return tuple(memory for memory in self._items.values() if memory.scope == scope)

    def candidate_ids(self, terms, scope) -> tuple[str, ...]:
        """Return memory IDs within scope whose terms intersect the query terms.

        Mirrors the SQLiteStore contract: pure candidate pre-filter, no
        validation-state filtering. Uses the exact same tokenization as the
        domain retrieve() (text.lower().split()).
        """
        term_set = set(terms)
        return tuple(
            memory.memory_id
            for memory in self._items.values()
            if memory.scope == scope and term_set & set(memory.text.lower().split())
        )
