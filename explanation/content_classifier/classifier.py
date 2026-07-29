"""
ContentClassifier — Context-Aware Multi-Prompt Ensemble Engine.

Uses MobileCLIP2-S0 (~54M params, ~108MB FP16) via open_clip with a
multi-template weighted-fusion prompt ensemble for zero-shot image content
categorization.

Key innovation over single-prompt CLIP:
  - Each category defines 2–4 prompt templates spanning different visual
    dimensions (close-up, environment, documentary style, action).
  - Prompts carry per-template weights; text features are fused via
    weighted summation then L2-normalized to produce a single "super
    feature vector" per category.
  - The ensemble is more robust to prompt phrasing variation and yields
    better-aligned similarity scores without any fine-tuning.

Architecture:
  - Category prompt templates are pre-encoded and fused once in __init__.
  - classify() only runs image encoding + one matrix multiplication.
  - Inference: ~15ms GPU / ~80ms CPU per image.

Usage:
    classifier = ContentClassifier(device="cuda")
    result = classifier.classify(pil_image)
    # result: {"category": "warfare", "is_super_oversight_domain": True, ...}
"""

from __future__ import annotations

import logging
from typing import Optional

import torch
import torch.nn.functional as F
from PIL import Image

logger = logging.getLogger(__name__)

# ==============================================================================
# Multi-template weighted-fusion prompt configuration
# ==============================================================================

PROMPT_CONFIG: dict[str, dict] = {
    # ---- Super-oversight domain categories --------------------------------
    "warfare": {
        "is_supervised": True,
        "prompts": [
            (
                "a photograph of warfare, military conflict, and battle scenes",
                1.2,
            ),
            (
                "soldiers, tanks, and combat vehicles in active battlefield environments",
                1.0,
            ),
            (
                "news coverage of military strikes, war zones, and armed violence",
                1.0,
            ),
            (
                "a scene of military explosion, air strike, or combat destruction",
                0.8,
            ),
        ],
    },
    "terrorism": {
        "is_supervised": True,
        "prompts": [
            (
                "a photo of terrorist attacks, extremist violence, or bombings",
                1.2,
            ),
            (
                "political violence, armed militants, and extremist group activity",
                1.0,
            ),
            (
                "imagery of hostage situations, terror attacks, or violent extremism",
                1.0,
            ),
        ],
    },
    "weapons": {
        "is_supervised": True,
        "prompts": [
            (
                "a close-up photograph of firearms, handguns, rifles, or assault weapons",
                1.2,
            ),
            (
                "military armaments, heavy weapons, missiles, and explosives",
                1.0,
            ),
            (
                "a picture showing dangerous weapons, guns, or ammunition",
                1.0,
            ),
        ],
    },
    "gore_violence": {
        "is_supervised": True,
        "prompts": [
            (
                "graphic violence, severe physical injury, blood, and corpses",
                1.2,
            ),
            (
                "human suffering, casualties, and traumatic bodily harm",
                1.0,
            ),
            (
                "bloody violence, violent assault, and crime scene casualties",
                1.0,
            ),
        ],
    },

    # ---- Normal / safe categories -----------------------------------------
    "nature_animals": {
        "is_supervised": False,
        "prompts": [
            (
                "a photo of natural landscapes, mountains, forests, or scenic views",
                1.0,
            ),
            (
                "wildlife, domestic animals, pets, plants, and natural environments",
                1.0,
            ),
        ],
    },
    "portraits_people": {
        "is_supervised": False,
        "prompts": [
            (
                "a portrait of a person, daily human life, or social activities",
                1.0,
            ),
            (
                "people smiling, casual selfies, or crowd gatherings in normal context",
                1.0,
            ),
        ],
    },
    "objects_architecture": {
        "is_supervised": False,
        "prompts": [
            (
                "everyday commercial products, buildings, vehicles, or city architecture",
                1.0,
            ),
            (
                "indoor furniture, appliances, food, or street scenery",
                1.0,
            ),
        ],
    },
    "art_illustration": {
        "is_supervised": False,
        "prompts": [
            (
                "artistic paintings, digital illustrations, abstract imagery, or cartoons",
                1.0,
            ),
            (
                "drawings, 3d rendered artwork, or graphic design",
                1.0,
            ),
        ],
    },
    "text_documents": {
        "is_supervised": False,
        "prompts": [
            (
                "screenshots, text documents, paper forms, infographics, or charts",
                1.0,
            ),
            (
                "digital memes with text overlays or social media posts",
                1.0,
            ),
        ],
    },
}


class ContentClassifier:
    """Zero-shot content classifier with multi-template weighted-fusion prompts.

    Each category defines several prompt templates viewed from different
    visual dimensions.  During initialisation those templates are encoded,
    fused via weighted summation, and L2-normalised into a single *super
    feature vector* per category.  At inference time only one image forward
    pass + one dot-product are needed — the ensemble cost is paid once at
    startup.
    """

    def __init__(
        self,
        model_name: str = "MobileCLIP2-S0",
        pretrained: str = "dfndr2b",
        device: str = "cuda",
    ):
        """Load CLIP model, pre-encode and fuse category prompt templates.

        Args:
            model_name: open_clip model identifier.
            pretrained: Pretrained weights tag.
            device: ``"cuda"`` or ``"cpu"``.
        """
        self.device = device
        self._model_name = model_name

        import open_clip

        logger.info(
            "Loading content classifier: %s (pretrained=%s) on %s",
            model_name,
            pretrained,
            device,
        )
        self._model, _, self._preprocess = open_clip.create_model_and_transforms(
            model_name,
            pretrained=pretrained,
        )
        self._tokenizer = open_clip.get_tokenizer(model_name)
        self._model.to(device).eval()

        # Build ordered category list and supervised-index set from PROMPT_CONFIG
        self._category_names: list[str] = list(PROMPT_CONFIG.keys())
        self._supervised_indices: set[int] = {
            i
            for i, name in enumerate(self._category_names)
            if PROMPT_CONFIG[name].get("is_supervised", False)
        }

        # Pre-encode and fuse all category prompts
        self._encode_texts()

        logger.info(
            "Content classifier ready: %d categories (%d supervised), "
            "%d total prompt templates pre-encoded and fused.",
            len(self._category_names),
            len(self._supervised_indices),
            sum(len(PROMPT_CONFIG[n]["prompts"]) for n in self._category_names),
        )

    # ------------------------------------------------------------------
    # Internal: multi-template weighted-fusion text encoding
    # ------------------------------------------------------------------

    def _encode_texts(self) -> None:
        """Pre-encode and fuse prompt templates for every category.

        For each category:

        1. Tokenize all its prompt templates.
        2. Encode them with ``model.encode_text`` → shape [T, D].
        3. Weighted summation across the T templates (broadcast weights).
        4. L2-normalize the resulting *super feature vector*.

        The per-category super vectors are stacked into ``self._text_features``
        with shape [num_categories, D].
        """
        super_vectors: list[torch.Tensor] = []

        for cat_name in self._category_names:
            cfg = PROMPT_CONFIG[cat_name]
            prompts: list[tuple[str, float]] = cfg["prompts"]

            texts = [p[0] for p in prompts]
            weights = torch.tensor(
                [p[1] for p in prompts],
                dtype=torch.float32,
                device=self.device,
            )  # [T]

            tokens = self._tokenizer(texts).to(self.device)  # [T, ctx_len]

            with torch.no_grad():
                text_feats = self._model.encode_text(tokens)  # [T, D]
                text_feats = F.normalize(text_feats, dim=-1)  # unit-norm each template

                # Weighted fusion: sum(template_i * weight_i)
                fused = (text_feats * weights.unsqueeze(-1)).sum(dim=0)  # [D]
                fused = F.normalize(fused, dim=-1)  # L2 unit super vector

            super_vectors.append(fused)

        self._text_features = torch.stack(super_vectors, dim=0)  # [C, D]
        logger.debug(
            "Text super-feature tensor: %s", tuple(self._text_features.shape),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @torch.no_grad()
    def classify(self, image: Image.Image) -> dict:
        """Classify a single PIL image into content categories.

        Args:
            image: PIL RGB image of any resolution (resized by CLIP preprocess).

        Returns:
            dict:
                category:                  str   — top-1 category name (key in PROMPT_CONFIG).
                is_super_oversight_domain: bool  — True if top-1 is a supervised category.
                super_oversight_score:     float — highest softmax probability among supervised categories.
                scores:                    dict  — {category_name: probability} for all categories.
        """
        img_tensor = self._preprocess(image).unsqueeze(0).to(self.device)

        with torch.amp.autocast("cuda" if self.device == "cuda" else "cpu"):
            img_features = self._model.encode_image(img_tensor)
            img_features = F.normalize(img_features, dim=-1)  # [1, D]

        # Cosine similarity → softmax over categories
        similarity = (img_features @ self._text_features.T).squeeze(0)  # [C]
        probs = similarity.softmax(dim=0)  # [C]

        best_idx: int = int(probs.argmax().item())
        is_so: bool = best_idx in self._supervised_indices
        top_so_score: float = float(
            max(probs[i].item() for i in self._supervised_indices)
        ) if self._supervised_indices else 0.0

        return {
            "category": self._category_names[best_idx],
            "is_super_oversight_domain": is_so,
            "super_oversight_score": top_so_score,
            "scores": {
                name: float(probs[i].item())
                for i, name in enumerate(self._category_names)
            },
        }

    def classify_batch(self, images: list[Image.Image]) -> list[dict]:
        """Classify a batch of PIL images (sequential for small batches).

        Args:
            images: List of PIL RGB images.

        Returns:
            List of dicts, same structure as :meth:`classify`.
        """
        return [self.classify(img) for img in images]

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def category_names(self) -> list[str]:
        """Ordered list of category names (keys of PROMPT_CONFIG)."""
        return list(self._category_names)

    @property
    def category_count(self) -> int:
        return len(self._category_names)

    @property
    def supervised_count(self) -> int:
        return len(self._supervised_indices)

    @property
    def supervised_indices(self) -> set[int]:
        return set(self._supervised_indices)
