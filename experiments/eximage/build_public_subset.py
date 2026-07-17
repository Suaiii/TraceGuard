"""Build a deterministic zero-shot evaluation subset from the PUBLIC ExImage release.

Scope and provenance
--------------------
Source archive is the publicly released ``ExImage.zip`` distributed through the
ExDA project README (Google Drive file id ``1s2JYbZyMe-SzWjkja9tlZFrzIJiFhwI-``,
no login required). The outer ZIP contains one nested ZIP per generator
(``ExImage/<Gen>.zip``), and each nested ZIP holds ``<Gen>/test/*.png`` and
``<Gen>/train/*.png``.

Two facts about the public release drive the design of this script:

1. The public release contains **only fake images**. There is no ``real`` split
   anywhere in the archive, so any subset built from it can support Fake Recall
   only -- never Accuracy, Macro F1, ROC AUC or a false-positive rate.
2. The public release ships **no official evaluation split** (the upstream
   ``dataset_paths.py`` is not part of the public distribution). The subset built
   here is therefore *self-constructed*; it must never be described as the split
   used by the original paper.

Sampling procedure (deterministic)
----------------------------------
For every generator found in the outer archive, in ``sorted()`` order:

1. List every image entry under that generator's ``test/`` split.
2. Sort those entry names with ``key=str.casefold`` to remove any dependence on
   ZIP central-directory ordering.
3. Draw ``--per-generator`` names with a **freshly seeded** ``random.Random(seed)``
   (default ``seed=42``) via ``rng.sample(...)``, then re-sort the drawn names.

The RNG is re-seeded per generator, so each generator's draw is independent of
how many generators precede it and of their sizes. Identical inputs therefore
always yield an identical subset, and adding a generator never perturbs another
generator's selection.

If a generator's ``test/`` split holds fewer than ``--per-generator`` images, all
of its images are taken and the shortfall is recorded verbatim in
``subset_counts.json``. The script never pads a short generator and never borrows
from ``train/``.

Outputs (written under ``--output-dir``; ``dataset/`` is gitignored)
-------------------------------------------------------------------
``fake_subset.zip``      entries laid out as ``<Gen>/<filename>.png`` so that the
                         existing pipeline can infer the generator with
                         ``--generator-part 0``. Byte-reproducible: fixed entry
                         timestamps and sorted write order.
``manifest.csv``         columns ``sample_id, generator, label, entry_path,
                         crc32, source``.
``subset_counts.json``   per-generator available/selected counts, the seed, and
                         the SHA-256 of the produced ZIP and manifest.

This script performs file-level operations only -- ZIP entry read/write, CRC-32
and SHA-256. It never decodes, renders or displays image content.
"""

import argparse
import csv
import hashlib
import json
import random
import shutil
import zipfile
from pathlib import Path, PurePosixPath

# Image suffixes recognised inside the ExImage archives.
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

# Fixed entry timestamp keeps the produced ZIP byte-reproducible across runs.
_FIXED_ZIP_DATE = (1980, 1, 1, 0, 0, 0)

DEFAULT_DATASET_NAME = "eximage_zeroshot_public"
DEFAULT_SEED = 42
DEFAULT_PER_GENERATOR = 250

PUBLIC_SOURCE = {
    "archive": "ExImage.zip",
    "origin": "ExDA project README public Google Drive link (no login required)",
    "google_drive_file_id": "1s2JYbZyMe-SzWjkja9tlZFrzIJiFhwI-",
}


def sha256_file(path: Path) -> str:
    """Stream a file through SHA-256 and return the uppercase hex digest."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(16 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def discover_generators(outer_zip: Path) -> list[str]:
    """Return sorted generator names from ``ExImage/<Gen>.zip`` outer entries."""
    with zipfile.ZipFile(outer_zip) as archive:
        names = [
            PurePosixPath(info.filename).stem
            for info in archive.infolist()
            if not info.is_dir() and info.filename.lower().endswith(".zip")
        ]
    if not names:
        raise ValueError(f"no nested generator ZIPs found in {outer_zip}")
    return sorted(names)


def list_test_entries(nested_zip: Path, generator: str) -> list[str]:
    """List image entry names under the generator's ``test/`` split."""
    with zipfile.ZipFile(nested_zip) as archive:
        entries = []
        for info in archive.infolist():
            if info.is_dir():
                continue
            path = PurePosixPath(info.filename)
            if path.suffix.lower() not in IMAGE_SUFFIXES:
                continue
            parts = path.parts
            if ".ipynb_checkpoints" in parts:
                continue
            # Expect <Gen>/test/<file>; accept any depth whose parent dir is test.
            if len(parts) < 2 or parts[-2].casefold() != "test":
                continue
            entries.append(info.filename)
    return sorted(entries, key=str.casefold)


def select_entries(entries: list[str], per_generator: int, seed: int) -> list[str]:
    """Deterministically draw ``per_generator`` names from sorted ``entries``.

    A fresh ``random.Random(seed)`` is used so the draw depends only on the
    sorted candidate list and the seed.
    """
    if per_generator <= 0:
        raise ValueError("per_generator must be positive")
    candidates = sorted(entries, key=str.casefold)
    if len(candidates) <= per_generator:
        return candidates
    rng = random.Random(seed)
    return sorted(rng.sample(candidates, per_generator), key=str.casefold)


def _extract_nested(outer: zipfile.ZipFile, entry: str, target: Path) -> Path:
    """Stream one nested ZIP out of the outer archive onto disk."""
    target.parent.mkdir(parents=True, exist_ok=True)
    with outer.open(entry) as source, target.open("wb") as sink:
        shutil.copyfileobj(source, sink, length=16 * 1024 * 1024)
    return target


def build_public_subset(
    source_zip,
    output_dir,
    *,
    per_generator: int = DEFAULT_PER_GENERATOR,
    seed: int = DEFAULT_SEED,
    dataset_name: str = DEFAULT_DATASET_NAME,
    work_dir=None,
) -> dict:
    """Build ``fake_subset.zip`` + ``manifest.csv`` from the public ExImage ZIP."""
    source_zip = Path(source_zip).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    work_dir = Path(work_dir).resolve() if work_dir else output_dir / "_work"
    work_dir.mkdir(parents=True, exist_ok=True)

    generators = discover_generators(source_zip)
    subset_zip = output_dir / "fake_subset.zip"
    manifest_path = output_dir / "manifest.csv"

    manifest_rows: list[dict] = []
    counts: dict[str, dict] = {}
    seen_ids: set[str] = set()

    with zipfile.ZipFile(source_zip) as outer:
        nested_lookup = {
            PurePosixPath(info.filename).stem: info.filename
            for info in outer.infolist()
            if not info.is_dir() and info.filename.lower().endswith(".zip")
        }
        with zipfile.ZipFile(subset_zip, "w", zipfile.ZIP_DEFLATED) as out:
            for generator in generators:
                nested_path = work_dir / f"{generator}.zip"
                try:
                    _extract_nested(outer, nested_lookup[generator], nested_path)
                    available = list_test_entries(nested_path, generator)
                    chosen = select_entries(available, per_generator, seed)
                    counts[generator] = {
                        "test_available": len(available),
                        "selected": len(chosen),
                        "short": len(chosen) < per_generator,
                    }
                    with zipfile.ZipFile(nested_path) as nested:
                        for name in chosen:
                            payload = nested.read(name)
                            filename = PurePosixPath(name).name
                            entry_path = f"{generator}/{filename}"
                            sample_id = (
                                f"{dataset_name}:{generator.casefold()}:"
                                f"{PurePosixPath(filename).stem}"
                            )
                            if sample_id in seen_ids:
                                raise ValueError(f"duplicate sample_id: {sample_id}")
                            seen_ids.add(sample_id)
                            info = zipfile.ZipInfo(entry_path, date_time=_FIXED_ZIP_DATE)
                            info.compress_type = zipfile.ZIP_DEFLATED
                            out.writestr(info, payload)
                            manifest_rows.append(
                                {
                                    "sample_id": sample_id,
                                    "generator": generator,
                                    "label": "fake",
                                    "entry_path": entry_path,
                                    "crc32": format(zipfile.crc32(payload) & 0xFFFFFFFF, "08X"),
                                    "source": (
                                        f"{source_zip.name}!{nested_lookup[generator]}!{name}"
                                    ),
                                }
                            )
                finally:
                    nested_path.unlink(missing_ok=True)

    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["sample_id", "generator", "label", "entry_path", "crc32", "source"],
        )
        writer.writeheader()
        writer.writerows(manifest_rows)

    shutil.rmtree(work_dir, ignore_errors=True)

    summary = {
        "dataset": dataset_name,
        "label": "fake",
        "note": (
            "Self-constructed subset of the PUBLIC ExImage release. The public "
            "release contains no real images and ships no official split; this "
            "subset is not the split used by the original paper."
        ),
        "seed": seed,
        "per_generator_target": per_generator,
        "sampling": (
            "per generator: sort test/ entry names casefold, then "
            "random.Random(seed).sample(...), re-sorted"
        ),
        "source_zip": {
            "path": str(source_zip),
            "size_bytes": source_zip.stat().st_size,
            **PUBLIC_SOURCE,
        },
        "generators": generators,
        "counts_by_generator": counts,
        "selected_total": len(manifest_rows),
        "fake_subset_zip": {
            "path": str(subset_zip),
            "size_bytes": subset_zip.stat().st_size,
            "sha256": sha256_file(subset_zip),
        },
        "manifest": {
            "path": str(manifest_path),
            "sha256": sha256_file(manifest_path),
        },
    }
    with (output_dir / "subset_counts.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
    return summary


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a deterministic zero-shot subset from the public ExImage release"
    )
    parser.add_argument("--source-zip", default="dataset/eximage/ExImage.zip")
    parser.add_argument("--output-dir", default="dataset/eximage_public_subset")
    parser.add_argument("--per-generator", type=int, default=DEFAULT_PER_GENERATOR)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--dataset-name", default=DEFAULT_DATASET_NAME)
    parser.add_argument("--work-dir", default=None)
    return parser


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    summary = build_public_subset(
        args.source_zip,
        args.output_dir,
        per_generator=args.per_generator,
        seed=args.seed,
        dataset_name=args.dataset_name,
        work_dir=args.work_dir,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
