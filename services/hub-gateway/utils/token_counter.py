"""
Token Counter Utility
Count tokens for API usage tracking
"""

import logging

logger = logging.getLogger("ai_assistant_hub")


def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    """
    Estimate token count for text.
    
    Args:
        text: Input text
        model: Model name for accurate counting
    
    Returns:
        Estimated token count
    """
    try:
        # Try using tiktoken for accurate counting
        import tiktoken
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except ImportError:
        # Fallback to simple estimation (1 token ≈ 4 characters)
        return len(text) // 4
    except Exception as e:
        logger.warning(f"Error counting tokens: {e}. Using fallback method.")
        return len(text) // 4


def estimate_cost(tokens: int, model: str = "gpt-3.5-turbo") -> float:
    """
    Estimate API cost based on token count.
    
    Args:
        tokens: Number of tokens
        model: Model name
    
    Returns:
        Estimated cost in USD
    """
    # Pricing per 1K tokens (as of 2025)
    pricing = {
        "gpt-3.5-turbo": 0.0015,  # $0.0015 per 1K tokens
        "gpt-4": 0.03,            # $0.03 per 1K tokens
        "grok-3": 0.00025,        # $0.00025 per 1K tokens
        "deepseek": 0.0002,       # $0.0002 per 1K tokens
    }
    
    price_per_1k = pricing.get(model, 0.001)
    return (tokens / 1000) * price_per_1k
