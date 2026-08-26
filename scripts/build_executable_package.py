from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "tmp" / "TraceGuard_executable_stage_title_unified"
OUTPUT = ROOT / "作品" / "TraceGuard_可执行程序.zip"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest().upper()


def main():
    exe = STAGE / "TraceGuard.exe"
    runtime = STAGE / "TraceGuard"
    readme = STAGE / "README_可执行程序.txt"
    for path in (exe, runtime / "server.py", runtime / "best.pth", readme):
        if not path.exists():
            raise FileNotFoundError(path)
    manifest = {
        "package": "TraceGuard Windows executable launcher and runtime",
        "formal_title": "TraceGuard:面向社交媒体网络传播的 可解释 AIGC 图像取证平台",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "launcher": "TraceGuard.exe",
        "runtime": "TraceGuard/",
        "launcher_sha256": sha256(exe),
        "checkpoint_sha256": sha256(runtime / "best.pth"),
        "runtime_entry": "TraceGuard/server.py",
        "launch_test": "TraceGuard.exe --help -> exit code 0",
        "notes": "The launcher starts server.py and uses an installed Python environment; PyTorch and the checkpoint remain in the runtime directory.",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in sorted(STAGE.rglob("*")):
            if path.is_file():
                zf.write(path, arcname=str(path.relative_to(STAGE)).replace("\\", "/"), compress_type=zipfile.ZIP_STORED if path.suffix == ".pth" else zipfile.ZIP_DEFLATED)
        zf.writestr("PACKAGE_MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    print(json.dumps({"output": str(OUTPUT), "size": OUTPUT.stat().st_size, **manifest}, ensure_ascii=False))


if __name__ == "__main__":
    main()
