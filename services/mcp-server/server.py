"""
AI-Assistant MCP Server
=======================
Model Context Protocol server cho AI-Assistant project.
Sử dụng FastMCP SDK (miễn phí, mã nguồn mở).

Server này cung cấp:
- Tools: Các công cụ để AI thực thi (search, query database, file operations)
- Resources: Dữ liệu và tài nguyên từ project (logs, configs, data)
- Prompts: Template prompts cho các tác vụ phổ biến
"""

import os
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("ERROR: FastMCP không được cài đặt.")
    print("Vui lòng chạy: pip install 'mcp[cli]'")
    exit(1)

# Khởi tạo MCP server
mcp = FastMCP("AI-Assistant")

# Base paths
BASE_DIR = Path(__file__).parent.parent.parent
LOCAL_DATA_DIR = BASE_DIR / "local_data"
RESOURCES_DIR = BASE_DIR / "resources"
LOGS_DIR = RESOURCES_DIR / "logs"


# ==================== TOOLS ====================

@mcp.tool()
def search_files(query: str, file_type: str = "all", max_results: int = 10) -> Dict[str, Any]:
    """
    Tìm kiếm files trong workspace theo query.
    
    Args:
        query: Từ khóa tìm kiếm
        file_type: Loại file (all, py, md, json, txt)
        max_results: Số kết quả tối đa
        
    Returns:
        Dict chứa danh sách files tìm thấy
    """
    results = []
    extensions = {
        "all": ["*"],
        "py": [".py"],
        "md": [".md"],
        "json": [".json"],
        "txt": [".txt"]
    }
    
    exts = extensions.get(file_type, ["*"])
    
    for root, dirs, files in os.walk(BASE_DIR):
        # Skip venv, __pycache__, node_modules
        dirs[:] = [d for d in dirs if d not in ['.venv', 'venv', '__pycache__', 'node_modules', '.git']]
        
        for file in files:
            if any(ext == "*" or file.endswith(ext) for ext in exts):
                if query.lower() in file.lower():
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, BASE_DIR)
                    results.append({
                        "filename": file,
                        "path": rel_path,
                        "full_path": full_path,
                        "size": os.path.getsize(full_path)
                    })
                    
                    if len(results) >= max_results:
                        break
        
        if len(results) >= max_results:
            break
    
    return {
        "query": query,
        "file_type": file_type,
        "total_found": len(results),
        "results": results
    }


@mcp.tool()
def read_file_content(file_path: str, max_lines: int = 100) -> Dict[str, Any]:
    """
    Đọc nội dung file.
    
    Args:
        file_path: Đường dẫn tương đối từ project root
        max_lines: Số dòng tối đa đọc
        
    Returns:
        Dict chứa nội dung file
    """
    try:
        full_path = BASE_DIR / file_path
        
        if not full_path.exists():
            return {"error": f"File không tồn tại: {file_path}"}
        
        if not full_path.is_file():
            return {"error": f"Đường dẫn không phải là file: {file_path}"}
        
        # Đọc file
        with open(full_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        content_lines = lines[:max_lines]
        
        return {
            "file_path": file_path,
            "total_lines": total_lines,
            "lines_read": len(content_lines),
            "truncated": total_lines > max_lines,
            "content": "".join(content_lines)
        }
    
    except Exception as e:
        return {"error": f"Lỗi đọc file: {str(e)}"}


@mcp.tool()
def list_directory(dir_path: str = ".", include_hidden: bool = False) -> Dict[str, Any]:
    """
    Liệt kê nội dung thư mục.
    
    Args:
        dir_path: Đường dẫn thư mục (tương đối từ project root)
        include_hidden: Có hiển thị file/folder ẩn không
        
    Returns:
        Dict chứa danh sách files và folders
    """
    try:
        full_path = BASE_DIR / dir_path
        
        if not full_path.exists():
            return {"error": f"Thư mục không tồn tại: {dir_path}"}
        
        if not full_path.is_dir():
            return {"error": f"Đường dẫn không phải là thư mục: {dir_path}"}
        
        files = []
        folders = []
        
        for item in os.listdir(full_path):
            if not include_hidden and item.startswith('.'):
                continue
            
            item_path = full_path / item
            item_info = {
                "name": item,
                "size": os.path.getsize(item_path) if item_path.is_file() else None,
                "modified": datetime.fromtimestamp(os.path.getmtime(item_path)).isoformat()
            }
            
            if item_path.is_file():
                files.append(item_info)
            else:
                folders.append(item_info)
        
        return {
            "directory": dir_path,
            "total_items": len(files) + len(folders),
            "folders": sorted(folders, key=lambda x: x["name"]),
            "files": sorted(files, key=lambda x: x["name"])
        }
    
    except Exception as e:
        return {"error": f"Lỗi liệt kê thư mục: {str(e)}"}


@mcp.tool()
def get_project_info() -> Dict[str, Any]:
    """
    Lấy thông tin tổng quan về project AI-Assistant.
    
    Returns:
        Dict chứa thông tin project
    """
    services = []
    services_dir = BASE_DIR / "services"
    
    if services_dir.exists():
        for item in os.listdir(services_dir):
            item_path = services_dir / item
            if item_path.is_dir() and not item.startswith('.'):
                services.append(item)
    
    return {
        "project_name": "AI-Assistant",
        "base_directory": str(BASE_DIR),
        "services": services,
        "structure": {
            "config": (BASE_DIR / "config").exists(),
            "services": (BASE_DIR / "services").exists(),
            "tests": (BASE_DIR / "tests").exists(),
            "docs": (BASE_DIR / "docs").exists(),
            "resources": (BASE_DIR / "resources").exists(),
            "local_data": (BASE_DIR / "local_data").exists()
        },
        "description": "Multi-service AI application với chatbot, document intelligence, image processing, và nhiều tính năng khác."
    }


@mcp.tool()
def search_logs(service: str = "all", level: str = "all", last_n_lines: int = 50) -> Dict[str, Any]:
    """
    Tìm kiếm và đọc logs từ các services.
    
    Args:
        service: Tên service (all, chatbot, text2sql, etc.)
        level: Log level (all, error, warning, info)
        last_n_lines: Số dòng cuối cùng đọc từ log
        
    Returns:
        Dict chứa log entries
    """
    try:
        logs_found = []
        
        if not LOGS_DIR.exists():
            return {"error": "Thư mục logs không tồn tại"}
        
        # Tìm log files
        for log_file in LOGS_DIR.glob("*.log"):
            if service != "all" and service.lower() not in log_file.name.lower():
                continue
            
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            recent_lines = lines[-last_n_lines:] if len(lines) > last_n_lines else lines
            
            # Filter by level
            if level != "all":
                recent_lines = [line for line in recent_lines if level.upper() in line]
            
            logs_found.append({
                "service": log_file.stem,
                "file": log_file.name,
                "total_lines": len(lines),
                "entries": recent_lines
            })
        
        return {
            "service_filter": service,
            "level_filter": level,
            "logs_found": len(logs_found),
            "data": logs_found
        }
    
    except Exception as e:
        return {"error": f"Lỗi đọc logs: {str(e)}"}


@mcp.tool()
def calculate(expression: str) -> Dict[str, Any]:
    """
    Thực hiện phép tính toán học.
    
    Args:
        expression: Biểu thức toán học (vd: "2 + 2", "sqrt(16)", "10 ** 2")
        
    Returns:
        Dict chứa kết quả tính toán
    """
    import math
    
    try:
        # Safe eval với math functions
        allowed_names = {
            k: v for k, v in math.__dict__.items() if not k.startswith("__")
        }
        allowed_names.update({
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "sum": sum,
            "pow": pow
        })
        
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        
        return {
            "expression": expression,
            "result": result,
            "type": type(result).__name__
        }
    
    except Exception as e:
        return {
            "expression": expression,
            "error": f"Lỗi tính toán: {str(e)}"
        }


# ==================== RESOURCES ====================

@mcp.resource("config://model")
def get_model_config() -> str:
    """Lấy cấu hình model từ config/model_config.py"""
    try:
        config_file = BASE_DIR / "config" / "model_config.py"
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                return f.read()
        return "Model config file not found"
    except Exception as e:
        return f"Error reading model config: {str(e)}"


@mcp.resource("config://logging")
def get_logging_config() -> str:
    """Lấy cấu hình logging từ config/logging_config.py"""
    try:
        config_file = BASE_DIR / "config" / "logging_config.py"
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                return f.read()
        return "Logging config file not found"
    except Exception as e:
        return f"Error reading logging config: {str(e)}"


@mcp.resource("docs://readme")
def get_readme() -> str:
    """Lấy nội dung README.md chính của project"""
    try:
        readme_file = BASE_DIR / "README.md"
        if readme_file.exists():
            with open(readme_file, 'r', encoding='utf-8') as f:
                return f.read()
        return "README.md not found"
    except Exception as e:
        return f"Error reading README: {str(e)}"


@mcp.resource("docs://structure")
def get_structure_doc() -> str:
    """Lấy tài liệu cấu trúc project"""
    try:
        structure_file = BASE_DIR / "docs" / "STRUCTURE.md"
        if structure_file.exists():
            with open(structure_file, 'r', encoding='utf-8') as f:
                return f.read()
        return "STRUCTURE.md not found"
    except Exception as e:
        return f"Error reading structure doc: {str(e)}"


# ==================== PROMPTS ====================

@mcp.prompt()
def code_review_prompt(file_path: str) -> str:
    """
    Prompt template để review code.
    
    Args:
        file_path: Đường dẫn file cần review
    """
    return f"""Hãy review code trong file: {file_path}

Tập trung vào:
1. Code quality và best practices
2. Potential bugs hoặc issues
3. Performance optimization
4. Security concerns
5. Suggestions for improvement

Hãy đưa ra phân tích chi tiết và constructive feedback."""


@mcp.prompt()
def debug_prompt(error_message: str, context: str = "") -> str:
    """
    Prompt template để debug lỗi.
    
    Args:
        error_message: Thông báo lỗi
        context: Context thêm về lỗi
    """
    return f"""Debug lỗi sau:

Error Message: {error_message}

Context: {context}

Hãy:
1. Phân tích nguyên nhân gốc rễ của lỗi
2. Đưa ra các bước để reproduce
3. Suggest solution để fix
4. Recommend preventive measures"""


@mcp.prompt()
def explain_code_prompt(code_snippet: str) -> str:
    """
    Prompt template để giải thích code.
    
    Args:
        code_snippet: Đoạn code cần giải thích
    """
    return f"""Hãy giải thích đoạn code sau:

```
{code_snippet}
```

Giải thích:
1. Mục đích của code
2. Cách hoạt động từng phần
3. Input/Output expected
4. Các edge cases cần lưu ý"""


# ==================== MAIN ====================

def main():
    """Khởi động MCP server"""
    print(f"🚀 Starting AI-Assistant MCP Server...")
    print(f"📁 Base Directory: {BASE_DIR}")
    print(f"\n📋 Available Features:")
    print(f"   🔧 Tools: File operations, search, logs, calculations")
    print(f"   📦 Resources: Configuration, documentation")
    print(f"   💬 Prompts: Code review, debugging, explanations")
    print(f"\n✅ Server is ready!")
    print(f"📡 Listening for MCP client connections...")
    
    # Run server
    mcp.run()


if __name__ == "__main__":
    main()
