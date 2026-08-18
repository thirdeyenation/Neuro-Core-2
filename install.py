"""Install Neuro Core 2 plugin files into the running Agent Zero container."""
import importlib.util
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


# --- Validation checks (run after copy, before reporting success) ---

EXPECTED_PLUGIN_NAME = "neuro_core_2"
REQUIRED_MANIFEST_FIELDS = ("name", "version", "author")
TOOL_FILES = (
    "neuro_core_2_capture.py",
    "neuro_core_2_retrieve.py",
    "neuro_core_2_validate.py",
)


def _parse_simple_yaml(text):
    """Parse a simple key:value YAML document.

    Handles the subset of YAML used by plugin.yaml: top-level scalar keys
    with string values. Block scalars (`key: |`) are recorded as present
    but their content is not parsed (we only need name/version/author).
    Returns a dict.
    """
    result = {}
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[0] in " \t":
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value in ("|", "|-", ">", ">-") or value == "":
            result.setdefault(key, None)
            continue
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        result[key] = value
    return result


def validate_permissions():
    """Verify TARGET directory is writable."""
    if not os.access(str(TARGET), os.W_OK):
        sys.exit(
            f"ERROR: target directory {TARGET} is not writable. "
            f"Permission validation failed. "
            f"Check directory permissions and retry."
        )
    print(f"[OK] Permission validation: {TARGET} is writable")


def _load_manifest():
    """Load and parse plugin.yaml from TARGET. Exits on failure."""
    manifest_path = TARGET / "plugin.yaml"
    if not manifest_path.is_file():
        sys.exit(
            f"ERROR: plugin.yaml not found at {manifest_path}. "
            f"Discovery validation failed."
        )
    try:
        text = manifest_path.read_text(encoding="utf-8")
    except OSError as exc:
        sys.exit(
            f"ERROR: could not read {manifest_path}: {exc}. "
            f"Discovery validation failed."
        )
    try:
        manifest = _parse_simple_yaml(text)
    except Exception as exc:
        sys.exit(
            f"ERROR: plugin.yaml at {manifest_path} is not valid YAML: {exc}. "
            f"Discovery validation failed."
        )
    return manifest_path, manifest


def validate_discovery():
    """Verify plugin.yaml is valid YAML with required fields."""
    manifest_path, manifest = _load_manifest()
    missing = [f for f in REQUIRED_MANIFEST_FIELDS if not manifest.get(f)]
    if missing:
        sys.exit(
            f"ERROR: plugin.yaml at {manifest_path} is missing required fields: "
            f"{', '.join(missing)}. Discovery validation failed."
        )
    print(
        f"[OK] Discovery validation: plugin.yaml is valid YAML "
        f"with required fields ({', '.join(REQUIRED_MANIFEST_FIELDS)})"
    )


def validate_manifest_behavior():
    """Verify plugin name matches expected identity."""
    _, manifest = _load_manifest()
    name = manifest.get("name")
    if name != EXPECTED_PLUGIN_NAME:
        sys.exit(
            f"ERROR: plugin name in plugin.yaml is {name!r}, "
            f"expected {EXPECTED_PLUGIN_NAME!r}. "
            f"Manifest behavior validation failed."
        )
    print(f"[OK] Manifest behavior validation: plugin name is {EXPECTED_PLUGIN_NAME!r}")


def validate_imports():
    """Verify all copied .py files import without error."""
    target_str = str(TARGET)
    tools_str = str(TOOLS_DST)
    added = []
    for p in (target_str, tools_str):
        if p not in sys.path:
            sys.path.insert(0, p)
            added.append(p)
    try:
        for tool_name in TOOL_FILES:
            tool_path = TOOLS_DST / tool_name
            if not tool_path.is_file():
                sys.exit(
                    f"ERROR: tool file {tool_path} not found. "
                    f"Import validation failed."
                )
            spec = importlib.util.spec_from_file_location(
                f"_neuro_core_2_install_check_{tool_name[:-3]}", str(tool_path)
            )
            if spec is None or spec.loader is None:
                sys.exit(
                    f"ERROR: could not create import spec for {tool_path}. "
                    f"Import validation failed."
                )
            module = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(module)
            except Exception as exc:
                sys.exit(
                    f"ERROR: importing {tool_path} failed: "
                    f"{type(exc).__name__}: {exc}. "
                    f"Import validation failed."
                )
    finally:
        for p in added:
            try:
                sys.path.remove(p)
            except ValueError:
                pass
    print(
        f"[OK] Import validation: all {len(TOOL_FILES)} tool files "
        f"import without error"
    )


validate_permissions()
validate_discovery()
validate_manifest_behavior()
validate_imports()

print(f"Installed Neuro Core 2 plugin to {TARGET}")
