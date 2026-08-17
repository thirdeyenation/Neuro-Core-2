"""Neuro Core 2 validate tool."""
from neuro_core_2_service import NeuroCoreService
from sqlite_store import SQLiteStore
from memory_lifecycle import ValidationState
from _config import load_config

def neuro_core_2_validate(memory_id: str, target: str) -> dict:
    db_path = load_config()["database_path"]
    store = SQLiteStore(db_path)
    service = NeuroCoreService(store)
    updated = service.validate(memory_id, ValidationState(target))
    return {"memory_id": updated.memory_id, "text": updated.text, "scope": {"project": updated.scope.project, "agent": updated.scope.agent}, "importance": updated.importance, "confidence": updated.confidence, "validation": updated.validation.value}
