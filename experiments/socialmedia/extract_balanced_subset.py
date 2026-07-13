"""Extract a deterministic balanced subset from prediction-indexed ZIP archives."""

import argparse
import csv
import hashlib
import json
import random
import zipfile
from collections import defaultdict
from pathlib import Path


def _allocate_fake_counts(groups: dict[str, list[dict]], total: int) -> dict[str, int]:
    names = sorted(groups)
    if not names:
        raise ValueError("no fake generator groups are available")
    base, remainder = divmod(total, len(names))
    allocation = {name: base + (index < remainder) for index, name in enumerate(names)}
    if any(allocation[name] > len(groups[name]) for name in names):
        raise ValueError("requested fake count exceeds at least one generator group")
    return allocation


def extract_balanced_subset(
    predictions_csv: Path,
    output_dir: Path,
    *,
    variant: str,
    real_count: int,
    fake_count: int,
    seed: int,
) -> dict:
    predictions_csv = Path(predictions_csv)
    output_dir = Path(output_dir)
    with predictions_csv.open("r", encoding="utf-8", newline="") as handle:
        rows = [
            row
            for row in csv.DictReader(handle)
            if row.get("status") == "ok" and row.get("variant", "").lower() == variant.lower()
        ]

    real_rows = [row for row in rows if row.get("label") == "real"]
    fake_groups = defaultdict(list)
    for row in rows:
        if row.get("label") == "fake":
            fake_groups[row.get("generator") or "unknown"].append(row)
    if real_count > len(real_rows):
        raise ValueError(f"requested {real_count} real images, only {len(real_rows)} available")

    rng = random.Random(seed)
    selected = rng.sample(sorted(real_rows, key=lambda row: row["sample_id"]), real_count)
    allocation = _allocate_fake_counts(fake_groups, fake_count)
    for generator in sorted(fake_groups):
        candidates = sorted(fake_groups[generator], key=lambda row: row["sample_id"])
        selected.extend(rng.sample(candidates, allocation[generator]))

    output_dir.mkdir(parents=True, exist_ok=True)
    for label in ("real", "fake"):
        (output_dir / label).mkdir(parents=True, exist_ok=True)

    archives: dict[str, zipfile.ZipFile] = {}
    manifest_rows = []
    try:
        for row in selected:
            archive_path = row["archive_path"]
            archive = archives.setdefault(archive_path, zipfile.ZipFile(archive_path))
            data = archive.read(row["entry_path"])
            suffix = Path(row["entry_path"]).suffix.lower() or ".img"
            safe_id = row["sample_id"].replace(":", "_").replace("/", "_")
            derived_path = output_dir / row["label"] / f"{safe_id}{suffix}"
            derived_path.write_bytes(data)
            manifest_rows.append(
                {
                    "sample_id": row["sample_id"],
                    "label": row["label"],
                    "generator": row["generator"],
                    "variant": row["variant"],
                    "source_archive": archive_path,
                    "source_entry": row["entry_path"],
                    "derived_path": str(derived_path),
                    "sha256": hashlib.sha256(data).hexdigest().upper(),
                }
            )
    finally:
        for archive in archives.values():
            archive.close()

    manifest_path = output_dir / "manifest.csv"
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(manifest_rows[0]))
        writer.writeheader()
        writer.writerows(manifest_rows)

    summary = {
        "source_predictions": str(predictions_csv),
        "source_predictions_sha256": hashlib.sha256(predictions_csv.read_bytes()).hexdigest().upper(),
        "variant": variant.lower(),
        "seed": seed,
        "selected": {"real": real_count, "fake": fake_count},
        "fake_by_generator": allocation,
        "manifest": str(manifest_path),
    }
    with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, ensure_ascii=False)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--variant", default="facebook")
    parser.add_argument("--real-count", type=int, default=500)
    parser.add_argument("--fake-count", type=int, default=500)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    summary = extract_balanced_subset(
        args.predictions_csv,
        args.output_dir,
        variant=args.variant,
        real_count=args.real_count,
        fake_count=args.fake_count,
        seed=args.seed,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
