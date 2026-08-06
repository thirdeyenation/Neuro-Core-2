"""Install Neuro Core 2 plugin files into the running Agent Zero container."""
import os
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
TARGET = Path("plugins") / "neuro_core_2"

TARGET.mkdir(parents=True, exist_ok=True)
for name in ["plugin.yaml", "default_config.yaml", "README.md"]:
    shutil.copy(HERE / name, TARGET / name)

TOOLS_SRC = HERE / "tools"
TOOLS_DST = TARGET / "tools"
TOOLS_DST.mkdir(parents=True, exist_ok=True)
for name in ["neuro_core_2_capture.py", "neuro_core_2_retrieve.py", "neuro_core_2_validate.py"]:
    shutil.copy(TOOLS_SRC / name, TOOLS_DST / name)

print(f"Installed Neuro Core 2 plugin to {TARGET}")
