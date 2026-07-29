"""
ContentClassifier — lightweight zero-shot image content classifier.

Uses MobileCLIP2-S0 (~54M params, ~108MB FP16) via open_clip for zero-shot
categorization of image content into super-oversight domains (warfare,
terrorism, firearms, graphic violence) versus normal categories.

Architecture:
  - Category texts are pre-encoded once in __init__ (frozen text embeddings).
  - classify() only runs image encoding + one matrix multiplication.
  - Inference: ~15ms GPU / ~80ms CPU per image.

Usage:
    classifier = ContentClassifier(device="cuda")
    result = classifier.classify(pil_image)
    # result: {"category": "warfare...", "is_super_oversight_domain": True, ...}
"""

import logging
from typing import Optional

import torch
from PIL import Image

logger = logging.getLogger(__name__)


class ContentClassifier:
    """Zero-shot content category classifier (CLIP multimodal alignment).

    Classifies images against 9 categories (4 super-oversight + 5 normal).
    Designed for integration into ExplanationPipeline as an optional component.
    """

    # ---- Super-oversight domain categories (indices 0–3) -------------------
    SUPERVISED_CATEGORIES: list[str] = [
        "warfare, military conflict, armed combat, soldiers in battle, explosions on battlefield",
        "terrorism, extremist violence, political attacks, bombings, armed militants",
        "weapons, firearms, rifles, handguns, explosives, missiles, military equipment",
        "graphic violence, severe injury, blood, corpses, human suffering, war casualties",
    ]

    # ---- Normal / safe categories (indices 4–8) -----------------------------
    NORMAL_CATEGORIES: list[str] = [
        "nature, landscapes, animals, plants, scenic outdoor views, wildlife",
        "portraits, people, daily life, social activities, family, friends",
        "objects, products, buildings, architecture, vehicles, urban scenes",
        "art, paintings, illustrations, abstract imagery, cartoons, digital art",
        "text, documents, screenshots, memes, charts, diagrams, code",
    ]

    SUPERVISED_INDICES: set[int] = {0, 1, 2, 3}

    # ------------------------------------------------------------------

    def __init__(
        self,
        model_name: str = "MobileCLIP2-S0",
        pretrained: str = "dfndr2b",
        device: str = "cuda",
    ):
        """Load CLIP model and pre-encode category texts.

        Args:
            model_name: open_clip model identifier.
            pretrained: Pretrained weights tag.
            device: "cuda" or "cpu".
        """
        self.device = device
        self._model_name = model_name

        import open_clip

        logger.info(
            "Loading content classifier: %s (pretrained=%s) on %s",
            model_name, pretrained, device,
        )
        self._model, _, self._preprocess = open_clip.create_model_and_transforms(
            model_name, pretrained=pretrained,
        )
        self._tokenizer = open_clip.get_tokenizer(model_name)
        self._model.to(device).eval()

        self.all_categories: list[str] = (
            self.SUPERVISED_CATEGORIES + self.NORMAL_CATEGORIES
        )

        # Pre-encode all category texts — these are frozen and never change.
        self._encode_texts()
        logger.info(
            "Content classifier ready: %d categories pre-encoded", len(self.all_categories),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _encode_texts(self) -> None:
        """Pre-encode all category texts into normalized feature vectors."""
        texts = self._tokenizer(self.all_categories).to(self.device)
        with torch.no_grad():
            self._text_features: torch.Tensor = self._model.encode_text(texts)
            self._text_features = torch.nn.functional.normalize(
                self._text_features, dim=-1,
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @torch.no_grad()
    def classify(self, image: Image.Image) -> dict:
        """Classify a single PIL image into content categories.

        Args:
            image: PIL RGB image of any resolution (will be resized by CLIP preprocess).

        Returns:
            dict:
                category:                  str   — top-1 category text.
                is_super_oversight_domain: bool  — True if top-1 is in supervised set.
                super_oversight_score:     float — highest score among supervised categories.
                scores:                    dict  — {category_text: probability} for all 9 cats.
        """
        img_tensor = self._preprocess(image).unsqueeze(0).to(self.device)

        with torch.amp.autocast("cuda" if self.device == "cuda" else "cpu"):
            img_features = self._model.encode_image(img_tensor)
            img_features = torch.nn.functional.normalize(img_features, dim=-1)

        # Cosine similarity → softmax over categories
        similarity = (img_features @ self._text_features.T).squeeze(0)  # [N_cats]
        probs = similarity.softmax(dim=0)

        best_idx: int = int(probs.argmax().item())
        is_so: bool = best_idx in self.SUPERVISED_INDICES
        top_so_score: float = float(
            max(probs[i].item() for i in self.SUPERVISED_INDICES)
        )

        return {
            "category": self.all_categories[best_idx],
            "is_super_oversight_domain": is_so,
            "super_oversight_score": top_so_score,
            "scores": {
                cat: float(probs[i].item())
                for i, cat in enumerate(self.all_categories)
            },
        }

    def classify_batch(self, images: list[Image.Image]) -> list[dict]:
        """Classify a batch of PIL images.

        Args:
            images: List of PIL RGB images.

        Returns:
            List of dicts, same structure as classify().
        """
        # Simple sequential processing — batch sizes are small in this application.
        # For larger batches, images could be stacked and processed in one forward pass.
        return [self.classify(img) for img in images]

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def category_count(self) -> int:
        return len(self.all_categories)

    @property
    def supervised_count(self) -> int:
        return len(self.SUPERVISED_INDICES)
