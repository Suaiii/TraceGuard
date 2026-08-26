from __future__ import annotations

import hashlib
import json
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "作品" / "TraceGuard_源程序.zip"

ROOT_FILES = {
    "README.md",
    "REPRODUCIBILITY.md",
    "batch_analyze.py",
    "calibrate_risk.py",
    "classify_cases.py",
    "evaluate_localization.py",
    "requirements-dev.txt",
    "requirements.txt",
    "run_test.py",
    "server.py",
    "start_traceguard.bat",
}
DIRECTORIES = ("configs", "detection", "explanation", "experiments", "tests", "web")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest().upper()


def tracked_files() -> list[Path]:
    raw = subprocess.check_output(["git", "-C", str(ROOT), "ls-files"], text=True)
    result = []
    for item in raw.splitlines():
        if item in ROOT_FILES or any(item.startswith(d + "/") for d in DIRECTORIES):
            p = ROOT / item
            if p.is_file():
                result.append(p)
    return sorted(result)


def main():
    files = tracked_files()
    checkpoint = ROOT / "best.pth"
    if not checkpoint.is_file():
        raise FileNotFoundError(checkpoint)
    manifest = {
        "package": "TraceGuard source and offline runtime package",
        "formal_title": "TraceGuard:面向社交媒体网络传播的 可解释 AIGC 图像取证平台",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source_root": "TraceGuard/",
        "runtime_entry": "TraceGuard/server.py",
        "checkpoint": "TraceGuard/best.pth",
        "checkpoint_sha256": sha256(checkpoint),
        "included_file_count": len(files) + 1,
        "exclusions": [".git", "__pycache__", "*.pyc", "results", "tmp", "output", "internal coordination files"],
        "files": [str(p.relative_to(ROOT)).replace("\\", "/") for p in files],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in files:
            arc = Path("TraceGuard") / path.relative_to(ROOT)
            zf.write(path, arcname=str(arc).replace("\\", "/"))
        # Model weights are already compressed; store them without wasting CPU.
        zf.write(checkpoint, arcname="TraceGuard/best.pth", compress_type=zipfile.ZIP_STORED)
        zf.writestr("TraceGuard/PACKAGE_MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    print(json.dumps({"output": str(OUTPUT), "size": OUTPUT.stat().st_size, "checkpoint_sha256": manifest["checkpoint_sha256"], "files": manifest["included_file_count"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
