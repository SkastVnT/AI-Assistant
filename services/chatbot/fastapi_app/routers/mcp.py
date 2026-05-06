"""
MCP (Model Context Protocol) integration routes — /api/mcp/*
Mirrors Flask routes/mcp.py and chatbot_main.py MCP routes.
"""
import base64
import mimetypes
import random
import re
from pathlib import Path

import httpx
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from core.extensions import logger
from core.url_safety import assert_safe_external_url

router = APIRouter(prefix="/api/mcp", tags=["MCP"])

# ---------------------------------------------------------------------------
# MCP client availability
# ---------------------------------------------------------------------------
MCP_AVAILABLE = False
mcp_client = None

try:
    from src.utils.mcp_integration import get_mcp_client, inject_code_context
    mcp_client = get_mcp_client()
    MCP_AVAILABLE = True
    logger.info("MCP integration loaded in FastAPI routes")
except ImportError as e:
    logger.warning(f"MCP integration not available: {e}")


def _mcp_unavailable() -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"success": False, "error": "MCP integration is not available"},
    )


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

@router.get("/status")
async def mcp_status():
    """Get MCP client status."""
    try:
        if not MCP_AVAILABLE or mcp_client is None:
            return {
                "success": True,
                "status": {
                    "available": False,
                    "enabled": False,
                    "message": "MCP integration module not installed",
                },
            }
        return {"success": True, "status": mcp_client.get_status()}
    except Exception as e:
        logger.error(f"MCP status error: {e}")
        raise HTTPException(500, "Failed to get MCP status")


# ---------------------------------------------------------------------------
# Enable / Disable
# ---------------------------------------------------------------------------

@router.post("/enable")
async def mcp_enable():
    if not MCP_AVAILABLE or mcp_client is None:
        return _mcp_unavailable()
    try:
        success = mcp_client.enable()
        return {"success": success, "status": mcp_client.get_status()}
    except Exception as e:
        logger.error(f"MCP enable error: {e}")
        raise HTTPException(500, "Failed to enable MCP")


@router.post("/disable")
async def mcp_disable():
    if not MCP_AVAILABLE or mcp_client is None:
        return _mcp_unavailable()
    try:
        mcp_client.disable()
        return {"success": True, "status": mcp_client.get_status()}
    except Exception as e:
        logger.error(f"MCP disable error: {e}")
        raise HTTPException(500, "Failed to disable MCP")


# ---------------------------------------------------------------------------
# Folder management
# ---------------------------------------------------------------------------

class FolderBody(BaseModel):
    folder_path: str


@router.post("/add-folder")
async def mcp_add_folder(body: FolderBody):
    if not MCP_AVAILABLE or mcp_client is None:
        return _mcp_unavailable()
    try:
        if not body.folder_path:
            raise HTTPException(400, "folder_path is required")
        success = mcp_client.add_folder(body.folder_path)
        return {"success": success, "status": mcp_client.get_status()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MCP add-folder error: {e}")
        raise HTTPException(500, "Failed to add folder")


@router.post("/remove-folder")
async def mcp_remove_folder(body: FolderBody):
    if not MCP_AVAILABLE or mcp_client is None:
        return _mcp_unavailable()
    try:
        if not body.folder_path:
            raise HTTPException(400, "folder_path is required")
        mcp_client.remove_folder(body.folder_path)
        return {"success": True, "status": mcp_client.get_status()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MCP remove-folder error: {e}")
        raise HTTPException(500, "Failed to remove folder")


# ---------------------------------------------------------------------------
# File listing / search / read
# ---------------------------------------------------------------------------

@router.get("/list-files")
async def mcp_list_files(folder: str | None = None):
    if not MCP_AVAILABLE or mcp_client is None:
        return _mcp_unavailable()
    try:
        files = mcp_client.list_files_in_folder(folder)
        return {"success": True, "files": files, "count": len(files)}
    except Exception as e:
        logger.error(f"MCP list-files error: {e}")
        raise HTTPException(500, "Failed to list files")


@router.get("/search-files")
async def mcp_search_files(query: str = "", type: str = "all"):
    if not MCP_AVAILABLE or mcp_client is None:
        return _mcp_unavailable()
    try:
        files = mcp_client.search_files(query, type)
        return {"success": True, "files": files, "count": len(files)}
    except Exception as e:
        logger.error(f"MCP search-files error: {e}")
        raise HTTPException(500, "Failed to search files")


@router.get("/read-file")
async def mcp_read_file(path: str | None = None, max_lines: int = 500):
    if not MCP_AVAILABLE or mcp_client is None:
        return _mcp_unavailable()
    try:
        if not path:
            raise HTTPException(400, "path is required")
        content = mcp_client.read_file(path, max_lines)
        if content and "error" in content:
            raise HTTPException(400, content["error"])
        return {"success": True, "content": content}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MCP read-file error: {e}")
        raise HTTPException(500, "Failed to read file")


# ---------------------------------------------------------------------------
# Grep
# ---------------------------------------------------------------------------

@router.get("/grep")
async def mcp_grep(
    pattern: str = "",
    type: str = "all",
    max_results: int = 30,
    case_sensitive: bool = False,
    regex: bool = False,
):
    if not MCP_AVAILABLE or mcp_client is None:
        return _mcp_unavailable()
    try:
        if not pattern:
            raise HTTPException(400, "pattern is required")
        results = mcp_client.grep_content(
            pattern=pattern,
            file_type=type,
            max_results=max_results,
            case_sensitive=case_sensitive,
            regex=regex,
        )
        return {"success": True, "pattern": pattern, "results": results, "count": len(results)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MCP grep error: {e}")
        raise HTTPException(500, "Failed to grep files")


# ---------------------------------------------------------------------------
# OCR extract
# ---------------------------------------------------------------------------

class OcrBody(BaseModel):
    path: str = ""
    max_chars: int = 6000


@router.post("/ocr-extract")
async def mcp_ocr_extract(body: OcrBody):
    if not MCP_AVAILABLE or mcp_client is None:
        return _mcp_unavailable()
    try:
        file_path = body.path.strip()
        if not file_path:
            raise HTTPException(400, "path is required")
        max_chars = max(500, min(body.max_chars, 50_000))
        result = mcp_client.extract_file_with_ocr(file_path=file_path, max_chars=max_chars)
        status = 200 if result.get("success") else 400
        return JSONResponse(status_code=status, content=result)
    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(400, "Invalid max_chars")
    except Exception as e:
        logger.error(f"MCP ocr-extract error: {e}")
        raise HTTPException(500, "Failed to extract OCR text")


# ---------------------------------------------------------------------------
# Warm cache
# ---------------------------------------------------------------------------

class WarmCacheBody(BaseModel):
    question: str = ""
    domain: str | None = None
    extra_queries: list[str] | None = None
    force_refresh: bool = False
    cache_ttl_seconds: int = 900
    limit: int = 20
    min_importance: int = 4
    max_chars: int = 12000


@router.post("/warm-cache")
async def mcp_warm_cache(body: WarmCacheBody):
    if not MCP_AVAILABLE or mcp_client is None:
        return _mcp_unavailable()
    try:
        question = body.question.strip()
        if not question:
            raise HTTPException(400, "question is required")
        result = mcp_client.warm_memory_cache_by_question(
            question=question,
            domain=body.domain,
            extra_queries=body.extra_queries,
            force_refresh=body.force_refresh,
            cache_ttl_seconds=body.cache_ttl_seconds,
            limit=body.limit,
            min_importance=body.min_importance,
            max_chars=body.max_chars,
        )
        status = 200 if result.get("success") else 503
        return JSONResponse(status_code=status, content=result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MCP warm-cache error: {e}")
        raise HTTPException(500, "Failed to warm memory cache")


# ---------------------------------------------------------------------------
# Fetch URL
# ---------------------------------------------------------------------------

class FetchUrlBody(BaseModel):
    url: str


_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]


@router.post("/fetch-url")
async def mcp_fetch_url(body: FetchUrlBody):
    """Fetch and extract text content from a URL."""
    url = body.url.strip()
    if not url:
        raise HTTPException(400, "url is required")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        assert_safe_external_url(url)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    from urllib.parse import urlparse
    parsed = urlparse(url)
    domain = parsed.netloc

    headers = {
        "User-Agent": random.choice(_USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
        "Referer": f"https://www.google.com/search?q={domain}",
    }

    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 403:
                headers["User-Agent"] = random.choice(_USER_AGENTS)
                resp = await client.get(url, headers=headers)
            try:
                assert_safe_external_url(str(resp.url))
            except ValueError as exc:
                raise HTTPException(400, f"Unsafe redirect target: {exc}")
            resp.raise_for_status()

        content_type = resp.headers.get("content-type", "").lower()
        extracted = ""
        title = url

        if any(t in content_type for t in ("image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp")):
            try:
                from src.ocr_integration import ocr_client
                img_b64 = base64.b64encode(resp.content).decode()
                extracted = ocr_client.extract_text_from_image(img_b64)
                title = f"Image: {url.split('/')[-1]}"
            except Exception as e:
                logger.warning(f"OCR for image URL failed: {e}")
                extracted = f"[Image content from: {url}]"

        elif "application/pdf" in content_type:
            try:
                from src.ocr_integration import ocr_client
                pdf_b64 = base64.b64encode(resp.content).decode()
                extracted = ocr_client.extract_text_from_pdf(pdf_b64)
                title = f"PDF: {url.split('/')[-1]}"
            except Exception as e:
                logger.warning(f"PDF extraction for URL failed: {e}")
                extracted = f"[PDF content from: {url}]"

        elif "text/html" in content_type:
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, "html.parser")
                title_tag = soup.find("title")
                if title_tag:
                    title = title_tag.get_text(strip=True)
                for el in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
                    el.decompose()
                main = soup.find("main") or soup.find("article") or soup.find("div", {"class": ["content", "main", "post"]})
                raw = (main or soup.find("body") or soup).get_text(separator="\n", strip=True)
                extracted = re.sub(r"\n{3,}", "\n\n", raw)[:10000]
            except ImportError:
                extracted = resp.text[:10000]

        elif "text/" in content_type or "application/json" in content_type:
            extracted = resp.text[:10000]
            title = f"Text: {url.split('/')[-1]}"
        else:
            extracted = f"[Binary content from: {url}]"

        return {"success": True, "url": url, "title": title, "content": extracted, "content_type": content_type}

    except httpx.TimeoutException:
        raise HTTPException(408, "Request timeout - URL took too long to respond")
    except httpx.HTTPStatusError as e:
        code = e.response.status_code
        msg = {
            403: "403 Forbidden - Website blocked access (possible bot protection)",
            401: "401 Unauthorized - Website requires authentication",
            404: "404 Not Found - Page does not exist",
            429: "429 Too Many Requests - Rate limited",
            503: "503 Service Unavailable",
        }.get(code, str(e))
        logger.error(f"MCP fetch-url HTTP error {code}: {e}")
        return JSONResponse(status_code=400, content={"success": False, "error": msg, "status_code": code})
    except Exception as e:
        logger.error(f"MCP fetch-url error: {e}")
        raise HTTPException(500, "Failed to process URL content")


# ---------------------------------------------------------------------------
# Upload file (for MCP context — OCR + text extraction)
# ---------------------------------------------------------------------------

@router.post("/upload-file")
async def mcp_upload_file(file: UploadFile = File(...)):
    """Upload a file and extract its text content for MCP context."""
    try:
        filename = file.filename or "upload"
        content = await file.read()
        mime_type = mimetypes.guess_type(filename)[0] or ""

        extracted = ""

        if mime_type.startswith("image/"):
            try:
                from src.ocr_integration import ocr_client
                img_b64 = base64.b64encode(content).decode()
                extracted = ocr_client.extract_text_from_image(img_b64)
            except Exception as e:
                logger.warning(f"OCR failed for uploaded image: {e}")
                extracted = f"[Image: {filename}]"

        elif mime_type == "application/pdf" or filename.lower().endswith(".pdf"):
            try:
                from src.ocr_integration import ocr_client
                pdf_b64 = base64.b64encode(content).decode()
                extracted = ocr_client.extract_text_from_pdf(pdf_b64)
            except Exception as e:
                logger.warning(f"PDF extraction failed: {e}")
                extracted = f"[PDF: {filename}]"

        elif mime_type and (mime_type.startswith("text/") or mime_type in ("application/json", "application/javascript", "application/xml")):
            try:
                extracted = content.decode("utf-8")[:10000]
            except UnicodeDecodeError:
                extracted = content.decode("latin-1")[:10000]

        elif any(filename.lower().endswith(ext) for ext in (
            ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp",
            ".h", ".css", ".html", ".md", ".txt", ".json", ".yaml", ".yml",
            ".xml", ".sh", ".bat", ".sql",
        )):
            try:
                extracted = content.decode("utf-8")[:10000]
            except UnicodeDecodeError:
                extracted = content.decode("latin-1")[:10000]

        else:
            extracted = f"[Binary file: {filename}]"

        return {"success": True, "filename": filename, "content": extracted, "mime_type": mime_type}

    except Exception as e:
        logger.error(f"MCP upload-file error: {e}")
        raise HTTPException(500, "Failed to process uploaded file")
