"""
AI-Assistant MCP Server V2.0 - WITH PERSISTENT MEMORY
=======================================================
Káº¿t há»£p tÃ­nh nÄƒng cá»§a claude-mem vÃ  MCP Server:
  âœ… Real-time project access (Tools)
  âœ… Persistent memory across sessions (Memory System)
  âœ… AI-powered observations & summaries
  âœ… Full-text search qua history
  âœ… Web UI Ä‘á»ƒ xem memory

Sá»­ dá»¥ng FastMCP SDK (miá»…n phÃ­, mÃ£ nguá»“n má»Ÿ).
"""

import os
import ast
import math
import json
import re
import sqlite3
import subprocess
import operator as _op
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
from functools import wraps
import time
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("ERROR: FastMCP khÃ´ng Ä‘Æ°á»£c cÃ i Ä‘áº·t.")
    print("Vui lÃ²ng cháº¡y: pip install 'mcp[cli]'")
    exit(1)

# Import memory system
from database import get_memory_manager

# Khá»Ÿi táº¡o MCP server
mcp = FastMCP("AI-Assistant-V2-Memory")

# Base paths
BASE_DIR = Path(__file__).parent.parent.parent
LOCAL_DATA_DIR = BASE_DIR / "local_data"
RESOURCES_DIR = BASE_DIR / "resources"
LOGS_DIR = RESOURCES_DIR / "logs"

# Module-level safe math evaluator setup
_MATH_ALLOWED = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
_MATH_ALLOWED.update({"abs": abs, "round": round, "min": min, "max": max, "sum": sum, "pow": pow})
_MATH_BINOPS = {
    ast.Add: _op.add, ast.Sub: _op.sub, ast.Mult: _op.mul,
    ast.Div: _op.truediv, ast.Pow: _op.pow, ast.Mod: _op.mod,
    ast.FloorDiv: _op.floordiv,
}
_MATH_UNOPS = {ast.UAdd: _op.pos, ast.USub: _op.neg}


def _safe_math_eval(expression: str):
    """Evaluate a mathematical expression safely using AST parsing."""
    def _eval_node(node):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float, complex)):
                return node.value
            raise ValueError(f"Unsupported literal: {node.value!r}")
        if isinstance(node, ast.Name):
            if node.id in _MATH_ALLOWED:
                return _MATH_ALLOWED[node.id]
            raise ValueError(f"Name not allowed: {node.id}")
        if isinstance(node, ast.BinOp):
            if type(node.op) not in _MATH_BINOPS:
                raise ValueError(f"Operator not allowed: {type(node.op).__name__}")
            return _MATH_BINOPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
        if isinstance(node, ast.UnaryOp):
            if type(node.op) not in _MATH_UNOPS:
                raise ValueError(f"Operator not allowed: {type(node.op).__name__}")
            return _MATH_UNOPS[type(node.op)](_eval_node(node.operand))
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in _MATH_ALLOWED or not callable(_MATH_ALLOWED[node.func.id]):
                raise ValueError(f"Function not allowed: {ast.dump(node.func)}")
            func = _MATH_ALLOWED[node.func.id]
            args = [_eval_node(a) for a in node.args]
            kwargs = {kw.arg: _eval_node(kw.value) for kw in node.keywords}
            return func(*args, **kwargs)
        raise ValueError(f"Unsupported expression: {type(node).__name__}")
    return _eval_node(ast.parse(expression, mode='eval').body)

# Initialize Memory Manager
memory = get_memory_manager(
    db_path=RESOURCES_DIR / "memory" / "mcp_memory.db"
)

# Auto-create session on startup
SESSION_ID = memory.create_session(project_name="AI-Assistant")
logger.info(f"ðŸš€ Session created: {SESSION_ID}")

SERVER_START_TIME = time.time()
STARTED_AT = datetime.utcnow().isoformat()

# Tool access mode: "read-write" (default) or "read-only"
TOOL_MODE = os.getenv("MCP_TOOL_MODE", "read-write").strip().lower()
if TOOL_MODE not in {"read-only", "read-write"}:
    TOOL_MODE = "read-write"

# Memory retention policy
MEMORY_RETENTION_DAYS = int(os.getenv("MCP_MEMORY_RETENTION_DAYS", "90"))
ARCHIVED_DELETE_DAYS = int(os.getenv("MCP_ARCHIVED_DELETE_DAYS", "365"))
WARMUP_CONTEXT_CACHE = os.getenv("MCP_WARMUP_CONTEXT_CACHE", "true").strip().lower() in {"1", "true", "yes", "on"}
WARMUP_QUERIES_RAW = os.getenv(
    "MCP_MEMORY_WARMUP_QUERIES",
    "error,bugfix,refactor,performance,security,chatbot,mcp"
)
WARMUP_CACHE_TTL_SECONDS = int(os.getenv("MCP_WARMUP_CACHE_TTL_SECONDS", "900"))


def _error_response(
    code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    retryable: bool = False
) -> Dict[str, Any]:
    """Return a standardized error payload (backward-compatible)."""
    return {
        "success": False,
        "error": message,
        "error_code": code,
        "error_details": details or {},
        "retryable": retryable
    }


def _require_write_access(func):
    """Block mutating tools when MCP_TOOL_MODE=read-only."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if TOOL_MODE == "read-only":
            return _error_response(
                "ACCESS_DENIED_READ_ONLY",
                f"Tool '{func.__name__}' is disabled in read-only mode",
                {"tool_mode": TOOL_MODE, "tool_name": func.__name__}
            )
        return func(*args, **kwargs)
    return wrapper


def _safe_tool(func):
    """Catch unexpected exceptions and return standardized internal error."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception("Unhandled error in tool '%s': %s", func.__name__, str(e))
            return _error_response(
                "INTERNAL_TOOL_ERROR",
                f"Tool '{func.__name__}' failed unexpectedly",
                {"exception_type": type(e).__name__},
                retryable=True
            )
    return wrapper


def _safe_json_list(value: Any) -> List[str]:
    """Parse JSON list safely and return a normalized list of strings."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value][:50]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(v) for v in parsed][:50]
        except Exception:
            return []
    return []


# ==================== DECORATOR: Auto-save to memory ====================

def _safe_resolve_path(path_str: str, base_dir: Path) -> Optional[Path]:
    """
    Safely resolve a path relative to base_dir, preventing path traversal.
    Returns None if path attempts to escape base_dir.
    """
    if not path_str or not isinstance(path_str, str):
        return None
    try:
        candidate = (base_dir / path_str).resolve()
        base_resolved = base_dir.resolve()
        # Ensure the resolved path is inside base_dir
        candidate.relative_to(base_resolved)
        return candidate
    except (ValueError, OSError):
        return None


def with_memory(importance: int = 5, observation_type: str = "general"):
    """
    Decorator tá»± Ä‘á»™ng lÆ°u tool usage vÃ o memory
    
    Args:
        importance: 1-10 scale
        observation_type: decision, bugfix, feature, refactor, discovery
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error_msg = None
            result = None
            
            try:
                # Execute tool
                result = func(*args, **kwargs)
                
                # Log to memory
                duration_ms = int((time.time() - start_time) * 1000)
                memory.log_tool_usage(
                    tool_name=func.__name__,
                    input_params=kwargs,
                    output_data=result,
                    duration_ms=duration_ms,
                    success=True
                )
                
                # Create simple observation
                observation = f"Tool '{func.__name__}' executed successfully"
                if kwargs:
                    param_str = ", ".join([f"{k}={v}" for k, v in list(kwargs.items())[:3]])
                    observation += f" with params: {param_str}"
                
                memory.save_observation(
                    tool_name=func.__name__,
                    observation=observation,
                    observation_type=observation_type,
                    importance=importance,
                    tool_input=kwargs,
                    tool_output=str(result)[:500] if result else None
                )
                
                return result
                
            except Exception as e:
                success = False
                error_msg = str(e)
                
                # Log error to memory
                memory.log_tool_usage(
                    tool_name=func.__name__,
                    input_params=kwargs,
                    output_data=None,
                    duration_ms=int((time.time() - start_time) * 1000),
                    success=False,
                    error_message=error_msg
                )
                
                raise
        
        return wrapper
    return decorator


def _run_startup_maintenance() -> None:
    """Apply retention policy at startup without crashing server on failure."""
    try:
        cleanup_stats = memory.cleanup_old_data(days=MEMORY_RETENTION_DAYS)
        hard_delete_stats = memory.hard_delete_archived_data(days=ARCHIVED_DELETE_DAYS)
        logger.info("Startup maintenance cleanup=%s hard_delete=%s", cleanup_stats, hard_delete_stats)
    except Exception as e:
        logger.warning("Startup maintenance skipped due to error: %s", str(e))


def _run_startup_cache_warmup() -> None:
    """Warm query context cache at startup for common topics."""
    if not WARMUP_CONTEXT_CACHE:
        logger.info("Startup cache warmup disabled")
        return

    queries = [q.strip() for q in WARMUP_QUERIES_RAW.split(",") if q.strip()]
    if not queries:
        logger.info("Startup cache warmup skipped: no queries configured")
        return

    try:
        stats = memory.warm_context_cache(
            queries=queries,
            project_name="AI-Assistant",
            cache_ttl_seconds=max(60, min(WARMUP_CACHE_TTL_SECONDS, 86400)),
            force_refresh=False
        )
        logger.info("Startup cache warmup completed: %s", stats)
    except Exception as e:
        logger.warning("Startup cache warmup skipped due to error: %s", str(e))


_run_startup_maintenance()
_run_startup_cache_warmup()


# ==================== TOOLS: FILE OPERATIONS ====================

@mcp.tool()
@with_memory(importance=5, observation_type="search")
def search_files(query: str, file_type: str = "all", max_results: int = 10) -> Dict[str, Any]:
    """
    TÃ¬m kiáº¿m files trong workspace theo query.
    
    Args:
        query: Tá»« khÃ³a tÃ¬m kiáº¿m
        file_type: Loáº¡i file (all, py, md, json, txt, js, html, css)
        max_results: Sá»‘ káº¿t quáº£ tá»‘i Ä‘a
        
    Returns:
        Dict chá»©a danh sÃ¡ch files tÃ¬m tháº¥y
    """
    results = []
    search_path = BASE_DIR
    
    # Map file types
    extensions = {
        "py": [".py"],
        "md": [".md"],
        "json": [".json"],
        "txt": [".txt"],
        "js": [".js", ".jsx", ".ts", ".tsx"],
        "html": [".html", ".htm"],
        "css": [".css", ".scss", ".sass"],
        "all": None
    }
    
    target_exts = extensions.get(file_type, None)
    
    for file_path in search_path.rglob("*"):
        if len(results) >= max_results:
            break
            
        if not file_path.is_file():
            continue
        
        # Skip certain directories
        if any(skip in str(file_path) for skip in ['.venv', '__pycache__', 'node_modules', '.git']):
            continue
        
        # Check extension
        if target_exts and file_path.suffix not in target_exts:
            continue
        
        # Check query in filename or path
        if query.lower() in str(file_path).lower():
            results.append({
                "path": str(file_path.relative_to(BASE_DIR)),
                "name": file_path.name,
                "size": file_path.stat().st_size,
                "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            })
    
    return {
        "query": query,
        "file_type": file_type,
        "found": len(results),
        "results": results
    }


@mcp.tool()
@with_memory(importance=6, observation_type="read")
def read_file_content(
    file_path: str, 
    start_line: int = 1, 
    end_line: Optional[int] = None,
    max_lines: int = 500
) -> Dict[str, Any]:
    """
    Äá»c ná»™i dung file.
    
    Args:
        file_path: ÄÆ°á»ng dáº«n file (relative to BASE_DIR)
        start_line: DÃ²ng báº¯t Ä‘áº§u (1-based)
        end_line: DÃ²ng káº¿t thÃºc (None = Ä‘áº¿n cuá»‘i file)
        max_lines: Sá»‘ dÃ²ng tá»‘i Ä‘a
        
    Returns:
        Dict chá»©a ná»™i dung file
    """
    full_path = _safe_resolve_path(file_path, BASE_DIR)
    
    if full_path is None:
        return _error_response(
            "INVALID_PATH",
            f"Invalid or restricted path: {file_path}",
            {"file_path": file_path}
        )
    
    if not full_path.exists():
        return _error_response("FILE_NOT_FOUND", f"File not found: {file_path}")
    
    if not full_path.is_file():
        return _error_response("NOT_A_FILE", f"Not a file: {file_path}")
    
    try:
        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        
        # Adjust indices (1-based to 0-based)
        start_idx = max(0, start_line - 1)
        end_idx = min(total_lines, end_line if end_line else total_lines)
        
        # Apply max_lines limit
        if end_idx - start_idx > max_lines:
            end_idx = start_idx + max_lines
        
        selected_lines = lines[start_idx:end_idx]
        
        return {
            "file": file_path,
            "total_lines": total_lines,
            "start_line": start_line,
            "end_line": start_idx + len(selected_lines),
            "lines_returned": len(selected_lines),
            "content": "".join(selected_lines)
        }
        
    except Exception as e:
        return _error_response("READ_FAILED", str(e), {"file_path": file_path})


@mcp.tool()
@with_memory(importance=4, observation_type="list")
def list_directory(directory_path: str = ".", show_hidden: bool = False) -> Dict[str, Any]:
    """
    Liá»‡t kÃª files vÃ  folders trong directory.
    
    Args:
        directory_path: ÄÆ°á»ng dáº«n directory (relative to BASE_DIR)
        show_hidden: Hiá»ƒn thá»‹ files/folders áº©n
        
    Returns:
        Dict chá»©a danh sÃ¡ch files vÃ  folders
    """
    full_path = _safe_resolve_path(directory_path, BASE_DIR)
    
    if full_path is None:
        return _error_response(
            "INVALID_PATH",
            f"Invalid or restricted path: {directory_path}",
            {"directory_path": directory_path}
        )
    
    if not full_path.exists():
        return _error_response("DIRECTORY_NOT_FOUND", f"Directory not found: {directory_path}")
    
    if not full_path.is_dir():
        return _error_response("NOT_A_DIRECTORY", f"Not a directory: {directory_path}")
    
    files = []
    folders = []
    
    for item in full_path.iterdir():
        if not show_hidden and item.name.startswith('.'):
            continue
        
        item_info = {
            "name": item.name,
            "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
        }
        
        if item.is_file():
            item_info["size"] = item.stat().st_size
            files.append(item_info)
        else:
            folders.append(item_info)
    
    return {
        "path": directory_path,
        "folders": sorted(folders, key=lambda x: x['name']),
        "files": sorted(files, key=lambda x: x['name']),
        "total_items": len(files) + len(folders)
    }


# ==================== TOOLS: PROJECT INFO ====================

@mcp.tool()
@with_memory(importance=7, observation_type="info")
def get_project_info() -> Dict[str, Any]:
    """
    Láº¥y thÃ´ng tin tá»•ng quan vá» AI-Assistant project.
    
    Returns:
        Dict chá»©a thÃ´ng tin project
    """
    services = [
        {"name": "Hub Gateway", "port": 3000, "path": "services/hub-gateway"},
        {"name": "ChatBot", "port": 5001, "path": "services/chatbot"},
        {"name": "Text2SQL", "port": 5002, "path": "services/text2sql"},
        {"name": "Document Intelligence", "port": 5003, "path": "services/document-intelligence"},
        {"name": "Speech2Text", "port": 7860, "path": "services/speech2text"},
        {"name": "Stable Diffusion", "port": 7861, "path": "services/stable-diffusion"},
        {"name": "LoRA Training", "port": 7862, "path": "services/lora-training"},
        {"name": "Image Upscale", "port": 7863, "path": "services/image-upscale"},
        {"name": "MCP Server", "port": None, "path": "services/mcp-server"}
    ]
    
    return {
        "project": "AI-Assistant",
        "version": "2.3",
        "services": services,
        "base_directory": str(BASE_DIR),
        "python_version": "3.10.6"
    }


@mcp.tool()
@with_memory(importance=6, observation_type="search")
def search_logs(
    service_name: str, 
    level: str = "ALL", 
    max_lines: int = 100
) -> Dict[str, Any]:
    """
    TÃ¬m kiáº¿m trong log files cá»§a services.
    
    Args:
        service_name: TÃªn service (chatbot, text2sql, hub-gateway, etc.)
        level: Log level (ALL, ERROR, WARNING, INFO, DEBUG)
        max_lines: Sá»‘ dÃ²ng tá»‘i Ä‘a
        
    Returns:
        Dict chá»©a káº¿t quáº£ tÃ¬m kiáº¿m logs
    """
    log_file = LOGS_DIR / f"{service_name}.log"
    
    if not log_file.exists():
        return {
            "service": service_name,
            "error": f"Log file not found: {log_file}"
        }
    
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        # Filter by level
        if level != "ALL":
            filtered = [line for line in lines if level in line]
        else:
            filtered = lines
        
        # Get last N lines
        results = filtered[-max_lines:] if len(filtered) > max_lines else filtered
        
        return {
            "service": service_name,
            "level": level,
            "total_lines": len(lines),
            "filtered_lines": len(filtered),
            "returned_lines": len(results),
            "logs": "".join(results)
        }
        
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
@with_memory(importance=3, observation_type="calculation")
def calculate(expression: str) -> Dict[str, Any]:
    """
    Thá»±c hiá»‡n tÃ­nh toÃ¡n an toÃ n.
    
    Args:
        expression: Biá»ƒu thá»©c toÃ¡n há»c (vd: "2 + 2", "(10 * 5) / 2")
        
    Returns:
        Dict chứa kết quả tính toán
    """
    try:
        result = _safe_math_eval(expression)
        
        return {
            "expression": expression,
            "result": result,
            "type": type(result).__name__
        }
        
    except Exception as e:
        return {
            "expression": expression,
            "error": str(e)
        }


# ==================== TOOLS: CONTENT SEARCH & FILE OPS ====================

@mcp.tool()
@with_memory(importance=7, observation_type="search")
def grep_in_files(
    pattern: str,
    directory: str = ".",
    file_type: str = "all",
    max_results: int = 50,
    case_sensitive: bool = False
) -> Dict[str, Any]:
    """
    TÃ¬m kiáº¿m Ná»˜I DUNG trong files báº±ng regex/text pattern (nhÆ° grep).
    
    Args:
        pattern: Text hoáº·c regex pattern cáº§n tÃ¬m
        directory: ThÆ° má»¥c tÃ¬m kiáº¿m (relative to BASE_DIR)
        file_type: Loáº¡i file (all, py, md, json, txt, js, html)
        max_results: Sá»‘ káº¿t quáº£ tá»‘i Ä‘a
        case_sensitive: PhÃ¢n biá»‡t hoa/thÆ°á»ng
        
    Returns:
        Dict chá»©a danh sÃ¡ch matches vá»›i file vÃ  line number
    """
    search_dir = _safe_resolve_path(directory, BASE_DIR)
    if search_dir is None or not search_dir.is_dir():
        return {"error": f"Invalid directory: {directory}"}

    extensions = {
        "py": [".py"], "md": [".md"], "json": [".json"],
        "txt": [".txt"], "js": [".js", ".jsx", ".ts", ".tsx"],
        "html": [".html", ".htm"], "css": [".css", ".scss"],
        "all": None
    }
    target_exts = extensions.get(file_type, None)

    try:
        flags = 0 if case_sensitive else re.IGNORECASE
        compiled = re.compile(pattern, flags)
    except re.error as e:
        return {"error": f"Invalid regex pattern: {str(e)}"}

    skip_dirs = {'.venv', 'venv', '__pycache__', 'node_modules', '.git', '.mypy_cache'}
    results = []

    for file_path in search_dir.rglob("*"):
        if len(results) >= max_results:
            break
        if not file_path.is_file():
            continue
        if any(skip in file_path.parts for skip in skip_dirs):
            continue
        if target_exts and file_path.suffix not in target_exts:
            continue
        if file_path.stat().st_size > 5 * 1024 * 1024:  # Skip files > 5MB
            continue

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for lineno, line in enumerate(f, 1):
                    if compiled.search(line):
                        results.append({
                            "file": str(file_path.relative_to(BASE_DIR)),
                            "line": lineno,
                            "content": line.rstrip('\n')
                        })
                        if len(results) >= max_results:
                            break
        except OSError:
            continue

    return {
        "pattern": pattern,
        "directory": directory,
        "file_type": file_type,
        "total_matches": len(results),
        "truncated": len(results) >= max_results,
        "results": results
    }


@mcp.tool()
@_safe_tool
@with_memory(importance=8, observation_type="write")
@_require_write_access
def write_file(
    file_path: str,
    content: str,
    mode: str = "overwrite",
    create_dirs: bool = True
) -> Dict[str, Any]:
    """
    Ghi ná»™i dung vÃ o file (táº¡o má»›i hoáº·c chá»‰nh sá»­a).
    
    Args:
        file_path: ÄÆ°á»ng dáº«n file (relative to BASE_DIR)
        content: Ná»™i dung cáº§n ghi
        mode: 'overwrite' (ghi Ä‘Ã¨) hoáº·c 'append' (thÃªm vÃ o cuá»‘i)
        create_dirs: Tá»± Ä‘á»™ng táº¡o thÆ° má»¥c cha náº¿u chÆ°a tá»“n táº¡i
        
    Returns:
        Dict vá»›i káº¿t quáº£ thao tÃ¡c
    """
    resolved = _safe_resolve_path(file_path, BASE_DIR)
    if resolved is None:
        return _error_response("INVALID_PATH", f"Invalid or restricted path: {file_path}")

    try:
        if mode not in {"overwrite", "append"}:
            return _error_response(
                "INVALID_WRITE_MODE",
                "mode must be either 'overwrite' or 'append'",
                {"mode": mode}
            )

        if create_dirs:
            resolved.parent.mkdir(parents=True, exist_ok=True)

        write_mode = 'a' if mode == 'append' else 'w'
        with open(resolved, write_mode, encoding='utf-8') as f:
            f.write(content)

        return {
            "success": True,
            "file_path": str(resolved.relative_to(BASE_DIR)),
            "mode": mode,
            "bytes_written": len(content.encode('utf-8'))
        }
    except OSError as e:
        return _error_response("WRITE_FAILED", f"Write failed: {str(e)}", {"file_path": file_path})


# ==================== TOOLS: GIT ====================

@mcp.tool()
@with_memory(importance=6, observation_type="git")
def git_status() -> Dict[str, Any]:
    """
    Láº¥y git status cá»§a repository (modified, added, deleted, untracked files).
    
    Returns:
        Dict chá»©a tráº¡ng thÃ¡i git working tree
    """
    try:
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            capture_output=True, text=True,
            cwd=BASE_DIR, timeout=10
        )
        if result.returncode != 0:
            return {"error": "Not a git repository or git not installed"}

        modified, added, deleted, untracked = [], [], [], []
        for line in result.stdout.splitlines():
            if not line:
                continue
            status, file_path = line[:2].strip(), line[3:]
            if status == 'M':
                modified.append(file_path)
            elif status == 'A':
                added.append(file_path)
            elif status == 'D':
                deleted.append(file_path)
            elif status == '??':
                untracked.append(file_path)

        return {
            "modified": modified,
            "added": added,
            "deleted": deleted,
            "untracked": untracked,
            "total_changes": len(modified) + len(added) + len(deleted),
            "clean": not any([modified, added, deleted, untracked])
        }
    except FileNotFoundError:
        return {"error": "Git is not installed"}
    except subprocess.TimeoutExpired:
        return {"error": "Git command timed out"}


@mcp.tool()
@with_memory(importance=5, observation_type="git")
def git_log(max_commits: int = 10) -> Dict[str, Any]:
    """
    Láº¥y git commit history.
    
    Args:
        max_commits: Sá»‘ commits tá»‘i Ä‘a (max 50)
        
    Returns:
        Dict chá»©a danh sÃ¡ch commits
    """
    max_commits = min(max_commits, 50)
    try:
        result = subprocess.run(
            ['git', 'log', f'-{max_commits}', '--pretty=format:%H|%an|%ad|%s', '--date=short'],
            capture_output=True, text=True,
            cwd=BASE_DIR, timeout=10
        )
        if result.returncode != 0:
            return {"error": "Git log failed"}

        commits = []
        for line in result.stdout.splitlines():
            parts = line.split('|', 3)
            if len(parts) == 4:
                commits.append({
                    "hash": parts[0][:12],
                    "author": parts[1],
                    "date": parts[2],
                    "message": parts[3]
                })

        return {"total": len(commits), "commits": commits}
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return {"error": str(e)}


@mcp.tool()
@with_memory(importance=4, observation_type="git")
def git_diff(file_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Láº¥y git diff Ä‘á»ƒ xem cÃ¡c thay Ä‘á»•i chÆ°a staged.
    
    Args:
        file_path: ÄÆ°á»ng dáº«n file cá»¥ thá»ƒ (None = toÃ n bá»™ repo)
        
    Returns:
        Dict chá»©a diff output
    """
    cmd = ['git', 'diff']
    if file_path:
        # Validate path to prevent command injection
        safe = _safe_resolve_path(file_path, BASE_DIR)
        if safe is None:
            return {"error": "Invalid file path"}
        cmd.append(str(safe))

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            cwd=BASE_DIR, timeout=15
        )
        return {
            "file": file_path,
            "diff": result.stdout,
            "has_changes": bool(result.stdout.strip())
        }
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return {"error": str(e)}


# ==================== TOOLS: CODE ANALYSIS ====================

@mcp.tool()
@with_memory(importance=7, observation_type="analysis")
def analyze_python_file(file_path: str) -> Dict[str, Any]:
    """
    PhÃ¢n tÃ­ch cáº¥u trÃºc Python file: functions, classes, imports, Ä‘á»™ phá»©c táº¡p.
    
    Args:
        file_path: ÄÆ°á»ng dáº«n file .py (relative to BASE_DIR)
        
    Returns:
        Dict chá»©a phÃ¢n tÃ­ch chi tiáº¿t
    """
    full_path = _safe_resolve_path(file_path, BASE_DIR)
    if full_path is None:
        return {"error": f"Invalid path: {file_path}"}
    if not full_path.exists():
        return {"error": f"File not found: {file_path}"}
    if full_path.suffix != '.py':
        return {"error": "Not a Python file"}

    try:
        source = full_path.read_text(encoding='utf-8')
        tree = ast.parse(source)
    except SyntaxError as e:
        return {"error": f"Syntax error: {str(e)}"}
    except OSError as e:
        return {"error": str(e)}

    functions, classes, imports = [], [], []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append({
                "name": node.name,
                "line": node.lineno,
                "args": [arg.arg for arg in node.args.args],
                "is_async": isinstance(node, ast.AsyncFunctionDef),
                "decorators": [
                    getattr(d, 'id', getattr(d, 'attr', str(d)))
                    for d in node.decorator_list
                ]
            })
        elif isinstance(node, ast.ClassDef):
            methods = [n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            classes.append({
                "name": node.name,
                "line": node.lineno,
                "methods": methods,
                "bases": [getattr(b, 'id', str(b)) for b in node.bases]
            })
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({"module": alias.name, "alias": alias.asname})
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imports.append({
                    "from": node.module or "",
                    "import": alias.name,
                    "alias": alias.asname
                })

    lines = source.splitlines()
    return {
        "file": file_path,
        "functions": functions,
        "classes": classes,
        "imports": imports,
        "stats": {
            "total_lines": len(lines),
            "code_lines": sum(1 for l in lines if l.strip() and not l.strip().startswith('#')),
            "comment_lines": sum(1 for l in lines if l.strip().startswith('#')),
            "function_count": len(functions),
            "class_count": len(classes),
            "import_count": len(imports)
        }
    }


@mcp.tool()
@with_memory(importance=5, observation_type="analysis")
def find_todos(directory: str = ".") -> Dict[str, Any]:
    """
    TÃ¬m táº¥t cáº£ TODO, FIXME, HACK, NOTE comments trong code.
    
    Args:
        directory: ThÆ° má»¥c tÃ¬m kiáº¿m (relative to BASE_DIR)
        
    Returns:
        Dict chá»©a danh sÃ¡ch todos phÃ¢n loáº¡i
    """
    search_dir = _safe_resolve_path(directory, BASE_DIR)
    if search_dir is None or not search_dir.is_dir():
        return {"error": f"Invalid directory: {directory}"}

    pattern = re.compile(r'#\s*(TODO|FIXME|HACK|NOTE|XXX):?\s*(.*)', re.IGNORECASE)
    skip_dirs = {'.venv', 'venv', '__pycache__', 'node_modules', '.git'}
    todos = []

    for file_path in search_dir.rglob("*.py"):
        if any(skip in file_path.parts for skip in skip_dirs):
            continue
        try:
            for i, line in enumerate(file_path.read_text(encoding='utf-8', errors='ignore').splitlines(), 1):
                match = pattern.search(line)
                if match:
                    todos.append({
                        "file": str(file_path.relative_to(BASE_DIR)),
                        "line": i,
                        "type": match.group(1).upper(),
                        "message": match.group(2).strip()
                    })
        except OSError:
            continue

    by_type: Dict[str, List] = {}
    for todo in todos:
        by_type.setdefault(todo['type'], []).append(todo)

    return {
        "directory": directory,
        "total": len(todos),
        "by_type": {k: len(v) for k, v in by_type.items()},
        "todos": todos
    }


# ==================== TOOLS: HTTP / SERVICE CALLS ====================

@mcp.tool()
@_safe_tool
@with_memory(importance=5, observation_type="http")
@_require_write_access
def http_request(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    body: Optional[str] = None,
    timeout: int = 10
) -> Dict[str, Any]:
    """
    Thá»±c hiá»‡n HTTP request Ä‘áº¿n services hoáº·c APIs.
    Chá»‰ Ä‘Æ°á»£c phÃ©p gá»i localhost/internal services.
    
    Args:
        url: URL cáº§n gá»i (chá»‰ http://localhost:... hoáº·c http://127.0.0.1:...)
        method: HTTP method (GET, POST, PUT, DELETE)
        headers: HTTP headers dáº¡ng dict
        body: Request body (string, sáº½ Ä‘Æ°á»£c gá»­i dÆ°á»›i dáº¡ng JSON náº¿u cÃ³ Content-Type)
        timeout: Timeout tÃ­nh báº±ng giÃ¢y (max 30)
        
    Returns:
        Dict chá»©a status code, headers, body
    """
    import urllib.request
    import urllib.error
    import urllib.parse

    # Security: only allow localhost
    allowed_hosts = ('localhost', '127.0.0.1', '0.0.0.0')
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.hostname not in allowed_hosts:
            return _error_response(
                "HOST_NOT_ALLOWED",
                f"Only localhost requests are allowed. Got: {parsed.hostname}",
                {"hostname": parsed.hostname}
            )
    except Exception:
        return _error_response("INVALID_URL", "Invalid URL")

    method = method.upper()
    if method not in {'GET', 'POST', 'PUT', 'DELETE', 'PATCH'}:
        return _error_response(
            "UNSUPPORTED_HTTP_METHOD",
            f"Unsupported HTTP method: {method}",
            {"method": method}
        )

    timeout = min(max(1, timeout), 30)
    req_headers = headers or {}

    try:
        data = body.encode('utf-8') if body else None
        req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            response_body = resp.read().decode('utf-8', errors='replace')
            return {
                "status_code": resp.status,
                "headers": dict(resp.headers),
                "body": response_body[:10000],
                "truncated": len(response_body) > 10000
            }
    except urllib.error.HTTPError as e:
        body_text = e.read().decode('utf-8', errors='replace') if e.fp else ""
        return _error_response(
            "HTTP_ERROR_RESPONSE",
            str(e),
            {"status_code": e.code, "body": body_text[:2000]},
            retryable=e.code >= 500
        )
    except urllib.error.URLError as e:
        return _error_response(
            "HTTP_CONNECTION_FAILED",
            f"Connection failed: {str(e.reason)}",
            retryable=True
        )
    except Exception as e:
        return _error_response("HTTP_REQUEST_FAILED", f"Request failed: {str(e)}", retryable=True)


@mcp.tool()
@_safe_tool
def get_server_health() -> Dict[str, Any]:
    """
    Kiá»ƒm tra tráº¡ng thÃ¡i cá»§a MCP server vÃ  memory system.
    
    Returns:
        Dict chá»©a thÃ´ng tin health vÃ  stats
    """
    import platform
    import sys

    uptime_seconds = round(time.time() - SERVER_START_TIME, 2)

    db_ok = False
    db_stats = {}
    db_health = {}
    try:
        stats = memory.get_statistics()
        db_health = memory.get_database_health()
        db_ok = True
        db_stats = {
            "total_sessions": stats.get('total_sessions', 0),
            "total_observations": stats.get('total_observations', 0),
            "total_tool_calls": stats.get('total_tools', 0)
        }
    except Exception as e:
        db_stats = {"error": str(e)}

    git_ok = False
    git_error = None
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--is-inside-work-tree'],
            capture_output=True,
            text=True,
            cwd=BASE_DIR,
            timeout=5
        )
        git_ok = result.returncode == 0
        if not git_ok:
            git_error = (result.stderr or result.stdout).strip()[:200]
    except Exception as e:
        git_error = str(e)

    file_system = {
        "base_dir_exists": BASE_DIR.exists(),
        "resources_dir_exists": RESOURCES_DIR.exists(),
        "base_dir_writable": os.access(BASE_DIR, os.W_OK),
    }

    return {
        "status": "ok" if db_ok else "degraded",
        "server": "AI-Assistant MCP V2.0",
        "current_session": SESSION_ID,
        "tool_mode": TOOL_MODE,
        "started_at": STARTED_AT,
        "uptime_seconds": uptime_seconds,
        "database_ok": db_ok,
        "database_stats": db_stats,
        "database_health": db_health,
        "subsystems": {
            "database": {"ok": db_ok},
            "git": {"ok": git_ok, "error": git_error},
            "filesystem": file_system,
        },
        "base_directory": str(BASE_DIR),
        "python_version": sys.version.split()[0],
        "platform": platform.system(),
        "uptime_since": STARTED_AT
    }


# ==================== TOOLS: MEMORY SYSTEM (NEW!) ====================

@mcp.tool()
@_safe_tool
def search_memory(
    query: str, 
    limit: int = 10,
    min_importance: int = 0
) -> Dict[str, Any]:
    """
    ðŸ†• TÃ¬m kiáº¿m trong memory (observations tá»« cÃ¡c sessions trÆ°á»›c).
    
    Args:
        query: Tá»« khÃ³a tÃ¬m kiáº¿m
        limit: Sá»‘ káº¿t quáº£ tá»‘i Ä‘a
        min_importance: Äá»™ quan trá»ng tá»‘i thiá»ƒu (0-10)
        
    Returns:
        Dict chá»©a observations tÃ¬m tháº¥y
    """
    results = memory.search_observations(
        query=query,
        limit=limit,
        min_importance=min_importance
    )
    
    return {
        "query": query,
        "found": len(results),
        "observations": [
            {
                "id": obs['id'],
                "observation": obs['observation'],
                "type": obs['observation_type'],
                "importance": obs['importance'],
                "tool": obs['tool_name'],
                "timestamp": obs['timestamp'],
                "files": _safe_json_list(obs.get('file_references')),
                "tags": _safe_json_list(obs.get('concept_tags'))
            }
            for obs in results
        ]
    }


@mcp.tool()
@_safe_tool
def get_recent_context(
    limit: int = 30,
    min_importance: int = 5,
    max_chars: int = 12000
) -> Dict[str, Any]:
    """
    ðŸ†• Láº¥y context gáº§n Ä‘Ã¢y Ä‘á»ƒ inject vÃ o session má»›i.
    
    Args:
        limit: Sá»‘ observations
        min_importance: Äá»™ quan trá»ng tá»‘i thiá»ƒu
        
    Returns:
        Dict chá»©a formatted context
    """
    context_text = memory.get_context_for_session(
        max_observations=limit,
        min_importance=min_importance,
        max_chars=max_chars
    )
    
    observations = memory.get_recent_observations(
        limit=limit,
        min_importance=min_importance
    )
    
    return {
        "context": context_text,
        "observation_count": len(observations),
        "min_importance": min_importance,
        "max_chars": max_chars
    }


@mcp.tool()
@_safe_tool
def get_relevant_memory_context(
    query: str,
    limit: int = 20,
    min_importance: int = 4,
    max_chars: int = 12000,
    use_cache: bool = True,
    cache_ttl_seconds: int = 600
) -> Dict[str, Any]:
    """
    Láº¥y context memory liÃªn quan trá»±c tiáº¿p Ä‘áº¿n query Ä‘á»ƒ inject vÃ o chatbot.

    Args:
        query: CÃ¢u truy váº¥n hoáº·c keyword
        limit: Sá»‘ memory entries tá»‘i Ä‘a
        min_importance: Äá»™ quan trá»ng tá»‘i thiá»ƒu
        max_chars: Äá»™ dÃ i context tá»‘i Ä‘a

    Returns:
        Dict chá»©a context rÃºt gá»n + danh sÃ¡ch observations liÃªn quan
    """
    query = (query or "").strip()
    if not query:
        return _error_response("EMPTY_QUERY", "query is required", {"query": query})

    return memory.get_relevant_context(
        query=query,
        limit=max(1, min(limit, 100)),
        min_importance=max(0, min(min_importance, 10)),
        max_chars=max(1000, min(max_chars, 50000)),
        use_cache=bool(use_cache),
        cache_ttl_seconds=max(60, min(cache_ttl_seconds, 86400))
    )


@mcp.tool()
@_safe_tool
def get_memory_cache_stats() -> Dict[str, Any]:
    """Láº¥y thá»‘ng kÃª cache context cá»§a memory system."""
    return memory.get_context_cache_stats()


@mcp.tool()
@_safe_tool
@_require_write_access
def clear_memory_context_cache(
    context_type: Optional[str] = None,
    older_than_hours: Optional[int] = None
) -> Dict[str, Any]:
    """
    XÃ³a cache memory_context theo filter.

    Args:
        context_type: Lá»c theo loáº¡i cache (vd: relevant_query)
        older_than_hours: Chá»‰ xÃ³a cache cÅ© hÆ¡n N giá»

    Returns:
        Dict chá»©a sá»‘ báº£n ghi Ä‘Ã£ xÃ³a
    """
    if older_than_hours is not None:
        older_than_hours = max(0, min(int(older_than_hours), 24 * 365))
    return memory.clear_context_cache(
        context_type=context_type,
        older_than_hours=older_than_hours
    )


@mcp.tool()
@_safe_tool
@_require_write_access
def warm_memory_context_cache(
    queries: List[str],
    limit: int = 20,
    min_importance: int = 4,
    max_chars: int = 12000,
    cache_ttl_seconds: int = 900,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Warm cache cho relevant memory context báº±ng danh sÃ¡ch queries.

    Args:
        queries: Danh sÃ¡ch query cáº§n warm cache
        limit: Sá»‘ observations tá»‘i Ä‘a cho má»—i query
        min_importance: Äá»™ quan trá»ng tá»‘i thiá»ƒu
        max_chars: Äá»™ dÃ i context tá»‘i Ä‘a
        cache_ttl_seconds: TTL cá»§a cache
        force_refresh: XÃ³a cache relevant_query cÅ© trÆ°á»›c khi warm

    Returns:
        Dict chá»©a thá»‘ng kÃª warm cache
    """
    if not queries:
        return _error_response("EMPTY_QUERIES", "queries must not be empty")

    safe_queries = [str(q).strip() for q in queries if str(q).strip()]
    if not safe_queries:
        return _error_response("EMPTY_QUERIES", "queries must not be empty")

    return memory.warm_context_cache(
        queries=safe_queries[:100],
        project_name="AI-Assistant",
        limit=max(1, min(limit, 100)),
        min_importance=max(0, min(min_importance, 10)),
        max_chars=max(1000, min(max_chars, 50000)),
        cache_ttl_seconds=max(60, min(cache_ttl_seconds, 86400)),
        force_refresh=bool(force_refresh)
    )


@mcp.tool()
@_safe_tool
def get_memory_by_file(file_path: str, limit: int = 20) -> Dict[str, Any]:
    """
    ðŸ†• Láº¥y memories liÃªn quan Ä‘áº¿n file cá»¥ thá»ƒ.
    
    Args:
        file_path: ÄÆ°á»ng dáº«n file
        limit: Sá»‘ káº¿t quáº£
        
    Returns:
        Dict chá»©a observations liÃªn quan
    """
    results = memory.get_observations_by_file(file_path, limit)
    
    return {
        "file": file_path,
        "found": len(results),
        "observations": [
            {
                "observation": obs['observation'],
                "type": obs['observation_type'],
                "importance": obs['importance'],
                "timestamp": obs['timestamp']
            }
            for obs in results
        ]
    }


@mcp.tool()
@_safe_tool
def get_session_history(limit: int = 10) -> Dict[str, Any]:
    """
    ðŸ†• Láº¥y lá»‹ch sá»­ cÃ¡c sessions gáº§n Ä‘Ã¢y.
    
    Args:
        limit: Sá»‘ sessions
        
    Returns:
        Dict chá»©a session history
    """
    sessions = memory.get_recent_sessions(limit)
    
    return {
        "total_sessions": len(sessions),
        "sessions": [
            {
                "id": sess['id'],
                "project": sess['project_name'],
                "start_time": sess['start_time'],
                "tool_count": sess['tool_count'],
                "summary": sess['summary'],
                "observation_count": sess['observation_count']
            }
            for sess in sessions
        ]
    }


@mcp.tool()
@_safe_tool
@_require_write_access
def save_important_observation(
    observation: str,
    observation_type: str = "general",
    importance: int = 8,
    file_references: Optional[List[str]] = None,
    tags: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    ðŸ†• LÆ°u má»™t observation quan trá»ng thá»§ cÃ´ng.
    
    Args:
        observation: Ná»™i dung observation
        observation_type: decision, bugfix, feature, refactor, discovery
        importance: 1-10 scale
        file_references: Danh sÃ¡ch files liÃªn quan
        tags: Tags (discovery, problem-solution, pattern, etc.)
        
    Returns:
        Dict vá»›i observation_id
    """
    obs_id = memory.save_observation(
        tool_name="manual_save",
        observation=observation,
        observation_type=observation_type,
        concept_tags=tags,
        file_references=file_references,
        importance=importance
    )
    
    return {
        "saved": True,
        "observation_id": obs_id,
        "importance": importance,
        "type": observation_type
    }


@mcp.tool()
@_safe_tool
def get_memory_statistics() -> Dict[str, Any]:
    """
    ðŸ†• Láº¥y thá»‘ng kÃª vá» memory system.
    
    Returns:
        Dict chá»©a statistics
    """
    stats = memory.get_statistics()
    
    return {
        "total_sessions": stats['total_sessions'],
        "total_observations": stats['total_observations'],
        "total_tools_used": stats['total_tools'],
        "total_tokens": stats['total_tokens'],
        "avg_importance": stats.get('avg_importance', 0),
        "unique_observation_types": stats.get('unique_observation_types', 0),
        "cache": memory.get_context_cache_stats(),
        "top_tools": stats['tool_stats'][:5]
    }


@mcp.tool()
@_safe_tool
@_require_write_access
def run_memory_maintenance(
    retention_days: int = 90,
    hard_delete_days: int = 365,
    vacuum: bool = False
) -> Dict[str, Any]:
    """
    Cháº¡y maintenance cho memory database: archive, hard delete, optional vacuum.

    Args:
        retention_days: Sessions completed cÅ© hÆ¡n N ngÃ y sáº½ chuyá»ƒn archived
        hard_delete_days: Sessions archived cÅ© hÆ¡n N ngÃ y sáº½ bá»‹ xÃ³a cá»©ng
        vacuum: CÃ³ cháº¡y VACUUM hay khÃ´ng

    Returns:
        Dict chá»©a thá»‘ng kÃª maintenance
    """
    retention_days = max(1, min(retention_days, 3650))
    hard_delete_days = max(retention_days, min(hard_delete_days, 3650))

    cleanup_stats = memory.cleanup_old_data(days=retention_days)
    hard_delete_stats = memory.hard_delete_archived_data(days=hard_delete_days)

    vacuum_done = False
    if vacuum:
        memory.vacuum_database()
        vacuum_done = True

    return {
        "success": True,
        "retention_days": retention_days,
        "hard_delete_days": hard_delete_days,
        "cleanup": cleanup_stats,
        "hard_delete": hard_delete_stats,
        "vacuum_done": vacuum_done
    }


# ==================== RESOURCES ====================

@mcp.resource("config://model")
def get_model_config() -> str:
    """Cáº¥u hÃ¬nh models cá»§a AI-Assistant"""
    config_file = BASE_DIR / "config" / "model_config.py"
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            return f.read()
    return "Model config not found"


@mcp.resource("config://logging")
def get_logging_config() -> str:
    """Cáº¥u hÃ¬nh logging cá»§a AI-Assistant"""
    config_file = BASE_DIR / "config" / "logging_config.py"
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            return f.read()
    return "Logging config not found"


@mcp.resource("docs://readme")
def get_readme() -> str:
    """README cá»§a AI-Assistant project"""
    readme_file = BASE_DIR / "README.md"
    if readme_file.exists():
        with open(readme_file, 'r', encoding='utf-8') as f:
            return f.read()
    return "README not found"


@mcp.resource("docs://structure")
def get_project_structure() -> str:
    """Cáº¥u trÃºc thÆ° má»¥c cá»§a AI-Assistant"""
    structure_file = BASE_DIR / "docs" / "STRUCTURE.md"
    if structure_file.exists():
        with open(structure_file, 'r', encoding='utf-8') as f:
            return f.read()
    return "Structure documentation not found"


@mcp.resource("memory://context")
def get_memory_context_resource() -> str:
    """ðŸ†• Context tá»« memory Ä‘á»ƒ inject vÃ o session"""
    return memory.get_context_for_session(max_observations=30, min_importance=5)


# ==================== PROMPTS ====================

@mcp.prompt()
def code_review(file_path: str) -> str:
    """
    Prompt template Ä‘á»ƒ review code.
    
    Args:
        file_path: ÄÆ°á»ng dáº«n file cáº§n review
    """
    return f"""HÃ£y review code trong file: {file_path}

Vui lÃ²ng phÃ¢n tÃ­ch:
1. Code quality vÃ  best practices
2. Potential bugs hoáº·c security issues
3. Performance concerns
4. Suggestions for improvement

Sá»­ dá»¥ng tool read_file_content Ä‘á»ƒ Ä‘á»c file vÃ  phÃ¢n tÃ­ch chi tiáº¿t."""


@mcp.prompt()
def debug_error(error_message: str, service_name: str) -> str:
    """
    Prompt template Ä‘á»ƒ debug lá»—i.
    
    Args:
        error_message: ThÃ´ng bÃ¡o lá»—i
        service_name: TÃªn service bá»‹ lá»—i
    """
    return f"""Service '{service_name}' Ä‘ang gáº·p lá»—i:
Error: {error_message}

HÃ£y giÃºp tÃ´i debug báº±ng cÃ¡ch:
1. TÃ¬m kiáº¿m logs liÃªn quan (search_logs)
2. Kiá»ƒm tra memory xem cÃ³ gáº·p lá»—i tÆ°Æ¡ng tá»± trÆ°á»›c Ä‘Ã¢y khÃ´ng (search_memory)
3. XÃ¡c Ä‘á»‹nh root cause
4. Äá» xuáº¥t solution"""


@mcp.prompt()
def explain_code(file_path: str, function_name: Optional[str] = None) -> str:
    """
    Prompt template Ä‘á»ƒ giáº£i thÃ­ch code.
    
    Args:
        file_path: ÄÆ°á»ng dáº«n file
        function_name: TÃªn function cáº§n giáº£i thÃ­ch (optional)
    """
    target = f"function {function_name} trong " if function_name else ""
    return f"""HÃ£y giáº£i thÃ­ch code {target}file: {file_path}

Vui lÃ²ng:
1. Äá»c code (read_file_content)
2. Kiá»ƒm tra memory xem cÃ³ context vá» file nÃ y khÃ´ng (get_memory_by_file)
3. Giáº£i thÃ­ch logic báº±ng tiáº¿ng Viá»‡t
4. Input/Output expected
5. CÃ¡c edge cases cáº§n lÆ°u Ã½"""


@mcp.prompt()
def session_summary() -> str:
    """ðŸ†• Prompt Ä‘á»ƒ táº¡o summary cho session"""
    return """HÃ£y táº¡o summary cho session lÃ m viá»‡c vá»«a rá»“i.

Sá»­ dá»¥ng:
1. get_session_history Ä‘á»ƒ xem session hiá»‡n táº¡i
2. get_memory_statistics Ä‘á»ƒ xem cÃ¡c tools Ä‘Ã£ dÃ¹ng
3. Tá»•ng há»£p thÃ nh summary ngáº¯n gá»n vá»›i:
   - CÃ¡c cÃ´ng viá»‡c Ä‘Ã£ lÃ m
   - Files Ä‘Ã£ thao tÃ¡c
   - Decisions quan trá»ng
   - Next steps"""


# ==================== MAIN ====================

def main():
    """Khá»Ÿi Ä‘á»™ng MCP server"""
    print(f"ðŸš€ Starting AI-Assistant MCP Server V2.0 WITH MEMORY...")
    print(f"ðŸ“ Base Directory: {BASE_DIR}")
    print(f"ðŸ§  Memory Database: {memory.db_path}")
    print(f"ðŸ“‹ Session ID: {SESSION_ID}")
    print(f"\nâœ¨ NEW FEATURES:")
    print(f"   ðŸ”§ Tools: All original tools + 11 memory tools")
    print(f"   ðŸ“¦ Resources: Config, docs + memory context")
    print(f"   ðŸ’¬ Prompts: Code review, debug, explain + session summary")
    print(f"   ðŸ§  MEMORY: Persistent storage, search history, AI observations")
    print(f"\nâœ… Server is ready!")
    print(f"ðŸ“¡ Listening for MCP client connections...")
    print(f"\nðŸ’¡ TIP: Sau má»—i session, memory sáº½ tá»± Ä‘á»™ng lÆ°u láº¡i!")
    
    try:
        # Run server
        mcp.run()
    finally:
        # End session on shutdown
        print(f"\n\nðŸ›‘ Shutting down...")
        print(f"ðŸ’¾ Saving session summary...")
        memory.end_session(SESSION_ID, summary="Session ended")
        print(f"âœ… Session saved: {SESSION_ID}")


if __name__ == "__main__":
    main()
