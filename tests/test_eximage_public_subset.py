"""Tests for the deterministic public-ExImage subset builder.

Fixtures are synthetic byte blobs written into nested ZIPs that mimic the public
ExImage layout (``ExImage/<Gen>.zip`` -> ``<Gen>/{test,train}/<Gen>_test_NNNN.png``).
No real ExImage data is required, and no image is ever decoded.
"""

import csv
import json
import zipfile
from pathlib import PurePosixPath

import pytest

from experiments.eximage.build_public_subset import (
    build_public_subset,
    discover_generators,
    list_test_entries,
    select_entries,
)

GENERATORS = ("BigGAN", "Flux", "SD15")


def _make_nested_zip(path, generator, test_count, train_count):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for index in range(test_count):
            name = f"{generator}/test/{generator}_test_{index:04d}.png"
            archive.writestr(name, f"{generator}-test-{index}".encode())
        for index in range(train_count):
            name = f"{generator}/train/{generator}_train_{index:04d}.png"
            archive.writestr(name, f"{generator}-train-{index}".encode())


@pytest.fixture
def public_zip(tmp_path):
    """Build a miniature stand-in for the public ExImage.zip."""
    nested_dir = tmp_path / "nested"
    nested_dir.mkdir()
    outer = tmp_path / "ExImage.zip"
    # BigGAN is deliberately short (8 < 10) to exercise the shortfall path.
    plan = {"BigGAN": (8, 5), "Flux": (40, 12), "SD15": (40, 12)}
    with zipfile.ZipFile(outer, "w", zipfile.ZIP_DEFLATED) as archive:
        for generator, (test_count, train_count) in plan.items():
            nested = nested_dir / f"{generator}.zip"
            _make_nested_zip(nested, generator, test_count, train_count)
            archive.write(nested, f"ExImage/{generator}.zip")
    return outer


def test_discover_generators_sorted(public_zip):
    assert discover_generators(public_zip) == sorted(GENERATORS)


def test_list_test_entries_excludes_train(tmp_path):
    nested = tmp_path / "Flux.zip"
    _make_nested_zip(nested, "Flux", test_count=6, train_count=4)
    entries = list_test_entries(nested, "Flux")
    assert len(entries) == 6
    assert all(PurePosixPath(name).parts[-2] == "test" for name in entries)
    assert entries == sorted(entries, key=str.casefold)


def test_select_entries_is_deterministic_for_same_seed():
    entries = [f"Flux/test/Flux_test_{i:04d}.png" for i in range(100)]
    first = select_entries(entries, per_generator=10, seed=42)
    second = select_entries(list(reversed(entries)), per_generator=10, seed=42)
    assert first == second
    assert len(first) == 10
    assert first == sorted(first, key=str.casefold)


def test_select_entries_differs_for_other_seed():
    entries = [f"Flux/test/Flux_test_{i:04d}.png" for i in range(100)]
    assert select_entries(entries, 10, seed=42) != select_entries(entries, 10, seed=7)


def test_select_entries_takes_all_when_short():
    entries = [f"Flux/test/Flux_test_{i:04d}.png" for i in range(4)]
    assert select_entries(entries, per_generator=10, seed=42) == sorted(entries)


def test_build_public_subset_is_deterministic(public_zip, tmp_path):
    """Same seed, two independent runs -> identical manifest and identical ZIP bytes."""
    first = build_public_subset(
        public_zip, tmp_path / "run1", per_generator=10, seed=42, dataset_name="ds"
    )
    second = build_public_subset(
        public_zip, tmp_path / "run2", per_generator=10, seed=42, dataset_name="ds"
    )
    assert first["fake_subset_zip"]["sha256"] == second["fake_subset_zip"]["sha256"]
    assert first["manifest"]["sha256"] == second["manifest"]["sha256"]
    assert (tmp_path / "run1" / "manifest.csv").read_bytes() == (
        tmp_path / "run2" / "manifest.csv"
    ).read_bytes()
    assert (tmp_path / "run1" / "fake_subset.zip").read_bytes() == (
        tmp_path / "run2" / "fake_subset.zip"
    ).read_bytes()


def test_build_public_subset_records_shortfall_without_padding(public_zip, tmp_path):
    summary = build_public_subset(
        public_zip, tmp_path / "run", per_generator=10, seed=42, dataset_name="ds"
    )
    counts = summary["counts_by_generator"]
    # BigGAN only has 8 test images: take all 8, record the shortfall, never pad.
    assert counts["BigGAN"] == {"test_available": 8, "selected": 8, "short": True}
    assert counts["Flux"] == {"test_available": 40, "selected": 10, "short": False}
    assert summary["selected_total"] == 8 + 10 + 10


def test_manifest_and_zip_agree(public_zip, tmp_path):
    build_public_subset(
        public_zip, tmp_path / "run", per_generator=10, seed=42, dataset_name="ds"
    )
    with (tmp_path / "run" / "manifest.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert [*rows[0]] == ["sample_id", "generator", "label", "entry_path", "crc32", "source"]
    assert {row["label"] for row in rows} == {"fake"}
    assert len({row["sample_id"] for row in rows}) == len(rows)
    with zipfile.ZipFile(tmp_path / "run" / "fake_subset.zip") as archive:
        names = sorted(archive.namelist())
        crcs = {info.filename: format(info.CRC & 0xFFFFFFFF, "08X") for info in archive.infolist()}
    assert names == sorted(row["entry_path"] for row in rows)
    # Entries are <Gen>/<file>, so evaluate/perturb can use --generator-part 0.
    for row in rows:
        assert row["entry_path"].split("/")[0] == row["generator"]
        assert crcs[row["entry_path"]] == row["crc32"]
        # source must trace back into the public archive, test split only.
        assert row["source"].startswith("ExImage.zip!ExImage/")
        assert "/test/" in row["source"]


def test_only_test_split_is_sampled(public_zip, tmp_path):
    build_public_subset(
        public_zip, tmp_path / "run", per_generator=10, seed=42, dataset_name="ds"
    )
    with (tmp_path / "run" / "manifest.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert not any("/train/" in row["source"] for row in rows)


def test_work_dir_is_cleaned_up(public_zip, tmp_path):
    out = tmp_path / "run"
    build_public_subset(public_zip, out, per_generator=10, seed=42, dataset_name="ds")
    assert not (out / "_work").exists()
    assert sorted(p.name for p in out.iterdir()) == [
        "fake_subset.zip",
        "manifest.csv",
        "subset_counts.json",
    ]


def test_subset_counts_json_records_seed_and_public_source(public_zip, tmp_path):
    build_public_subset(
        public_zip, tmp_path / "run", per_generator=10, seed=42, dataset_name="ds"
    )
    summary = json.loads((tmp_path / "run" / "subset_counts.json").read_text(encoding="utf-8"))
    assert summary["seed"] == 42
    assert summary["label"] == "fake"
    assert summary["source_zip"]["google_drive_file_id"] == "1s2JYbZyMe-SzWjkja9tlZFrzIJiFhwI-"
