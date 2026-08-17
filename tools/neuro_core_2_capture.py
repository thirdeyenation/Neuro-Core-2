"""Neuro Core 2 capture tool."""
from neuro_core_2_service import NeuroCoreService
from sqlite_store import SQLiteStore
from neuro_core_2 import Memory, Scope
from _config import load_config

def neuro_core_2_capture(text: str, project: str, agent: str | None = None, importance: float = 0.5, confidence: float = 0.5) -> dict:
    db_path = load_config()["database_path"]
    store = SQLiteStore(db_path)
    service = NeuroCoreService(store)
    memory = service.capture(Memory(text, "tool", Scope(project, agent), importance, confidence))
    return {"memory_id": memory.memory_id, "text": memory.text, "scope": {"project": memory.scope.project, "agent": memory.scope.agent}, "importance": memory.importance, "confidence": memory.confidence, "validation": memory.validation.value}
