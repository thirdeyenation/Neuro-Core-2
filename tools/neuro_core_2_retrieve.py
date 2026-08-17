"""Neuro Core 2 retrieve tool."""
from neuro_core_2_service import NeuroCoreService
from sqlite_store import SQLiteStore
from neuro_core_2 import Scope
from _config import load_config

def neuro_core_2_retrieve(query: str, project: str, agent: str | None = None) -> list[dict]:
    db_path = load_config()["database_path"]
    store = SQLiteStore(db_path)
    service = NeuroCoreService(store)
    results = service.retrieve(query, Scope(project, agent))
    return [{"memory_id": r["memory"].memory_id, "text": r["memory"].text, "scope": {"project": r["memory"].scope.project, "agent": r["memory"].scope.agent}, "importance": r["memory"].importance, "confidence": r["memory"].confidence, "validation": r["memory"].validation.value, "factors": r["factors"]} for r in results]
