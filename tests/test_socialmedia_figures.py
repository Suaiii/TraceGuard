"""Verified social-media report figure tests."""

from pathlib import Path

import pytest

from experiments.socialmedia.plot_verified_results import (
    build_figure_data,
    generate_figures,
)
from experiments.socialmedia.plot_case_evidence import generate_case_figure


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = PROJECT_ROOT / "experiments" / "socialmedia" / "verified_results"


def test_build_figure_data_has_expected_conditions_and_shape():
    data = build_figure_data(SOURCE_DIR)

    assert data["variants"] == ["original", "facebook", "wechat", "weibo"]
    assert data["platforms"] == ["facebook", "wechat", "weibo"]
    assert len(data["generators"]) == 8
    assert data["retention_matrix"].shape == (8, 3)
    assert data["original_recall_by_generator"]["VQDM"] == pytest.approx(0.132)


def test_generate_figures_exports_editable_svg_and_secondary_formats(tmp_path):
    generated = generate_figures(SOURCE_DIR, tmp_path)

    assert len(generated) == 8
    assert all(path.is_file() and path.stat().st_size > 0 for path in generated)
    svg = (tmp_path / "socialmedia_overall.svg").read_text(encoding="utf-8")
    assert "<text" in svg


def test_generate_case_figure_exports_four_formats(tmp_path):
    from PIL import Image

    inputs = tmp_path / "inputs"
    inputs.mkdir()
    rows = []
    for role in ("stable", "degraded", "conflict"):
        for variant in ("original", "facebook"):
            image_path = inputs / f"{role}_{variant}.png"
            Image.new("RGB", (64, 48), color=(40, 120, 160)).save(image_path)
            rows.append({
                "role": role,
                "variant": variant,
                "image_path": str(image_path),
                "fake_prob": "0.9" if role == "stable" else "0.1",
                "label": "fake" if role == "stable" else "real",
                "tamper_type": "local_tamper" if role == "conflict" else "confirmed_real",
            })

    generated = generate_case_figure(rows, tmp_path / "case_evidence")

    assert len(generated) == 4
    assert all(path.is_file() and path.stat().st_size > 0 for path in generated)
    svg = (tmp_path / "case_evidence.svg").read_text(encoding="utf-8")
    assert "Stable" in svg
    assert "Degraded" in svg
    assert "Conflict" in svg
    assert all(line == line.rstrip() for line in svg.splitlines())
