"""Propagation case classification tests."""

from classify_cases import classify_sample, summarize


def _result(fake_prob, risk_level, bbox_count=0, label="fake", tamper_type="full_aigc"):
    return {
        "fake_prob": fake_prob,
        "risk_score": fake_prob,
        "risk_level": risk_level,
        "label": label,
        "tamper_type": tamper_type,
        "bbox_list": [{"area": 10}] * bbox_count,
        "dimension_scores": {"artifact_intensity": fake_prob},
    }


def test_opposite_probability_and_risk_directions_are_conflict():
    original = _result(0.8, "medium")
    variant = _result(0.5, "high")

    result = classify_sample(original, variant, "facebook")

    assert result["has_conflict"] is True
    assert "prob_down_risk_up" in result["conflict_reasons"]


def test_matching_probability_and_risk_directions_are_not_direction_conflict():
    original = _result(0.8, "high")
    variant = _result(0.5, "medium")

    result = classify_sample(original, variant, "facebook")

    assert "prob_down_risk_up" not in result["conflict_reasons"]
    assert "prob_up_risk_down" not in result["conflict_reasons"]


def test_summarize_handles_no_selected_typical_cases(tmp_path):
    moderate = {
        "category": "moderate",
        "sample_id": "S1",
        "variant_condition": "facebook",
        "fake_prob_delta": 0.0,
        "conflict_reasons": "",
        "original": {"fake_prob": 0.5, "bbox_count": 0, "risk_level": "low"},
        "variant": {"fake_prob": 0.5, "bbox_count": 0, "risk_level": "low"},
    }

    selected, categories = summarize([moderate], tmp_path)

    assert selected == {}
    assert len(categories["moderate"]) == 1
    assert (tmp_path / "case_classification_selected.csv").is_file()
