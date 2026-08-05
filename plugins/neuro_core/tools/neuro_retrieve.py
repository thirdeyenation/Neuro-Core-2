"""Agent Zero tool for explainable Neuro Core retrieval."""
from pathlib import Path
from helpers.tool import Tool

from neuro_core import Scope
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


class NeuroRetrieve(Tool):
    async def execute(self, query="", project="default", agent="", **kwargs):
        if not query or not project:
            raise ValueError("query and project are required")
        store = SQLiteStore(_db_path())
        try:
            results = NeuroCoreService(store).retrieve(query, Scope(project, agent or None))
            return [{"memory_id": item["memory"].memory_id, "text": item["memory"].text, "source": item["memory"].source, "score": item["score"], "factors": item["factors"]} for item in results]
        finally:
            store.close()
