"""
Core chat router — POST /chat
Mirrors the Flask /chat endpoint with full file-upload, STT, OCR, tool, and MCP support.
"""
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, Request, UploadFile, HTTPException

from fastapi_app.dependencies import get_chatbot_for_session, get_session_id
from fastapi_app.models import ChatRequest, ChatResponse
from fastapi_app.rag_helpers import retrieve_rag_context
from core.config import MEMORY_DIR
from core.extensions import logger

router = APIRouter()

# MCP availability
MCP_AVAILABLE = False
try:
    from src.handlers.mcp_handler import inject_code_context, get_mcp_client
    MCP_AVAILABLE = True
except ImportError:
    pass

# STT / OCR availability
STT_AVAILABLE = False
OCR_AVAILABLE = False
try:
    from src.audio_transcription import is_audio_file, transcribe_audio
    STT_AVAILABLE = True
except ImportError:
    pass
try:
    from src.ocr_integration import extract_file_content
    OCR_AVAILABLE = True
except ImportError:
    pass


def _safe_json(value: str | None, default: Any = None) -> Any:
    if not value or value == "null":
        return default
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default


def _load_memories(memory_ids: list[str]) -> list[dict]:
    memories: list[dict] = []
    for mid in memory_ids:
        path = MEMORY_DIR / f"{mid}.json"
        if path.exists():
            try:
                memories.append(json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                pass
    return memories


async def _process_files(
    files: list[UploadFile], language: str
) -> list[dict[str, str]]:
    """Process uploaded files through STT / OCR extraction."""
    contents: list[dict[str, str]] = []
    for f in files:
        if not f.filename:
            continue
        data = await f.read()
        filename = f.filename
        logger.info(f"[UPLOAD] Processing file: {filename} ({len(data)} bytes)")

        if STT_AVAILABLE and is_audio_file(filename):
            result = transcribe_audio(data, filename, language=language)
            if result["success"] and result["text"]:
                contents.append(
                    {"filename": filename, "content": result["text"], "type": "audio_transcript"}
                )
        elif OCR_AVAILABLE:
            success, text = extract_file_content(data, filename)
            if success and text:
                ext = Path(filename).suffix.lower()
                contents.append(
                    {"filename": filename, "content": text[:10000], "type": ext}
                )
    return contents


def _inject_file_context(message: str, file_contents: list[dict]) -> str:
    if not file_contents:
        return message
    ctx = "\n\n--- UPLOADED FILES ---\n"
    for fc in file_contents:
        if fc["type"] == "audio_transcript":
            ctx += f"\n[Audio transcript from {fc['filename']}]:\n{fc['content']}\n"
        else:
            ext = fc["type"].lstrip(".")
            ctx += f"\n[File: {fc['filename']}]:\n```{ext}\n{fc['content']}\n```\n"
    ctx += "--- END FILES ---\n\n"
    return ctx + message


# ── JSON endpoint ──────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat_json(body: ChatRequest, request: Request):
    """Chat via JSON body (no file uploads)."""
    return await _do_chat(
        request=request,
        message=body.message,
        model=body.model,
        context=body.context,
        deep_thinking=body.deep_thinking,
        language=body.language,
        custom_prompt=body.custom_prompt,
        memory_ids=body.memory_ids,
        history=body.history,
        mcp_selected_files=body.mcp_selected_files,
        agent_config=body.agent_config,
        tools=body.tools,
        rag_collection_ids=body.rag_collection_ids,
        rag_top_k=body.rag_top_k,
    )


# ── Multipart endpoint (file uploads) ─────────────────────────────────

@router.post("/chat/upload", response_model=ChatResponse)
async def chat_upload(
    request: Request,
    message: str = Form(""),
    model: str = Form("grok"),
    context: str = Form("casual"),
    deep_thinking: str = Form("false"),
    language: str = Form("vi"),
    custom_prompt: str = Form(""),
    agent_config: str = Form("null"),
    tools: str = Form("[]"),
    history: str = Form("null"),
    memory_ids: str = Form("[]"),
    mcp_selected_files: str = Form("[]"),
    rag_collection_ids: str = Form("[]"),
    rag_top_k: int = Form(5),
    files: list[UploadFile] = File(default=[]),
):
    """Chat with file uploads (multipart/form-data)."""
    file_contents = await _process_files(files, language)
    message = _inject_file_context(message, file_contents)

    return await _do_chat(
        request=request,
        message=message,
        model=model,
        context=context,
        deep_thinking=deep_thinking == "true",
        language=language,
        custom_prompt=custom_prompt,
        memory_ids=_safe_json(memory_ids, []),
        history=_safe_json(history),
        mcp_selected_files=_safe_json(mcp_selected_files, []),
        agent_config=_safe_json(agent_config),
        tools=_safe_json(tools, []),
        rag_collection_ids=_safe_json(rag_collection_ids, []),
        rag_top_k=rag_top_k,
    )


# ── Shared implementation ─────────────────────────────────────────────

async def _do_chat(
    *,
    request: Request,
    message: str,
    model: str,
    context: str,
    deep_thinking: bool,
    language: str,
    custom_prompt: str,
    memory_ids: list[str],
    history: list | None,
    mcp_selected_files: list[str],
    agent_config: dict | None,
    tools: list[str],
    rag_collection_ids: list[str] | None = None,
    rag_top_k: int = 5,
) -> ChatResponse:
    # Agent config processing
    if agent_config:
        if not custom_prompt and agent_config.get("systemPrompt"):
            custom_prompt = agent_config["systemPrompt"]
        if agent_config.get("injectionPrompt"):
            message = f"{agent_config['injectionPrompt']}\n\n{message}"
        if agent_config.get("contextPrompt"):
            custom_prompt = f"{custom_prompt}\n\n--- Context ---\n{agent_config['contextPrompt']}"
        if agent_config.get("thinkingBudget") == "advanced":
            model = "deepseek-reasoner"
            deep_thinking = True

    if not message:
        raise HTTPException(status_code=400, detail="Empty message")

    # MCP context injection
    if MCP_AVAILABLE:
        try:
            mcp_client = get_mcp_client()
            if mcp_client and mcp_client.enabled:
                message = inject_code_context(message, mcp_client, mcp_selected_files)
        except Exception as e:
            logger.warning(f"[MCP] Error injecting context: {e}")

    chatbot = get_chatbot_for_session(request)
    memories = _load_memories(memory_ids) if memory_ids else None

    # RAG retrieval — shared helper (no logic duplication with stream.py)
    rag = await retrieve_rag_context(
        message=message,
        custom_prompt=custom_prompt,
        language=language,
        tenant_id=get_session_id(request),
        rag_collection_ids=rag_collection_ids or [],
        rag_top_k=rag_top_k,
    )
    message = rag.message
    custom_prompt = rag.custom_prompt

    # Call chatbot
    result = chatbot.chat(
        message=message,
        model=model,
        context=context,
        deep_thinking=deep_thinking,
        history=history,
        memories=memories,
        language=language,
        custom_prompt=custom_prompt,
    )

    response_text = result.get("response", "") if isinstance(result, dict) else str(result)
    thinking = result.get("thinking_process") if isinstance(result, dict) else None

    return ChatResponse(
        response=response_text,
        model=model,
        context=context,
        deep_thinking=deep_thinking,
        thinking_process=thinking,
        citations=rag.citations,
    )
