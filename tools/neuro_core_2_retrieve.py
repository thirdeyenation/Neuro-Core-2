"""Neuro Core 2 retrieve tool."""
from neuro_core_2_service import NeuroCoreService
from sqlite_store import SQLiteStore
from neuro_core_2 import Scope
from _config import load_config


def neuro_core_2_retrieve(query: str, project: str, agent: str | None = None, max_results: int | None = None) -> dict:
    """Retrieve memories for a scope with a bounded result set.

    The result cap defaults to the max_results value in default_config.yaml
    (100). The optional max_results argument overrides the config value for
    a single call. The returned payload includes count_exceeded and
    total_matches so callers can distinguish truncation from exhaustion.
    """
    config = load_config()
    db_path = config["database_path"]
    if max_results is None:
        max_results = config.get("max_results", 100)
    store = SQLiteStore(db_path)
    service = NeuroCoreService(store)
    payload = service.retrieve_with_meta(query, Scope(project, agent), max_results=max_results)
    results = [
        {
            "memory_id": r["memory"].memory_id,
            "text": r["memory"].text,
            "scope": {"project": r["memory"].scope.project, "agent": r["memory"].scope.agent},
            "importance": r["memory"].importance,
            "confidence": r["memory"].confidence,
            "validation": r["memory"].validation.value,
            "factors": r["factors"],
        }
        for r in payload["results"]
    ]
    return {
        "results": results,
        "count_exceeded": payload["count_exceeded"],
        "total_matches": payload["total_matches"],
    }
