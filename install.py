"""Install Neuro Core 2 plugin files into the running Agent Zero container."""
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Target the Agent Zero container's plugins directory.
# Allow override via NEURO_CORE_2_INSTALL_TARGET environment variable.
_default_target = Path("/a0/usr/plugins") / "neuro_core_2"
TARGET = Path(os.environ.get("NEURO_CORE_2_INSTALL_TARGET", str(_default_target))).resolve()

# Safety check: refuse to run if the target would be a subdirectory of the source.
# This prevents the nested-duplicate problem that occurred when TARGET was a
# relative path resolved against the current working directory.
try:
    TARGET.relative_to(HERE)
    sys.exit(
        f"ERROR: install target {TARGET} is inside the source directory {HERE}. "
        f"Refusing to run to avoid creating a nested duplicate. "
        f"Set NEURO_CORE_2_INSTALL_TARGET to a path outside {HERE} and retry."
    )
except ValueError:
    pass  # TARGET is not inside HERE — safe to proceed.

TARGET.mkdir(parents=True, exist_ok=True)
for name in ["plugin.yaml", "default_config.yaml", "README.md"]:
    shutil.copy(HERE / name, TARGET / name)

TOOLS_SRC = HERE / "tools"
TOOLS_DST = TARGET / "tools"
TOOLS_DST.mkdir(parents=True, exist_ok=True)
for name in ["neuro_core_2_capture.py", "neuro_core_2_retrieve.py", "neuro_core_2_validate.py"]:
    shutil.copy(TOOLS_SRC / name, TOOLS_DST / name)

print(f"Installed Neuro Core 2 plugin to {TARGET}")
