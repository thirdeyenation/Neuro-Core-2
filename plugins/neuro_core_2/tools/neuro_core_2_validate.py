"""Neuro Core 2 validate tool."""
from pathlib import Path
import yaml
from neuro_service import NeuroCoreService
from sqlite_store import SQLiteStore
from memory_lifecycle import ValidationState

def neuro_core_2_validate(memory_id: str, target: str) -> dict:
    config_path = Path(__file__).resolve().parent.parent / "default_config.yaml"
    with config_path.open() as f:
        cfg = yaml.safe_load(f)
    db_path = cfg["neuro_core_2"]["database_path"]
    store = SQLiteStore(db_path)
    service = NeuroCoreService(store)
    updated = service.validate(memory_id, ValidationState(target))
    return {"memory_id": updated.memory_id, "text": updated.text, "scope": {"project": updated.scope.project, "agent": updated.scope.agent}, "importance": updated.importance, "confidence": updated.confidence, "validation": updated.validation.value}
