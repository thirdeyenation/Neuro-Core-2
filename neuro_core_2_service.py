"""Application service composing Neuro Core domain capabilities."""
from activity_ledger import ActivityEvent, ActivityLedger
from memory_lifecycle import ValidationState, transition
from memory_store import MemoryStore
from neuro_core_2 import Memory, Scope, retrieve


class NeuroCoreService:
    def __init__(self, store: MemoryStore, ledger: ActivityLedger | None = None) -> None:
        self.store = store
        self.ledger = ledger or ActivityLedger()

    def capture(self, memory: Memory) -> Memory:
        self.store.put(memory)
        self._event("captured", memory, "stored")
        return memory

    def retrieve(self, query: str, scope: Scope, max_results: int | None = None) -> list[dict]:
        """Backward-compatible retrieve returning the ranked result list.

        Uses candidate_ids as a pure candidate pre-filter before domain
        scoring, then applies the result cap after scoring and sorting.
        Returns only the result list (no cap metadata) for compatibility
        with existing callers; use retrieve_with_meta() for the full
        payload including count_exceeded and total_matches.
        """
        return self.retrieve_with_meta(query, scope, max_results)["results"]

    def retrieve_with_meta(self, query: str, scope: Scope, max_results: int | None = None) -> dict:
        """Retrieve with cap metadata.

        Returns a dict with:
          - results: ranked result list (same shape as domain retrieve())
          - count_exceeded: True when the full match count exceeds max_results
          - total_matches: the full match count before the cap

        The index is a pure candidate pre-filter: candidate_ids(terms, scope)
        returns exactly the memories within scope whose text.lower().split()
        has non-empty intersection with query.lower().split(). Scoring,
        ranking, and the factors dict remain in the domain retrieve()
        function and are unchanged. The cap is applied AFTER scoring and
        sorting (top-K selection), never before. Silent truncation is
        prohibited: callers receive count_exceeded and total_matches.
        """
        terms = set(query.lower().split())
        candidate_ids = getattr(self.store, "candidate_ids", None)
        if callable(candidate_ids):
            ids = candidate_ids(terms, scope)
            memories = [self.store.get(mid) for mid in ids]
            memories = [m for m in memories if m is not None]
        else:
            memories = list(self.store.list(scope))
        results = retrieve(query, scope, memories)
        total_matches = len(results)
        count_exceeded = False
        if max_results is not None and total_matches > max_results:
            results = results[:max_results]
            count_exceeded = True
        for item in results:
            self._event("retrieved", item["memory"], "selected")
        return {
            "results": results,
            "count_exceeded": count_exceeded,
            "total_matches": total_matches,
        }

    def validate(self, memory_id: str, target: ValidationState) -> Memory:
        current = self.store.get(memory_id)
        if current is None:
            raise KeyError(memory_id)
        updated = Memory(current.text, current.source, current.scope, current.importance, current.confidence, transition(current.validation, target), current.memory_id)
        self.store.put(updated)
        self._event("validation_changed", updated, target.value)
        return updated

    def list_activity(self, scope: Scope | None = None) -> tuple[tuple, ...] | tuple[ActivityEvent, ...]:
        list_events = getattr(self.store, "list_events", None)
        if callable(list_events):
            return list_events(scope)
        return self.ledger.for_scope(scope) if scope is not None else self.ledger.all()

    def _event(self, kind: str, memory: Memory, outcome: str) -> None:
        event = ActivityEvent(kind, memory.scope, (memory.memory_id,), outcome, {"source": memory.source})
        self.ledger.append(event)
        append_event = getattr(self.store, "append_event", None)
        if callable(append_event):
            append_event(event)
