"""
Coordinated Reasoning Service — Research Council Architecture
==============================================================
2-phase council model with 5 specialized team members, structured
compaction, round cache, and adaptive trajectory routing.

Phase 1 — Wide Exploration (5 personas, parallel)
Phase 2 — Focused Debate   (top-3 personas, see each other's output)
Synthesis — Single call with cached structured data

Workflow:
    Question → Complexity Assessment → Phase 1 (5 parallel trajectories)
    → Structured Compaction + Scoring → Phase 2 (top-3 debate, cross-ref)
    → Final Synthesis (cached structured data) → Answer
"""

import asyncio
import hashlib
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class ReasoningTrajectory:
    """A single reasoning path produced by one team member."""
    id: str
    content: str
    confidence: float = 0.0
    tokens_used: int = 0
    round_number: int = 0
    persona_name: str = ""
    insights: List[str] = field(default_factory=list)
    conclusion: str = ""


@dataclass
class CoordinatedReasoningResult:
    """Result from coordinated reasoning process."""
    final_answer: str
    thinking_process: str
    total_rounds: int
    total_trajectories: int
    total_tokens: int
    reasoning_time: float
    trajectories: List[ReasoningTrajectory] = field(default_factory=list)


def _extract_token_count(tokens) -> int:
    """Safely extract total token count from tokens value (int or dict)."""
    if isinstance(tokens, dict):
        return sum(v for v in tokens.values() if isinstance(v, (int, float)))
    if isinstance(tokens, (int, float)):
        return int(tokens)
    return 0


# ── Model fallback chains ───────────────────────────────────────────────────

MODEL_FALLBACK_CHAINS = {
    'exploration': ['deepseek', 'grok', 'openai'],
    'debate':      ['grok', 'deepseek', 'openai'],
    'synthesis':   ['grok', 'deepseek', 'openai'],
}


# ══════════════════════════════════════════════════════════════════════════════
# RESEARCH COUNCIL — 5 Team Members
# ══════════════════════════════════════════════════════════════════════════════
# Each persona is a distinct cognitive role. In Phase 1 all 5 explore
# independently.  In Phase 2, the top-3 (by score) see each other's
# Phase 1 outputs and debate/refine — like a real research meeting.

_TEAM: Dict[int, Dict[str, str]] = {
    0: {
        "name": "Logic Architect",
        "icon": "🏗️",
        "directive": (
            "Tiếp cận hoàn toàn bằng logic hình thức và tính toán. "
            "Phân rã bài toán thành các mệnh đề, xác định điều kiện cần/đủ, "
            "lập luận từng bước có chứng minh. Dùng pseudocode hoặc toán "
            "khi cần. Ưu tiên tính chính xác tuyệt đối hơn toàn diện."
        ),
        "strength": "logic",
    },
    1: {
        "name": "Research Lead",
        "icon": "📚",
        "directive": (
            "Thu thập chứng cứ, cross-reference nhiều nguồn, phân biệt "
            "thực tế vs. ý kiến. Cấu trúc output rõ ràng với heading, "
            "bullet points. Ghi chú confidence level (high/medium/low) "
            "cho từng claim. Đề xuất hướng nghiên cứu tiếp theo."
        ),
        "strength": "evidence",
    },
    2: {
        "name": "Creative Strategist",
        "icon": "💡",
        "directive": (
            "Tìm giải pháp bất ngờ: analogies từ lĩnh vực khác, "
            "lateral thinking, 'nếu làm ngược lại thì sao?'. "
            "Đặt câu hỏi phá vỡ giả định. Đưa ra ít nhất 2 hướng "
            "tiếp cận hoàn toàn khác nhau. Không cần 'đúng' — cần 'mới'."
        ),
        "strength": "creative",
    },
    3: {
        "name": "Optimization Engineer",
        "icon": "⚡",
        "directive": (
            "Phân tích complexity (time/space/token), tìm bottlenecks, "
            "đề xuất trade-offs rõ ràng. So sánh approach A vs B bằng "
            "metrics cụ thể. Compact lại dữ liệu thừa — chỉ giữ core "
            "value. Ưu tiên hiệu quả và khả thi hơn lý thuyết."
        ),
        "strength": "optimization",
    },
    4: {
        "name": "DevOps / QA Critic",
        "icon": "🛡️",
        "directive": (
            "Edge cases, failure modes, security implications, deployment "
            "concerns. 'Cái gì có thể sai?' 'Scale lên thì thế nào?' "
            "Phản biện mọi giả định ẩn. Kiểm tra tính khả thi thực tế "
            "với ví dụ cụ thể. Cho điểm risk level mỗi approach."
        ),
        "strength": "validation",
    },
}


# ── Phase missions ───────────────────────────────────────────────────────────

_PHASE_MISSIONS: Dict[int, Dict[str, str]] = {
    0: {
        "name": "Khám phá song song",
        "directive": (
            "Đây là Phase 1 — mỗi thành viên khám phá ĐỘC LẬP. "
            "Không có context trước. Mở rộng tối đa không gian giải pháp. "
            "GỌN — tối đa 300 words. Tập trung vào insights mới, không giải thích lại đề bài."
        ),
    },
    1: {
        "name": "Thảo luận nhóm",
        "directive": (
            "Phase 2 — bạn đã đọc output của các thành viên khác. "
            "Nhiệm vụ: PHẢN BIỆN hoặc BỔ SUNG, không lặp lại. "
            "Tham chiếu cụ thể: 'Logic Architect nói X nhưng bỏ qua Y'. "
            "GỌN — tối đa 200 words. Chỉ đưa ra điểm MỚI."
        ),
    },
}


# ── Context → team member routing ────────────────────────────────────────────
# Maps context type → ordered list of 5 skill IDs (one per persona slot).

_CONTEXT_SKILL_MAP: Dict[str, List[str]] = {
    "programming": ["code-expert",       "research-analyst", "prompt-engineer",  "repo-analyzer",    "code-expert"],
    "code":        ["code-expert",       "research-analyst", "prompt-engineer",  "repo-analyzer",    "code-expert"],
    "research":    ["research-analyst",  "research-web",     "creative-writer",  "research-analyst", "research-web"],
    "casual":      ["research-analyst",  "creative-writer",  "counselor",        "research-analyst", "creative-writer"],
    "creative":    ["creative-writer",   "prompt-engineer",  "creative-writer",  "research-analyst", "prompt-engineer"],
    "shopping":    ["shopping-advisor",  "research-web",     "creative-writer",  "research-analyst", "shopping-advisor"],
}

# ── Strength → context affinity (mandatory personas per context) ─────────────
_CONTEXT_MANDATORY: Dict[str, List[str]] = {
    "programming": ["logic", "validation"],
    "code":        ["logic", "validation"],
    "research":    ["evidence", "creative"],
    "casual":      ["evidence", "creative"],
    "creative":    ["creative", "evidence"],
    "shopping":    ["evidence", "optimization"],
}


# ══════════════════════════════════════════════════════════════════════════════
# Round Cache — structured intermediate storage
# ══════════════════════════════════════════════════════════════════════════════

class _RoundCache:
    """In-memory cache for a single reasoning session.

    Stores structured data from each phase so later phases and synthesis
    can reference specific team member outputs without full re-processing.
    """

    def __init__(self):
        self.question_hash: str = ""
        self.phase_results: Dict[int, List[Dict[str, Any]]] = {}
        self.compacted: Dict[int, str] = {}
        self.scores: Dict[str, float] = {}

    def store_phase(self, phase: int, trajectories: List[ReasoningTrajectory]) -> None:
        entries = []
        for t in trajectories:
            entry = {
                "id": t.id,
                "persona": t.persona_name,
                "confidence": t.confidence,
                "tokens": t.tokens_used,
                "insights": t.insights,
                "conclusion": t.conclusion,
                "content_hash": hashlib.md5(t.content.encode(), usedforsecurity=False).hexdigest()[:8],
            }
            entries.append(entry)
            self.scores[t.id] = t.confidence
        self.phase_results[phase] = entries

    def store_compacted(self, phase: int, text: str) -> None:
        self.compacted[phase] = text

    def get_top_ids(self, phase: int, n: int = 3) -> List[int]:
        """Return trajectory slot IDs of top-N from a phase."""
        entries = self.phase_results.get(phase, [])
        ranked = sorted(entries, key=lambda e: e["confidence"], reverse=True)
        result = []
        for e in ranked[:n]:
            try:
                result.append(int(e["id"].split("_t")[1]))
            except (IndexError, ValueError):
                pass
        return result

    def build_synthesis_context(self) -> str:
        """Build a compact structured summary for the final synthesis."""
        parts = []
        for phase_num in sorted(self.phase_results.keys()):
            entries = self.phase_results[phase_num]
            phase_label = "Khám phá" if phase_num == 0 else "Thảo luận"
            parts.append(f"### Phase {phase_num + 1}: {phase_label}")
            for e in sorted(entries, key=lambda x: x["confidence"], reverse=True):
                persona = e["persona"]
                stars = "★" * max(1, int(e["confidence"] * 5))
                tok_count = e["tokens"]
                parts.append(f"**{persona}** [{stars}] ({tok_count} tokens)")
                if e["insights"]:
                    for ins in e["insights"][:3]:
                        parts.append(f"  → {ins[:150]}")
                if e["conclusion"]:
                    conclusion_text = e["conclusion"]
                    parts.append(f"  ⇒ {conclusion_text[:200]}")
            if phase_num in self.compacted:
                compacted_text = self.compacted[phase_num]
                parts.append(f"**Tổng hợp:** {compacted_text[:300]}")
            parts.append("")
        return "\n".join(parts)


# ══════════════════════════════════════════════════════════════════════════════
# ReasoningService
# ══════════════════════════════════════════════════════════════════════════════

class ReasoningService:
    """Research Council — 2-phase coordinated reasoning with 5 team members.

    Phase 1: 5 personas explore in parallel (wide, independent)
    Phase 2: Top-3 personas debate (focused, cross-referencing)
    Synthesis: Single call with cached structured data
    """

    COMPLEXITY_PATTERNS = [
        (r'giải thích|explain|why|tại sao|như thế nào|how', 1),
        (r'so sánh|compare|difference|khác nhau', 1),
        (r'phân tích|analyze|analysis', 1),
        (r'code|programming|bug|error|lỗi|debug', 2),
        (r'math|toán|calculate|tính|equation', 2),
        (r'step by step|từng bước|chi tiết', 1),
        (r'complex|phức tạp|nhiều bước', 2),
        (r'optimize|tối ưu|improve|cải thiện', 1),
        (r'design|thiết kế|architecture|kiến trúc', 2),
        (r'implement|triển khai|xây dựng|build', 1),
    ]

    COMPLEXITY_THRESHOLD_THINKING = 2
    COMPLEXITY_THRESHOLD_DEEP = 4

    def __init__(self, ai_service=None):
        self.ai_service = ai_service
        self.phase1_width = 5
        self.phase2_width = 3
        self.max_rounds = 2
        self.max_trajectories_per_round = 5  # compat with old callers
        self._cache: Optional[_RoundCache] = None

    # ── Complexity estimation ────────────────────────────────────────────

    def estimate_complexity(self, message: str) -> int:
        score = 0
        message_lower = message.lower()
        for pattern, weight in self.COMPLEXITY_PATTERNS:
            if re.search(pattern, message_lower):
                score += weight
        if len(message) > 200:
            score += 1
        if len(message) > 500:
            score += 1
        if len(message) > 1000:
            score += 1
        question_count = message.count('?')
        if question_count > 1:
            score += min(question_count - 1, 2)
        return min(score, 10)

    def auto_decide_mode(self, message: str) -> str:
        complexity = self.estimate_complexity(message)
        logger.info(f"[Reasoning] Complexity score: {complexity}")
        if complexity >= self.COMPLEXITY_THRESHOLD_DEEP:
            return 'deep'
        elif complexity >= self.COMPLEXITY_THRESHOLD_THINKING:
            return 'thinking'
        return 'instant'

    def should_use_deep_reasoning(self, thinking_mode: str, message: str) -> bool:
        if thinking_mode == 'deep':
            return True
        if thinking_mode == 'auto':
            return self.auto_decide_mode(message) == 'deep'
        return False

    # ── Model fallback ───────────────────────────────────────────────────

    def _call_with_fallback(
        self,
        prompt: str,
        context: str,
        chain_key: str = 'exploration',
        deep_thinking: bool = True,
        token_callback=None,
    ) -> Dict[str, Any]:
        """Call AI service with automatic model fallback on failure."""
        chain = MODEL_FALLBACK_CHAINS.get(chain_key, ['deepseek', 'grok', 'openai'])
        last_error = None
        for model_name in chain:
            model_cfg = self.ai_service.models.get(model_name)
            if not model_cfg or not model_cfg.get('available'):
                continue
            try:
                if token_callback and hasattr(self.ai_service, 'chat_stream_callback'):
                    return self.ai_service.chat_stream_callback(
                        message=prompt, model=model_name, context=context,
                        deep_thinking=deep_thinking, token_callback=token_callback,
                    )
                else:
                    return self.ai_service.chat(
                        message=prompt, model=model_name, context=context,
                        deep_thinking=deep_thinking,
                    )
            except Exception as e:
                last_error = e
                logger.warning("[Reasoning] Model '%s' failed, trying next: %s", model_name, e)
        raise RuntimeError(f"All models in '{chain_key}' chain failed. Last: {last_error}")

    # ── Skill fragment loader ────────────────────────────────────────────

    def _get_skill_fragment(self, context: str, trajectory_id: int) -> str:
        """Return prompt_fragment from a built-in skill for this slot."""
        skill_ids = _CONTEXT_SKILL_MAP.get(context, [])
        if not skill_ids:
            return ""
        slot = trajectory_id % len(skill_ids)
        skill_id = skill_ids[slot]
        try:
            from core.skills.registry import SkillRegistry
            registry = SkillRegistry()
            registry.load_builtins()
            skill = registry.get(skill_id)
            if skill and skill.enabled and skill.prompt_fragments:
                return skill.prompt_fragments[0]
        except Exception as exc:
            logger.debug("[Reasoning] Skill lookup failed for '%s': %s", skill_id, exc)
        return ""

    # ── Prompt builders ──────────────────────────────────────────────────

    def _build_exploration_prompt(
        self,
        message: str,
        round_number: int,
        trajectory_id: int,
        previous_insights: str,
        skill_fragment: str = "",
        peer_outputs: Optional[Dict[str, str]] = None,
    ) -> str:
        """Build prompt for a team member.

        Phase 1 (round_number=0): independent exploration.
        Phase 2 (round_number=1): debate with peer_outputs visible.
        """
        team_member = _TEAM[trajectory_id % len(_TEAM)]
        phase = _PHASE_MISSIONS[min(round_number, len(_PHASE_MISSIONS) - 1)]

        member_icon = team_member["icon"]
        member_name = team_member["name"]
        member_directive = team_member["directive"]
        phase_name = phase["name"]
        phase_directive = phase["directive"]

        parts: List[str] = []

        # 1. Identity
        parts.append(
            f"Bạn là **{member_icon} {member_name}** trong nhóm Research Council.\n"
            f"→ {member_directive}"
        )

        # 2. Skill lens (optional)
        if skill_fragment:
            parts.append(f"--- Kỹ năng chuyên môn ---\n{skill_fragment.strip()}")

        # 3. Phase mission
        parts.append(f"**Nhiệm vụ ({phase_name}):** {phase_directive}")

        # 4. Original question
        parts.append(f"**Câu hỏi:** {message}")

        # 5. Peer outputs (Phase 2 only — creates the "discussion" feel)
        if peer_outputs:
            parts.append("--- Output của các thành viên khác (Phase 1) ---")
            for peer_name, peer_summary in peer_outputs.items():
                parts.append(f"**{peer_name}:** {peer_summary[:400]}")
            parts.append(
                "---\n"
                "⚠️ KHÔNG lặp lại — phản biện, bổ sung, hoặc kết hợp. "
                "Tham chiếu cụ thể theo tên thành viên."
            )

        # 6. Previous compacted insights (cross-phase)
        if previous_insights and not peer_outputs:
            parts.append(f"Context từ vòng trước:\n{previous_insights[:500]}")

        # 7. Output format
        parts.append(
            "**Format output:**\n"
            "- Đánh dấu phát hiện: [INSIGHT] nội dung\n"
            "- Đánh dấu phản biện: [CHALLENGE] nội dung\n"
            "- Kết với: [CONCLUSION] tóm tắt 1-2 câu\n"
            "- Cho điểm tin cậy: [CONFIDENCE: X/10]"
        )

        return "\n\n".join(parts)

    # ── Trajectory generation ────────────────────────────────────────────

    async def _generate_trajectory(
        self,
        message: str,
        context: str,
        round_number: int,
        trajectory_id: int,
        previous_insights: str = "",
        progress_callback: Optional[Callable] = None,
        peer_outputs: Optional[Dict[str, str]] = None,
    ) -> ReasoningTrajectory:
        """Generate a single trajectory from one team member."""
        team_member = _TEAM[trajectory_id % len(_TEAM)]
        member_name = team_member["name"]
        member_icon = team_member["icon"]
        skill_fragment = self._get_skill_fragment(context, trajectory_id)
        prompt = self._build_exploration_prompt(
            message, round_number, trajectory_id, previous_insights,
            skill_fragment, peer_outputs,
        )

        _cb = progress_callback or (lambda msg: None)
        phase_label = "Khám phá" if round_number == 0 else "Thảo luận"
        header = f"\n\n**{member_icon} {member_name} ({phase_label})**\n"
        _cb(header)

        try:
            if self.ai_service:
                streaming_buf: list[str] = []
                _tid = f"p{round_number}_t{trajectory_id}"

                def _on_token(token_text: str):
                    streaming_buf.append(token_text)
                    _cb({"type": "token", "tid": _tid, "text": token_text})

                chain = 'debate' if round_number > 0 else 'exploration'
                result = await asyncio.to_thread(
                    self._call_with_fallback,
                    prompt, context, chain, True, _on_token,
                )
                content = result.get('text', '') or ''.join(streaming_buf)
                tokens = _extract_token_count(result.get('tokens', 0))
                _cb(f"\n✅ *{member_name} — {tokens} tokens*\n")
            else:
                content = f"[{member_name}] Reasoning about: {message[:100]}..."
                tokens = 0

            # Parse structured output
            insights = re.findall(r'\[INSIGHT\]\s*(.*?)(?=\[|$)', content, re.DOTALL)
            insights = [i.strip()[:200] for i in insights if i.strip()]
            challenges = re.findall(r'\[CHALLENGE\]\s*(.*?)(?=\[|$)', content, re.DOTALL)
            insights.extend([f"⚔️ {c.strip()[:200]}" for c in challenges if c.strip()])
            conclusion_m = re.findall(r'\[CONCLUSION\]\s*(.*?)(?=\[|$)', content, re.DOTALL)
            conclusion = conclusion_m[0].strip()[:300] if conclusion_m else ""
            conf_m = re.search(r'\[CONFIDENCE:\s*(\d+)/10\]', content)
            confidence = (int(conf_m.group(1)) / 10.0) if conf_m else self._estimate_confidence(content)

            return ReasoningTrajectory(
                id=f"p{round_number}_t{trajectory_id}",
                content=content,
                confidence=confidence,
                tokens_used=tokens,
                round_number=round_number,
                persona_name=member_name,
                insights=insights,
                conclusion=conclusion,
            )
        except Exception as e:
            logger.error(f"[Reasoning] Trajectory failed: {e}")
            _cb(f"\n❌ {member_name} lỗi: {e}\n")
            return ReasoningTrajectory(
                id=f"p{round_number}_t{trajectory_id}",
                content=f"Error: {e}",
                confidence=0.0,
                tokens_used=0,
                round_number=round_number,
                persona_name=member_name,
            )

    # ── Confidence estimation ────────────────────────────────────────────

    def _estimate_confidence(self, content: str) -> float:
        confidence = 0.5
        if '[INSIGHT]' in content:
            confidence += 0.1
        if '[CONCLUSION]' in content:
            confidence += 0.1
        if '[CHALLENGE]' in content:
            confidence += 0.05
        lower = content.lower()
        if 'chắc chắn' in lower or 'confident' in lower:
            confidence += 0.1
        if len(content) > 500:
            confidence += 0.1
        if 'bước 1' in lower or 'step 1' in lower:
            confidence += 0.05
        return min(confidence, 1.0)

    # ── Structured compaction ────────────────────────────────────────────

    def _compact_trajectories(self, trajectories: List[ReasoningTrajectory]) -> str:
        """Structured compaction — extracts and ranks insights, filters noise.

        Returns a compact summary usable by the next phase, sorted by
        confidence. Much more aggressive than naive concatenation.
        """
        if not trajectories:
            return ""

        scored_insights: List[Tuple[float, str, str]] = []
        conclusions: List[Tuple[float, str, str]] = []

        for t in trajectories:
            for ins in t.insights:
                scored_insights.append((t.confidence, t.persona_name, ins))
            if t.conclusion:
                conclusions.append((t.confidence, t.persona_name, t.conclusion))

        scored_insights.sort(key=lambda x: x[0], reverse=True)
        conclusions.sort(key=lambda x: x[0], reverse=True)

        parts = []

        # Top insights (max 6, deduplicated by hash)
        seen_hashes: set[str] = set()
        if scored_insights:
            parts.append("**Insights (ranked):**")
            count = 0
            for score, persona, text in scored_insights:
                h = hashlib.md5(text[:50].encode(), usedforsecurity=False).hexdigest()[:6]
                if h in seen_hashes:
                    continue
                seen_hashes.add(h)
                stars = "★" * max(1, int(score * 5))
                parts.append(f"  {stars} [{persona}] {text[:200]}")
                count += 1
                if count >= 6:
                    break

        # Top conclusions (max 3)
        if conclusions:
            parts.append("**Kết luận sơ bộ:**")
            for _score, persona, text in conclusions[:3]:
                parts.append(f"  → [{persona}] {text[:250]}")

        # Metrics
        total_tokens = sum(t.tokens_used for t in trajectories)
        avg_conf = sum(t.confidence for t in trajectories) / len(trajectories)
        parts.append(f"**Metrics:** {len(trajectories)} members, {total_tokens} tokens, avg confidence {avg_conf:.0%}")

        return "\n".join(parts) if parts else "Chưa có insights rõ ràng."

    # ── Phase execution ──────────────────────────────────────────────────

    async def _run_phase1(
        self,
        message: str,
        context: str,
        previous_insights: str,
        progress_callback: Optional[Callable] = None,
    ) -> Tuple[List[ReasoningTrajectory], str]:
        """Phase 1: 5 parallel independent explorations."""
        logger.info("[Reasoning] Phase 1 — Wide exploration (%d personas)", self.phase1_width)
        tasks = [
            self._generate_trajectory(
                message, context, 0, i, previous_insights,
                progress_callback=progress_callback,
            )
            for i in range(self.phase1_width)
        ]
        trajectories = list(await asyncio.gather(*tasks))
        compacted = self._compact_trajectories(trajectories)
        if self._cache:
            self._cache.store_phase(0, trajectories)
            self._cache.store_compacted(0, compacted)
        logger.info("[Reasoning] Phase 1 complete: %d trajectories", len(trajectories))
        return trajectories, compacted

    async def _run_phase2(
        self,
        message: str,
        context: str,
        phase1_trajectories: List[ReasoningTrajectory],
        phase1_compacted: str,
        progress_callback: Optional[Callable] = None,
    ) -> Tuple[List[ReasoningTrajectory], str]:
        """Phase 2: Top-3 personas debate, seeing each other's Phase 1 output.

        This creates the "team discussion" feel — each member receives the
        others' conclusions and is instructed to challenge/extend.
        """
        logger.info("[Reasoning] Phase 2 — Focused debate")

        top_ids = self._select_debate_slots(phase1_trajectories, context)

        # Build peer_outputs map: summaries from ALL Phase 1 members
        all_summaries: Dict[str, str] = {}
        for t in phase1_trajectories:
            summary = t.conclusion if t.conclusion else t.content[:200]
            all_summaries[t.persona_name] = summary

        tasks = []
        for slot_id in top_ids:
            team_member = _TEAM[slot_id % len(_TEAM)]
            # Each debater sees everyone EXCEPT themselves
            peers = {k: v for k, v in all_summaries.items() if k != team_member["name"]}
            tasks.append(
                self._generate_trajectory(
                    message, context, 1, slot_id, phase1_compacted,
                    progress_callback=progress_callback,
                    peer_outputs=peers,
                )
            )

        trajectories = list(await asyncio.gather(*tasks))
        compacted = self._compact_trajectories(trajectories)
        if self._cache:
            self._cache.store_phase(1, trajectories)
            self._cache.store_compacted(1, compacted)
        logger.info("[Reasoning] Phase 2 complete: %d trajectories", len(trajectories))
        return trajectories, compacted

    def _select_debate_slots(
        self,
        phase1_trajectories: List[ReasoningTrajectory],
        context: str,
    ) -> List[int]:
        """Pick which 3 persona slots join Phase 2.

        Strategy: top-2 by confidence + 1 mandatory strength for context.
        """
        ranked = sorted(phase1_trajectories, key=lambda t: t.confidence, reverse=True)
        selected_slots: list[int] = []
        selected_strengths: set[str] = set()

        # Top 2 by score
        for t in ranked[:2]:
            slot = int(t.id.split("_t")[1]) if "_t" in t.id else 0
            selected_slots.append(slot)
            selected_strengths.add(_TEAM[slot % len(_TEAM)]["strength"])

        # Mandatory strength check
        mandatory = _CONTEXT_MANDATORY.get(context, [])
        for strength in mandatory:
            if strength not in selected_strengths and len(selected_slots) < self.phase2_width:
                for slot_id, member in _TEAM.items():
                    if member["strength"] == strength and slot_id not in selected_slots:
                        selected_slots.append(slot_id)
                        selected_strengths.add(strength)
                        break

        # Fill remaining
        for t in ranked:
            if len(selected_slots) >= self.phase2_width:
                break
            slot = int(t.id.split("_t")[1]) if "_t" in t.id else 0
            if slot not in selected_slots:
                selected_slots.append(slot)

        return selected_slots[:self.phase2_width]

    # ── Synthesis ────────────────────────────────────────────────────────

    def _synthesize_final_answer(
        self,
        message: str,
        all_trajectories: List[ReasoningTrajectory],
        final_insights: str,
        context: str,
        progress_callback=None,
    ) -> str:
        """Final synthesis using cached structured data from both phases."""
        cache_context = self._cache.build_synthesis_context() if self._cache else final_insights
        member_count = len(all_trajectories)

        synthesis_prompt = (
            "Bạn là Facilitator của Research Council. "
            f"Dựa trên thảo luận của {member_count} thành viên qua 2 phase, "
            "hãy tổng hợp câu trả lời TỐT NHẤT.\n\n"
            f"**Câu hỏi gốc:** {message}\n\n"
            f"**Dữ liệu từ Council:**\n{cache_context}\n\n"
            "**Yêu cầu:**\n"
            "- Ưu tiên insights có confidence cao nhất\n"
            "- Giải quyết mâu thuẫn giữa các thành viên (nếu có)\n"
            "- Kết hợp các góc nhìn bổ trợ nhau\n"
            "- Trả lời toàn diện, chính xác, dễ hiểu\n"
            "- KHÔNG nhắc lại quá trình thảo luận trong câu trả lời"
        )

        _cb = progress_callback or (lambda msg: None)
        try:
            if self.ai_service:
                _cb("\n\n**✨ Đang tổng hợp từ Research Council...**\n")

                def _on_synth_token(tok):
                    _cb({"type": "token", "tid": "synthesis", "text": tok})

                result = self._call_with_fallback(
                    prompt=synthesis_prompt, context=context,
                    chain_key='synthesis', token_callback=_on_synth_token,
                )
                return result.get('text', 'Không thể tổng hợp câu trả lời.')
            else:
                return f"[Synthesized] Answer from {member_count} council members"
        except Exception as e:
            logger.error(f"[Reasoning] Synthesis failed: {e}")
            return f"Lỗi tổng hợp: {e}"

    # ── Main entry point ─────────────────────────────────────────────────

    async def coordinate_reasoning(
        self,
        message: str,
        context: str = 'casual',
        max_rounds: Optional[int] = None,
        images: Optional[List[str]] = None,
        progress_callback: Optional[Callable] = None,
    ) -> CoordinatedReasoningResult:
        """2-phase Research Council reasoning.

        Phase 1: Wide exploration (5 personas in parallel)
        Phase 2: Focused debate (top-3 cross-referencing)
        Synthesis: Final answer from cached structured data
        """
        start_time = time.time()
        self._cache = _RoundCache()
        self._cache.question_hash = hashlib.md5(message.encode(), usedforsecurity=False).hexdigest()[:12]

        all_trajectories: List[ReasoningTrajectory] = []
        thinking_parts: List[str] = []
        _cb = progress_callback or (lambda msg: None)
        previous_insights = ""

        logger.info("[Reasoning] Starting Research Council (2-phase)")
        _cb("🚀 Research Council — 5 thành viên, 2 phase")

        # ── Image pre-analysis ───────────────────────────────────────────
        if images:
            _cb("🖼️ Đang phân tích ảnh đính kèm...")
            thinking_parts.append("### 🖼️ Phân tích ảnh")
            try:
                from core.tools import reverse_image_search
                ris = reverse_image_search(image_data_url=images[0])
                if ris.get("sources") or ris.get("similar"):
                    img_parts = []
                    if ris.get("knowledge"):
                        img_parts.append("Knowledge: " + ris["knowledge"])
                    for s in ris.get("sources", [])[:6]:
                        sim = f" ({s['similarity']:.0f}%)" if s.get("similarity") else ""
                        author = f" by {s['author']}" if s.get("author") else ""
                        engine = s["source_engine"]
                        title = s["title"]
                        url = s["url"]
                        img_parts.append(f"- [{engine}]{sim}{author}: {title} → {url}")
                    for s in ris.get("similar", [])[:4]:
                        engine = s["source_engine"]
                        title = s["title"]
                        url = s["url"]
                        img_parts.append(f"- [similar|{engine}]: {title} → {url}")
                    previous_insights = "### Image Context\n" + "\n".join(img_parts)
                    source_count = len(ris.get("sources", []))
                    similar_count = len(ris.get("similar", []))
                    thinking_parts.append(f"Tìm thấy {source_count} nguồn, {similar_count} tương tự")
                    _cb(f"✅ Tìm thấy {source_count} nguồn ảnh")
                else:
                    thinking_parts.append("Không tìm thấy nguồn ảnh")
                    _cb("⚠️ Không tìm thấy nguồn ảnh")
            except Exception as e:
                logger.warning(f"[Reasoning] Image pre-analysis failed: {e}")
                _cb(f"⚠️ Lỗi phân tích ảnh: {e}")

        # ── Phase 1: Wide Exploration ────────────────────────────────────
        _cb(f"🔍 Phase 1 — {self.phase1_width} thành viên khám phá song song...")
        phase1_trajs, phase1_compacted = await self._run_phase1(
            message, context, previous_insights, progress_callback=_cb,
        )
        all_trajectories.extend(phase1_trajs)
        thinking_parts.append(f"### 🔍 Phase 1: Khám phá ({len(phase1_trajs)} thành viên)")
        thinking_parts.append(f"**Compacted:**\n{phase1_compacted}")
        _cb(f"📋 Phase 1 xong — {len(phase1_trajs)} trajectories")

        # Early exit if very high consensus
        avg_conf = sum(t.confidence for t in phase1_trajs) / len(phase1_trajs) if phase1_trajs else 0
        skip_phase2 = avg_conf > 0.9

        # ── Phase 2: Focused Debate ──────────────────────────────────────
        if not skip_phase2:
            _cb(f"💬 Phase 2 — Top {self.phase2_width} thảo luận nhóm...")
            phase2_trajs, phase2_compacted = await self._run_phase2(
                message, context, phase1_trajs, phase1_compacted,
                progress_callback=_cb,
            )
            all_trajectories.extend(phase2_trajs)
            thinking_parts.append(f"### 💬 Phase 2: Thảo luận ({len(phase2_trajs)} thành viên)")
            thinking_parts.append(f"**Compacted:**\n{phase2_compacted}")
            _cb(f"📋 Phase 2 xong — {len(phase2_trajs)} trajectories")
            final_insights = phase2_compacted
            total_phases = 2
        else:
            logger.info("[Reasoning] High consensus (%.0f%%), skipping Phase 2", avg_conf * 100)
            _cb(f"🎯 Consensus cao ({avg_conf:.0%}), bỏ qua Phase 2")
            final_insights = phase1_compacted
            total_phases = 1

        # ── Synthesis ────────────────────────────────────────────────────
        thinking_parts.append("### ✨ Tổng hợp Research Council")
        final_answer = self._synthesize_final_answer(
            message, all_trajectories, final_insights, context,
            progress_callback=_cb,
        )
        _cb("\n✅ Research Council hoàn thành\n")

        reasoning_time = time.time() - start_time
        total_tokens = sum(t.tokens_used for t in all_trajectories)
        logger.info(
            "[Reasoning] Council complete: %d members, %d tokens, %.1fs",
            len(all_trajectories), total_tokens, reasoning_time,
        )

        return CoordinatedReasoningResult(
            final_answer=final_answer,
            thinking_process="\n\n".join(thinking_parts),
            total_rounds=total_phases,
            total_trajectories=len(all_trajectories),
            total_tokens=total_tokens,
            reasoning_time=reasoning_time,
            trajectories=all_trajectories,
        )

    def coordinate_reasoning_sync(
        self,
        message: str,
        context: str = 'casual',
        max_rounds: Optional[int] = None,
        images: Optional[List[str]] = None,
        progress_callback: Optional[Callable] = None,
    ) -> CoordinatedReasoningResult:
        """Synchronous wrapper for coordinated reasoning."""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                self.coordinate_reasoning(
                    message, context, max_rounds,
                    images=images,
                    progress_callback=progress_callback,
                )
            )
        finally:
            loop.close()


# ── Singleton ────────────────────────────────────────────────────────────────

_reasoning_service: Optional[ReasoningService] = None


def get_reasoning_service(ai_service=None) -> ReasoningService:
    """Get or create the reasoning service singleton."""
    global _reasoning_service
    if _reasoning_service is None:
        _reasoning_service = ReasoningService(ai_service)
    elif ai_service is not None:
        _reasoning_service.ai_service = ai_service
    return _reasoning_service
