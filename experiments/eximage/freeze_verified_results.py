"""Freeze the public-ExImage zero-shot run into experiments/eximage/verified_results/.

Copies the report-level summaries into the tracked evidence directory and writes
``provenance.json`` per AGENTS.md §12.1. Every SHA-256 is computed here -- never
transcribed by hand.

Only Fake Recall style metrics are carried over: the public ExImage release has
no real images, so Accuracy / Macro F1 / ROC AUC / false-positive rate are not
computable and are deliberately absent.
"""

import argparse
import csv
import hashlib
import json
import shutil
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CHECKPOINT_SHA256 = "29F85CAFFA5FCE11C7F31A2FB29C4DC44F65782D5300064BC4F73ADB153B0474"
PUBLIC_SOURCE = {
    "archive": "dataset/eximage/ExImage.zip",
    "origin": "ExDA project README public Google Drive link (no login required)",
    "google_drive_file_id": "1s2JYbZyMe-SzWjkja9tlZFrzIJiFhwI-",
}

# Measured by a path-string scan of every entry in every nested ZIP; no image was
# decoded. Recorded here so the release's shape is auditable from provenance alone.
PUBLIC_RELEASE_SURVEY = {
    "method": "path-string scan of all entries in all nested ZIPs (no decoding)",
    "entries_total": 35605,
    "split_dirs": {"train": 28800, "test": 6805},
    "test_by_generator": {
        "BigGAN": 800, "CycleGAN": 800, "DALLE": 800, "Flux": 800, "Glide": 800,
        "LatentDM": 405, "Midjourney": 800, "SD14": 800, "SD15": 800,
    },
    "real_keyword_hits": 0,
    "real_images": 0,
    "byte_duplicates_in_release": {
        "method": "match on (crc32, uncompressed_size) from ZIP central directories",
        "distinct_entries": 35530,
        "duplicate_entries": 75,
        "by_generator": {"CycleGAN": 27, "Midjourney": 36, "SD14": 12},
        "note": (
            "Explains why deduplicated per-generator totals read 3973/3964/3988 "
            "instead of 4000; the built subset itself contains no duplicate crc32."
        ),
    },
}

# Independent check of the prior run's provenance, same (crc32, size) method.
PRIOR_RUN_SOURCE_AUDIT = {
    "method": "match on (crc32, uncompressed_size) from ZIP central directories",
    "old_subset_fake_total": 2250,
    "js_total": 1152,
    "js_found_in_public_release": 1152,
    "db_total": 1098,
    "db_found_in_public_release": 0,
}


def sha256_file(path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(16 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _read_csv(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _write_subset_counts_csv(subset_counts: dict, target: Path) -> None:
    rows = [
        {
            "generator": generator,
            "test_available": info["test_available"],
            "selected": info["selected"],
            "short_of_target": info["short"],
        }
        for generator, info in sorted(subset_counts["counts_by_generator"].items())
    ]
    rows.append(
        {
            "generator": "ALL",
            "test_available": sum(r["test_available"] for r in rows),
            "selected": sum(r["selected"] for r in rows),
            "short_of_target": any(r["short_of_target"] for r in rows),
        }
    )
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["generator", "test_available", "selected", "short_of_target"]
        )
        writer.writeheader()
        writer.writerows(rows)


def freeze(run_dir, subset_dir, derived_dir, verified_dir) -> dict:
    run_dir = Path(run_dir).resolve()
    subset_dir = Path(subset_dir).resolve()
    derived_dir = Path(derived_dir).resolve()
    verified_dir = Path(verified_dir).resolve()
    verified_dir.mkdir(parents=True, exist_ok=True)

    raw_path = run_dir / "raw_predictions.csv"
    metadata = json.loads((run_dir / "run_metadata.json").read_text(encoding="utf-8"))
    subset_counts = json.loads((subset_dir / "subset_counts.json").read_text(encoding="utf-8"))
    derived_summary = json.loads((derived_dir / "derived_summary.json").read_text(encoding="utf-8"))

    shutil.copyfile(run_dir / "summary_all.csv", verified_dir / "zeroshot_summary_all.csv")
    shutil.copyfile(
        run_dir / "summary_by_generator.csv", verified_dir / "zeroshot_summary_by_generator.csv"
    )
    _write_subset_counts_csv(subset_counts, verified_dir / "subset_counts.csv")

    raw_rows = _read_csv(raw_path)
    failures = [row for row in raw_rows if row.get("status") != "ok"]
    probs_ok = all(
        0.0 <= float(row["fake_prob"]) <= 1.0 and 0.0 <= float(row["real_prob"]) <= 1.0
        for row in raw_rows
        if row.get("status") == "ok"
    )
    labels = {row["label"] for row in raw_rows}
    checkpoint_hashes = {row["checkpoint_sha256"] for row in raw_rows if row.get("checkpoint_sha256")}

    provenance = {
        "frozen_at": date.today().isoformat(),
        "experiment": (
            "Zero-shot fake recall + deterministic propagation retention on a "
            "self-constructed subset of the PUBLIC ExImage release"
        ),
        "runtime": {
            "python": metadata.get("python"),
            "platform": metadata.get("platform"),
            "torch": metadata.get("torch"),
            "cuda_available": metadata.get("cuda_available"),
            "cuda_device": metadata.get("cuda_device"),
            "device": "cuda" if metadata.get("cuda_available") else "cpu",
            "command": metadata.get("command"),
        },
        "checkpoint": {
            "path": "best.pth",
            "sha256": CHECKPOINT_SHA256,
            "sha256_recomputed": metadata.get("checkpoint_sha256"),
        },
        "public_source": {
            **PUBLIC_SOURCE,
            "size_bytes": subset_counts["source_zip"]["size_bytes"],
            "sha256": None,  # filled by --eximage-sha256
            "release_survey": PUBLIC_RELEASE_SURVEY,
        },
        "subset": {
            "builder": "experiments/eximage/build_public_subset.py",
            "seed": subset_counts["seed"],
            "sampling": subset_counts["sampling"],
            "per_generator_target": subset_counts["per_generator_target"],
            "selected_total": subset_counts["selected_total"],
            "counts_by_generator": subset_counts["counts_by_generator"],
            "fake_subset_zip": {
                "path": "dataset/eximage_public_subset/fake_subset.zip",
                "sha256": sha256_file(subset_dir / "fake_subset.zip"),
            },
            "manifest": {
                "path": "dataset/eximage_public_subset/manifest.csv",
                "sha256": sha256_file(subset_dir / "manifest.csv"),
            },
            "real_images": 0,
            "real_note": (
                "The public ExImage release contains no real images; this experiment "
                "reports Fake Recall only."
            ),
        },
        "derived_archives": {
            name: {
                "path": f"dataset/eximage_public_subset/derived_fake/derived_{name}.zip",
                "sha256": sha256_file(derived_dir / f"derived_{name}.zip"),
            }
            for name in sorted(derived_summary["derived_archives"])
        },
        "derived_manifest": {
            "path": "dataset/eximage_public_subset/derived_fake/derived_manifest.csv",
            "sha256": sha256_file(derived_dir / "derived_manifest.csv"),
        },
        "raw_predictions": {
            "path": "output/eximage_zeroshot_public/fake/raw_predictions.csv",
            "sha256": sha256_file(raw_path),
            "rows": len(raw_rows),
            "failures": len(failures),
        },
        "frozen_summaries": {
            name: sha256_file(verified_dir / name)
            for name in (
                "zeroshot_summary_all.csv",
                "zeroshot_summary_by_generator.csv",
                "subset_counts.csv",
            )
        },
        "cross_checks": {
            "all_rows_ok": not failures,
            "probabilities_in_range": probs_ok,
            "labels_are_fake_only": labels == {"fake"},
            "single_checkpoint_hash": len(checkpoint_hashes) == 1,
            "checkpoint_hash_matches_expected": checkpoint_hashes == {CHECKPOINT_SHA256},
            "rows_equal_samples_times_variants": len(raw_rows)
            == subset_counts["selected_total"] * len(derived_summary["variants"]),
        },
        "metrics_not_computable": [
            "accuracy",
            "macro_f1",
            "roc_auc",
            "real_false_positive_rate",
        ],
        "gaps": [
            "The public ExImage release ships no official split (dataset_paths.py is "
            "not distributed); the subset here is self-constructed and is not the "
            "split used by the original paper.",
            "The public release contains no real images, so no false-positive rate "
            "can be measured on this data.",
            "Perturbations are local deterministic simulations, not real platform "
            "transmission; they do not replace the socialmedia platform experiments.",
        ],
        "relation_to_prior_run": {
            "prior_output": "output/eximage_zeroshot/",
            "prior_overall_fake_recall": 0.9884,
            "prior_real_false_positive_rate": 0.014,
            "prior_source": (
                "Mixed set: 1152 'js' fake images are byte-identical to entries in the "
                "public ExImage release, 1098 'db' fake images are absent from it; the "
                "500 real images are not from the public release either."
            ),
            "prior_source_audit": PRIOR_RUN_SOURCE_AUDIT,
            "comparable": False,
            "note": (
                "Different sample set and different provenance. The two numbers must "
                "not be mixed, substituted for one another, or presented as versions "
                "of the same experiment."
            ),
        },
    }
    return provenance


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", default="output/eximage_zeroshot_public/fake")
    parser.add_argument("--subset-dir", default="dataset/eximage_public_subset")
    parser.add_argument("--derived-dir", default="dataset/eximage_public_subset/derived_fake")
    parser.add_argument("--verified-dir", default="experiments/eximage/verified_results")
    parser.add_argument(
        "--eximage-sha256",
        default=None,
        help="precomputed SHA-256 of the 12GB public ExImage.zip (computed if omitted)",
    )
    parser.add_argument("--source-zip", default="dataset/eximage/ExImage.zip")
    args = parser.parse_args(argv)

    provenance = freeze(args.run_dir, args.subset_dir, args.derived_dir, args.verified_dir)
    provenance["public_source"]["sha256"] = args.eximage_sha256 or sha256_file(args.source_zip)

    target = Path(args.verified_dir).resolve() / "provenance.json"
    with target.open("w", encoding="utf-8") as handle:
        json.dump(provenance, handle, ensure_ascii=False, indent=2)
    print(json.dumps(provenance, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
