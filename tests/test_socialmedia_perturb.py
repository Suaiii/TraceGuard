"""Deterministic perturbation derivation unit tests."""

import json
from io import BytesIO
from zipfile import ZipFile

import pytest
from PIL import Image

from experiments.socialmedia.evaluate import (
    expand_pair_manifest,
    summarize_paired_predictions,
    validate_prediction_records,
)
from experiments.socialmedia.perturb import (
    build_derived_archives,
    infer_generator,
    main,
    select_entries,
)


def _gradient_png_bytes(size=(64, 48), seed=0):
    image = Image.new("RGB", size)
    pixels = image.load()
    for x in range(size[0]):
        for y in range(size[1]):
            pixels[x, y] = ((x * 4) % 256, (y * 5) % 256, (x + y + seed) % 256)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def make_source_zip(path, entries, size=(64, 48)):
    with ZipFile(path, "w") as archive:
        for index, name in enumerate(entries):
            archive.writestr(name, _gradient_png_bytes(size=size, seed=index))
    return path


SOURCE_ENTRIES = [
    "ExImage/SD14/a.png",
    "ExImage/SD14/b.png",
    "ExImage/BigGAN/c.png",
]
ALL_CONDITIONS = ["jpeg75", "jpeg50", "resize50", "screenshot"]


def test_infer_generator_uses_path_component():
    assert infer_generator("ExImage/SD14/a.png") == "SD14"
    assert infer_generator("flat.png") == "unknown"
    assert infer_generator("only_dir/a.png") == "unknown"


def test_select_entries_rejects_non_positive_caps():
    with pytest.raises(ValueError):
        select_entries([], limit=0)
    with pytest.raises(ValueError):
        select_entries([], per_generator_limit=0)


def test_build_derived_archives_end_to_end(tmp_path):
    source = make_source_zip(tmp_path / "source.zip", SOURCE_ENTRIES)
    output_dir = tmp_path / "derived"

    summary = build_derived_archives(
        source, output_dir, ALL_CONDITIONS, dataset_name="eximage"
    )

    assert summary["sample_count"] == 3
    assert summary["generators"] == ["BigGAN", "SD14"]
    assert summary["variants"] == ["original", *ALL_CONDITIONS]

    with ZipFile(output_dir / "derived_jpeg75.zip") as archive:
        names = archive.namelist()
        assert len(names) == 3
        assert all(name.endswith(".jpg") for name in names)
        image = Image.open(BytesIO(archive.read(names[0])))
        assert image.size == (64, 48)

    with ZipFile(output_dir / "derived_resize50.zip") as archive:
        image = Image.open(BytesIO(archive.read(archive.namelist()[0])))
        assert image.size == (64, 48)

    with ZipFile(output_dir / "derived_screenshot.zip") as archive:
        image = Image.open(BytesIO(archive.read(archive.namelist()[0])))
        assert image.size == (51, 38)


def test_manifest_expands_and_validates(tmp_path):
    source = make_source_zip(tmp_path / "source.zip", SOURCE_ENTRIES)
    output_dir = tmp_path / "derived"
    build_derived_archives(source, output_dir, ALL_CONDITIONS, dataset_name="eximage")
    variants = ("original", *ALL_CONDITIONS)

    records = expand_pair_manifest(
        output_dir / "derived_manifest.csv", project_root=tmp_path, variants=variants
    )

    assert len(records) == 3 * len(variants)
    validation = validate_prediction_records(records)
    assert validation["sample_count"] == 3
    assert validation["variant_count"] == len(variants)


def test_derived_archives_are_deterministic(tmp_path):
    source = make_source_zip(tmp_path / "source.zip", SOURCE_ENTRIES)
    first = tmp_path / "first"
    second = tmp_path / "second"
    build_derived_archives(source, first, ["jpeg75"], dataset_name="eximage")
    build_derived_archives(source, second, ["jpeg75"], dataset_name="eximage")

    assert (
        (first / "derived_jpeg75.zip").read_bytes()
        == (second / "derived_jpeg75.zip").read_bytes()
    )


def test_per_generator_limit_caps_selection(tmp_path):
    source = make_source_zip(tmp_path / "source.zip", SOURCE_ENTRIES)
    summary = build_derived_archives(
        source,
        tmp_path / "derived",
        ["jpeg75"],
        dataset_name="eximage",
        per_generator_limit=1,
    )
    assert summary["sample_count"] == 2


def test_unknown_condition_is_rejected(tmp_path):
    source = make_source_zip(tmp_path / "source.zip", SOURCE_ENTRIES)
    with pytest.raises(ValueError, match="unknown conditions"):
        build_derived_archives(
            source, tmp_path / "derived", ["wechat"], dataset_name="eximage"
        )


def test_duplicate_sample_id_is_rejected(tmp_path):
    source = make_source_zip(
        tmp_path / "source.zip",
        ["D1/SD14/x.png", "D2/SD14/x.png"],
    )
    with pytest.raises(ValueError, match="duplicate sample_id"):
        build_derived_archives(
            source, tmp_path / "derived", ["jpeg75"], dataset_name="eximage"
        )


def test_summarize_supports_custom_variants():
    def row(sample_id, variant, predicted, prob):
        return {
            "sample_id": sample_id,
            "generator": "SD14",
            "variant": variant,
            "predicted_label": predicted,
            "fake_prob": str(prob),
            "status": "ok",
        }

    rows = [
        row("s1", "original", "fake", 0.9),
        row("s2", "original", "fake", 0.8),
        row("s1", "jpeg75", "fake", 0.7),
        row("s2", "jpeg75", "real", 0.2),
    ]

    summary = summarize_paired_predictions(rows, variants=("original", "jpeg75"))

    scoped = {item["variant"]: item for item in summary if item["scope"] == "all"}
    assert scoped["original"]["fake_recall"] == 1.0
    assert scoped["jpeg75"]["fake_recall"] == 0.5
    assert scoped["jpeg75"]["recall_retention"] == 0.5
    assert scoped["jpeg75"]["mean_probability_delta"] == pytest.approx(-0.4)


def test_summarize_rejects_variants_without_original():
    with pytest.raises(ValueError, match="start with original"):
        summarize_paired_predictions([], variants=("jpeg75",))


def test_cli_main_end_to_end(tmp_path, capsys):
    source = make_source_zip(tmp_path / "source.zip", SOURCE_ENTRIES)
    output_dir = tmp_path / "derived"

    exit_code = main(
        [
            "--source-zip", str(source),
            "--output-dir", str(output_dir),
            "--dataset-name", "eximage",
            "--conditions", "jpeg75,screenshot",
            "--per-generator-limit", "1",
        ]
    )

    assert exit_code == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["sample_count"] == 2
    assert (output_dir / "derived_manifest.csv").exists()
    assert (output_dir / "derived_summary.json").exists()
