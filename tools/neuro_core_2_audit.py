"""Neuro Core 2 audit query tool.

Exposes NeuroCoreService.list_activity(...) as a first-class tool surface
for durable cross-session audit queries.

Scope isolation: Scope(project, agent) is constructed explicitly in this
tool layer and passed to the service. agent=None means project-level scope,
not "all agents".

Ordering: results are ordered by occurred_at DESC (most recent first).

Limits: default 100, maximum cap 1000. Inputs exceeding the cap return
an explicit error dict.
"""
from neuro_core_2_service import NeuroCoreService
from sqlite_store import SQLiteStore
from neuro_core_2 import Scope
from _config import load_config

MAX_LIMIT = 1000
DEFAULT_LIMIT = 100


def neuro_core_2_audit(
    project: str,
    agent: str | None = None,
    event_type: str | None = None,
    memory_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = DEFAULT_LIMIT,
) -> dict:
    """Query activity events for a given scope with optional filters.

    Args:
        project: Required scope identifier.
        agent: Optional agent scope. None means project-level scope.
        event_type: Optional filter by activity kind.
        memory_id: Optional filter by target memory ID.
        start_date: Optional inclusive ISO-8601 start bound on occurred_at.
        end_date: Optional inclusive ISO-8601 end bound on occurred_at.
        limit: Maximum number of events to return. Default 100, max 1000.

    Returns:
        Dict with either {"events": [...]} on success or
        {"error": "...", "limit": N, "max_limit": 1000} if limit exceeded.
    """
    if limit > MAX_LIMIT:
        return {
            "error": f"limit {limit} exceeds maximum cap {MAX_LIMIT}",
            "limit": limit,
            "max_limit": MAX_LIMIT,
        }

    db_path = load_config()["database_path"]
    store = SQLiteStore(db_path)
    service = NeuroCoreService(store)

    scope = Scope(project, agent)
    events = service.list_activity(scope)

    # Apply optional filters in tool layer
    if event_type is not None:
        events = [e for e in events if e.kind == event_type]
    if memory_id is not None:
        events = [e for e in events if memory_id in (e.targets or [])]
    if start_date is not None:
        events = [e for e in events if e.occurred_at >= start_date]
    if end_date is not None:
        events = [e for e in events if e.occurred_at <= end_date]

    # Order by occurred_at DESC (most recent first)
    events = sorted(events, key=lambda e: e.occurred_at, reverse=True)

    # Apply limit
    events = events[:limit]

    # Serialize each ActivityEvent to dict with full audit detail
    serialized = [
        {
            "event_id": e.event_id,
            "kind": e.kind,
            "occurred_at": e.occurred_at,
            "scope": {"project": e.scope.project, "agent": e.scope.agent},
            "targets": e.targets,
            "outcome": e.outcome,
            "evidence": e.evidence,
        }
        for e in events
    ]

    return {"events": serialized}
