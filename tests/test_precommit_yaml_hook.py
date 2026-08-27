"""Unit tests for the pre-commit YAML validation hook."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOK_PATH = Path("/a0/usr/plugins/neuro_core_2/scripts/hooks/pre-commit")


class TestPrecommitHook(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.repo_dir = Path(self.tmpdir)
        subprocess.run(["git", "init", "-q"], cwd=self.repo_dir, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=self.repo_dir, check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=self.repo_dir, check=True,
        )
        # Copy hook into .git/hooks/pre-commit
        git_hooks = self.repo_dir / ".git" / "hooks"
        git_hooks.mkdir(parents=True, exist_ok=True)
        hook_dest = git_hooks / "pre-commit"
        hook_dest.write_text(HOOK_PATH.read_text())
        hook_dest.chmod(0o755)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _stage_file(self, name, content):
        path = self.repo_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        subprocess.run(["git", "add", name], cwd=self.repo_dir, check=True)

    def _run_commit(self):
        result = subprocess.run(
            ["git", "commit", "-m", "test"],
            cwd=self.repo_dir, capture_output=True, text=True,
        )
        return result

    def test_valid_yaml_passes(self):
        self._stage_file("config.yaml", "key: value\nlist:\n  - a\n  - b\n")
        result = self._run_commit()
        self.assertEqual(result.returncode, 0, f"Expected pass, got: {result.stderr}")

    def test_invalid_yaml_blocks(self):
        # Unquoted colon-space in scalar value
        self._stage_file("bad.yaml", "key: value: with: colons\n")
        result = self._run_commit()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("YAML", result.stderr)

    def test_excluded_a0proj_files_skipped(self):
        # Even invalid YAML in .a0proj/ should be skipped
        self._stage_file(".a0proj/team/bad.yaml", "key: value: with: colons\n")
        result = self._run_commit()
        self.assertEqual(result.returncode, 0, f"Expected pass (excluded), got: {result.stderr}")

    def test_non_yaml_files_ignored(self):
        self._stage_file("script.py", "def f():\n    return 'value: with: colons'\n")
        result = self._run_commit()
        self.assertEqual(result.returncode, 0)

    def test_mixed_valid_and_invalid(self):
        self._stage_file("good.yaml", "key: value\n")
        self._stage_file("bad.yaml", "key: value: with: colons\n")
        result = self._run_commit()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("bad.yaml", result.stderr)

    def test_empty_yaml_file_passes(self):
        self._stage_file("empty.yaml", "")
        result = self._run_commit()
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
