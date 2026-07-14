"""Deterministic local perturbation derivation for propagation-robustness experiments.

Builds paired derived archives (JPEG re-encode, down-up resize, screenshot
simulation) from a source ZIP, plus a wide-format manifest compatible with
``evaluate.expand_pair_manifest``. No randomness is used anywhere so derived
archives are byte-reproducible.
"""

import argparse
import csv
import json
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from PIL import Image

from experiments.socialmedia.evaluate import list_image_entries, sha256_file

# Fixed archive timestamp keeps derived ZIPs byte-reproducible across runs.
_FIXED_ZIP_DATE = (1980, 1, 1, 0, 0, 0)


def _jpeg_bytes(image, quality):
    buffer = BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=quality)
    return buffer.getvalue(), ".jpg"


def _png_bytes(image):
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue(), ".png"


def perturb_jpeg75(image):
    """Single JPEG re-encode at quality 75 (moderate platform compression)."""
    return _jpeg_bytes(image, 75)


def perturb_jpeg50(image):
    """Single JPEG re-encode at quality 50 (aggressive platform compression)."""
    return _jpeg_bytes(image, 50)


def perturb_resize50(image):
    """Bilinear 0.5x downscale then restore to the original size, saved as PNG."""
    width, height = image.size
    small = image.resize((max(1, width // 2), max(1, height // 2)), Image.BILINEAR)
    restored = small.resize((width, height), Image.BILINEAR)
    return _png_bytes(restored)


def perturb_screenshot(image):
    """Screenshot simulation: 0.8x bilinear rescale kept at the new size + JPEG 90."""
    width, height = image.size
    scaled = image.resize(
        (max(1, int(width * 0.8)), max(1, int(height * 0.8))), Image.BILINEAR
    )
    return _jpeg_bytes(scaled, 90)


PERTURBATIONS = {
    "jpeg75": perturb_jpeg75,
    "jpeg50": perturb_jpeg50,
    "resize50": perturb_resize50,
    "screenshot": perturb_screenshot,
}


def infer_generator(entry_name, part_index=1):
    """Infer the generator name from a directory component of the entry path."""
    parts = Path(entry_name).parts
    if len(parts) > part_index + 1 and parts[part_index]:
        return parts[part_index]
    return "unknown"


def select_entries(entries, limit=None, per_generator_limit=None, generator_part=1):
    """Deterministically select entries sorted by name with optional caps."""
    if limit is not None and limit <= 0:
        raise ValueError("limit must be positive")
    if per_generator_limit is not None and per_generator_limit <= 0:
        raise ValueError("per_generator_limit must be positive")
    selected = []
    per_generator = {}
    for entry in sorted(entries, key=lambda item: item.name.casefold()):
        generator = infer_generator(entry.name, generator_part)
        if (
            per_generator_limit is not None
            and per_generator.get(generator, 0) >= per_generator_limit
        ):
            continue
        selected.append((entry, generator))
        per_generator[generator] = per_generator.get(generator, 0) + 1
        if limit is not None and len(selected) >= limit:
            break
    return selected


def build_derived_archives(
    source_zip,
    output_dir,
    conditions,
    dataset_name,
    label="fake",
    limit=None,
    per_generator_limit=None,
    generator_part=1,
):
    """Derive one ZIP per condition plus a paired manifest and summary JSON."""
    source_zip = Path(source_zip).resolve()
    output_dir = Path(output_dir).resolve()
    conditions = list(conditions)
    unknown = [name for name in conditions if name not in PERTURBATIONS]
    if unknown:
        raise ValueError(f"unknown conditions: {unknown}")
    if not conditions:
        raise ValueError("at least one condition is required")
    if label not in {"real", "fake"}:
        raise ValueError(f"invalid label: {label}")

    selected = select_entries(
        list_image_entries(source_zip),
        limit=limit,
        per_generator_limit=per_generator_limit,
        generator_part=generator_part,
    )
    if not selected:
        raise ValueError(f"no image entries selected from {source_zip}")

    output_dir.mkdir(parents=True, exist_ok=True)
    derived_paths = {name: output_dir / f"derived_{name}.zip" for name in conditions}
    manifest_rows = []
    seen_sample_ids = set()
    with ZipFile(source_zip) as source:
        writers = {
            name: ZipFile(path, "w", ZIP_DEFLATED)
            for name, path in derived_paths.items()
        }
        try:
            for entry, generator in selected:
                sample_id = f"{dataset_name}:{generator.casefold()}:{entry.stem}"
                if sample_id in seen_sample_ids:
                    raise ValueError(f"duplicate sample_id: {sample_id}")
                seen_sample_ids.add(sample_id)
                image = Image.open(BytesIO(source.read(entry.name))).convert("RGB")
                row = {
                    "sample_id": sample_id,
                    "dataset": dataset_name,
                    "generator": generator,
                    "label": label,
                    "pair_status": "complete",
                    "original_archive": str(source_zip),
                    "original_entry": entry.name,
                }
                for condition in conditions:
                    payload, suffix = PERTURBATIONS[condition](image)
                    derived_name = str(Path(entry.name).with_suffix(suffix).as_posix())
                    info = ZipInfo(derived_name, date_time=_FIXED_ZIP_DATE)
                    writers[condition].writestr(info, payload)
                    row[f"{condition}_archive"] = str(derived_paths[condition])
                    row[f"{condition}_entry"] = derived_name
                manifest_rows.append(row)
        finally:
            for writer in writers.values():
                writer.close()

    manifest_path = output_dir / "derived_manifest.csv"
    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(manifest_rows[0]))
        writer.writeheader()
        writer.writerows(manifest_rows)

    summary = {
        "source_zip": str(source_zip),
        "source_sha256": sha256_file(source_zip),
        "dataset": dataset_name,
        "label": label,
        "conditions": conditions,
        "variants": ["original", *conditions],
        "sample_count": len(manifest_rows),
        "generators": sorted(
            {row["generator"] for row in manifest_rows}, key=str.casefold
        ),
        "manifest": str(manifest_path),
        "derived_archives": {
            name: {"path": str(path), "sha256": sha256_file(path)}
            for name, path in derived_paths.items()
        },
    }
    with (output_dir / "derived_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
    return summary


def _build_parser():
    parser = argparse.ArgumentParser(
        description="Derive deterministic perturbation archives from a source ZIP"
    )
    parser.add_argument("--source-zip", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--dataset-name", required=True)
    parser.add_argument(
        "--conditions",
        default="jpeg75,jpeg50,resize50,screenshot",
        help="comma-separated subset of: " + ",".join(PERTURBATIONS),
    )
    parser.add_argument("--label", default="fake", choices=("real", "fake"))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--per-generator-limit", type=int, default=None)
    parser.add_argument(
        "--generator-part",
        type=int,
        default=1,
        help="0-based path component used as the generator name",
    )
    return parser


def main(argv=None):
    args = _build_parser().parse_args(argv)
    conditions = [name.strip() for name in args.conditions.split(",") if name.strip()]
    summary = build_derived_archives(
        source_zip=args.source_zip,
        output_dir=args.output_dir,
        conditions=conditions,
        dataset_name=args.dataset_name,
        label=args.label,
        limit=args.limit,
        per_generator_limit=args.per_generator_limit,
        generator_part=args.generator_part,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
