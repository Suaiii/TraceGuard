"""Windows launcher contract tests."""

import os
import subprocess
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(os.name != "nt", reason="Windows batch launcher")
def test_launcher_forwards_help_without_loading_checkpoint():
    env = os.environ.copy()
    env["TRACEGUARD_PYTHON"] = sys.executable
    result = subprocess.run(
        ["cmd", "/c", "start_traceguard.bat", "--help"],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )

    assert result.returncode == 0
    assert "--checkpoint" in result.stdout
