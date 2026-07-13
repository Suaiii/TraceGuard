"""Report-grade system architecture figure tests."""

from experiments.plot_system_figures import generate_system_figures
from experiments.plot_detection_example import generate_detection_example


def test_generate_system_figures_exports_editable_formats(tmp_path):
    generated = generate_system_figures(tmp_path)

    assert len(generated) == 8
    assert all(path.is_file() and path.stat().st_size > 0 for path in generated)
    architecture = (tmp_path / "system_architecture.svg").read_text(encoding="utf-8")
    workflow = (tmp_path / "web_workflow.svg").read_text(encoding="utf-8")
    assert "Detector.predict()" in architecture
    assert "AnalysisResponse" in architecture
    assert "POST /api/v1/" in workflow
    assert "analyze" in workflow
    assert "人工复核" in workflow
    assert all(line == line.rstrip() for line in architecture.splitlines())
    assert all(line == line.rstrip() for line in workflow.splitlines())


def test_generate_detection_example_exports_editable_formats(tmp_path):
    from PIL import Image

    paths = []
    for name, color in (("original", "gray"), ("overlay", "blue"), ("bbox", "red")):
        path = tmp_path / f"{name}.png"
        Image.new("RGB", (80, 60), color=color).save(path)
        paths.append(path)

    generated = generate_detection_example(*paths, tmp_path / "detection_example")

    assert len(generated) == 4
    svg = (tmp_path / "detection_example.svg").read_text(encoding="utf-8")
    assert "Original" in svg
    assert "Grad-CAM overlay" in svg
    assert "Suspicious regions" in svg
    assert all(line == line.rstrip() for line in svg.splitlines())
