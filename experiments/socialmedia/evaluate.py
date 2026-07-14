"""Reproducible social-media robustness evaluation utilities."""

import argparse
from dataclasses import dataclass
import csv
from collections import defaultdict
import hashlib
from io import BytesIO
import json
import math
import os
from pathlib import Path
import platform as platform_module
import re
import sys
import time
from typing import Dict, Iterable, List, Mapping, Sequence
from zipfile import ZipFile

from PIL import Image


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
REQUIRED_PLATFORMS = ("facebook", "wechat", "weibo")


@dataclass(frozen=True)
class ArchiveImage:
    archive_path: Path
    name: str
    size: int

    @property
    def stem(self) -> str:
        return Path(self.name).stem


@dataclass(frozen=True)
class PairRecord:
    sample_id: str
    generator: str
    entries: Mapping[str, ArchiveImage]
    pair_status: str = "complete"


@dataclass(frozen=True)
class PredictionInput:
    sample_id: str
    dataset: str
    generator: str
    label: str
    variant: str
    archive_path: Path
    entry_path: str


PREDICTION_FIELDS = [
    "sample_id", "dataset", "generator", "label", "variant",
    "archive_path", "entry_path", "predicted_label", "real_prob",
    "fake_prob", "checkpoint_sha256", "elapsed_ms", "status", "error",
]


def list_image_entries(zip_path) -> List[ArchiveImage]:
    """List canonical image entries while excluding notebook checkpoints."""
    archive_path = Path(zip_path).resolve()
    with ZipFile(archive_path) as archive:
        return [
            ArchiveImage(archive_path, info.filename, info.file_size)
            for info in archive.infolist()
            if Path(info.filename).suffix.lower() in SUPPORTED_EXTENSIONS
            and ".ipynb_checkpoints" not in info.filename.lower().split("/")
        ]


def _unique_stem_map(entries: Iterable[ArchiveImage], source: str) -> Dict[str, ArchiveImage]:
    result = {}
    for entry in entries:
        key = entry.stem.casefold()
        if key in result:
            raise ValueError(f"duplicate sample stem in {source}: {entry.stem}")
        result[key] = entry
    return result


def _platform_generator(entry: ArchiveImage) -> str:
    parts = entry.name.split("/")
    if len(parts) < 3 or not parts[1]:
        raise ValueError(f"cannot determine generator from entry: {entry.name}")
    return parts[1]


def build_genimage_pairs(original_zip, platform_zips) -> List[PairRecord]:
    """Build strict Original/Facebook/WeChat/Weibo GenImage pairs."""
    normalized = {str(name).casefold(): Path(path) for name, path in platform_zips.items()}
    if set(normalized) != set(REQUIRED_PLATFORMS):
        raise ValueError("platform_zips must contain facebook, wechat, and weibo")

    original_map = _unique_stem_map(list_image_entries(original_zip), "original")
    platform_maps = {
        platform: _unique_stem_map(list_image_entries(path), platform)
        for platform, path in normalized.items()
    }

    original_keys = set(original_map)
    for platform, entries in platform_maps.items():
        missing = original_keys - set(entries)
        extra = set(entries) - original_keys
        if missing or extra:
            raise ValueError(
                f"missing variants or unmatched samples for {platform}: "
                f"missing={len(missing)}, extra={len(extra)}"
            )

    pairs = []
    for stem_key, original in original_map.items():
        platform_entries = {
            platform: platform_maps[platform][stem_key]
            for platform in REQUIRED_PLATFORMS
        }
        generators = {_platform_generator(entry) for entry in platform_entries.values()}
        if len(generators) != 1:
            raise ValueError(f"generator mismatch for sample: {original.stem}")
        generator = generators.pop()
        entries = {"original": original, **platform_entries}
        pairs.append(PairRecord(
            sample_id=f"genimage:{generator.casefold()}:{original.stem}",
            generator=generator,
            entries=entries,
        ))

    return sorted(pairs, key=lambda pair: (pair.generator.casefold(), pair.sample_id))


def parse_eachfake_label(filename: str) -> str:
    """Parse the validated `_0_real` / `_1_fake` filename suffix."""
    match = re.search(r"_([01])_(real|fake)\.[^.]+$", Path(filename).name, re.IGNORECASE)
    if not match:
        raise ValueError(f"cannot determine label from filename: {filename}")
    numeric, label = match.groups()
    label = label.casefold()
    if (numeric, label) not in {("0", "real"), ("1", "fake")}:
        raise ValueError(f"inconsistent label encoding in filename: {filename}")
    return label


def build_platform_records(platform, archive_path) -> List[PredictionInput]:
    """Build labeled prediction inputs for a platform classification archive."""
    platform = str(platform).casefold()
    if platform not in REQUIRED_PLATFORMS:
        raise ValueError(f"unsupported platform: {platform}")
    archive_path = Path(archive_path).resolve()
    records = []
    sample_ids = set()
    for entry in list_image_entries(archive_path):
        label = parse_eachfake_label(entry.name)
        stem = entry.stem
        sample_id = f"eachfake:{stem}"
        if sample_id.casefold() in sample_ids:
            raise ValueError(f"duplicate sample_id in platform archive: {sample_id}")
        sample_ids.add(sample_id.casefold())
        parts = stem.split("_")
        if len(parts) < 2:
            raise ValueError(f"cannot determine generator from filename: {entry.name}")
        generator = "Real" if label == "real" else parts[1]
        records.append(PredictionInput(
            sample_id=sample_id,
            dataset="test_eachfake_500_real500",
            generator=generator,
            label=label,
            variant=platform,
            archive_path=archive_path,
            entry_path=entry.name,
        ))
    return sorted(records, key=lambda record: (record.label, record.generator.casefold(), record.sample_id))


def _class_f1(labels: Sequence[str], predictions: Sequence[str], target: str) -> float:
    true_positive = sum(
        label == target and prediction == target
        for label, prediction in zip(labels, predictions)
    )
    false_positive = sum(
        label != target and prediction == target
        for label, prediction in zip(labels, predictions)
    )
    false_negative = sum(
        label == target and prediction != target
        for label, prediction in zip(labels, predictions)
    )
    denominator = 2 * true_positive + false_positive + false_negative
    return 0.0 if denominator == 0 else 2 * true_positive / denominator


def _roc_auc(labels: Sequence[str], probabilities: Sequence[float]) -> float:
    ranked = sorted(zip(probabilities, labels), key=lambda item: item[0])
    positive_rank_sum = 0.0
    rank = 1
    index = 0
    while index < len(ranked):
        end = index + 1
        while end < len(ranked) and ranked[end][0] == ranked[index][0]:
            end += 1
        average_rank = (rank + (rank + end - index - 1)) / 2
        positive_rank_sum += average_rank * sum(
            label == "fake" for _, label in ranked[index:end]
        )
        rank += end - index
        index = end

    positive_count = sum(label == "fake" for label in labels)
    negative_count = len(labels) - positive_count
    return (
        positive_rank_sum - positive_count * (positive_count + 1) / 2
    ) / (positive_count * negative_count)


def binary_metrics(labels, probabilities, threshold=0.5):
    """Compute binary metrics using fake as the positive class."""
    labels = list(labels)
    probabilities = [float(value) for value in probabilities]
    if len(labels) != len(probabilities) or not labels:
        raise ValueError("labels and probabilities must have the same non-zero length")
    if any(label not in {"real", "fake"} for label in labels):
        raise ValueError("labels must be real or fake")
    if any(not math.isfinite(value) or not 0.0 <= value <= 1.0 for value in probabilities):
        raise ValueError("probabilities must be finite values in [0, 1]")

    real_count = sum(label == "real" for label in labels)
    fake_count = len(labels) - real_count
    if real_count == 0 or fake_count == 0:
        raise ValueError("ROC AUC requires both real and fake labels")

    predictions = ["fake" if probability > threshold else "real" for probability in probabilities]
    correct = sum(label == prediction for label, prediction in zip(labels, predictions))
    real_recall = sum(
        label == prediction == "real" for label, prediction in zip(labels, predictions)
    ) / real_count
    fake_recall = sum(
        label == prediction == "fake" for label, prediction in zip(labels, predictions)
    ) / fake_count

    return {
        "count": len(labels),
        "real_count": real_count,
        "fake_count": fake_count,
        "accuracy": correct / len(labels),
        "macro_f1": (
            _class_f1(labels, predictions, "real")
            + _class_f1(labels, predictions, "fake")
        ) / 2,
        "roc_auc": _roc_auc(labels, probabilities),
        "real_recall": real_recall,
        "fake_recall": fake_recall,
    }


def expand_pair_manifest(
    manifest_path,
    project_root=None,
    variants=("original", "facebook", "wechat", "weibo"),
) -> List[PredictionInput]:
    """Expand one paired-manifest row into one prediction record per variant."""
    manifest_path = Path(manifest_path).resolve()
    root = Path(project_root).resolve() if project_root else manifest_path.parents[3]
    records = []
    sample_ids = set()
    with manifest_path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            sample_id = row["sample_id"]
            if sample_id in sample_ids:
                raise ValueError(f"duplicate sample_id in manifest: {sample_id}")
            sample_ids.add(sample_id)
            if row.get("pair_status") != "complete":
                raise ValueError(f"incomplete pair in manifest: {sample_id}")
            for variant in variants:
                archive_value = row[f"{variant}_archive"]
                archive_path = Path(archive_value)
                if not archive_path.is_absolute():
                    archive_path = root / archive_path
                records.append(PredictionInput(
                    sample_id=sample_id,
                    dataset=row["dataset"],
                    generator=row["generator"],
                    label=row["label"],
                    variant=variant,
                    archive_path=archive_path.resolve(),
                    entry_path=row[f"{variant}_entry"],
                ))
    return records


def _read_success_keys(output_path: Path):
    if not output_path.exists():
        return set()
    with output_path.open(newline="", encoding="utf-8-sig") as handle:
        return {
            (row["sample_id"], row["variant"])
            for row in csv.DictReader(handle)
            if row.get("status") == "ok"
        }


def _failure_path(output_path: Path) -> Path:
    return output_path.with_name(f"{output_path.stem}_failures{output_path.suffix}")


def run_prediction_records(
    records,
    detector,
    output_path,
    checkpoint_sha256,
    batch_size=32,
):
    """Run resumable ZIP-backed inference and append only successful rows."""
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    success_keys = _read_success_keys(output_path)
    pending = [record for record in records if (record.sample_id, record.variant) not in success_keys]
    skipped = len(records) - len(pending)
    grouped = defaultdict(list)
    for record in pending:
        grouped[record.archive_path].append(record)

    completed = 0
    failure_rows = []
    needs_header = not output_path.exists() or output_path.stat().st_size == 0
    with output_path.open("a", newline="", encoding="utf-8") as output_handle:
        writer = csv.DictWriter(output_handle, fieldnames=PREDICTION_FIELDS)
        if needs_header:
            writer.writeheader()

        for archive_path, archive_records in grouped.items():
            with ZipFile(archive_path) as archive:
                for start in range(0, len(archive_records), batch_size):
                    batch_records = archive_records[start:start + batch_size]
                    valid_records = []
                    images = []
                    for record in batch_records:
                        try:
                            with archive.open(record.entry_path) as entry_handle:
                                image = Image.open(BytesIO(entry_handle.read())).convert("RGB")
                                images.append(image.copy())
                            valid_records.append(record)
                        except Exception as exc:
                            failure_rows.append(_prediction_row(
                                record, checkpoint_sha256, status="error", error=str(exc)
                            ))

                    if not valid_records:
                        continue
                    started = time.perf_counter()
                    try:
                        predictions = detector.predict_batch(images, batch_size=batch_size)
                        if len(predictions) != len(valid_records):
                            raise ValueError("detector returned an unexpected number of predictions")
                        elapsed_ms = (time.perf_counter() - started) * 1000 / len(valid_records)
                        for record, prediction in zip(valid_records, predictions):
                            fake_prob = float(prediction["fake_prob"])
                            real_prob = float(prediction["real_prob"])
                            if (
                                not math.isfinite(fake_prob)
                                or not math.isfinite(real_prob)
                                or not 0.0 <= fake_prob <= 1.0
                                or not 0.0 <= real_prob <= 1.0
                            ):
                                raise ValueError("detector returned an invalid probability")
                            row = _prediction_row(
                                record,
                                checkpoint_sha256,
                                predicted_label=prediction["label"],
                                real_prob=real_prob,
                                fake_prob=fake_prob,
                                elapsed_ms=elapsed_ms,
                                status="ok",
                            )
                            writer.writerow(row)
                            completed += 1
                        output_handle.flush()
                    except Exception as exc:
                        failure_rows.extend(
                            _prediction_row(
                                record, checkpoint_sha256, status="error", error=str(exc)
                            )
                            for record in valid_records
                        )

    failure_path = _failure_path(output_path)
    with failure_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=PREDICTION_FIELDS)
        writer.writeheader()
        writer.writerows(failure_rows)
    return {"completed": completed, "failed": len(failure_rows), "skipped": skipped}


def _prediction_row(
    record,
    checkpoint_sha256,
    predicted_label="",
    real_prob="",
    fake_prob="",
    elapsed_ms="",
    status="error",
    error="",
):
    return {
        "sample_id": record.sample_id,
        "dataset": record.dataset,
        "generator": record.generator,
        "label": record.label,
        "variant": record.variant,
        "archive_path": str(record.archive_path),
        "entry_path": record.entry_path,
        "predicted_label": predicted_label,
        "real_prob": real_prob,
        "fake_prob": fake_prob,
        "checkpoint_sha256": checkpoint_sha256,
        "elapsed_ms": elapsed_ms,
        "status": status,
        "error": error,
    }


def summarize_paired_predictions(
    rows,
    variants=("original", "facebook", "wechat", "weibo"),
):
    """Summarize fake-only paired predictions by variant and generator."""
    if not variants or variants[0] != "original":
        raise ValueError("variants must start with original")
    valid = [row for row in rows if row.get("status") == "ok"]
    generators = sorted({row["generator"] for row in valid}, key=str.casefold)
    summaries = []
    for scope in ["all", *generators]:
        scoped = valid if scope == "all" else [row for row in valid if row["generator"] == scope]
        by_variant = defaultdict(dict)
        for row in scoped:
            by_variant[row["variant"]][row["sample_id"]] = row
        originals = by_variant.get("original", {})
        if not originals:
            continue
        original_recall = sum(
            row["predicted_label"] == "fake" for row in originals.values()
        ) / len(originals)

        for variant in variants:
            variant_rows = by_variant.get(variant, {})
            common_ids = sorted(set(originals) & set(variant_rows))
            if not common_ids:
                continue
            fake_recall = sum(
                variant_rows[sample_id]["predicted_label"] == "fake"
                for sample_id in common_ids
            ) / len(common_ids)
            mean_fake_prob = sum(
                float(variant_rows[sample_id]["fake_prob"])
                for sample_id in common_ids
            ) / len(common_ids)
            mean_delta = sum(
                float(variant_rows[sample_id]["fake_prob"])
                - float(originals[sample_id]["fake_prob"])
                for sample_id in common_ids
            ) / len(common_ids)
            summaries.append({
                "scope": scope,
                "variant": variant,
                "sample_count": len(common_ids),
                "fake_recall": fake_recall,
                "mean_fake_prob": mean_fake_prob,
                "mean_probability_delta": mean_delta,
                "recall_retention": (
                    fake_recall / original_recall if original_recall > 0 else None
                ),
            })
    return summaries


def summarize_classification_predictions(rows):
    """Summarize full real/fake classification metrics for each platform."""
    valid = [row for row in rows if row.get("status") == "ok"]
    by_platform = defaultdict(list)
    for row in valid:
        by_platform[row["variant"]].append(row)

    summaries = []
    for platform in sorted(by_platform):
        platform_rows = by_platform[platform]
        metrics = binary_metrics(
            labels=[row["label"] for row in platform_rows],
            probabilities=[float(row["fake_prob"]) for row in platform_rows],
        )
        summaries.append({"platform": platform, **metrics})
    return summaries


def validate_prediction_records(records):
    """Validate unique keys and confirm every referenced ZIP entry exists."""
    records = list(records)
    keys = [(record.sample_id, record.variant) for record in records]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate (sample_id, variant) prediction key")
    by_archive = defaultdict(list)
    for record in records:
        if record.label not in {"real", "fake"}:
            raise ValueError(f"invalid label: {record.label}")
        by_archive[record.archive_path].append(record)
    for archive_path, archive_records in by_archive.items():
        if not archive_path.is_file():
            raise FileNotFoundError(f"archive not found: {archive_path}")
        with ZipFile(archive_path) as archive:
            names = set(archive.namelist())
        missing = [record.entry_path for record in archive_records if record.entry_path not in names]
        if missing:
            raise ValueError(f"archive entries missing from {archive_path}: {missing[:3]}")
    return {
        "sample_count": len({record.sample_id for record in records}),
        "prediction_record_count": len(records),
        "archive_count": len(by_archive),
        "variant_count": len({record.variant for record in records}),
        "generator_count": len({record.generator for record in records}),
    }


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _read_csv_rows(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    if not rows:
        raise ValueError(f"cannot write empty CSV: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _runtime_metadata(mode, records, checkpoint_path, checkpoint_hash, command):
    import torch

    archives = sorted({record.archive_path for record in records}, key=str)
    return {
        "mode": mode,
        "status": "running",
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "command": command,
        "python": sys.version,
        "platform": platform_module.platform(),
        "torch": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_sha256": checkpoint_hash,
        "record_count": len(records),
        "sample_count": len({record.sample_id for record in records}),
        "archives": [
            {"path": str(path), "sha256": sha256_file(path), "bytes": path.stat().st_size}
            for path in archives
        ],
    }


def _write_metadata(output_dir, metadata):
    with (Path(output_dir) / "run_metadata.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, ensure_ascii=False, indent=2)


def _add_inference_arguments(parser):
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--device", default="cuda", choices=("cuda", "cpu"))
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--output", required=True)
    parser.add_argument("--limit", type=int, default=None)


def _build_parser():
    parser = argparse.ArgumentParser(description="TraceGuard social-media robustness evaluation")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate the paired manifest")
    validate.add_argument("--manifest", required=True)
    validate.add_argument("--project-root", default=None)

    paired = subparsers.add_parser("paired-genimage", help="run paired GenImage inference")
    paired.add_argument("--manifest", required=True)
    paired.add_argument("--project-root", default=None)
    _add_inference_arguments(paired)

    derived = subparsers.add_parser(
        "paired-derived", help="run paired inference over locally derived perturbations"
    )
    derived.add_argument("--manifest", required=True)
    derived.add_argument("--project-root", default=None)
    derived.add_argument(
        "--variants",
        required=True,
        help="comma-separated variant list starting with original",
    )
    _add_inference_arguments(derived)

    benchmark = subparsers.add_parser(
        "platform-benchmark", help="run labeled platform classification benchmarks"
    )
    benchmark.add_argument(
        "--archive",
        action="append",
        required=True,
        metavar="PLATFORM=PATH",
        help="repeat for facebook, wechat, and weibo",
    )
    _add_inference_arguments(benchmark)
    return parser


def _limit_paired_records(records, limit):
    if limit is None:
        return records
    if limit <= 0:
        raise ValueError("limit must be positive")
    sample_ids = []
    for record in records:
        if record.sample_id not in sample_ids:
            sample_ids.append(record.sample_id)
        if len(sample_ids) == limit:
            break
    selected = set(sample_ids)
    return [record for record in records if record.sample_id in selected]


def _parse_archive_arguments(values):
    archives = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"archive must use PLATFORM=PATH: {value}")
        platform, path = value.split("=", 1)
        platform = platform.casefold()
        if platform in archives:
            raise ValueError(f"duplicate archive platform: {platform}")
        archives[platform] = Path(path).resolve()
    if set(archives) != set(REQUIRED_PLATFORMS):
        raise ValueError("archives must contain facebook, wechat, and weibo")
    return archives


def _run_inference(mode, records, args, variants=None):
    from detection import Detector

    records = list(records)
    validation = validate_prediction_records(records)
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = Path(args.checkpoint).resolve()
    checkpoint_hash = sha256_file(checkpoint_path)
    metadata = _runtime_metadata(
        mode,
        records,
        checkpoint_path,
        checkpoint_hash,
        " ".join(sys.argv),
    )
    metadata["validation"] = validation
    _write_metadata(output_dir, metadata)

    detector = Detector(str(checkpoint_path), device=args.device)
    raw_path = output_dir / "raw_predictions.csv"
    run_result = run_prediction_records(
        records,
        detector,
        raw_path,
        checkpoint_hash,
        batch_size=args.batch_size,
    )
    rows = _read_csv_rows(raw_path)
    if mode in ("paired-genimage", "paired-derived"):
        summary = summarize_paired_predictions(
            rows, variants=variants or ("original", "facebook", "wechat", "weibo")
        )
        _write_csv(output_dir / "summary_all.csv", [row for row in summary if row["scope"] == "all"])
        _write_csv(output_dir / "summary_by_generator.csv", [row for row in summary if row["scope"] != "all"])
    else:
        _write_csv(
            output_dir / "classification_summary.csv",
            summarize_classification_predictions(rows),
        )

    complete = run_result["failed"] == 0 and run_result["completed"] + run_result["skipped"] == len(records)
    metadata.update({
        "status": "complete" if complete else "incomplete",
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "run_result": run_result,
    })
    _write_metadata(output_dir, metadata)
    print(json.dumps({"validation": validation, "run_result": run_result}, indent=2))
    return 0 if complete else 2


def main(argv=None):
    args = _build_parser().parse_args(argv)
    if args.command == "validate":
        records = expand_pair_manifest(args.manifest, project_root=args.project_root)
        print(json.dumps(validate_prediction_records(records), indent=2))
        return 0

    if args.command == "paired-genimage":
        records = expand_pair_manifest(args.manifest, project_root=args.project_root)
        records = _limit_paired_records(records, args.limit)
        return _run_inference("paired-genimage", records, args)

    if args.command == "paired-derived":
        variants = tuple(
            value.strip().casefold()
            for value in args.variants.split(",")
            if value.strip()
        )
        if not variants or variants[0] != "original" or len(set(variants)) != len(variants):
            raise ValueError("variants must be unique and start with original")
        records = expand_pair_manifest(
            args.manifest, project_root=args.project_root, variants=variants
        )
        records = _limit_paired_records(records, args.limit)
        return _run_inference("paired-derived", records, args, variants=variants)

    archives = _parse_archive_arguments(args.archive)
    records = []
    for platform, archive_path in archives.items():
        platform_records = build_platform_records(platform, archive_path)
        if args.limit is not None:
            if args.limit <= 0:
                raise ValueError("limit must be positive")
            platform_records = platform_records[:args.limit]
        records.extend(platform_records)
    return _run_inference("platform-benchmark", records, args)


if __name__ == "__main__":
    raise SystemExit(main())
