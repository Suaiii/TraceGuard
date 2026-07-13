"""Social-media robustness experiment unit tests."""

import csv
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pytest
from PIL import Image

from experiments.socialmedia.evaluate import (
    PredictionInput,
    binary_metrics,
    build_platform_records,
    build_genimage_pairs,
    expand_pair_manifest,
    list_image_entries,
    main,
    parse_eachfake_label,
    run_prediction_records,
    summarize_classification_predictions,
    summarize_paired_predictions,
)


def make_zip(path: Path, names):
    with ZipFile(path, "w") as archive:
        for name in names:
            archive.writestr(name, b"image-bytes")
    return path


def test_checkpoint_entries_are_excluded(tmp_path):
    archive = make_zip(
        tmp_path / "images.zip",
        [
            "set/a.jpg",
            "set/.ipynb_checkpoints/a-checkpoint.jpg",
            "set/readme.txt",
        ],
    )

    entries = list_image_entries(archive)

    assert [entry.name for entry in entries] == ["set/a.jpg"]


def test_genimage_pairs_require_all_variants(tmp_path):
    original = make_zip(
        tmp_path / "original.zip",
        ["GenImage_Test/0_adm_174.png", "GenImage_Test/1_biggan_2.png"],
    )
    platforms = {
        platform: make_zip(
            tmp_path / f"{platform}.zip",
            [
                f"{platform}_GenImage_Test/ADM/0_adm_174.jpg",
                f"{platform}_GenImage_Test/BigGAN/1_biggan_2.jpg",
            ],
        )
        for platform in ("facebook", "wechat", "weibo")
    }

    pairs = build_genimage_pairs(original, platforms)

    assert len(pairs) == 2
    assert pairs[0].sample_id == "genimage:adm:0_adm_174"
    assert pairs[0].pair_status == "complete"
    assert set(pairs[0].entries) == {"original", "facebook", "wechat", "weibo"}


def test_genimage_pairs_reject_missing_variant(tmp_path):
    original = make_zip(tmp_path / "original.zip", ["GenImage_Test/0_adm_174.png"])
    platforms = {
        "facebook": make_zip(
            tmp_path / "facebook.zip",
            ["Facebook_GenImage_Test/ADM/0_adm_174.jpg"],
        ),
        "wechat": make_zip(tmp_path / "wechat.zip", []),
        "weibo": make_zip(
            tmp_path / "weibo.zip",
            ["Weibo_GenImage_Test/ADM/0_adm_174.jpg"],
        ),
    }

    with pytest.raises(ValueError, match="missing variants"):
        build_genimage_pairs(original, platforms)


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("00011_Real_military_rocket_0_real.jpg", "real"),
        ("0001_BigGAN_db_test_1_fake.jpg", "fake"),
    ],
)
def test_parse_eachfake_label(filename, expected):
    assert parse_eachfake_label(filename) == expected


def test_parse_eachfake_label_rejects_ambiguous_name():
    with pytest.raises(ValueError, match="label"):
        parse_eachfake_label("unknown.jpg")


def test_binary_metrics_match_hand_calculation():
    metrics = binary_metrics(
        labels=["real", "real", "fake", "fake"],
        probabilities=[0.1, 0.4, 0.35, 0.8],
    )

    assert metrics["count"] == 4
    assert metrics["real_count"] == 2
    assert metrics["fake_count"] == 2
    assert metrics["accuracy"] == pytest.approx(0.75)
    assert metrics["macro_f1"] == pytest.approx((0.8 + 2 / 3) / 2)
    assert metrics["roc_auc"] == pytest.approx(0.75)
    assert metrics["real_recall"] == pytest.approx(1.0)
    assert metrics["fake_recall"] == pytest.approx(0.5)


def test_binary_metrics_rejects_single_class_auc():
    with pytest.raises(ValueError, match="both real and fake"):
        binary_metrics(labels=["fake", "fake"], probabilities=[0.7, 0.9])


def test_expand_pair_manifest_creates_four_prediction_records(tmp_path):
    manifest = tmp_path / "pairs.csv"
    with manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "sample_id", "dataset", "label", "generator",
                "original_archive", "original_entry",
                "facebook_archive", "facebook_entry",
                "wechat_archive", "wechat_entry",
                "weibo_archive", "weibo_entry", "pair_status",
            ],
        )
        writer.writeheader()
        writer.writerow({
            "sample_id": "genimage:adm:0_adm_174",
            "dataset": "GenImage",
            "label": "fake",
            "generator": "ADM",
            "original_archive": "original.zip",
            "original_entry": "GenImage_Test/0_adm_174.png",
            "facebook_archive": "facebook.zip",
            "facebook_entry": "Facebook_GenImage_Test/ADM/0_adm_174.jpg",
            "wechat_archive": "wechat.zip",
            "wechat_entry": "Wechat_GenImage_Test/ADM/0_adm_174.jpg",
            "weibo_archive": "weibo.zip",
            "weibo_entry": "Weibo_GenImage_Test/ADM/0_adm_174.jpg",
            "pair_status": "complete",
        })

    records = expand_pair_manifest(manifest, project_root=tmp_path)

    assert [record.variant for record in records] == [
        "original", "facebook", "wechat", "weibo"
    ]
    assert all(record.archive_path.is_absolute() for record in records)


def png_bytes(red):
    buffer = BytesIO()
    Image.new("RGB", (2, 2), (red, 0, 0)).save(buffer, format="PNG")
    return buffer.getvalue()


class RecordingDetector:
    def __init__(self):
        self.calls = 0

    def predict_batch(self, images, batch_size=32):
        self.calls += 1
        return [
            {
                "label": "fake" if image.getpixel((0, 0))[0] > 127 else "real",
                "real_prob": 1.0 - image.getpixel((0, 0))[0] / 255.0,
                "fake_prob": image.getpixel((0, 0))[0] / 255.0,
                "risk_score": image.getpixel((0, 0))[0] / 255.0,
            }
            for image in images
        ]


def test_run_prediction_records_resumes_without_duplicate_rows(tmp_path):
    archive = tmp_path / "images.zip"
    with ZipFile(archive, "w") as handle:
        handle.writestr("set/a.png", png_bytes(255))
        handle.writestr("set/b.png", png_bytes(0))
    records = [
        PredictionInput("sample-a", "GenImage", "ADM", "fake", "original", archive, "set/a.png"),
        PredictionInput("sample-b", "GenImage", "ADM", "fake", "original", archive, "set/b.png"),
    ]
    detector = RecordingDetector()
    output = tmp_path / "predictions.csv"

    first = run_prediction_records(records, detector, output, "checkpoint-hash", batch_size=2)
    second = run_prediction_records(records, detector, output, "checkpoint-hash", batch_size=2)

    with output.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert first == {"completed": 2, "failed": 0, "skipped": 0}
    assert second == {"completed": 0, "failed": 0, "skipped": 2}
    assert detector.calls == 1
    assert len(rows) == 2
    assert {(row["sample_id"], row["variant"]) for row in rows} == {
        ("sample-a", "original"), ("sample-b", "original")
    }


def test_summarize_paired_predictions_reports_probability_delta_and_retention():
    rows = [
        {"sample_id": "a", "generator": "ADM", "label": "fake", "variant": "original", "fake_prob": "0.8", "predicted_label": "fake", "status": "ok"},
        {"sample_id": "a", "generator": "ADM", "label": "fake", "variant": "wechat", "fake_prob": "0.4", "predicted_label": "real", "status": "ok"},
        {"sample_id": "b", "generator": "ADM", "label": "fake", "variant": "original", "fake_prob": "0.6", "predicted_label": "fake", "status": "ok"},
        {"sample_id": "b", "generator": "ADM", "label": "fake", "variant": "wechat", "fake_prob": "0.7", "predicted_label": "fake", "status": "ok"},
    ]

    summary = summarize_paired_predictions(rows)
    wechat = next(row for row in summary if row["scope"] == "all" and row["variant"] == "wechat")

    assert wechat["sample_count"] == 2
    assert wechat["fake_recall"] == pytest.approx(0.5)
    assert wechat["mean_fake_prob"] == pytest.approx(0.55)
    assert wechat["mean_probability_delta"] == pytest.approx(-0.15)
    assert wechat["recall_retention"] == pytest.approx(0.5)


def test_build_platform_records_parses_labels_and_excludes_checkpoints(tmp_path):
    archive = make_zip(
        tmp_path / "wechat.zip",
        [
            "Wechat_test/test/00011_Real_rocket_0_real.jpg",
            "Wechat_test/test/0001_BigGAN_db_test_1_fake.jpg",
            "Wechat_test/.ipynb_checkpoints/duplicate_1_fake.jpg",
        ],
    )

    records = build_platform_records("wechat", archive)

    assert len(records) == 2
    assert [record.label for record in records] == ["fake", "real"]
    assert all(record.variant == "wechat" for record in records)
    assert records[0].generator == "BigGAN"
    assert records[1].generator == "Real"


def test_summarize_classification_predictions_reports_platform_metrics():
    rows = [
        {"variant": "facebook", "label": "real", "fake_prob": "0.1", "status": "ok"},
        {"variant": "facebook", "label": "real", "fake_prob": "0.4", "status": "ok"},
        {"variant": "facebook", "label": "fake", "fake_prob": "0.35", "status": "ok"},
        {"variant": "facebook", "label": "fake", "fake_prob": "0.8", "status": "ok"},
    ]

    summary = summarize_classification_predictions(rows)

    assert len(summary) == 1
    assert summary[0]["platform"] == "facebook"
    assert summary[0]["count"] == 4
    assert summary[0]["real_count"] == 2
    assert summary[0]["fake_count"] == 2
    assert summary[0]["accuracy"] == pytest.approx(0.75)
    assert summary[0]["roc_auc"] == pytest.approx(0.75)


def test_validate_cli_checks_manifest_entries(tmp_path, capsys):
    archives = {}
    entries = {
        "original": "GenImage_Test/0_adm_174.png",
        "facebook": "Facebook_GenImage_Test/ADM/0_adm_174.jpg",
        "wechat": "Wechat_GenImage_Test/ADM/0_adm_174.jpg",
        "weibo": "Weibo_GenImage_Test/ADM/0_adm_174.jpg",
    }
    for variant, entry in entries.items():
        archives[variant] = make_zip(tmp_path / f"{variant}.zip", [entry])
    manifest = tmp_path / "pairs.csv"
    fields = [
        "sample_id", "dataset", "label", "generator",
        "original_archive", "original_entry", "facebook_archive", "facebook_entry",
        "wechat_archive", "wechat_entry", "weibo_archive", "weibo_entry", "pair_status",
    ]
    with manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        row = {
            "sample_id": "genimage:adm:0_adm_174",
            "dataset": "GenImage",
            "label": "fake",
            "generator": "ADM",
            "pair_status": "complete",
        }
        for variant in entries:
            row[f"{variant}_archive"] = archives[variant].name
            row[f"{variant}_entry"] = entries[variant]
        writer.writerow(row)

    exit_code = main([
        "validate",
        "--manifest", str(manifest),
        "--project-root", str(tmp_path),
    ])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert '"sample_count": 1' in output
    assert '"prediction_record_count": 4' in output
