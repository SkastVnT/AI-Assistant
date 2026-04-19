"""
CritiqueAgent — Stage 6: Vision-based quality scoring of pipeline output.

Scores the output image against the original prompt using vision AI.
Returns structured CritiqueResult JSON — no hidden reasoning text.
Triggers refine loop if quality is below threshold.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Optional

from ..config import AnimePipelineConfig
from ..schemas import (
    AnimePipelineJob,
    AnimePipelineStatus,
    CritiqueResult,
    CritiqueDimension,
)

logger = logging.getLogger(__name__)

_CRITIQUE_SYSTEM_PROMPT = """\
You are a strict quality critic for an anime image generation pipeline.
Evaluate the generated image on 11 dimensions using integer scores 0-10.
Be STRICT — only give 9 or 10 for truly excellent quality.

Return ONLY a valid JSON object — no markdown, no explanation:
{{
  "anatomy_score": <int 0-10>,
  "anatomy_issues": ["issue"],
  "face_score": <int 0-10>,
  "face_issues": ["issue"],
  "eye_consistency_score": <int 0-10>,
  "eye_reference_match_pct": <float 0-100>,
  "eye_issues": ["issue"],
  "hands_score": <int 0-10>,
  "hand_issues": ["issue"],
  "clothing_score": <int 0-10>,
  "clothing_issues": ["issue"],
  "composition_score": <int 0-10>,
  "composition_issues": ["issue"],
  "color_score": <int 0-10>,
  "color_issues": ["issue"],
  "style_score": <int 0-10>,
  "style_drift": ["issue"],
  "background_score": <int 0-10>,
  "background_issues": ["issue"],
  "accessories_score": <int 0-10>,
  "accessories_issues": ["issue"],
  "pose_score": <int 0-10>,
  "pose_issues": ["issue"],
  "retry_recommendation": <bool>,
  "prompt_patch": ["add: <tag>", "remove: <tag>"]
}}

Scoring guide (0=terrible, 5=acceptable, 7=good, 9=excellent, 10=perfect):
- anatomy_score: body proportions, limb structure, no extra limbs
- face_score: facial accuracy, expression, symmetry — MOST important dimension. Check jawline, mouth, nose, and overall face shape. Score below 7 if face looks flat, asymmetric, or has artifacts
- eye_consistency_score: CRITICAL — check eye symmetry, correct eye colors, iris detail, pupil shape, gaze direction, catchlight consistency. For heterochromia characters both eye colors MUST be correct and distinct. Score below 6 if eyes look wrong, blurry, or mismatched
- eye_reference_match_pct: CRITICAL — if reference image(s) are provided, compare the eye region of the generated image against the reference. Measure: correct eye color match, shape match, special features (heterochromia, glow, slit pupils). Return 0-100 float (100 = perfect match). If no reference images were provided, return 0.
- hands_score: correct finger count and hand form
- clothing_score: clothing matches the request, no artifacts
- composition_score: framing, balance, focal point
- color_score: palette consistency, lighting and shadows, vibrant colors
- style_score: anime art-style consistency with the request
- background_score: background detail, no artifacts
- accessories_score: required accessories present and correct
- pose_score: pose matches the request

retry_recommendation: set true if weighted overall < {threshold}/10 OR if face_score < 8 OR if eye_consistency_score < 8 OR if eye_reference_match_pct > 0 and eye_reference_match_pct < 95
prompt_patch: 1-3 prompt fixes as "add: <tag>" or "remove: <tag>"; empty list if passed

Rules: integers only for scores, empty lists when no issues, strict JSON.
Be particularly harsh on eyes and face — these are the most important features in anime art.
"""

_CRITIQUE_USER_TEMPLATE = """\
User request: {user_prompt}
{identity_context}
{reference_context}
Quality threshold: {threshold}/10. Critique this anime image and return the JSON.
Focus especially on eye quality, eye color accuracy, and face details.
Eye reference match threshold: 95% — if reference images were provided, eyes MUST score >=95 in eye_reference_match_pct to pass.
"""


class CritiqueAgent:
    """Vision-based quality scoring of pipeline output."""

    def __init__(self, config: AnimePipelineConfig):
        self._config = config
        self._detected_character: Optional[str] = None
        self._research_critique_context: Optional[str] = None

    def set_character_context(self, danbooru_tag: Optional[str]) -> None:
        """Set the detected character tag for identity-aware critique."""
        self._detected_character = danbooru_tag

    def set_research_context(self, critique_context: str) -> None:
        """Set pre-built critique context from character research."""
        self._research_critique_context = critique_context

    def execute(self, job: AnimePipelineJob) -> AnimePipelineJob:
        """Score the current pipeline output."""
        job.status = AnimePipelineStatus.CRITIQUING
        t0 = time.time()

        # Build identity context for character-aware critique
        # Prefer research context (richer) over legacy character_references
        identity_context = ""
        if self._research_critique_context:
            identity_context = self._research_critique_context
        elif self._detected_character:
            try:
                from ..character_references import build_identity_critique_context
                identity_context = build_identity_critique_context(self._detected_character)
            except Exception as e:
                logger.warning("[Critique] Could not load character identity: %s", e)

        # Get latest output image
        output_b64 = self._get_latest_output(job)
        if not output_b64:
            logger.warning("[Critique] No output image to critique")
            job.critique_results.append(CritiqueResult(
                anatomy_score=5, face_score=5, hands_score=5,
                composition_score=5, color_score=5, style_score=5,
                background_score=5,
                model_used="skipped",
            ))
            job.mark_stage("critique", 0.0)
            return job

        # Collect reference images for eye comparison (max 2 to stay within token limits)
        reference_images: list[str] = []
        if job.reference_images_b64:
            reference_images = job.reference_images_b64[:2]

        # Try each vision model
        result = None
        for model_name in self._config.vision_model_priority:
            try:
                result = self._critique_with_model(
                    model_name, job.user_prompt, output_b64,
                    identity_context=identity_context,
                    reference_images=reference_images,
                )
                if result:
                    result.model_used = model_name
                    break
            except Exception as e:
                logger.warning("[Critique] %s failed: %s", model_name, e)

        if not result:
            logger.warning("[Critique] All models failed, auto-passing")
            result = CritiqueResult(
                anatomy_score=5, face_score=5, hands_score=5,
                composition_score=5, color_score=5, style_score=5,
                background_score=5,
                model_used="auto_pass",
            )

        latency = (time.time() - t0) * 1000
        result.latency_ms = latency
        job.critique_results.append(result)
        job.mark_stage("critique", latency)

        logger.info(
            "[Critique] Score=%.2f eye_ref=%.0f%% passed=%s via %s in %.0fms",
            result.overall_score, result.eye_reference_match_pct,
            result.passed, result.model_used, latency,
        )
        return job

    def _get_latest_output(self, job: AnimePipelineJob) -> Optional[str]:
        """Get the most recent beauty/composition image."""
        for img in reversed(job.intermediates):
            if img.stage in ("beauty_pass", "composition_pass"):
                return img.image_b64
        return None

    def _critique_with_model(
        self,
        model_name: str,
        user_prompt: str,
        image_b64: str,
        identity_context: str = "",
        reference_images: Optional[list[str]] = None,
    ) -> Optional[CritiqueResult]:
        """Run critique using a vision model."""
        if model_name.startswith("gemini"):
            return self._critique_gemini(model_name, user_prompt, image_b64, identity_context, reference_images)
        elif model_name.startswith("gpt"):
            return self._critique_openai(model_name, user_prompt, image_b64, identity_context, reference_images)
        return None

    def _critique_gemini(
        self, model_name: str, user_prompt: str, image_b64: str,
        identity_context: str = "",
        reference_images: Optional[list[str]] = None,
    ) -> Optional[CritiqueResult]:
        """Critique using Gemini vision."""
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("No GEMINI_API_KEY")

        import httpx

        threshold_10 = round(self._config.quality_threshold * 10, 1)
        system = _CRITIQUE_SYSTEM_PROMPT.format(threshold=threshold_10)

        # Build reference context message
        ref_list = reference_images or []
        reference_context = (
            f"Reference images ({len(ref_list)}) are provided above — compare eye region "
            f"against reference and score eye_reference_match_pct 0-100."
            if ref_list else ""
        )

        user_msg = _CRITIQUE_USER_TEMPLATE.format(
            user_prompt=user_prompt, threshold=threshold_10,
            identity_context=identity_context,
            reference_context=reference_context,
        )

        raw_b64 = image_b64.split(",", 1)[-1] if "," in image_b64 else image_b64

        # Build parts: [system+user text] + [reference images] + [generated image]
        parts: list[dict] = [{"text": system + "\n\n" + user_msg}]

        if ref_list:
            parts.append({"text": "REFERENCE IMAGE(S) — use these to compare eye colors, shape, and features:"})
            for ref_b64 in ref_list:
                raw_ref = ref_b64.split(",", 1)[-1] if "," in ref_b64 else ref_b64
                parts.append({"inline_data": {"mime_type": "image/png", "data": raw_ref}})
            parts.append({"text": "GENERATED IMAGE to critique (compare eyes against reference above):"})

        parts.append({"inline_data": {"mime_type": "image/png", "data": raw_b64}})

        model_map = {
            "gemini-2.0-flash": "gemini-2.0-flash",
            "gemini-2-0-flash": "gemini-2.0-flash",
        }
        api_model = model_map.get(model_name, model_name)

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{api_model}:generateContent?key={api_key}"
        )

        with httpx.Client(timeout=30) as client:
            resp = client.post(url, json={
                "contents": [{"parts": parts}],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 700,
                    "responseMimeType": "application/json",
                },
            })
            resp.raise_for_status()

        data = resp.json()
        text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "{}")
        )
        return self._parse_critique(text)

    def _critique_openai(
        self, model_name: str, user_prompt: str, image_b64: str,
        identity_context: str = "",
        reference_images: Optional[list[str]] = None,
    ) -> Optional[CritiqueResult]:
        """Critique using OpenAI vision."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("No OPENAI_API_KEY")

        import httpx

        threshold_10 = round(self._config.quality_threshold * 10, 1)
        system = _CRITIQUE_SYSTEM_PROMPT.format(threshold=threshold_10)

        ref_list = reference_images or []
        reference_context = (
            f"Reference images ({len(ref_list)}) are provided — compare eye region "
            f"against reference and score eye_reference_match_pct 0-100."
            if ref_list else ""
        )

        user_msg = _CRITIQUE_USER_TEMPLATE.format(
            user_prompt=user_prompt, threshold=threshold_10,
            identity_context=identity_context,
            reference_context=reference_context,
        )
        raw_b64 = image_b64.split(",", 1)[-1] if "," in image_b64 else image_b64

        # Build content: text + reference images + generated image
        content: list[dict] = [{"type": "text", "text": user_msg}]
        if ref_list:
            content.append({"type": "text", "text": "REFERENCE IMAGE(S) — compare eye colors, shape, and features:"})
            for ref_b64 in ref_list:
                raw_ref = ref_b64.split(",", 1)[-1] if "," in ref_b64 else ref_b64
                content.append({"type": "image_url", "image_url": {
                    "url": f"data:image/png;base64,{raw_ref}", "detail": "low",
                }})
            content.append({"type": "text", "text": "GENERATED IMAGE to critique (compare eyes against reference):"})
        content.append({"type": "image_url", "image_url": {
            "url": f"data:image/png;base64,{raw_b64}", "detail": "low",
        }})

        with httpx.Client(timeout=30) as client:
            resp = client.post(
                "https://api.openai.com/v1/chat/completions",
                json={
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": content},
                    ],
                    "max_tokens": 700,
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                },
                headers={"Authorization": f"Bearer {api_key}"},
            )
            resp.raise_for_status()

        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        return self._parse_critique(text)

    def _parse_critique(self, raw_text: str) -> Optional[CritiqueResult]:
        """Parse JSON critique response into CritiqueReport."""
        try:
            text = raw_text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1]
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0]
            text = text.strip()

            obj = json.loads(text)

            # Support both old (overall_score 0-1) and new (per-dimension 0-10) formats
            if "anatomy_score" in obj:
                # New format
                return CritiqueResult(
                    anatomy_score=int(obj.get("anatomy_score", 5)),
                    anatomy_issues=obj.get("anatomy_issues", []),
                    face_score=int(obj.get("face_score", 5)),
                    face_issues=obj.get("face_issues", []),
                    eye_consistency_score=int(obj.get("eye_consistency_score", 0)),
                    eye_reference_match_pct=float(obj.get("eye_reference_match_pct", 0.0)),
                    eye_issues=obj.get("eye_issues", []),
                    hands_score=int(obj.get("hands_score", 5)),
                    hand_issues=obj.get("hand_issues", []),
                    clothing_score=int(obj.get("clothing_score", 0)),
                    clothing_issues=obj.get("clothing_issues", []),
                    composition_score=int(obj.get("composition_score", 5)),
                    composition_issues=obj.get("composition_issues", []),
                    color_score=int(obj.get("color_score", 5)),
                    color_issues=obj.get("color_issues", []),
                    style_score=int(obj.get("style_score", 5)),
                    style_drift=obj.get("style_drift", []),
                    background_score=int(obj.get("background_score", 5)),
                    background_issues=obj.get("background_issues", []),
                    accessories_score=int(obj.get("accessories_score", 0)),
                    accessories_issues=obj.get("accessories_issues", []),
                    pose_score=int(obj.get("pose_score", 0)),
                    pose_issues=obj.get("pose_issues", []),
                    retry_recommendation=bool(obj.get("retry_recommendation", False)),
                    prompt_patch=obj.get("prompt_patch", []),
                    control_patch=obj.get("control_patch", {}),
                )
            else:
                # Old format — convert overall_score (0-1) to per-dimension (0-10)
                overall = float(obj.get("overall_score", 0.5))
                score_10 = int(overall * 10)
                suggestions = obj.get("improvement_suggestions", [])
                return CritiqueResult(
                    anatomy_score=score_10,
                    face_score=score_10,
                    hands_score=score_10,
                    composition_score=score_10,
                    color_score=score_10,
                    style_score=score_10,
                    background_score=score_10,
                    retry_recommendation=not obj.get("passed", overall >= self._config.quality_threshold),
                    prompt_patch=suggestions,
                )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning("[Critique] Failed to parse response: %s", e)
            return None
