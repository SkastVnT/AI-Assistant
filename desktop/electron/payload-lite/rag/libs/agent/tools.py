"""Agent tools — protocol + concrete implementations.

Each tool wraps an existing platform capability (retrieval, guardrails, etc.)
behind a uniform interface. The planner sees tool names + descriptions;
the controller dispatches calls and captures results.

Tools enforce delegated authorization: every tool receives the caller's
AuthContext and must never exceed those permissions.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from libs.agent.types import ToolCall, ToolResult

if TYPE_CHECKING:
    from libs.auth.context import AuthContext

logger = logging.getLogger("rag.agent.tools")


# ═══════════════════════════════════════════════════════════════════════
# Tool protocol
# ═══════════════════════════════════════════════════════════════════════


@runtime_checkable
class AgentTool(Protocol):
    """Interface that every agent tool must implement."""

    @property
    def name(self) -> str:
        """Unique tool identifier used by the planner."""
        ...

    @property
    def description(self) -> str:
        """Human-readable description shown to the LLM planner."""
        ...

    @property
    def parameters_schema(self) -> dict:
        """JSON Schema describing the tool's input parameters."""
        ...

    async def execute(
        self,
        call: ToolCall,
        auth: AuthContext,
    ) -> ToolResult:
        """Run the tool within the caller's auth scope."""
        ...


# ═══════════════════════════════════════════════════════════════════════
# Tool registry
# ═══════════════════════════════════════════════════════════════════════


class ToolRegistry:
    """Central registry of available tools.

    The planner queries the registry for tool descriptions;
    the controller dispatches calls by name.
    """

    def __init__(self) -> None:
        self._tools: dict[str, AgentTool] = {}

    def register(self, tool: AgentTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> AgentTool | None:
        return self._tools.get(name)

    def available_tools(self) -> list[dict]:
        """Return tool descriptions for the LLM planner prompt."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters_schema,
            }
            for t in self._tools.values()
        ]

    @property
    def tool_names(self) -> list[str]:
        return list(self._tools.keys())


# ═══════════════════════════════════════════════════════════════════════
# Retriever Tool — wraps the existing retrieval + answer pipeline
# ═══════════════════════════════════════════════════════════════════════


class RetrieverTool:
    """Search the knowledge base and return relevant evidence chunks.

    Wraps the platform's retrieve() function. Inherits tenant isolation,
    sensitivity filtering, and hybrid retrieval from the existing pipeline.
    """

    def __init__(self, retrieve_fn) -> None:
        """Accept the retrieve() async function from libs.retrieval.service."""
        self._retrieve = retrieve_fn

    @property
    def name(self) -> str:
        return "retriever"

    @property
    def description(self) -> str:
        return (
            "Search the internal knowledge base for relevant information. "
            "Returns text passages with citation metadata. Use this tool to "
            "find facts, definitions, procedures, or any information stored "
            "in the organisation's documents."
        )

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to find relevant passages.",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return (1-20).",
                    "default": 5,
                },
            },
            "required": ["query"],
        }

    async def execute(
        self,
        call: ToolCall,
        auth: AuthContext,
    ) -> ToolResult:
        query = call.arguments.get("query", "")
        top_k = min(int(call.arguments.get("top_k", 5)), 20)

        try:
            result = await self._retrieve(
                tenant_id=auth.tenant_id,
                user_id=auth.user_id,
                query=query,
                top_k=top_k,
            )
            chunks_text = []
            for i, chunk in enumerate(result.get("chunks", []), 1):
                source = chunk.get("filename", "unknown")
                text = chunk.get("content", "")[:500]
                score = chunk.get("score", 0.0)
                chunks_text.append(
                    f"[Source {i}] ({source}, score={score:.2f})\n{text}"
                )
            output = "\n\n".join(chunks_text) if chunks_text else "No results found."
            return ToolResult(
                call_id=call.call_id,
                tool_name=self.name,
                output=output,
                metadata={"chunks_count": len(chunks_text), "query": query},
            )
        except Exception as exc:
            logger.exception("retriever_tool_error")
            return ToolResult(
                call_id=call.call_id,
                tool_name=self.name,
                output="",
                success=False,
                error=str(exc),
            )


# ═══════════════════════════════════════════════════════════════════════
# Web Search Tool — placeholder for future implementation
# ═══════════════════════════════════════════════════════════════════════


class WebSearchTool:
    """Search the public web for current information.

    Placeholder — returns a message that the tool is not yet configured.
    When implemented, should call a search API (Tavily, Bing, SerpAPI).
    """

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return (
            "Search the public web for current or external information. "
            "Use when internal knowledge base doesn't have the answer, "
            "or the question requires up-to-date facts."
        )

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Web search query.",
                },
            },
            "required": ["query"],
        }

    async def execute(
        self,
        call: ToolCall,
        auth: AuthContext,
    ) -> ToolResult:
        return ToolResult(
            call_id=call.call_id,
            tool_name=self.name,
            output="[Web search not configured] This tool is a placeholder. "
            "No external web search was performed.",
            success=True,
            metadata={"placeholder": True},
        )


# ═══════════════════════════════════════════════════════════════════════
# Python Execution Tool — placeholder for sandboxed code execution
# ═══════════════════════════════════════════════════════════════════════


class PythonTool:
    """Execute Python code in a sandboxed environment.

    Placeholder — returns a message that the tool is not yet configured.
    When implemented, should use a sandbox (E2B, Modal, Docker container).
    """

    @property
    def name(self) -> str:
        return "python"

    @property
    def description(self) -> str:
        return (
            "Execute Python code for calculations, data transformations, "
            "or analysis. Use when the query requires computation rather "
            "than information retrieval."
        )

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute.",
                },
            },
            "required": ["code"],
        }

    async def execute(
        self,
        call: ToolCall,
        auth: AuthContext,
    ) -> ToolResult:
        return ToolResult(
            call_id=call.call_id,
            tool_name=self.name,
            output="[Python sandbox not configured] This tool is a placeholder. "
            "No code was executed.",
            success=True,
            metadata={"placeholder": True},
        )


# ═══════════════════════════════════════════════════════════════════════
# Policy Check Tool — content compliance verification
# ═══════════════════════════════════════════════════════════════════════


class PolicyCheckTool:
    """Check whether a proposed answer complies with organisational policies.

    Wraps the existing guardrail pipeline to verify answers before
    returning them to the user.
    """

    def __init__(self, validate_fn=None) -> None:
        """Accept an optional policy validation function.

        If None, uses a basic length + content heuristic.
        """
        self._validate = validate_fn

    @property
    def name(self) -> str:
        return "policy_check"

    @property
    def description(self) -> str:
        return (
            "Verify that a draft answer complies with content policies, "
            "sensitivity rules, and organisational guidelines. Use before "
            "finalising an answer that references sensitive topics."
        )

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "answer_draft": {
                    "type": "string",
                    "description": "The draft answer to check for policy compliance.",
                },
            },
            "required": ["answer_draft"],
        }

    async def execute(
        self,
        call: ToolCall,
        auth: AuthContext,
    ) -> ToolResult:
        draft = call.arguments.get("answer_draft", "")

        if self._validate:
            try:
                result = await self._validate(draft, auth)
                return ToolResult(
                    call_id=call.call_id,
                    tool_name=self.name,
                    output=json.dumps(result) if isinstance(result, dict) else str(result),
                    metadata={"validated": True},
                )
            except Exception as exc:
                return ToolResult(
                    call_id=call.call_id,
                    tool_name=self.name,
                    output="",
                    success=False,
                    error=str(exc),
                )

        # Default heuristic check
        issues: list[str] = []
        if len(draft) < 10:
            issues.append("Answer is too short (less than 10 characters).")
        if len(draft) > 10000:
            issues.append("Answer exceeds maximum length (10000 characters).")
        if not issues:
            output = "PASS: No policy violations detected."
        else:
            output = "ISSUES:\n" + "\n".join(f"- {i}" for i in issues)

        return ToolResult(
            call_id=call.call_id,
            tool_name=self.name,
            output=output,
            metadata={"issues_count": len(issues)},
        )


# ═══════════════════════════════════════════════════════════════════════
# Factory
# ═══════════════════════════════════════════════════════════════════════


def build_tool_registry(
    *,
    retrieve_fn=None,
    validate_fn=None,
    enable_web: bool = False,
    enable_python: bool = False,
) -> ToolRegistry:
    """Build a ToolRegistry with the standard set of tools.

    Parameters
    ----------
    retrieve_fn:
        Async function matching the retriever tool's expected signature.
    validate_fn:
        Optional async policy validation function.
    enable_web:
        Register the web search placeholder.
    enable_python:
        Register the python execution placeholder.
    """
    registry = ToolRegistry()

    if retrieve_fn is not None:
        registry.register(RetrieverTool(retrieve_fn))

    registry.register(PolicyCheckTool(validate_fn))

    if enable_web:
        registry.register(WebSearchTool())
    if enable_python:
        registry.register(PythonTool())

    return registry
