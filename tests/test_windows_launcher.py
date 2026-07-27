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
    # 必须用显式路径：部分 Windows 配置（NoDefaultCurrentDirectoryInExePath）下
    # cmd 不从当前目录解析裸文件名，会报 "is not recognized as an internal or
    # external command"，与启动脚本本身是否可用无关。
    launcher = PROJECT_ROOT / "start_traceguard.bat"
    result = subprocess.run(
        ["cmd", "/c", str(launcher), "--help"],
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
