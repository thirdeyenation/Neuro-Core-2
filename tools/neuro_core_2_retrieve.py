"""Neuro Core 2 retrieve tool."""
from pathlib import Path
import yaml
from neuro_core_2_service import NeuroCoreService
from sqlite_store import SQLiteStore
from neuro_core_2 import Scope

def neuro_core_2_retrieve(query: str, project: str, agent: str | None = None) -> list[dict]:
    config_path = Path(__file__).resolve().parent.parent / "default_config.yaml"
    with config_path.open() as f:
        cfg = yaml.safe_load(f)
    db_path_raw = cfg["neuro_core_2"]["database_path"]
    db_path = str((config_path.parent / db_path_raw).resolve()) if not os.path.isabs(db_path_raw) else db_path_raw
    store = SQLiteStore(db_path)
    service = NeuroCoreService(store)
    results = service.retrieve(query, Scope(project, agent))
    return [{"memory_id": r["memory"].memory_id, "text": r["memory"].text, "scope": {"project": r["memory"].scope.project, "agent": r["memory"].scope.agent}, "importance": r["memory"].importance, "confidence": r["memory"].confidence, "validation": r["memory"].validation.value, "factors": r["factors"]} for r in results]
