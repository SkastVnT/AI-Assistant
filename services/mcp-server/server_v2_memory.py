"""
AI-Assistant MCP Server V2.0 - WITH PERSISTENT MEMORY
=======================================================
Kết hợp tính năng của claude-mem và MCP Server:
  ✅ Real-time project access (Tools)
  ✅ Persistent memory across sessions (Memory System)
  ✅ AI-powered observations & summaries
  ✅ Full-text search qua history
  ✅ Web UI để xem memory

Sử dụng FastMCP SDK (miễn phí, mã nguồn mở).
"""

import os
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
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
    print("ERROR: FastMCP không được cài đặt.")
    print("Vui lòng chạy: pip install 'mcp[cli]'")
    exit(1)

# Import memory system
from database import get_memory_manager

# Khởi tạo MCP server
mcp = FastMCP("AI-Assistant-V2-Memory")

# Base paths
BASE_DIR = Path(__file__).parent.parent.parent
LOCAL_DATA_DIR = BASE_DIR / "local_data"
RESOURCES_DIR = BASE_DIR / "resources"
LOGS_DIR = RESOURCES_DIR / "logs"

# Initialize Memory Manager
memory = get_memory_manager(
    db_path=RESOURCES_DIR / "memory" / "mcp_memory.db"
)

# Auto-create session on startup
SESSION_ID = memory.create_session(project_name="AI-Assistant")
logger.info(f"🚀 Session created: {SESSION_ID}")


# ==================== DECORATOR: Auto-save to memory ====================

def with_memory(importance: int = 5, observation_type: str = "general"):
    """
    Decorator tự động lưu tool usage vào memory
    
    Args:
        importance: 1-10 scale
        observation_type: decision, bugfix, feature, refactor, discovery
    """
    def decorator(func):
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


# ==================== TOOLS: FILE OPERATIONS ====================

@mcp.tool()
@with_memory(importance=5, observation_type="search")
def search_files(query: str, file_type: str = "all", max_results: int = 10) -> Dict[str, Any]:
    """
    Tìm kiếm files trong workspace theo query.
    
    Args:
        query: Từ khóa tìm kiếm
        file_type: Loại file (all, py, md, json, txt, js, html, css)
        max_results: Số kết quả tối đa
        
    Returns:
        Dict chứa danh sách files tìm thấy
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
    Đọc nội dung file.
    
    Args:
        file_path: Đường dẫn file (relative to BASE_DIR)
        start_line: Dòng bắt đầu (1-based)
        end_line: Dòng kết thúc (None = đến cuối file)
        max_lines: Số dòng tối đa
        
    Returns:
        Dict chứa nội dung file
    """
    full_path = BASE_DIR / file_path
    
    if not full_path.exists():
        return {"error": f"File not found: {file_path}"}
    
    if not full_path.is_file():
        return {"error": f"Not a file: {file_path}"}
    
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
        return {"error": str(e)}


@mcp.tool()
@with_memory(importance=4, observation_type="list")
def list_directory(directory_path: str = ".", show_hidden: bool = False) -> Dict[str, Any]:
    """
    Liệt kê files và folders trong directory.
    
    Args:
        directory_path: Đường dẫn directory (relative to BASE_DIR)
        show_hidden: Hiển thị files/folders ẩn
        
    Returns:
        Dict chứa danh sách files và folders
    """
    full_path = BASE_DIR / directory_path
    
    if not full_path.exists():
        return {"error": f"Directory not found: {directory_path}"}
    
    if not full_path.is_dir():
        return {"error": f"Not a directory: {directory_path}"}
    
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
    Lấy thông tin tổng quan về AI-Assistant project.
    
    Returns:
        Dict chứa thông tin project
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
    Tìm kiếm trong log files của services.
    
    Args:
        service_name: Tên service (chatbot, text2sql, hub-gateway, etc.)
        level: Log level (ALL, ERROR, WARNING, INFO, DEBUG)
        max_lines: Số dòng tối đa
        
    Returns:
        Dict chứa kết quả tìm kiếm logs
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
    Thực hiện tính toán an toàn.
    
    Args:
        expression: Biểu thức toán học (vd: "2 + 2", "(10 * 5) / 2")
        
    Returns:
        Dict chứa kết quả tính toán
    """
    try:
        # Safe eval - only allow math operations
        allowed_names = {
            "abs": abs, "round": round, "min": min, "max": max,
            "sum": sum, "pow": pow
        }
        
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        
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


# ==================== TOOLS: MEMORY SYSTEM (NEW!) ====================

@mcp.tool()
def search_memory(
    query: str, 
    limit: int = 10,
    min_importance: int = 0
) -> Dict[str, Any]:
    """
    🆕 Tìm kiếm trong memory (observations từ các sessions trước).
    
    Args:
        query: Từ khóa tìm kiếm
        limit: Số kết quả tối đa
        min_importance: Độ quan trọng tối thiểu (0-10)
        
    Returns:
        Dict chứa observations tìm thấy
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
                "files": json.loads(obs['file_references']) if obs['file_references'] else [],
                "tags": json.loads(obs['concept_tags']) if obs['concept_tags'] else []
            }
            for obs in results
        ]
    }


@mcp.tool()
def get_recent_context(limit: int = 30, min_importance: int = 5) -> Dict[str, Any]:
    """
    🆕 Lấy context gần đây để inject vào session mới.
    
    Args:
        limit: Số observations
        min_importance: Độ quan trọng tối thiểu
        
    Returns:
        Dict chứa formatted context
    """
    context_text = memory.get_context_for_session(
        max_observations=limit,
        min_importance=min_importance
    )
    
    observations = memory.get_recent_observations(
        limit=limit,
        min_importance=min_importance
    )
    
    return {
        "context": context_text,
        "observation_count": len(observations),
        "min_importance": min_importance
    }


@mcp.tool()
def get_memory_by_file(file_path: str, limit: int = 20) -> Dict[str, Any]:
    """
    🆕 Lấy memories liên quan đến file cụ thể.
    
    Args:
        file_path: Đường dẫn file
        limit: Số kết quả
        
    Returns:
        Dict chứa observations liên quan
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
def get_session_history(limit: int = 10) -> Dict[str, Any]:
    """
    🆕 Lấy lịch sử các sessions gần đây.
    
    Args:
        limit: Số sessions
        
    Returns:
        Dict chứa session history
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
def save_important_observation(
    observation: str,
    observation_type: str = "general",
    importance: int = 8,
    file_references: Optional[List[str]] = None,
    tags: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    🆕 Lưu một observation quan trọng thủ công.
    
    Args:
        observation: Nội dung observation
        observation_type: decision, bugfix, feature, refactor, discovery
        importance: 1-10 scale
        file_references: Danh sách files liên quan
        tags: Tags (discovery, problem-solution, pattern, etc.)
        
    Returns:
        Dict với observation_id
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
def get_memory_statistics() -> Dict[str, Any]:
    """
    🆕 Lấy thống kê về memory system.
    
    Returns:
        Dict chứa statistics
    """
    stats = memory.get_statistics()
    
    return {
        "total_sessions": stats['total_sessions'],
        "total_observations": stats['total_observations'],
        "total_tools_used": stats['total_tools'],
        "total_tokens": stats['total_tokens'],
        "top_tools": stats['tool_stats'][:5]
    }


# ==================== RESOURCES ====================

@mcp.resource("config://model")
def get_model_config() -> str:
    """Cấu hình models của AI-Assistant"""
    config_file = BASE_DIR / "config" / "model_config.py"
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            return f.read()
    return "Model config not found"


@mcp.resource("config://logging")
def get_logging_config() -> str:
    """Cấu hình logging của AI-Assistant"""
    config_file = BASE_DIR / "config" / "logging_config.py"
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            return f.read()
    return "Logging config not found"


@mcp.resource("docs://readme")
def get_readme() -> str:
    """README của AI-Assistant project"""
    readme_file = BASE_DIR / "README.md"
    if readme_file.exists():
        with open(readme_file, 'r', encoding='utf-8') as f:
            return f.read()
    return "README not found"


@mcp.resource("docs://structure")
def get_project_structure() -> str:
    """Cấu trúc thư mục của AI-Assistant"""
    structure_file = BASE_DIR / "docs" / "STRUCTURE.md"
    if structure_file.exists():
        with open(structure_file, 'r', encoding='utf-8') as f:
            return f.read()
    return "Structure documentation not found"


@mcp.resource("memory://context")
def get_memory_context_resource() -> str:
    """🆕 Context từ memory để inject vào session"""
    return memory.get_context_for_session(max_observations=30, min_importance=5)


# ==================== PROMPTS ====================

@mcp.prompt()
def code_review(file_path: str) -> str:
    """
    Prompt template để review code.
    
    Args:
        file_path: Đường dẫn file cần review
    """
    return f"""Hãy review code trong file: {file_path}

Vui lòng phân tích:
1. Code quality và best practices
2. Potential bugs hoặc security issues
3. Performance concerns
4. Suggestions for improvement

Sử dụng tool read_file_content để đọc file và phân tích chi tiết."""


@mcp.prompt()
def debug_error(error_message: str, service_name: str) -> str:
    """
    Prompt template để debug lỗi.
    
    Args:
        error_message: Thông báo lỗi
        service_name: Tên service bị lỗi
    """
    return f"""Service '{service_name}' đang gặp lỗi:
Error: {error_message}

Hãy giúp tôi debug bằng cách:
1. Tìm kiếm logs liên quan (search_logs)
2. Kiểm tra memory xem có gặp lỗi tương tự trước đây không (search_memory)
3. Xác định root cause
4. Đề xuất solution"""


@mcp.prompt()
def explain_code(file_path: str, function_name: Optional[str] = None) -> str:
    """
    Prompt template để giải thích code.
    
    Args:
        file_path: Đường dẫn file
        function_name: Tên function cần giải thích (optional)
    """
    target = f"function {function_name} trong " if function_name else ""
    return f"""Hãy giải thích code {target}file: {file_path}

Vui lòng:
1. Đọc code (read_file_content)
2. Kiểm tra memory xem có context về file này không (get_memory_by_file)
3. Giải thích logic bằng tiếng Việt
4. Input/Output expected
5. Các edge cases cần lưu ý"""


@mcp.prompt()
def session_summary() -> str:
    """🆕 Prompt để tạo summary cho session"""
    return """Hãy tạo summary cho session làm việc vừa rồi.

Sử dụng:
1. get_session_history để xem session hiện tại
2. get_memory_statistics để xem các tools đã dùng
3. Tổng hợp thành summary ngắn gọn với:
   - Các công việc đã làm
   - Files đã thao tác
   - Decisions quan trọng
   - Next steps"""


# ==================== MAIN ====================

def main():
    """Khởi động MCP server"""
    print(f"🚀 Starting AI-Assistant MCP Server V2.0 WITH MEMORY...")
    print(f"📁 Base Directory: {BASE_DIR}")
    print(f"🧠 Memory Database: {memory.db_path}")
    print(f"📋 Session ID: {SESSION_ID}")
    print(f"\n✨ NEW FEATURES:")
    print(f"   🔧 Tools: All original tools + 6 memory tools")
    print(f"   📦 Resources: Config, docs + memory context")
    print(f"   💬 Prompts: Code review, debug, explain + session summary")
    print(f"   🧠 MEMORY: Persistent storage, search history, AI observations")
    print(f"\n✅ Server is ready!")
    print(f"📡 Listening for MCP client connections...")
    print(f"\n💡 TIP: Sau mỗi session, memory sẽ tự động lưu lại!")
    
    try:
        # Run server
        mcp.run()
    finally:
        # End session on shutdown
        print(f"\n\n🛑 Shutting down...")
        print(f"💾 Saving session summary...")
        memory.end_session(SESSION_ID, summary="Session ended")
        print(f"✅ Session saved: {SESSION_ID}")


if __name__ == "__main__":
    main()
