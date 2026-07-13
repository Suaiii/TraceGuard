"""Balanced ZIP subset extraction tests."""

import csv
import zipfile

from experiments.socialmedia.extract_balanced_subset import extract_balanced_subset


def test_extract_balanced_subset_is_stratified_and_auditable(tmp_path):
    archive = tmp_path / "images.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        for name in ["real-1.jpg", "real-2.jpg", "a-1.jpg", "a-2.jpg", "b-1.jpg", "b-2.jpg"]:
            handle.writestr(f"dataset/{name}", name.encode("ascii"))

    predictions = tmp_path / "predictions.csv"
    rows = [
        ("r1", "real", "Real", "dataset/real-1.jpg"),
        ("r2", "real", "Real", "dataset/real-2.jpg"),
        ("a1", "fake", "A", "dataset/a-1.jpg"),
        ("a2", "fake", "A", "dataset/a-2.jpg"),
        ("b1", "fake", "B", "dataset/b-1.jpg"),
        ("b2", "fake", "B", "dataset/b-2.jpg"),
    ]
    with predictions.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["sample_id", "label", "generator", "variant", "archive_path", "entry_path", "status"],
        )
        writer.writeheader()
        for sample_id, label, generator, entry_path in rows:
            writer.writerow(
                {
                    "sample_id": sample_id,
                    "label": label,
                    "generator": generator,
                    "variant": "facebook",
                    "archive_path": archive,
                    "entry_path": entry_path,
                    "status": "ok",
                }
            )

    summary = extract_balanced_subset(
        predictions,
        tmp_path / "out",
        variant="facebook",
        real_count=2,
        fake_count=4,
        seed=9,
    )

    assert summary["selected"] == {"real": 2, "fake": 4}
    assert summary["fake_by_generator"] == {"A": 2, "B": 2}
    assert len(list((tmp_path / "out" / "real").glob("*.jpg"))) == 2
    assert len(list((tmp_path / "out" / "fake").glob("*.jpg"))) == 4
    assert (tmp_path / "out" / "manifest.csv").is_file()
