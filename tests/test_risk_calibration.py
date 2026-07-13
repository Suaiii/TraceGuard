"""Risk calibration methodology tests."""

import pandas as pd

from calibrate_risk import (
    calibrate_thresholds,
    evaluate_calibrated_levels,
    stratified_calibration_split,
)


def _separable_frame():
    return pd.DataFrame(
        {
            "filename": [f"real-{i}" for i in range(10)] + [f"fake-{i}" for i in range(10)],
            "ground_truth": ["real"] * 10 + ["fake"] * 10,
            "risk_score": [0.05 + i * 0.01 for i in range(10)] + [0.70 + i * 0.02 for i in range(10)],
        }
    )


def test_stratified_split_is_reproducible_and_preserves_classes():
    frame = _separable_frame()

    calibration_a, holdout_a = stratified_calibration_split(frame, fraction=0.6, seed=17)
    calibration_b, holdout_b = stratified_calibration_split(frame, fraction=0.6, seed=17)

    assert calibration_a["filename"].tolist() == calibration_b["filename"].tolist()
    assert holdout_a["filename"].tolist() == holdout_b["filename"].tolist()
    assert calibration_a["ground_truth"].value_counts().to_dict() == {"real": 6, "fake": 6}
    assert holdout_a["ground_truth"].value_counts().to_dict() == {"real": 4, "fake": 4}


def test_calibrated_thresholds_are_ordered_and_holdout_is_separate():
    calibration, holdout = stratified_calibration_split(_separable_frame(), fraction=0.6, seed=42)

    result = calibrate_thresholds(calibration, high_precision_target=0.95)
    levels = result["calibrated"]
    evaluation = evaluate_calibrated_levels(holdout, levels)

    assert 0.0 <= levels["low"][1] < levels["medium"][1] <= 1.0
    assert levels["medium"][0] == levels["low"][1]
    assert levels["high"][0] == levels["medium"][1]
    assert evaluation["review"]["f1"] == 1.0
    assert evaluation["sample_count"] == 8


def test_overlapping_scores_still_produce_valid_intervals():
    frame = pd.DataFrame(
        {
            "ground_truth": ["real", "real", "fake", "fake"],
            "risk_score": [0.3, 0.4, 0.35, 0.45],
        }
    )

    levels = calibrate_thresholds(frame)["calibrated"]

    assert levels["low"][1] < levels["medium"][1]
