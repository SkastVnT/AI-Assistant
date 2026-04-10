"""
image_pipeline.evaluator.scorer — LLM-as-judge scoring engine.

Scores images across 8 evaluation dimensions using a vision-capable LLM.
Supports three judge backends (tried in order):
    1. Qwen2.5-VL-72B on VPS (best, free)
    2. GPT-4o via API (fallback, $)
    3. GPT-4o-mini via API (cheap fallback)

Usage:
    scorer = Scorer()
    result = await scorer.score(job, output_image_path)
    # result => EvalResult with per-dimension scores, pass/fail, reasoning
"""

from __future__ import annotations

import base64
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml

from image_pipeline.job_schema import (
    EvalDimension,
    EvalResult,
    ImageJob,
)

logger = logging.getLogger(__name__)

# ── Config paths ──────────────────────────────────────────────────

_CONFIGS_DIR = Path(__file__).resolve().parent.parent.parent / "configs"
_PIPELINE_YAML = _CONFIGS_DIR / "pipeline.yaml"
_BENCHMARK_YAML = _CONFIGS_DIR / "benchmark_suite.yaml"


# ── Dimension → applicable intent mapping ─────────────────────────

_INTENT_DIMENSIONS: dict[str, list[str]] = {
    "t2i": [
        EvalDimension.INSTRUCTION_ADHERENCE,
        EvalDimension.DETAIL_HANDLING,
    ],
    "semantic_edit": [
        EvalDimension.INSTRUCTION_ADHERENCE,
        EvalDimension.SEMANTIC_EDIT,
        EvalDimension.IDENTITY_CONSISTENCY,
        EvalDimension.DETAIL_HANDLING,
    ],
    "multi_ref": [
        EvalDimension.INSTRUCTION_ADHERENCE,
        EvalDimension.MULTI_REF_QUALITY,
        EvalDimension.IDENTITY_CONSISTENCY,
    ],
    "multi_turn": [
        EvalDimension.INSTRUCTION_ADHERENCE,
        EvalDimension.MULTI_TURN_STABILITY,
        EvalDimension.IDENTITY_CONSISTENCY,
    ],
    "inpaint": [
        EvalDimension.INSTRUCTION_ADHERENCE,
        EvalDimension.SEMANTIC_EDIT,
        EvalDimension.DETAIL_HANDLING,
    ],
    "text_rendering": [
        EvalDimension.INSTRUCTION_ADHERENCE,
        EvalDimension.TEXT_RENDERING,
    ],
    "correction": [
        EvalDimension.CORRECTION_SUCCESS,
        EvalDimension.DETAIL_HANDLING,
    ],
}


# ── Scoring prompt template ───────────────────────────────────────

_JUDGE_SYSTEM_PROMPT = """\
You are a strict image quality evaluator for a production image generation system.
Score the output image along the specified dimensions.
For each dimension, provide:
  1. A score from 0.0 to 1.0 (two decimal places)
  2. A brief reasoning (one sentence)
Be objective. Compare against what the user instruction asked for.
If a reference image is provided, compare identity/style fidelity.
Return ONLY valid JSON with the structure shown below.
"""

_JUDGE_USER_TEMPLATE = """\
## Task
Evaluate this generated image against the user's instruction.

## User instruction
{instruction}

## Constraints
{constraints}

## Dimensions to evaluate
{dimensions_block}

## Scoring rubric (abbreviated)
{rubric_block}

## Output format (strict JSON)
{{
  "scores": {{
    "<dimension_name>": <float 0.0-1.0>,
    ...
  }},
  "reasoning": {{
    "<dimension_name>": "<one sentence>",
    ...
  }},
  "correction_targets": ["<region or aspect to fix>", ...],
  "correction_strategy": "<fill|semantic|composite|none>"
}}
"""


@dataclass
class JudgeConfig:
    """Configuration for a judge model backend."""
    name: str
    provider: str           # "vps" | "openai"
    endpoint: str           # URL or model identifier
    max_tokens: int = 1024
    temperature: float = 0.1


# ── Main scorer ───────────────────────────────────────────────────

class Scorer:
    """
    LLM-as-judge that scores pipeline outputs across 8 dimensions.

    Loads thresholds and rubrics from configs/pipeline.yaml and
    configs/benchmark_suite.yaml at initialization.
    """

    def __init__(
        self,
        pipeline_cfg_path: str | Path | None = None,
        benchmark_cfg_path: str | Path | None = None,
    ):
        self._pipeline_cfg = self._load_yaml(
            Path(pipeline_cfg_path or _PIPELINE_YAML)
        )
        self._benchmark_cfg = self._load_yaml(
            Path(benchmark_cfg_path or _BENCHMARK_YAML)
        )

        # Extract evaluation config
        eval_cfg = self._pipeline_cfg.get("evaluation", {})
        self._thresholds: dict[str, float] = {}
        self._weights: dict[str, float] = {}
        for dim_name, dim_cfg in eval_cfg.get("dimensions", {}).items():
            self._thresholds[dim_name] = float(dim_cfg.get("threshold", 0.7))
            self._weights[dim_name] = float(dim_cfg.get("weight", 1.0))

        # Build judge chain from config
        self._judge_chain: list[JudgeConfig] = []
        for model_name in eval_cfg.get("judge_models", []):
            self._judge_chain.append(self._make_judge_config(model_name))

        # Scoring rubric summaries for judge prompt
        self._rubric = self._benchmark_cfg.get("scoring_rubric", {})

        logger.info(
            "Scorer initialized: %d thresholds, %d judges, %d rubric dims",
            len(self._thresholds),
            len(self._judge_chain),
            len(self._rubric),
        )

    # ───────────────────────────────────────────────────────────────
    # Public API
    # ───────────────────────────────────────────────────────────────

    async def score(
        self,
        job: ImageJob,
        output_image_path: str | Path,
        source_image_path: str | Path | None = None,
        reference_paths: list[str | Path] | None = None,
        *,
        force_dimensions: list[str] | None = None,
    ) -> EvalResult:
        """
        Score the output image for a given job.

        Args:
            job:                The ImageJob being evaluated.
            output_image_path:  Path to the generated image.
            source_image_path:  Original source image (for edit comparisons).
            reference_paths:    Reference images used in composition.
            force_dimensions:   Override auto-detected dimensions.

        Returns:
            Populated EvalResult with scores, pass/fail, and correction hints.
        """
        start_ms = time.monotonic() * 1000

        # 1. Determine which dimensions to evaluate
        dimensions = force_dimensions or self._detect_dimensions(job)

        # 2. Build the judge prompt
        prompt = self._build_judge_prompt(job, dimensions)

        # 3. Encode images
        images = self._encode_images(
            output_image_path, source_image_path, reference_paths
        )

        # 4. Call judge (with fallback chain)
        raw_response, judge_model = await self._call_judge_chain(prompt, images)

        # 5. Parse response into EvalResult
        result = self._parse_judge_response(
            raw_response, dimensions, judge_model
        )

        result.eval_latency_ms = (time.monotonic() * 1000) - start_ms

        # 6. Apply thresholds and compute pass/fail
        result.thresholds = {
            dim: self._thresholds.get(dim, 0.7)
            for dim in dimensions
        }
        result.evaluate()

        logger.info(
            "Evaluation complete: passed=%s, overall=%.3f, judge=%s, latency=%.0fms",
            result.passed,
            result.overall_score,
            result.judge_model,
            result.eval_latency_ms,
        )

        return result

    def detect_dimensions(self, job: ImageJob) -> list[str]:
        """Public access to dimension detection logic."""
        return self._detect_dimensions(job)

    # ───────────────────────────────────────────────────────────────
    # Dimension detection
    # ───────────────────────────────────────────────────────────────

    def _detect_dimensions(self, job: ImageJob) -> list[str]:
        """
        Auto-detect which dimensions to evaluate based on job intent.

        Rules:
            - t2i → instruction_adherence + detail_handling
            - semantic_edit → + semantic_edit + identity_consistency
            - multi_ref → + multi_ref_quality + identity_consistency
            - multi_turn → + multi_turn_stability
            - text instructions → + text_rendering
            - correction round → + correction_success
        """
        intent = job.intent or "t2i"
        dims = list(_INTENT_DIMENSIONS.get(intent, [
            EvalDimension.INSTRUCTION_ADHERENCE,
            EvalDimension.DETAIL_HANDLING,
        ]))

        # Add text_rendering if instruction mentions text
        text_keywords = ["text", "sign", "letter", "write", "spell", "chữ", "viết"]
        instruction_lower = job.user_instruction.lower()
        if any(kw in instruction_lower for kw in text_keywords):
            if EvalDimension.TEXT_RENDERING not in dims:
                dims.append(EvalDimension.TEXT_RENDERING)

        # Add correction_success if this is a correction round
        if job.status and "correct" in str(job.status).lower():
            if EvalDimension.CORRECTION_SUCCESS not in dims:
                dims.append(EvalDimension.CORRECTION_SUCCESS)

        return dims

    # ───────────────────────────────────────────────────────────────
    # Prompt construction
    # ───────────────────────────────────────────────────────────────

    def _build_judge_prompt(
        self,
        job: ImageJob,
        dimensions: list[str],
    ) -> str:
        """Build the user message for the judge model."""
        # Constraints block
        constraints_parts: list[str] = []
        if job.must_keep:
            constraints_parts.append(f"MUST KEEP: {', '.join(job.must_keep)}")
        if job.may_change:
            constraints_parts.append(f"MAY CHANGE: {', '.join(job.may_change)}")
        if job.forbidden_changes:
            constraints_parts.append(f"FORBIDDEN: {', '.join(job.forbidden_changes)}")
        constraints = "\n".join(constraints_parts) or "None specified"

        # Dimensions block
        dim_lines: list[str] = []
        for dim in dimensions:
            rubric_entry = self._rubric.get(dim, {})
            desc = rubric_entry.get("description", dim)
            threshold = self._thresholds.get(dim, 0.7)
            dim_lines.append(f"- {dim}: {desc} (threshold={threshold})")
        dimensions_block = "\n".join(dim_lines)

        # Abbreviated rubric (only relevant dimensions)
        rubric_lines: list[str] = []
        for dim in dimensions:
            rubric_entry = self._rubric.get(dim, {})
            scale = rubric_entry.get("scale", {})
            if scale:
                rubric_lines.append(f"{dim}:")
                for range_key, label in scale.items():
                    rubric_lines.append(f"  {range_key}: {label}")
        rubric_block = "\n".join(rubric_lines) or "Use standard quality assessment."

        return _JUDGE_USER_TEMPLATE.format(
            instruction=job.user_instruction,
            constraints=constraints,
            dimensions_block=dimensions_block,
            rubric_block=rubric_block,
        )

    # ───────────────────────────────────────────────────────────────
    # Image encoding
    # ───────────────────────────────────────────────────────────────

    @staticmethod
    def _encode_images(
        output_path: str | Path,
        source_path: str | Path | None = None,
        reference_paths: list[str | Path] | None = None,
    ) -> list[dict[str, str]]:
        """
        Encode images as base64 for the judge model.

        Returns list of {"role": "output"|"source"|"ref_N", "b64": "..."}.
        """
        images: list[dict[str, str]] = []

        output_path = Path(output_path)
        if output_path.exists():
            images.append({
                "role": "output",
                "b64": base64.b64encode(output_path.read_bytes()).decode(),
            })

        if source_path:
            src = Path(source_path)
            if src.exists():
                images.append({
                    "role": "source",
                    "b64": base64.b64encode(src.read_bytes()).decode(),
                })

        for i, ref_path in enumerate(reference_paths or []):
            rp = Path(ref_path)
            if rp.exists():
                images.append({
                    "role": f"ref_{i}",
                    "b64": base64.b64encode(rp.read_bytes()).decode(),
                })

        return images

    # ───────────────────────────────────────────────────────────────
    # Judge call (with fallback chain)
    # ───────────────────────────────────────────────────────────────

    async def _call_judge_chain(
        self,
        prompt: str,
        images: list[dict[str, str]],
    ) -> tuple[str, str]:
        """
        Try each judge in the chain until one succeeds.

        Returns (raw_json_response, judge_model_name).
        Raises RuntimeError if all judges fail.
        """
        last_error: Exception | None = None

        for judge in self._judge_chain:
            try:
                response = await self._call_single_judge(judge, prompt, images)
                return response, judge.name
            except Exception as e:
                logger.warning(
                    "Judge %s failed: %s — trying next",
                    judge.name, str(e)[:200],
                )
                last_error = e

        raise RuntimeError(
            f"All {len(self._judge_chain)} judges failed. "
            f"Last error: {last_error}"
        )

    async def _call_single_judge(
        self,
        judge: JudgeConfig,
        prompt: str,
        images: list[dict[str, str]],
    ) -> str:
        """
        Call a single judge model.

        This is the integration point — each provider needs its own call impl.
        Returns the raw JSON string from the model.
        """
        if judge.provider == "vps":
            return await self._call_vps_judge(judge, prompt, images)
        elif judge.provider == "openai":
            return await self._call_openai_judge(judge, prompt, images)
        else:
            raise ValueError(f"Unknown judge provider: {judge.provider}")

    async def _call_vps_judge(
        self,
        judge: JudgeConfig,
        prompt: str,
        images: list[dict[str, str]],
    ) -> str:
        """
        Call Qwen2.5-VL on VPS via vLLM OpenAI-compatible API.

        Constructs a multi-image chat completion request.
        """
        # Build the message content with images
        content: list[dict[str, Any]] = []

        for img in images:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{img['b64']}",
                    "detail": "high",
                },
            })
            content.append({
                "type": "text",
                "text": f"[{img['role']} image above]",
            })

        content.append({"type": "text", "text": prompt})

        # Use aiohttp to call vLLM endpoint
        import aiohttp

        payload = {
            "model": judge.endpoint,
            "messages": [
                {"role": "system", "content": _JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            "max_tokens": judge.max_tokens,
            "temperature": judge.temperature,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{judge.endpoint}/v1/chat/completions",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data["choices"][0]["message"]["content"]

    async def _call_openai_judge(
        self,
        judge: JudgeConfig,
        prompt: str,
        images: list[dict[str, str]],
    ) -> str:
        """
        Call GPT-4o / GPT-4o-mini via OpenAI API.
        """
        import os

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set")

        content: list[dict[str, Any]] = []

        for img in images:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{img['b64']}",
                    "detail": "high",
                },
            })
            content.append({
                "type": "text",
                "text": f"[{img['role']} image above]",
            })

        content.append({"type": "text", "text": prompt})

        import aiohttp

        payload = {
            "model": judge.endpoint,
            "messages": [
                {"role": "system", "content": _JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            "max_tokens": judge.max_tokens,
            "temperature": judge.temperature,
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data["choices"][0]["message"]["content"]

    # ───────────────────────────────────────────────────────────────
    # Response parsing
    # ───────────────────────────────────────────────────────────────

    def _parse_judge_response(
        self,
        raw_response: str,
        dimensions: list[str],
        judge_model: str,
    ) -> EvalResult:
        """
        Parse the judge's JSON response into an EvalResult.

        Handles common LLM quirks: markdown fences, extra text, partial JSON.
        """
        result = EvalResult(
            evaluated=dimensions,
            judge_model=judge_model,
        )

        # Strip markdown fences if present
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # Remove first and last fence lines
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to extract JSON from the response
            start = cleaned.find("{")
            end = cleaned.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    parsed = json.loads(cleaned[start:end])
                except json.JSONDecodeError:
                    logger.error(
                        "Failed to parse judge response: %s",
                        cleaned[:500],
                    )
                    # Return zero scores for all dimensions
                    result.scores = {dim: 0.0 for dim in dimensions}
                    return result
            else:
                result.scores = {dim: 0.0 for dim in dimensions}
                return result

        # Extract scores
        raw_scores = parsed.get("scores", {})
        for dim in dimensions:
            score = raw_scores.get(dim, 0.0)
            # Clamp to [0.0, 1.0]
            result.scores[dim] = max(0.0, min(1.0, float(score)))

        # Extract reasoning
        result.judge_reasoning = {
            dim: parsed.get("reasoning", {}).get(dim, "")
            for dim in dimensions
        }

        # Extract correction hints
        result.correction_targets = parsed.get("correction_targets", [])
        result.correction_strategy = parsed.get("correction_strategy")

        return result

    # ───────────────────────────────────────────────────────────────
    # Helpers
    # ───────────────────────────────────────────────────────────────

    @staticmethod
    def _load_yaml(path: Path) -> dict[str, Any]:
        if not path.exists():
            logger.warning("Config not found: %s", path)
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    @staticmethod
    def _make_judge_config(model_name: str) -> JudgeConfig:
        """Map a judge model name to its provider and endpoint."""
        if "qwen" in model_name.lower():
            return JudgeConfig(
                name=model_name,
                provider="vps",
                endpoint=model_name,  # Will be resolved at call time
            )
        elif "gpt-4o-mini" in model_name.lower():
            return JudgeConfig(
                name=model_name,
                provider="openai",
                endpoint="gpt-4o-mini",
            )
        elif "gpt-4o" in model_name.lower():
            return JudgeConfig(
                name=model_name,
                provider="openai",
                endpoint="gpt-4o",
            )
        else:
            return JudgeConfig(
                name=model_name,
                provider="openai",
                endpoint=model_name,
            )

    # ───────────────────────────────────────────────────────────────
    # Utility: weighted score
    # ───────────────────────────────────────────────────────────────

    def weighted_overall_score(self, result: EvalResult) -> float:
        """Compute weighted average score across evaluated dimensions."""
        total_weight = 0.0
        weighted_sum = 0.0
        for dim in result.evaluated:
            w = self._weights.get(dim, 1.0)
            s = result.scores.get(dim, 0.0)
            weighted_sum += w * s
            total_weight += w
        return weighted_sum / total_weight if total_weight > 0 else 0.0
