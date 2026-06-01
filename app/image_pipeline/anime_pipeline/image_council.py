"""Typed local-only image council for anime generation guidance."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

import httpx

from .config import AnimePipelineConfig
from .runtime_policy import RuntimePolicy

_ROLES = ("Director", "IdentityGuardian", "CompositionCritic", "DetailCritic")


@dataclass
class CouncilRoleResult:
    role: str
    directives: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)


@dataclass
class ImageCouncilResult:
    roles: list[CouncilRoleResult] = field(default_factory=list)
    key_points: list[str] = field(default_factory=list)
    content: str = ""
    confidence: float = 0.0
    rounds: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "roles": [
                {
                    "role": role.role,
                    "directives": role.directives,
                    "risks": role.risks,
                }
                for role in self.roles
            ],
            "key_points": self.key_points,
            "content": self.content,
            "confidence": self.confidence,
            "rounds": self.rounds,
            "provenance": "local-vlm",
        }


class LocalImageCouncil:
    """Produces explicit image directives without exposing hidden reasoning."""

    def __init__(self, config: AnimePipelineConfig, policy: RuntimePolicy):
        self._config = config
        self._policy = policy

    def run(self, prompt: str, language: str = "en") -> dict[str, Any] | None:
        if not self._config.council_enabled or self._config.council_max_rounds <= 0:
            return None
        url = f"{self._config.local_vlm_url.rstrip('/')}/chat/completions"
        self._policy.assert_url(url, purpose="local_image_council")

        previous = ""
        parsed: dict[str, Any] = {}
        rounds = min(self._config.council_max_rounds, 2)
        for round_number in range(1, rounds + 1):
            parsed = self._call(url, prompt, language, previous, round_number)
            previous = json.dumps(parsed, ensure_ascii=False)

        raw_roles = parsed.get("roles", []) if isinstance(parsed, dict) else []
        roles: list[CouncilRoleResult] = []
        for role_name in _ROLES:
            raw = next(
                (
                    item
                    for item in raw_roles
                    if isinstance(item, dict) and item.get("role") == role_name
                ),
                {},
            )
            roles.append(
                CouncilRoleResult(
                    role=role_name,
                    directives=[str(v) for v in raw.get("directives", [])[:5]],
                    risks=[str(v) for v in raw.get("risks", [])[:5]],
                )
            )
        return ImageCouncilResult(
            roles=roles,
            key_points=[str(v) for v in parsed.get("key_points", [])[:12]],
            content=str(parsed.get("content", ""))[:2000],
            confidence=max(0.0, min(float(parsed.get("confidence", 0.0)), 1.0)),
            rounds=rounds,
        ).to_dict()

    def _call(
        self,
        url: str,
        prompt: str,
        language: str,
        previous: str,
        round_number: int,
    ) -> dict[str, Any]:
        system = (
            "You are a typed image-generation council. Return only JSON with "
            "roles, key_points, content, confidence. roles must contain exactly "
            "Director, IdentityGuardian, CompositionCritic, DetailCritic. "
            "Each role returns directives and risks arrays. Provide concise "
            "visual directives, not hidden reasoning."
        )
        user = (
            f"Language: {language}\nRound: {round_number}\nRequest:\n{prompt}\n"
            f"Previous directives:\n{previous or 'none'}"
        )
        with httpx.Client(timeout=30) as client:
            response = client.post(
                url,
                headers={
                    "Authorization": "Bearer "
                    + os.getenv("ANIME_PIPELINE_LOCAL_VLM_API_KEY", "local")
                },
                json={
                    "model": self._config.local_vlm_model or "local-vlm",
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 1000,
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
        text = response.json()["choices"][0]["message"]["content"].strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            raise ValueError("Local image council returned non-object JSON")
        return parsed

