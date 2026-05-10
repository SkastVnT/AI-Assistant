from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class RouterDecision:
    intent: str
    pipeline: str
    model: str
    confidence: float
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


def route_request(user_input: str) -> RouterDecision:
    text = (user_input or "").strip().lower()

    if any(k in text for k in ("git ", "sql", "database", "read file", "write file", "mcp")):
        return RouterDecision("tool_ops", "mcp_tool_flow", "hermes3", 0.9, "Tool operation request")
    if any(k in text for k in ("anime", "waifu", "reference image", "danbooru")):
        return RouterDecision("image_anime", "anime_pipeline", "image_router", 0.9, "Anime style image request")
    if any(k in text for k in ("tạo ảnh", "generate image", "edit image", "draw image")):
        return RouterDecision("image_general", "image_gen", "image_router", 0.85, "General image generation request")
    if any(k in text for k in ("web search", "latest", "news", "research online")):
        return RouterDecision("web_research", "xai_native", "grok", 0.83, "Web research request")
    if any(k in text for k in ("analyze", "phân tích", "reason", "tradeoff", "brainstorm")):
        return RouterDecision("deep_reasoning", "hermes", "hermes3", 0.78, "Long-form reasoning request")
    if any(k in text for k in ("citation", "repo", "rag", "sources", "file context")):
        return RouterDecision("grounded_analysis", "council", "hermes3", 0.8, "Likely needs tools/RAG")

    return RouterDecision("general_chat", "normal_chat", "default_chat", 0.7, "Default chat path")
