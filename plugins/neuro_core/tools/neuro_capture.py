"""Agent Zero tool for capturing scoped Neuro Core memories."""
from pathlib import Path
from helpers.tool import Tool

from neuro_core import Memory, Scope
from neuro_service import NeuroCoreService
from sqlite_store import SQLiteStore


def _load_config() -> dict[str, str]:
    path = Path(__file__).resolve().parents[1] / "default_config.yaml"
    config: dict[str, str] = {}
    if path.exists():
        for raw in path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            key, value = line.split(":", 1)
            config[key.strip()] = value.strip()
    return config


def _db_path() -> str:
    return _load_config().get("database_path", "/a0/usr/plugins/neuro_core_2/neuro_core.db")


class NeuroCapture(Tool):
    async def execute(self, text="", source="agent_zero", project="default", agent="", importance=0.5, confidence=0.5, **kwargs):
        if not text or not project:
            raise ValueError("text and project are required")
        store = SQLiteStore(_db_path())
        try:
            service = NeuroCoreService(store)
            memory = service.capture(Memory(text, source, Scope(project, agent or None), float(importance), float(confidence)))
            return {"memory_id": memory.memory_id, "outcome": "stored", "scope": project}
        finally:
            store.close()
