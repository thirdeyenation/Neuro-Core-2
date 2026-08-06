"""Neuro Core 2 capture tool."""
from pathlib import Path
import yaml
from neuro_service import NeuroCoreService
from sqlite_store import SQLiteStore
from neuro_core import Memory, Scope

def neuro_core_2_capture(text: str, project: str, agent: str | None = None, importance: float = 0.5, confidence: float = 0.5) -> dict:
    config_path = Path(__file__).resolve().parent.parent / "default_config.yaml"
    with config_path.open() as f:
        cfg = yaml.safe_load(f)
    db_path = cfg["neuro_core_2"]["database_path"]
    store = SQLiteStore(db_path)
    service = NeuroCoreService(store)
    memory = service.capture(Memory(text, "tool", Scope(project, agent), importance, confidence))
    return {"memory_id": memory.memory_id, "text": memory.text, "scope": {"project": memory.scope.project, "agent": memory.scope.agent}, "importance": memory.importance, "confidence": memory.confidence, "validation": memory.validation.value}
