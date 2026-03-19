"""
Coordinated Reasoning Service
Implements multi-round reasoning inspired by StepFun's approach

This service provides:
1. Auto-detection of question complexity
2. Multi-round parallel exploration
3. Reasoning trajectory compaction
4. Final answer synthesis

Workflow:
    Problem â†’ Model (Parallel Exploration) â†’ Reasoning Trajectories 
    â†’ Compaction Function â†’ Compacted Messages â†’ Final Output
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
import time
import json

logger = logging.getLogger(__name__)


@dataclass
class ReasoningTrajectory:
    """Represents a single reasoning path"""
    id: str
    content: str
    confidence: float = 0.0
    tokens_used: int = 0
    round_number: int = 0
    
    
@dataclass
class CoordinatedReasoningResult:
    """Result from coordinated reasoning process"""
    final_answer: str
    thinking_process: str
    total_rounds: int
    total_trajectories: int
    total_tokens: int
    reasoning_time: float
    trajectories: List[ReasoningTrajectory] = field(default_factory=list)


class ReasoningService:
    """
    Coordinated Reasoning Service
    
    Implements multi-round reasoning with:
    - Parallel exploration of reasoning paths
    - Message compaction between rounds
    - Final synthesis of best answer
    """
    
    # Complexity indicators for auto-detection
    COMPLEXITY_PATTERNS = [
        (r'giáº£i thÃ­ch|explain|why|táº¡i sao|nhÆ° tháº¿ nÃ o|how', 1),
        (r'so sÃ¡nh|compare|difference|khÃ¡c nhau', 1),
        (r'phÃ¢n tÃ­ch|analyze|analysis', 1),
        (r'code|programming|bug|error|lá»—i|debug', 2),
        (r'math|toÃ¡n|calculate|tÃ­nh|equation', 2),
        (r'step by step|tá»«ng bÆ°á»›c|chi tiáº¿t', 1),
        (r'complex|phá»©c táº¡p|nhiá»u bÆ°á»›c', 2),
        (r'optimize|tá»‘i Æ°u|improve|cáº£i thiá»‡n', 1),
        (r'design|thiáº¿t káº¿|architecture|kiáº¿n trÃºc', 2),
        (r'implement|triá»ƒn khai|xÃ¢y dá»±ng|build', 1),
    ]
    
    # Thresholds for auto-mode decision
    COMPLEXITY_THRESHOLD_THINKING = 2  # Use thinking mode
    COMPLEXITY_THRESHOLD_DEEP = 4      # Use deep reasoning
    
    def __init__(self, ai_service=None):
        """
        Initialize reasoning service
        
        Args:
            ai_service: Reference to AIService for making API calls
        """
        self.ai_service = ai_service
        self.max_rounds = 3
        self.max_trajectories_per_round = 3
        
    def estimate_complexity(self, message: str) -> int:
        """
        Estimate the complexity of a question
        
        Returns:
            Complexity score (0-10)
        """
        import re
        
        score = 0
        message_lower = message.lower()
        
        for pattern, weight in self.COMPLEXITY_PATTERNS:
            if re.search(pattern, message_lower):
                score += weight
                
        # Length-based scoring
        if len(message) > 200:
            score += 1
        if len(message) > 500:
            score += 1
        if len(message) > 1000:
            score += 1
            
        # Question mark count
        question_count = message.count('?')
        if question_count > 1:
            score += min(question_count - 1, 2)
            
        return min(score, 10)
    
    def auto_decide_mode(self, message: str) -> str:
        """
        Auto-decide which thinking mode to use
        
        Returns:
            'instant' | 'thinking' | 'deep'
        """
        complexity = self.estimate_complexity(message)
        logger.info(f"[Reasoning] Complexity score: {complexity}")
        
        if complexity >= self.COMPLEXITY_THRESHOLD_DEEP:
            return 'deep'
        elif complexity >= self.COMPLEXITY_THRESHOLD_THINKING:
            return 'thinking'
        else:
            return 'instant'
    
    def should_use_deep_reasoning(self, thinking_mode: str, message: str) -> bool:
        """
        Determine if deep reasoning should be used
        
        Args:
            thinking_mode: Current thinking mode setting
            message: User message
            
        Returns:
            True if deep reasoning should be used
        """
        if thinking_mode == 'deep':
            return True
        elif thinking_mode == 'auto':
            decided_mode = self.auto_decide_mode(message)
            return decided_mode == 'deep'
        return False
    
    async def _generate_trajectory(
        self,
        message: str,
        context: str,
        round_number: int,
        trajectory_id: int,
        previous_insights: str = ""
    ) -> ReasoningTrajectory:
        """
        Generate a single reasoning trajectory
        
        Args:
            message: Original question
            context: Conversation context type
            round_number: Current round number
            trajectory_id: ID of this trajectory
            previous_insights: Insights from previous rounds
        """
        # Build exploration prompt
        exploration_prompt = self._build_exploration_prompt(
            message, round_number, trajectory_id, previous_insights
        )
        
        try:
            # Call AI service (if available)
            if self.ai_service:
                result = self.ai_service.chat(
                    message=exploration_prompt,
                    model='deepseek',  # Use cheaper model for exploration
                    context=context,
                    deep_thinking=True
                )
                content = result.get('text', '')
                tokens = result.get('tokens', 0)
            else:
                # Fallback for testing
                content = f"[Trajectory {trajectory_id}] Reasoning about: {message[:100]}..."
                tokens = 0
                
            return ReasoningTrajectory(
                id=f"r{round_number}_t{trajectory_id}",
                content=content,
                confidence=self._estimate_confidence(content),
                tokens_used=tokens,
                round_number=round_number
            )
        except Exception as e:
            logger.error(f"[Reasoning] Trajectory generation failed: {e}")
            return ReasoningTrajectory(
                id=f"r{round_number}_t{trajectory_id}",
                content=f"Error: {str(e)}",
                confidence=0.0,
                tokens_used=0,
                round_number=round_number
            )
    
    def _build_exploration_prompt(
        self,
        message: str,
        round_number: int,
        trajectory_id: int,
        previous_insights: str
    ) -> str:
        """Build prompt for exploration phase"""
        
        base_prompt = f"""Báº¡n Ä‘ang trong vÃ²ng suy luáº­n thá»© {round_number + 1}.
HÃ£y suy nghÄ© theo má»™t hÆ°á»›ng tiáº¿p cáº­n riÃªng biá»‡t (trajectory {trajectory_id}).

CÃ¢u há»i gá»‘c: {message}

"""
        if previous_insights:
            base_prompt += f"""ThÃ´ng tin tá»« cÃ¡c vÃ²ng trÆ°á»›c:
{previous_insights}

Dá»±a trÃªn thÃ´ng tin nÃ y, hÃ£y:
1. KhÃ¡m phÃ¡ thÃªm cÃ¡c khÃ­a cáº¡nh chÆ°a Ä‘Æ°á»£c Ä‘á» cáº­p
2. ÄÃ o sÃ¢u vÃ o cÃ¡c Ä‘iá»ƒm quan trá»ng
3. ÄÆ°a ra gÃ³c nhÃ¬n má»›i

"""
        
        base_prompt += """HÃ£y suy luáº­n chi tiáº¿t tá»«ng bÆ°á»›c. 
ÄÃ¡nh dáº¥u cÃ¡c insight quan trá»ng vá»›i [INSIGHT].
Káº¿t thÃºc vá»›i [CONCLUSION] tÃ³m táº¯t káº¿t luáº­n chÃ­nh."""

        return base_prompt
    
    def _estimate_confidence(self, content: str) -> float:
        """Estimate confidence level of a reasoning trajectory"""
        # Simple heuristic based on content
        confidence = 0.5
        
        if '[INSIGHT]' in content:
            confidence += 0.1
        if '[CONCLUSION]' in content:
            confidence += 0.1
        if 'cháº¯c cháº¯n' in content.lower() or 'confident' in content.lower():
            confidence += 0.1
        if len(content) > 500:
            confidence += 0.1
        if 'bÆ°á»›c 1' in content.lower() or 'step 1' in content.lower():
            confidence += 0.1
            
        return min(confidence, 1.0)
    
    def _compact_trajectories(
        self,
        trajectories: List[ReasoningTrajectory]
    ) -> str:
        """
        Compact multiple trajectories into a summary
        
        This is the Compaction Function C from the workflow
        """
        if not trajectories:
            return ""
            
        # Extract insights and conclusions
        insights = []
        conclusions = []
        
        for traj in trajectories:
            content = traj.content
            
            # Extract [INSIGHT] sections
            import re
            insight_matches = re.findall(r'\[INSIGHT\](.*?)(?=\[|$)', content, re.DOTALL)
            insights.extend([m.strip() for m in insight_matches if m.strip()])
            
            # Extract [CONCLUSION] sections
            conclusion_matches = re.findall(r'\[CONCLUSION\](.*?)(?=\[|$)', content, re.DOTALL)
            conclusions.extend([m.strip() for m in conclusion_matches if m.strip()])
        
        # Build compacted message
        compacted = []
        
        if insights:
            compacted.append("### Insights Ä‘Ã£ phÃ¡t hiá»‡n:")
            for i, insight in enumerate(insights[:5], 1):  # Limit to 5
                compacted.append(f"{i}. {insight[:200]}...")
                
        if conclusions:
            compacted.append("\n### Káº¿t luáº­n sÆ¡ bá»™:")
            for i, conclusion in enumerate(conclusions[:3], 1):  # Limit to 3
                compacted.append(f"{i}. {conclusion[:300]}...")
                
        return "\n".join(compacted) if compacted else "ChÆ°a cÃ³ insights rÃµ rÃ ng."
    
    async def _run_round(
        self,
        message: str,
        context: str,
        round_number: int,
        previous_insights: str
    ) -> Tuple[List[ReasoningTrajectory], str]:
        """
        Run a single round of coordinated reasoning
        
        Returns:
            Tuple of (trajectories, compacted_insights)
        """
        logger.info(f"[Reasoning] Starting round {round_number + 1}")
        
        # Generate multiple trajectories in parallel
        tasks = []
        for i in range(self.max_trajectories_per_round):
            tasks.append(
                self._generate_trajectory(
                    message, context, round_number, i, previous_insights
                )
            )
        
        # Wait for all trajectories
        trajectories = await asyncio.gather(*tasks)
        
        # Compact trajectories into insights
        compacted = self._compact_trajectories(list(trajectories))
        
        logger.info(f"[Reasoning] Round {round_number + 1} complete: {len(trajectories)} trajectories")
        
        return list(trajectories), compacted
    
    def _synthesize_final_answer(
        self,
        message: str,
        all_trajectories: List[ReasoningTrajectory],
        final_insights: str,
        context: str
    ) -> str:
        """
        Synthesize final answer from all reasoning trajectories
        """
        synthesis_prompt = f"""Dá»±a trÃªn quÃ¡ trÃ¬nh suy luáº­n Ä‘a chiá»u, hÃ£y tá»•ng há»£p cÃ¢u tráº£ lá»i tá»‘t nháº¥t.

CÃ¢u há»i gá»‘c: {message}

CÃ¡c insights Ä‘Ã£ thu tháº­p:
{final_insights}

HÃ£y Ä‘Æ°a ra cÃ¢u tráº£ lá»i toÃ n diá»‡n, chÃ­nh xÃ¡c vÃ  dá»… hiá»ƒu.
Æ¯u tiÃªn cÃ¡c Ä‘iá»ƒm cÃ³ Ä‘á»™ tin cáº­y cao nháº¥t tá»« quÃ¡ trÃ¬nh suy luáº­n."""

        try:
            if self.ai_service:
                result = self.ai_service.chat(
                    message=synthesis_prompt,
                    model='grok',  # Use better model for final synthesis
                    context=context,
                    deep_thinking=True
                )
                return result.get('text', 'KhÃ´ng thá»ƒ tá»•ng há»£p cÃ¢u tráº£ lá»i.')
            else:
                return f"[Synthesized] Answer based on {len(all_trajectories)} trajectories"
        except Exception as e:
            logger.error(f"[Reasoning] Synthesis failed: {e}")
            return f"Lá»—i tá»•ng há»£p: {str(e)}"
    
    async def coordinate_reasoning(
        self,
        message: str,
        context: str = 'casual',
        max_rounds: Optional[int] = None
    ) -> CoordinatedReasoningResult:
        """
        Main entry point for coordinated reasoning
        
        This implements the full workflow:
        1. Multiple rounds of parallel exploration
        2. Compaction after each round
        3. Final synthesis
        
        Args:
            message: User's question
            context: Conversation context type
            max_rounds: Override max rounds
            
        Returns:
            CoordinatedReasoningResult with full reasoning trace
        """
        start_time = time.time()
        rounds = max_rounds or self.max_rounds
        
        all_trajectories = []
        current_insights = ""
        thinking_parts = []
        
        logger.info(f"[Reasoning] Starting coordinated reasoning with {rounds} rounds")
        
        # Run multiple rounds
        for round_num in range(rounds):
            trajectories, compacted = await self._run_round(
                message, context, round_num, current_insights
            )
            
            all_trajectories.extend(trajectories)
            current_insights = compacted
            
            # Build thinking display
            thinking_parts.append(f"### ðŸ”„ VÃ²ng {round_num + 1}")
            thinking_parts.append(f"ÄÃ£ khÃ¡m phÃ¡ {len(trajectories)} hÆ°á»›ng suy luáº­n")
            thinking_parts.append(f"**Insights:**\n{compacted}\n")
            
            # Early exit if high confidence reached
            avg_confidence = sum(t.confidence for t in trajectories) / len(trajectories)
            if avg_confidence > 0.85:
                logger.info(f"[Reasoning] High confidence ({avg_confidence:.2f}), stopping early")
                break
        
        # Synthesize final answer
        thinking_parts.append("### âœ¨ Tá»•ng há»£p cÃ¢u tráº£ lá»i")
        final_answer = self._synthesize_final_answer(
            message, all_trajectories, current_insights, context
        )
        
        reasoning_time = time.time() - start_time
        total_tokens = sum(t.tokens_used for t in all_trajectories)
        
        logger.info(f"[Reasoning] Complete: {len(all_trajectories)} trajectories, {reasoning_time:.2f}s")
        
        return CoordinatedReasoningResult(
            final_answer=final_answer,
            thinking_process="\n\n".join(thinking_parts),
            total_rounds=round_num + 1,
            total_trajectories=len(all_trajectories),
            total_tokens=total_tokens,
            reasoning_time=reasoning_time,
            trajectories=all_trajectories
        )
    
    def coordinate_reasoning_sync(
        self,
        message: str,
        context: str = 'casual',
        max_rounds: Optional[int] = None
    ) -> CoordinatedReasoningResult:
        """
        Synchronous wrapper for coordinated reasoning
        """
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                self.coordinate_reasoning(message, context, max_rounds)
            )
        finally:
            loop.close()


# Singleton instance
_reasoning_service: Optional[ReasoningService] = None


def get_reasoning_service(ai_service=None) -> ReasoningService:
    """Get or create the reasoning service singleton"""
    global _reasoning_service
    if _reasoning_service is None:
        _reasoning_service = ReasoningService(ai_service)
    elif ai_service is not None:
        _reasoning_service.ai_service = ai_service
    return _reasoning_service
