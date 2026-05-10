"""
Skill applicator — centralized skill-override application for the chat pipeline.

All route handlers call ``apply_skill_overrides()`` after parsing request data
and resolving the skill.  This module owns:

1. **Conditional override logic** — only override model / thinking_mode /
   context when the user hasn't explicitly chosen a value.
2. **System-prompt composition** — build the full prompt by combining the
   context-based prompt with the skill's prompt_injection (append, not
   replace).
3. **Tool gating** — remove blocked tools and add preferred tools.
4. **MCP preference** — flag when a skill wants MCP context to be injected.

Every field in ``AppliedSkill`` is a concrete value ready for the pipeline.
Route handlers do not need to interpret SkillOverrides themselves.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from core.skills.resolver import SkillOverrides, resolve_skill

logger = logging.getLogger(__name__)


@dataclass
class AppliedSkill:
    """Concrete parameter values after applying skill overrides.

    Every field holds the *final* value to be used by the pipeline.
    ``was_applied`` is True when a skill actually changed at least one value.
    """

    # Resolved skill identity
    skill_id: Optional[str] = None
    skill_name: Optional[str] = None
    was_applied: bool = False

    # Pipeline parameters (final values)
    model: str = "grok"
    context: str = "casual"
    thinking_mode: str = "auto"
    deep_thinking: bool = False
    custom_prompt: str = ""
    tools: List[str] = field(default_factory=list)

    # MCP hint — True when the skill wants MCP context injected
    prefer_mcp: bool = False


def apply_skill_overrides(
    *,
    data: dict,
    skill_overrides: SkillOverrides,
    language: str = "vi",
) -> AppliedSkill:
    """Apply resolved skill overrides to a parsed request dict.

    Parameters
    ----------
    data : dict
        Raw request data (from ``request.json`` or ``request.form``).
    skill_overrides : SkillOverrides
        Output of ``resolve_skill()``.
    language : str
        Language code used to select the base system prompt.

    Returns
    -------
    AppliedSkill
        Final parameter values ready for the chat pipeline.
    """
    # Start with the request's own values
    model = data.get("model", "grok")
    context = data.get("context", "casual")
    custom_prompt = data.get("custom_prompt", "") or ""
    thinking_mode = data.get("thinking_mode", "auto")
    deep_thinking = str(data.get("deep_thinking", "false")).lower() == "true"

    # Derive deep_thinking from thinking_mode (mirrors stream.py logic)
    if thinking_mode in ("thinking", "deep", "multi-thinking"):
        deep_thinking = True
    elif thinking_mode in ("instant", "auto"):
        deep_thinking = False

    # Extract tools
    tools = data.get("tools", [])
    if isinstance(tools, str):
        try:
            import json as _json
            tools = _json.loads(tools)
        except Exception:
            tools = []
    tools = list(tools)

    prefer_mcp = False

    if not skill_overrides.active:
        return AppliedSkill(
            model=model,
            context=context,
            thinking_mode=thinking_mode,
            deep_thinking=deep_thinking,
            custom_prompt=custom_prompt,
            tools=tools,
        )

    # ── Detect whether user explicitly set values vs. defaults ────────
    # When skill was *explicitly* chosen by the user (explicit_skill_id
    # was in the request), apply ALL overrides.  When auto-routed, only
    # override values the user left at their defaults.
    user_chose_skill = bool(data.get("skill"))
    user_set_model = "model" in data and data["model"] != "grok"
    user_set_thinking = "thinking_mode" in data and data["thinking_mode"] != "auto"
    user_set_context = "context" in data and data["context"] != "casual"

    # ── Context override ──────────────────────────────────────────────
    if skill_overrides.context:
        if user_chose_skill or not user_set_context:
            context = skill_overrides.context

    # ── Model override ────────────────────────────────────────────────
    if skill_overrides.model:
        if user_chose_skill or not user_set_model:
            model = skill_overrides.model

    # ── Thinking mode override ────────────────────────────────────────
    if skill_overrides.thinking_mode:
        if user_chose_skill or not user_set_thinking:
            thinking_mode = skill_overrides.thinking_mode
            if thinking_mode in ("thinking", "deep", "multi-thinking"):
                deep_thinking = True
            elif thinking_mode in ("instant", "auto"):
                deep_thinking = False

    # ── System prompt composition (append, not replace) ───────────────
    if skill_overrides.prompt_injection:
        if custom_prompt and custom_prompt.strip():
            # User already has a custom prompt — append skill injection
            custom_prompt = custom_prompt + "\n\n" + skill_overrides.prompt_injection
        else:
            # No user custom prompt — build context-based prompt + skill
            try:
                from core.config import get_system_prompts
                base_prompt = get_system_prompts(language).get(
                    context,
                    get_system_prompts(language).get("casual", ""),
                )
                custom_prompt = base_prompt + "\n\n" + skill_overrides.prompt_injection
            except Exception as exc:
                logger.warning("[Skill] Failed to load base system prompt: %s", exc)
                custom_prompt = skill_overrides.prompt_injection

    # ── Tool gating ───────────────────────────────────────────────────
    if skill_overrides.blocked_tools:
        tools = [t for t in tools if t not in skill_overrides.blocked_tools]
    if skill_overrides.preferred_tools:
        for pt in skill_overrides.preferred_tools:
            if pt not in tools:
                tools.append(pt)

    # ── MCP preference ────────────────────────────────────────────────
    # Skills with "mcp" tag or mcp-related preferred tools signal that
    # MCP context is especially valuable for this request.
    try:
        from core.skills.registry import get_skill_registry
        skill_def = get_skill_registry().get(skill_overrides.skill_id)
        if skill_def and ("mcp" in getattr(skill_def, "tags", [])):
            prefer_mcp = True
    except Exception as exc:
        logger.debug("[Skill] MCP preference check failed: %s", exc)

    logger.info(
        f"[SkillApply] Applied skill '{skill_overrides.skill_id}': "
        f"model={model}, ctx={context}, think={thinking_mode}, "
        f"tools={tools}, prefer_mcp={prefer_mcp}"
    )

    return AppliedSkill(
        skill_id=skill_overrides.skill_id,
        skill_name=skill_overrides.skill_name,
        was_applied=True,
        model=model,
        context=context,
        thinking_mode=thinking_mode,
        deep_thinking=deep_thinking,
        custom_prompt=custom_prompt,
        tools=tools,
        prefer_mcp=prefer_mcp,
    )
