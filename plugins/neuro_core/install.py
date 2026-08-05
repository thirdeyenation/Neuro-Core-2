"""Copy Neuro Core and its Agent Zero shell into a deployable plugin directory."""
from pathlib import Path
from shutil import copy2, copytree

ROOT = Path(__file__).resolve().parents[2]
DESTINATION = Path("/a0/usr/plugins/neuro_core_2")
MODULES = ("neuro_core.py", "memory_lifecycle.py", "memory_store.py", "sqlite_store.py", "activity_ledger.py", "neuro_service.py")


def install(destination: Path = DESTINATION) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    for name in MODULES:
        copy2(ROOT / name, destination / name)
    for name in ("plugin.yaml", "default_config.yaml", "README.md"):
        copy2(Path(__file__).parent / name, destination / name)
    source_tools = Path(__file__).parent / "tools"
    copytree(source_tools, destination / "tools", dirs_exist_ok=True)
    return destination


if __name__ == "__main__":
    print(install())
