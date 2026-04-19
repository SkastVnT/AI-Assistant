"""
image_pipeline.anime_pipeline.critique_service — Score outputs and propose refinements.

Uses vision LLMs (same provider chain as VisionService) to produce a
CritiqueReport with per-dimension scores and structured patches.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Optional

import httpx

from .config import AnimePipelineConfig
from .schemas import CritiqueReport, LayerPlan

logger = logging.getLogger(__name__)

_CRITIQUE_SYSTEM_PROMPT = """\
You are a quality critic for anime image generation. Score the image on each
dimension (0-10) and list specific issues. Return ONLY valid JSON:

{
  "anatomy_score": 0,
  "anatomy_issues": [],
  "face_score": 0,
  "face_issues": [],
  "hands_score": 0,
  "hand_issues": [],
  "composition_score": 0,
  "composition_issues": [],
  "color_score": 0,
  "color_issues": [],
  "style_score": 0,
  "style_drift": [],
  "background_score": 0,
  "background_issues": [],
  "retry_recommendation": false,
  "prompt_patch": [],
  "control_patch": {}
}

Scoring guide:
- 0-3: severe issues
- 4-6: noticeable problems
- 7-8: good quality
- 9-10: excellent

Set retry_recommendation=true only if issues are severe enough to warrant retry.
prompt_patch: list of tokens to ADD to the positive prompt.
control_patch: dict of control strengths to adjust (e.g. {"lineart_strength": 0.85}).

Return ONLY JSON, no markdown fences, no commentary.
"""


class CritiqueService:
    """Vision-based quality scoring and structured refinement proposals.

    Returns CritiqueReport with per-dimension scores and actionable patches.
    Uses the same Gemini / OpenAI fallback chain as VisionService.
    """

    def __init__(self, config: AnimePipelineConfig):
        self._config = config

    def critique(
        self,
        image_b64: str,
        user_prompt: str,
        layer_plan: Optional[LayerPlan] = None,
    ) -> CritiqueReport:
        """Score an image against the original prompt and plan."""
        t0 = time.time()
        report: Optional[CritiqueReport] = None

        context_parts = [f"Original prompt: {user_prompt}"]
        if layer_plan:
            context_parts.append(f"Scene summary: {layer_plan.scene_summary}")
            context_parts.append(f"Style tags: {', '.join(layer_plan.style_tags)}")
        context = "\n".join(context_parts)

        for model_name in self._config.vision_model_priority:
            try:
                report = self._call_model(model_name, image_b64, context)
                if report:
                    report.model_used = model_name
                    break
            except Exception as e:
                logger.warning("[CritiqueService] %s failed: %s", model_name, e)

        if not report:
            logger.warning("[CritiqueService] All models failed, returning default")
            report = CritiqueReport(
                anatomy_score=5, face_score=5, hands_score=5,
                composition_score=5, color_score=5, style_score=5,
                background_score=5, model_used="fallback",
            )

        report.latency_ms = (time.time() - t0) * 1000
        return report

    # ── Private dispatch ──────────────────────────────────────────────

    def _call_model(
        self, model_name: str, image_b64: str, context: str,
    ) -> Optional[CritiqueReport]:
        if model_name.startswith("gemini"):
            return self._gemini(model_name, image_b64, context)
        elif model_name.startswith("gpt"):
            return self._openai(model_name, image_b64, context)
        return None

    def _gemini(
        self, model_name: str, image_b64: str, context: str,
    ) -> Optional[CritiqueReport]:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("No GEMINI_API_KEY set")

        raw_img = image_b64.split(",", 1)[-1] if "," in image_b64 else image_b64
        parts = [
            {"text": _CRITIQUE_SYSTEM_PROMPT + "\n\n" + context},
            {"inline_data": {"mime_type": "image/png", "data": raw_img}},
        ]
        payload = {"contents": [{"parts": parts}], "generationConfig": {
            "temperature": 0.1, "maxOutputTokens": 800,
        }}

        with httpx.Client(timeout=30) as client:
            resp = client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}",
                json=payload,
            )
            resp.raise_for_status()
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            return self._parse(text)

    def _openai(
        self, model_name: str, image_b64: str, context: str,
    ) -> Optional[CritiqueReport]:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("No OPENAI_API_KEY set")

        raw_img = image_b64.split(",", 1)[-1] if "," in image_b64 else image_b64
        user_content = [
            {"type": "text", "text": context},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{raw_img}", "detail": "low"}},
        ]
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": _CRITIQUE_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.1,
            "max_tokens": 800,
        }

        with httpx.Client(timeout=30) as client:
            resp = client.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
            )
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"]
            return self._parse(text)

    def _parse(self, text: str) -> Optional[CritiqueReport]:
        """Parse LLM output into CritiqueReport."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("[CritiqueService] Failed to parse JSON: %.100s…", cleaned)
            return None

        return CritiqueReport(
            anatomy_score=int(data.get("anatomy_score", 5)),
            anatomy_issues=data.get("anatomy_issues", []),
            face_score=int(data.get("face_score", 5)),
            face_issues=data.get("face_issues", []),
            hands_score=int(data.get("hands_score", 5)),
            hand_issues=data.get("hand_issues", []),
            composition_score=int(data.get("composition_score", 5)),
            composition_issues=data.get("composition_issues", []),
            color_score=int(data.get("color_score", 5)),
            color_issues=data.get("color_issues", []),
            style_score=int(data.get("style_score", 5)),
            style_drift=data.get("style_drift", []),
            background_score=int(data.get("background_score", 5)),
            background_issues=data.get("background_issues", []),
            retry_recommendation=bool(data.get("retry_recommendation", False)),
            prompt_patch=data.get("prompt_patch", []),
            control_patch=data.get("control_patch", {}),
        )
