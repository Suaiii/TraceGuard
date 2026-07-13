"""Detector batch inference contract tests."""

import pytest
import torch
from PIL import Image

from detection import Detector


class RecordingModel:
    def __init__(self):
        self.batch_sizes = []

    def __call__(self, batch):
        self.batch_sizes.append(batch.shape[0])
        fake_logits = batch[:, 0, 0, 0]
        real_logits = 1.0 - fake_logits
        return torch.stack((real_logits, fake_logits), dim=1)


def make_detector():
    detector = Detector.__new__(Detector)
    detector.device = torch.device("cpu")
    detector.model = RecordingModel()
    detector.transform = lambda image: torch.full(
        (3, 2, 2), image.getpixel((0, 0))[0] / 255.0
    )
    return detector


def solid_image(red):
    return Image.new("RGB", (2, 2), (red, 0, 0))


def test_predict_batch_preserves_order_and_batch_boundaries():
    detector = make_detector()
    images = [solid_image(25), solid_image(230), solid_image(204)]

    results = detector.predict_batch(images, batch_size=2)

    assert detector.model.batch_sizes == [2, 1]
    assert [result["label"] for result in results] == ["real", "fake", "fake"]
    assert len(results) == len(images)
    assert all(
        set(result) == {"label", "real_prob", "fake_prob", "risk_score"}
        for result in results
    )
    assert all(result["risk_score"] == result["fake_prob"] for result in results)


def test_predict_batch_rejects_non_positive_batch_size():
    detector = make_detector()

    with pytest.raises(ValueError, match="batch_size"):
        detector.predict_batch([solid_image(25)], batch_size=0)


def test_predict_batch_accepts_empty_input():
    detector = make_detector()

    assert detector.predict_batch([], batch_size=2) == []
    assert detector.model.batch_sizes == []
