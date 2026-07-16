"""Submission packaging script syntax tests."""

import os
import subprocess
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(os.name != "nt", reason="PowerShell packaging script")
def test_submission_package_script_parses():
    script = PROJECT_ROOT / "scripts" / "build_submission_package.ps1"
    command = (
        "$errors = $null; "
        f"[System.Management.Automation.Language.Parser]::ParseFile('{script}', "
        "[ref]$null, [ref]$errors) | Out-Null; "
        "if ($errors.Count -gt 0) { $errors | ForEach-Object { Write-Error $_ }; exit 1 }"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )

    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(os.name != "nt", reason="PowerShell packaging script")
def test_submission_package_contains_runtime_allowlist_only(tmp_path):
    script = PROJECT_ROOT / "scripts" / "build_submission_package.ps1"
    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "-OutputRoot",
            str(tmp_path),
            "-NoArchive",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        cwd=PROJECT_ROOT,
    )

    assert result.returncode == 0, result.stderr
    package_dir = Path(result.stdout.strip().splitlines()[-1])
    program_dir = package_dir / "program"

    assert (program_dir / "server.py").is_file()
    assert (program_dir / "README.md").is_file()
    assert (program_dir / "explanation" / "pipeline.py").is_file()
    assert (program_dir / "tests" / "test_pipeline.py").is_file()

    for internal_path in (
        "AGENTS.md",
        "DEVLOG.md",
        "docs",
        "reports",
        "scripts",
        ".gitignore",
    ):
        assert not (program_dir / internal_path).exists(), internal_path
