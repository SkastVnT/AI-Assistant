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

from fastapi_app.dependencies import (
    get_chatbot_for_session,
    get_session_id,
    get_image_orchestrator_for_session,
    use_new_image_orchestrator,
    get_new_orchestration_service,
)
from fastapi_app.models import ChatRequest, ChatResponse
from fastapi_app.rag_helpers import retrieve_rag_context
from core.config import MEMORY_DIR
from core.extensions import logger
from core.agentic.council_entry import is_council_enabled, run_council
from core.agentic.xai_native.entrypoint import run_xai_native

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


# ── Image orchestration helper (extracted for clarity) ─────────────────

_LOCAL_PROVIDERS = frozenset({"comfyui", "stable-diffusion", "sd-webui"})


def _image_result_metadata(
    result,
    *,
    pipeline: str,
    session_id: str = "",
) -> dict:
    """
    Build the image_result dict for ChatResponse.

    Adds safe extra metadata fields on top of the existing shape so the
    frontend can read them when ready without breaking anything.
    """
    provider = getattr(result, "provider", "") or ""
    intent_val = getattr(result.intent, "value", str(result.intent)) if hasattr(result, "intent") else "generate"
    is_edit = intent_val in ("edit", "followup_edit")

    # Determine backend type from provider name
    used_local  = provider.lower() in _LOCAL_PROVIDERS
    used_remote = bool(provider) and not used_local

    # Scene spec summary (only available from the new pipeline)
    scene_summary = None
    scene = getattr(result, "scene", None)
    if scene is not None:
        scene_summary = {
            "subject":     getattr(scene, "subject", ""),
            "style":       getattr(scene, "style", ""),
            "background":  getattr(scene, "background", ""),
            "lighting":    getattr(scene, "lighting", ""),
            "mood":        getattr(scene, "mood", ""),
            "is_edit":     is_edit,
            "strength":    getattr(scene, "strength", None),
        }

    # Try to read lineage from session memory (new pipeline only)
    edit_lineage = None
    if pipeline == "new" and session_id:
        try:
            from app.services.image_orchestrator.session_memory import get_session_memory_store
            mem = get_session_memory_store().get(session_id)
            if mem is not None:
                edit_lineage = mem.edit_lineage_count
        except Exception:
            pass

    return {
        # ── Existing fields (backward compatible) ──
        "intent":          intent_val,
        "provider":        provider,
        "model":           getattr(result, "model", ""),
        "images_url":      getattr(result, "images_url", []),
        "images_b64":      getattr(result, "images_b64", []),
        "enhanced_prompt": getattr(result, "enhanced_prompt", ""),
        "cost_usd":        getattr(result, "cost_usd", 0.0),
        "latency_ms":      getattr(result, "latency_ms", 0.0),
        # ── New metadata fields (safe additions) ──
        "request_kind":               intent_val,
        "provider_selected":          provider,
        "used_local_backend":         used_local,
        "used_remote_backend":        used_remote,
        "scene_spec_summary":         scene_summary,
        "used_previous_image_context": is_edit,
        "pipeline":                   pipeline,
        "edit_lineage":               edit_lineage,
    }


def _try_image_orchestration(
    *,
    request: Request,
    original_message: str,
    language: str,
    tools: list[str],
    image_quality: str,
    model: str,
    context: str,
    deep_thinking: bool,
) -> ChatResponse | None:
    """
    Attempt image generation via the new or legacy orchestrator.

    Returns a ChatResponse if an image was generated, or None to fall
    through to the LLM path.  When USE_NEW_IMAGE_ORCHESTRATOR=1, the
    new pipeline runs first with an automatic internal fallback to legacy.
    When the flag is off, the legacy pipeline runs directly (unchanged
    behavior from before this integration).
    """
    session_id = get_session_id(request)

    # ── New pipeline (feature-flagged) ────────────────────────────────
    if use_new_image_orchestrator():
        new_svc = get_new_orchestration_service()
        if new_svc is not None:
            new_result = new_svc.handle(
                message    = original_message,
                session_id = session_id,
                language   = language,
                tools      = tools,
                quality    = image_quality,
            )
            if new_result.is_image:
                logger.info(
                    f"[Chat] 🎨 Image generated (new pipeline) — "
                    f"intent={new_result.intent.value} provider={new_result.provider} "
                    f"cost=${new_result.cost_usd:.4f}"
                )
                return ChatResponse(
                    response      = new_result.response_text,
                    model         = model,
                    context       = context,
                    deep_thinking = deep_thinking,
                    image_result  = _image_result_metadata(
                        new_result, pipeline="new", session_id=session_id,
                    ),
                )
            # fallback_to_llm=True from new pipeline → fall through to LLM
            return None

    # ── Legacy pipeline (default, or when new pipeline unavailable) ───
    orchestrator = get_image_orchestrator_for_session(request)
    if orchestrator is not None:
        _orch_msg = original_message
        if image_quality and image_quality != "auto":
            _orch_msg = f"{original_message} [{image_quality}]"
        orch_result = orchestrator.handle(
            message  = _orch_msg,
            language = language,
            tools    = tools,
        )
        if orch_result.is_image:
            logger.info(
                f"[Chat] 🎨 Image generated (legacy) — "
                f"intent={orch_result.intent.value} provider={orch_result.provider} "
                f"cost=${orch_result.cost_usd:.4f}"
            )
            return ChatResponse(
                response      = orch_result.response_text,
                model         = model,
                context       = context,
                deep_thinking = deep_thinking,
                image_result  = _image_result_metadata(
                    orch_result, pipeline="legacy", session_id=session_id,
                ),
            )

    return None


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
        agent_mode=body.agent_mode,
        max_agent_iterations=body.max_agent_iterations,
        preferred_planner_model=body.preferred_planner_model,
        preferred_researcher_model=body.preferred_researcher_model,
        preferred_critic_model=body.preferred_critic_model,
        preferred_synthesizer_model=body.preferred_synthesizer_model,
        reasoning_effort=body.reasoning_effort,
        enable_web_search=body.enable_web_search,
        enable_x_search=body.enable_x_search,
        enable_image_gen=body.enable_image_gen,
        image_quality=body.image_quality,
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
    agent_mode: str = Form("off"),
    max_agent_iterations: int = Form(2),
    preferred_planner_model: str = Form(""),
    preferred_researcher_model: str = Form(""),
    preferred_critic_model: str = Form(""),
    preferred_synthesizer_model: str = Form(""),
    reasoning_effort: str = Form("high"),
    enable_web_search: bool = Form(True),
    enable_x_search: bool = Form(False),
    enable_image_gen: bool = Form(True),
    image_quality: str = Form("auto"),
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
        agent_mode=agent_mode,
        max_agent_iterations=max_agent_iterations,
        preferred_planner_model=preferred_planner_model or None,
        preferred_researcher_model=preferred_researcher_model or None,
        preferred_critic_model=preferred_critic_model or None,
        preferred_synthesizer_model=preferred_synthesizer_model or None,
        reasoning_effort=reasoning_effort,
        enable_web_search=enable_web_search,
        enable_x_search=enable_x_search,
        enable_image_gen=enable_image_gen,
        image_quality=image_quality,
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
    # ── Council parameters (defaults keep backward compat) ──
    agent_mode: str = "off",
    max_agent_iterations: int = 2,
    preferred_planner_model: str | None = None,
    preferred_researcher_model: str | None = None,
    preferred_critic_model: str | None = None,
    preferred_synthesizer_model: str | None = None,
    # ── xAI native parameters ──
    reasoning_effort: str = "high",
    enable_web_search: bool = True,
    enable_x_search: bool = False,
    # ── Image orchestration parameters ──
    enable_image_gen: bool = True,
    image_quality: str = "auto",
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

    # Save original message before MCP/RAG augmentation (for council)
    original_message = message
    mcp_context = ""

    # MCP context injection
    if MCP_AVAILABLE:
        try:
            mcp_client = get_mcp_client()
            if mcp_client and mcp_client.enabled:
                augmented = inject_code_context(message, mcp_client, mcp_selected_files)
                # Capture the injected MCP context for council mode
                if augmented != message:
                    mcp_context = augmented[: augmented.find(message)] if message in augmented else ""
                message = augmented
        except Exception as e:
            logger.warning(f"[MCP] Error injecting context: {e}")

    # ── Image Orchestration branch (before LLM) ────────────────────
    # Fast keyword-based intent detection — no extra latency when not triggered.
    # Falls through safely to LLM if disabled, no providers, or intent=NONE.
    if enable_image_gen and agent_mode == "off":
        try:
            image_response = _try_image_orchestration(
                request=request,
                original_message=original_message,
                language=language,
                tools=tools,
                image_quality=image_quality,
                model=model,
                context=context,
                deep_thinking=deep_thinking,
            )
            if image_response is not None:
                return image_response
            # fallback_to_llm=True → proceed normally below
        except Exception as _orch_err:
            logger.warning(f"[Chat] Orchestrator error (falling back to LLM): {_orch_err}")

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

    # ── Council branch ─────────────────────────────────────────────
    if agent_mode == "council":
        council_result = await run_council(
            original_message=original_message,
            augmented_message=message,
            language=language,
            context_type=context,
            custom_prompt=custom_prompt,
            rag_chunks=None,
            rag_citations=rag.citations,
            mcp_context=mcp_context,
            max_agent_iterations=max_agent_iterations,
            preferred_planner_model=preferred_planner_model,
            preferred_researcher_model=preferred_researcher_model,
            preferred_critic_model=preferred_critic_model,
            preferred_synthesizer_model=preferred_synthesizer_model,
        )
        return ChatResponse(**council_result)

    # ── xAI native multi-agent branch ──────────────────────────────
    if agent_mode == "grok_native_research":
        xai_result = await run_xai_native(
            original_message=original_message,
            augmented_message=message,
            language=language,
            context_type=context,
            custom_prompt=custom_prompt,
            rag_context="",
            rag_citations=rag.citations,
            mcp_context=mcp_context,
            reasoning_effort=reasoning_effort,
            enable_web_search=enable_web_search,
            enable_x_search=enable_x_search,
        )
        return ChatResponse(**xai_result)

    # ── Standard single-model path ─────────────────────────────────
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
