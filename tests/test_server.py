from pathlib import Path

import pytest


def test_default_checkpoint_finds_root_weight(tmp_path: Path):
    from server import resolve_checkpoint_path

    root_weight = tmp_path / "best.pth"
    root_weight.touch()

    assert resolve_checkpoint_path(None, project_root=tmp_path) == root_weight


def test_default_checkpoint_prefers_checkpoints_directory(tmp_path: Path):
    from server import resolve_checkpoint_path

    root_weight = tmp_path / "best.pth"
    canonical_weight = tmp_path / "checkpoints" / "best.pth"
    root_weight.touch()
    canonical_weight.parent.mkdir()
    canonical_weight.touch()

    assert resolve_checkpoint_path(None, project_root=tmp_path) == canonical_weight


def test_explicit_missing_checkpoint_does_not_fall_back(tmp_path: Path):
    from server import resolve_checkpoint_path

    (tmp_path / "best.pth").touch()
    missing = tmp_path / "missing.pth"

    with pytest.raises(FileNotFoundError, match="Explicit checkpoint not found"):
        resolve_checkpoint_path(str(missing), project_root=tmp_path)


def test_default_checkpoint_error_lists_supported_locations(tmp_path: Path):
    from server import resolve_checkpoint_path

    with pytest.raises(FileNotFoundError) as error:
        resolve_checkpoint_path(None, project_root=tmp_path)

    message = str(error.value)
    assert str(tmp_path / "checkpoints" / "best.pth") in message
    assert str(tmp_path / "best.pth") in message
    assert "--checkpoint" in message


def test_response_preserves_global_label_and_exposes_tamper_type(sample_pipeline_result):
    from explanation.api.routes import _build_response

    result = dict(sample_pipeline_result)
    result["label"] = "real"
    result["tamper_type"] = "local_tamper"
    result["bbox_list"] = []

    response = _build_response(result)

    assert response.label == "real"
    assert response.tamper_type == "local_tamper"
