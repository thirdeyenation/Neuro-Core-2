"""Run Neuro Core's standard-library test baseline from any working directory."""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-v"], cwd=root)
raise SystemExit(result.returncode)
