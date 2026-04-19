"""
image_pipeline.anime_pipeline.vision_service — Image analysis, captioning, and comparison.

Public API:
  - analyze_reference_images(images, user_prompt) → VisionAnalysis
  - analyze_intermediate_output(image, user_prompt, stage) → VisionAnalysis
  - compare_target_vs_output(target_plan, output_analysis) → DiscrepancyReport
  - build_prompt_patch_from_analysis(analysis, plan) → list[str]

Primary mode: Gemini / OpenAI vision (cloud LLM).
Optional: Florence-2, JoyCaption when configured locally.

All analysis stored as structured JSON — no hidden reasoning exposed.
Includes LRU cache for repeated image analysis and graceful fallback.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import threading
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

from .config import AnimePipelineConfig
from .schemas import LayerPlan, VisionAnalysis
from . import vision_prompts as prompts

logger = logging.getLogger(__name__)

_CACHE_MAX = 64


# ═══════════════════════════════════════════════════════════════════════
# Discrepancy report — returned by compare_target_vs_output
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class DiscrepancyReport:
    """Structured comparison between a target LayerPlan and a generated output."""
    match_score: float = 0.0
    subject_match: bool = True
    pose_match: bool = True
    color_match: bool = True
    background_match: bool = True
    missing_elements: list[str] = field(default_factory=list)
    extra_elements: list[str] = field(default_factory=list)
    identity_drift: list[str] = field(default_factory=list)
    style_drift: list[str] = field(default_factory=list)
    prompt_corrections: list[str] = field(default_factory=list)
    control_corrections: dict[str, float] = field(default_factory=dict)
    severity: str = "none"  # none | minor | major | critical
    model_used: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_score": self.match_score,
            "subject_match": self.subject_match,
            "pose_match": self.pose_match,
            "color_match": self.color_match,
            "background_match": self.background_match,
            "missing_elements": self.missing_elements,
            "extra_elements": self.extra_elements,
            "identity_drift": self.identity_drift,
            "style_drift": self.style_drift,
            "prompt_corrections": self.prompt_corrections,
            "control_corrections": self.control_corrections,
            "severity": self.severity,
            "model_used": self.model_used,
            "latency_ms": self.latency_ms,
        }


# ═══════════════════════════════════════════════════════════════════════
# VisionService
# ═══════════════════════════════════════════════════════════════════════

class VisionService:
    """Image analysis via vision LLMs with caching and fallback.

    Model priority (configurable):
      1. Gemini 2.0 Flash (fast, free tier)
      2. GPT-4o-mini (cheap fallback)
      3. GPT-4o (best, expensive)

    Optional local modes:
      - Florence-2: set FLORENCE2_ENDPOINT env var
      - JoyCaption: set JOYCAPTION_ENDPOINT env var
    """

    def __init__(self, config: AnimePipelineConfig):
        self._config = config
        self._cache: dict[str, VisionAnalysis] = {}
        self._cache_lock = threading.Lock()

    # ── Public API ────────────────────────────────────────────────────

    def analyze_reference_images(
        self,
        images_b64: list[str],
        user_prompt: str = "",
        language: str = "en",
    ) -> VisionAnalysis:
        """Analyze one or more reference images.

        Merges analysis across multiple images conservatively,
        preserving identity cues from the first image.
        """
        if not images_b64 and not user_prompt:
            return self._prompt_only(user_prompt)

        # Check cache
        cache_key = self._cache_key(user_prompt, images_b64)
        cached = self._cache_get(cache_key)
        if cached:
            logger.debug("[VisionService] Cache hit for %s", cache_key[:16])
            return cached

        result = self._run_analysis(
            system_prompt=prompts.FULL_ANALYSIS_SYSTEM,
            user_msg=prompts.full_analysis_user(
                user_prompt, len(images_b64),
            ),
            images_b64=images_b64,
        )
        self._cache_put(cache_key, result)
        return result

    def analyze_intermediate_output(
        self,
        image_b64: str,
        user_prompt: str = "",
        stage: str = "",
    ) -> VisionAnalysis:
        """Analyze a pipeline intermediate image for critique or comparison."""
        return self._run_analysis(
            system_prompt=prompts.FULL_ANALYSIS_SYSTEM,
            user_msg=prompts.full_analysis_user(
                user_prompt, 1, stage=stage,
            ),
            images_b64=[image_b64],
        )

    def compare_target_vs_output(
        self,
        target_plan: LayerPlan,
        output_analysis: VisionAnalysis,
        output_image_b64: str = "",
        user_prompt: str = "",
    ) -> DiscrepancyReport:
        """Compare the desired LayerPlan against a generated output.

        If output_image_b64 is provided, the vision model re-analyzes the
        image alongside the plan. Otherwise, a fast heuristic comparison
        is done using the existing output_analysis.
        """
        # If we have the image, do a full LLM-based comparison
        if output_image_b64:
            return self._llm_compare(
                target_plan, output_image_b64, user_prompt,
            )

        # Fast heuristic: compare fields from plan vs analysis
        return self._heuristic_compare(target_plan, output_analysis)

    def build_prompt_patch_from_analysis(
        self,
        analysis: VisionAnalysis,
        plan: LayerPlan,
    ) -> list[str]:
        """Generate prompt correction suggestions from a discrepancy.

        Compares what the analysis found vs what the plan expects.
        Returns a list of prompt patch strings to add/adjust.
        """
        patches: list[str] = []

        # Missing details → emphasize them
        for detail in analysis.missing_details:
            patches.append(f"(({detail}:1.3))")

        # Identity drift check: subjects mismatch
        plan_subjects_lower = {s.lower() for s in plan.subject_list}
        analysis_subjects_lower = {s.lower() for s in analysis.subjects}
        missing_subjects = plan_subjects_lower - analysis_subjects_lower
        for subj in missing_subjects:
            patches.append(f"(({subj}:1.2))")

        # Color drift: dominant colors in plan but not in output
        plan_colors = {c.lower() for c in plan.palette}
        analysis_colors = {c.lower() for c in analysis.dominant_colors}
        missing_colors = plan_colors - analysis_colors
        for color in missing_colors:
            patches.append(f"{color} color scheme")

        # Quality risks → add to negative
        if analysis.quality_risks:
            patches.append(
                f"NEGATIVE_ADD: {', '.join(analysis.quality_risks)}"
            )

        return patches

    # Backward-compat aliases for existing callers
    def analyze(
        self,
        user_prompt: str,
        images_b64: list[str] | None = None,
        language: str = "en",
    ) -> VisionAnalysis:
        """Backward-compatible entry point."""
        return self.analyze_reference_images(
            images_b64=images_b64 or [],
            user_prompt=user_prompt,
            language=language,
        )

    def analyze_intermediate(
        self,
        user_prompt: str,
        image_b64: str,
        stage: str,
    ) -> VisionAnalysis:
        """Backward-compatible intermediate analysis."""
        return self.analyze_intermediate_output(
            image_b64=image_b64,
            user_prompt=user_prompt,
            stage=stage,
        )

    # ── Core analysis runner ──────────────────────────────────────────

    def _run_analysis(
        self,
        system_prompt: str,
        user_msg: str,
        images_b64: list[str],
    ) -> VisionAnalysis:
        """Try each model in priority order. Falls back to prompt-only."""
        t0 = time.time()
        analysis: Optional[VisionAnalysis] = None

        # Try optional local models first
        if not analysis:
            analysis = self._try_florence2(user_msg, images_b64)
        if not analysis and self._joycaption_available():
            analysis = self._try_joycaption(user_msg, images_b64)

        # Cloud LLM fallback chain
        if not analysis:
            for model_name in self._config.vision_model_priority:
                try:
                    analysis = self._call_cloud_model(
                        model_name, system_prompt, user_msg, images_b64,
                    )
                    if analysis:
                        analysis.model_used = model_name
                        break
                except Exception as e:
                    logger.warning(
                        "[VisionService] %s failed: %s", model_name, e,
                    )

        if not analysis:
            logger.warning(
                "[VisionService] All models failed, prompt-only fallback",
            )
            analysis = self._prompt_only(user_msg)

        analysis.latency_ms = (time.time() - t0) * 1000
        return analysis

    # ── Cloud model dispatch ──────────────────────────────────────────

    def _call_cloud_model(
        self,
        model_name: str,
        system_prompt: str,
        user_msg: str,
        images_b64: list[str],
    ) -> Optional[VisionAnalysis]:
        if model_name.startswith("gemini"):
            return self._gemini(model_name, system_prompt, user_msg, images_b64)
        elif model_name.startswith("gpt"):
            return self._openai(model_name, system_prompt, user_msg, images_b64)
        else:
            logger.warning("[VisionService] Unknown model: %s", model_name)
            return None

    def _gemini(
        self,
        model_name: str,
        system_prompt: str,
        user_msg: str,
        images_b64: list[str],
    ) -> Optional[VisionAnalysis]:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("No GEMINI_API_KEY set")

        parts: list[dict] = [{"text": system_prompt + "\n\n" + user_msg}]
        for img in images_b64[:4]:
            raw = img.split(",", 1)[-1] if "," in img else img
            parts.append({
                "inline_data": {"mime_type": "image/png", "data": raw},
            })

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": self._config.vision_temperature,
                "maxOutputTokens": self._config.vision_max_tokens,
            },
        }

        with httpx.Client(timeout=30) as client:
            resp = client.post(
                f"https://generativelanguage.googleapis.com/v1beta/"
                f"models/{model_name}:generateContent?key={api_key}",
                json=payload,
            )
            resp.raise_for_status()
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            return self._parse_vision(text)

    def _openai(
        self,
        model_name: str,
        system_prompt: str,
        user_msg: str,
        images_b64: list[str],
    ) -> Optional[VisionAnalysis]:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("No OPENAI_API_KEY set")

        user_content: list[dict] = [{"type": "text", "text": user_msg}]
        for img in images_b64[:4]:
            raw = img.split(",", 1)[-1] if "," in img else img
            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{raw}",
                    "detail": "low",
                },
            })

        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": self._config.vision_temperature,
            "max_tokens": self._config.vision_max_tokens,
        }

        with httpx.Client(timeout=30) as client:
            resp = client.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
            )
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"]
            return self._parse_vision(text)

    # ── Optional local models ─────────────────────────────────────────

    def _try_florence2(
        self, user_msg: str, images_b64: list[str],
    ) -> Optional[VisionAnalysis]:
        """Try Florence-2 endpoint if FLORENCE2_ENDPOINT is set."""
        endpoint = os.getenv("FLORENCE2_ENDPOINT")
        if not endpoint or not images_b64:
            return None

        try:
            raw = images_b64[0]
            if "," in raw:
                raw = raw.split(",", 1)[-1]
            payload = {
                "image": raw,
                "task": "<CAPTION>",
                "text": user_msg[:200],
            }
            with httpx.Client(timeout=30) as client:
                resp = client.post(endpoint, json=payload)
                resp.raise_for_status()
                data = resp.json()

            caption = data.get("result", data.get("caption", ""))
            if not caption:
                return None

            logger.info("[VisionService] Florence-2 returned caption")
            return VisionAnalysis(
                caption_short=caption[:200],
                caption_detailed=caption,
                subjects=[caption.split(",")[0].strip()] if caption else [],
                confidence=0.7,
                model_used="florence-2",
            )
        except Exception as e:
            logger.debug("[VisionService] Florence-2 unavailable: %s", e)
            return None

    def _joycaption_available(self) -> bool:
        return bool(os.getenv("JOYCAPTION_ENDPOINT"))

    def _try_joycaption(
        self, user_msg: str, images_b64: list[str],
    ) -> Optional[VisionAnalysis]:
        """Try JoyCaption endpoint for richer diffusion-oriented captions."""
        endpoint = os.getenv("JOYCAPTION_ENDPOINT")
        if not endpoint or not images_b64:
            return None

        try:
            raw = images_b64[0]
            if "," in raw:
                raw = raw.split(",", 1)[-1]
            payload = {"image": raw, "prompt": user_msg[:200]}
            with httpx.Client(timeout=45) as client:
                resp = client.post(endpoint, json=payload)
                resp.raise_for_status()
                data = resp.json()

            caption = data.get("caption", data.get("result", ""))
            tags = data.get("tags", [])
            if not caption:
                return None

            logger.info("[VisionService] JoyCaption returned rich caption")
            return VisionAnalysis(
                caption_short=caption[:200],
                caption_detailed=caption,
                subjects=[caption.split(",")[0].strip()] if caption else [],
                anime_tags=tags,
                confidence=0.75,
                model_used="joycaption",
            )
        except Exception as e:
            logger.debug("[VisionService] JoyCaption unavailable: %s", e)
            return None

    # ── LLM-based discrepancy comparison ──────────────────────────────

    def _llm_compare(
        self,
        target_plan: LayerPlan,
        output_image_b64: str,
        user_prompt: str,
    ) -> DiscrepancyReport:
        """Use vision LLM to compare plan vs generated image."""
        t0 = time.time()
        user_msg = prompts.discrepancy_user(
            user_prompt=user_prompt,
            plan_summary=target_plan.scene_summary,
            plan_subjects=target_plan.subject_list,
            plan_palette=target_plan.palette,
            plan_pose=target_plan.pose,
        )

        report = DiscrepancyReport()
        for model_name in self._config.vision_model_priority:
            try:
                parsed = self._call_cloud_model_raw(
                    model_name,
                    prompts.DISCREPANCY_SYSTEM,
                    user_msg,
                    [output_image_b64],
                )
                if parsed:
                    report = self._parse_discrepancy(parsed)
                    report.model_used = model_name
                    break
            except Exception as e:
                logger.warning(
                    "[VisionService] Discrepancy %s failed: %s", model_name, e,
                )

        if not report.model_used:
            # Fall back to heuristic — analyze the image first
            analysis = self.analyze_intermediate_output(
                output_image_b64, user_prompt,
            )
            report = self._heuristic_compare(target_plan, analysis)

        report.latency_ms = (time.time() - t0) * 1000
        return report

    def _call_cloud_model_raw(
        self,
        model_name: str,
        system_prompt: str,
        user_msg: str,
        images_b64: list[str],
    ) -> Optional[dict]:
        """Call cloud model and return parsed JSON dict (not VisionAnalysis)."""
        if model_name.startswith("gemini"):
            return self._gemini_raw(
                model_name, system_prompt, user_msg, images_b64,
            )
        elif model_name.startswith("gpt"):
            return self._openai_raw(
                model_name, system_prompt, user_msg, images_b64,
            )
        return None

    def _gemini_raw(
        self, model_name: str, system_prompt: str,
        user_msg: str, images_b64: list[str],
    ) -> Optional[dict]:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("No GEMINI_API_KEY set")

        parts: list[dict] = [{"text": system_prompt + "\n\n" + user_msg}]
        for img in images_b64[:4]:
            raw = img.split(",", 1)[-1] if "," in img else img
            parts.append({
                "inline_data": {"mime_type": "image/png", "data": raw},
            })

        with httpx.Client(timeout=30) as client:
            resp = client.post(
                f"https://generativelanguage.googleapis.com/v1beta/"
                f"models/{model_name}:generateContent?key={api_key}",
                json={
                    "contents": [{"parts": parts}],
                    "generationConfig": {
                        "temperature": self._config.vision_temperature,
                        "maxOutputTokens": self._config.vision_max_tokens,
                    },
                },
            )
            resp.raise_for_status()
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            return self._strip_and_parse(text)

    def _openai_raw(
        self, model_name: str, system_prompt: str,
        user_msg: str, images_b64: list[str],
    ) -> Optional[dict]:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("No OPENAI_API_KEY set")

        user_content: list[dict] = [{"type": "text", "text": user_msg}]
        for img in images_b64[:4]:
            raw = img.split(",", 1)[-1] if "," in img else img
            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{raw}",
                    "detail": "low",
                },
            })

        with httpx.Client(timeout=30) as client:
            resp = client.post(
                "https://api.openai.com/v1/chat/completions",
                json={
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    "temperature": self._config.vision_temperature,
                    "max_tokens": self._config.vision_max_tokens,
                },
                headers={"Authorization": f"Bearer {api_key}"},
            )
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"]
            return self._strip_and_parse(text)

    # ── Heuristic comparison (no LLM call) ────────────────────────────

    def _heuristic_compare(
        self,
        plan: LayerPlan,
        analysis: VisionAnalysis,
    ) -> DiscrepancyReport:
        """Fast field-by-field comparison without an LLM call."""
        report = DiscrepancyReport(model_used="heuristic")

        # Subject match
        plan_subj = {s.lower() for s in plan.subject_list}
        analysis_subj = {s.lower() for s in analysis.subjects}
        report.subject_match = bool(plan_subj & analysis_subj) if plan_subj else True
        report.missing_elements = list(plan_subj - analysis_subj)

        # Pose match
        if plan.pose and analysis.pose:
            report.pose_match = (
                plan.pose.lower() in analysis.pose.lower()
                or analysis.pose.lower() in plan.pose.lower()
            )

        # Color match
        plan_colors = {c.lower() for c in plan.palette}
        analysis_colors = {c.lower() for c in analysis.dominant_colors}
        report.color_match = bool(
            plan_colors & analysis_colors
        ) if plan_colors else True

        # Background match
        plan_bg = plan.background_plan.lower() if plan.background_plan else ""
        analysis_bg_str = " ".join(analysis.background_elements).lower()
        report.background_match = (
            not plan_bg or any(
                word in analysis_bg_str
                for word in plan_bg.split()[:3]
            )
        )

        # Compute match score
        matches = sum([
            report.subject_match,
            report.pose_match,
            report.color_match,
            report.background_match,
        ])
        report.match_score = round(matches / 4.0, 2)

        # Severity
        if report.match_score >= 0.75:
            report.severity = "none" if report.match_score == 1.0 else "minor"
        elif report.match_score >= 0.5:
            report.severity = "major"
        else:
            report.severity = "critical"

        # Identity drift
        if not report.subject_match:
            report.identity_drift = [
                f"Expected {s} not found" for s in report.missing_elements
            ]

        return report

    # ── Parsing helpers ───────────────────────────────────────────────

    def _strip_and_parse(self, text: str) -> Optional[dict]:
        """Strip markdown fences and parse JSON."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning(
                "[VisionService] Failed to parse JSON: %.100s…", cleaned,
            )
            return None

    def _parse_vision(self, text: str) -> Optional[VisionAnalysis]:
        """Parse LLM output into VisionAnalysis."""
        data = self._strip_and_parse(text)
        if not data:
            return None

        # Handle old field names from LLM responses
        subjects = data.get("subjects", [])
        if not subjects and data.get("subject_description"):
            subjects = [data["subject_description"]]

        bg_elements = data.get("background_elements", [])
        if not bg_elements and data.get("background_description"):
            bg_elements = [data["background_description"]]

        return VisionAnalysis(
            caption_short=data.get("caption_short", ""),
            caption_detailed=data.get("caption_detailed", ""),
            subjects=subjects,
            pose=data.get("pose", data.get("pose_description", "")),
            camera_angle=data.get("camera_angle", ""),
            framing=data.get("framing", ""),
            background_elements=bg_elements,
            dominant_colors=data.get(
                "dominant_colors", data.get("color_palette", []),
            ),
            anime_tags=data.get("anime_tags", []),
            quality_risks=data.get("quality_risks", []),
            missing_details=data.get("missing_details", []),
            identity_anchors=data.get("identity_anchors", []),
            suggested_negative=data.get("suggested_negative", ""),
            confidence=0.85,
        )

    def _parse_discrepancy(self, data: dict) -> DiscrepancyReport:
        """Parse LLM JSON into DiscrepancyReport."""
        return DiscrepancyReport(
            match_score=float(data.get("match_score", 0.0)),
            subject_match=bool(data.get("subject_match", True)),
            pose_match=bool(data.get("pose_match", True)),
            color_match=bool(data.get("color_match", True)),
            background_match=bool(data.get("background_match", True)),
            missing_elements=data.get("missing_elements", []),
            extra_elements=data.get("extra_elements", []),
            identity_drift=data.get("identity_drift", []),
            style_drift=data.get("style_drift", []),
            prompt_corrections=data.get("prompt_corrections", []),
            control_corrections=data.get("control_corrections", {}),
            severity=data.get("severity", "minor"),
        )

    def _prompt_only(self, user_prompt: str) -> VisionAnalysis:
        """Extract basic info from prompt text without calling any API."""
        return VisionAnalysis(
            caption_short=user_prompt[:200],
            caption_detailed=user_prompt,
            subjects=(
                [user_prompt.split(",")[0].strip()] if user_prompt else []
            ),
            confidence=0.3,
            model_used="prompt_only",
        )

    # ── LRU cache ─────────────────────────────────────────────────────

    def _cache_key(
        self, prompt: str, images_b64: list[str],
    ) -> str:
        """Deterministic hash from prompt + first 256 chars of each image."""
        h = hashlib.sha256()
        h.update(prompt.encode("utf-8", errors="replace"))
        for img in images_b64:
            h.update(img[:256].encode("utf-8", errors="replace"))
        return h.hexdigest()

    def _cache_get(self, key: str) -> Optional[VisionAnalysis]:
        with self._cache_lock:
            return self._cache.get(key)

    def _cache_put(self, key: str, value: VisionAnalysis) -> None:
        with self._cache_lock:
            if len(self._cache) >= _CACHE_MAX:
                # Evict oldest (first inserted)
                oldest = next(iter(self._cache))
                del self._cache[oldest]
            self._cache[key] = value

    def cache_clear(self) -> None:
        """Clear the analysis cache."""
        with self._cache_lock:
            self._cache.clear()
