"""
AI-Assistant MCP Server - Enhanced Version
===========================================
Model Context Protocol server với advanced features.

NEW FEATURES:
- Error handling và validation
- Logging system
- Caching mechanism
- Rate limiting
- Health checks
- Metrics tracking
"""

import os
import json
import sqlite3
import logging
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
from functools import wraps
from collections import defaultdict
import time

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("ERROR: FastMCP không được cài đặt.")
    print("Vui lòng chạy: pip install 'mcp[cli]'")
    exit(1)

# ==================== SETUP LOGGING ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mcp_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('MCP-Server')

# ==================== CONFIGURATION ====================

class Config:
    """Server configuration"""
    CACHE_ENABLED = True
    CACHE_TTL = 300  # 5 minutes
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_RESULTS = 100
    RATE_LIMIT_REQUESTS = 100  # requests
    RATE_LIMIT_WINDOW = 60  # seconds
    
config = Config()

# ==================== CACHE SYSTEM ====================

class SimpleCache:
    """Simple in-memory cache với TTL"""
    
    def __init__(self):
        self.cache = {}
        self.timestamps = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get từ cache nếu còn valid"""
        if key not in self.cache:
            return None
        
        # Check TTL
        if time.time() - self.timestamps[key] > config.CACHE_TTL:
            del self.cache[key]
            del self.timestamps[key]
            return None
        
        logger.debug(f"Cache HIT: {key}")
        return self.cache[key]
    
    def set(self, key: str, value: Any):
        """Set value vào cache"""
        self.cache[key] = value
        self.timestamps[key] = time.time()
        logger.debug(f"Cache SET: {key}")
    
    def clear(self):
        """Clear toàn bộ cache"""
        self.cache.clear()
        self.timestamps.clear()
        logger.info("Cache cleared")

cache = SimpleCache()

# ==================== RATE LIMITER ====================

class RateLimiter:
    """Simple rate limiter"""
    
    def __init__(self):
        self.requests = defaultdict(list)
    
    def is_allowed(self, key: str = "default") -> bool:
        """Check nếu request được phép"""
        now = time.time()
        
        # Remove old requests
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if now - req_time < config.RATE_LIMIT_WINDOW
        ]
        
        # Check limit
        if len(self.requests[key]) >= config.RATE_LIMIT_REQUESTS:
            logger.warning(f"Rate limit exceeded for {key}")
            return False
        
        self.requests[key].append(now)
        return True

rate_limiter = RateLimiter()

# ==================== METRICS ====================

class Metrics:
    """Track server metrics"""
    
    def __init__(self):
        self.tool_calls = defaultdict(int)
        self.errors = defaultdict(int)
        self.total_requests = 0
        self.start_time = time.time()
    
    def record_call(self, tool_name: str):
        """Record tool call"""
        self.tool_calls[tool_name] += 1
        self.total_requests += 1
    
    def record_error(self, error_type: str):
        """Record error"""
        self.errors[error_type] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics"""
        uptime = time.time() - self.start_time
        return {
            "uptime_seconds": round(uptime, 2),
            "total_requests": self.total_requests,
            "tool_calls": dict(self.tool_calls),
            "errors": dict(self.errors),
            "requests_per_minute": round(self.total_requests / (uptime / 60), 2) if uptime > 0 else 0
        }

metrics = Metrics()

# ==================== DECORATORS ====================

def validate_path(func):
    """Decorator để validate file paths"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Check cho path parameter
        path = kwargs.get('file_path') or kwargs.get('dir_path')
        if path:
            # Security: Prevent path traversal
            if '..' in path or path.startswith('/'):
                logger.error(f"Invalid path detected: {path}")
                return {"error": "Invalid path: Path traversal not allowed"}
        return func(*args, **kwargs)
    return wrapper

def with_cache(cache_key_func):
    """Decorator để cache kết quả"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not config.CACHE_ENABLED:
                return func(*args, **kwargs)
            
            # Generate cache key
            cache_key = cache_key_func(*args, **kwargs)
            
            # Try cache
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
            
            # Execute and cache
            result = func(*args, **kwargs)
            cache.set(cache_key, result)
            return result
        return wrapper
    return decorator

def with_metrics(tool_name: str):
    """Decorator để track metrics"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            metrics.record_call(tool_name)
            try:
                return func(*args, **kwargs)
            except Exception as e:
                metrics.record_error(type(e).__name__)
                raise
        return wrapper
    return decorator

def with_rate_limit(func):
    """Decorator để rate limiting"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not rate_limiter.is_allowed():
            return {"error": "Rate limit exceeded. Please try again later."}
        return func(*args, **kwargs)
    return wrapper

# ==================== MAIN SERVER ====================

# Khởi tạo MCP server
mcp = FastMCP("AI-Assistant")

# Base paths
BASE_DIR = Path(__file__).parent.parent.parent
LOCAL_DATA_DIR = BASE_DIR / "local_data"
RESOURCES_DIR = BASE_DIR / "resources"
LOGS_DIR = RESOURCES_DIR / "logs"

# ==================== ENHANCED TOOLS ====================

@mcp.tool()
@with_rate_limit
@with_metrics("search_files")
@with_cache(lambda query, file_type="all", max_results=10: f"search:{query}:{file_type}:{max_results}")
def search_files(query: str, file_type: str = "all", max_results: int = 10) -> Dict[str, Any]:
    """
    Tìm kiếm files trong workspace theo query (WITH CACHING).
    
    Args:
        query: Từ khóa tìm kiếm
        file_type: Loại file (all, py, md, json, txt)
        max_results: Số kết quả tối đa
        
    Returns:
        Dict chứa danh sách files tìm thấy
    """
    try:
        logger.info(f"Searching files: query={query}, type={file_type}")
        
        results = []
        extensions = {
            "all": ["*"],
            "py": [".py"],
            "md": [".md"],
            "json": [".json"],
            "txt": [".txt"]
        }
        
        exts = extensions.get(file_type, ["*"])
        max_results = min(max_results, config.MAX_RESULTS)
        
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
        
        logger.info(f"Found {len(results)} files")
        return {
            "query": query,
            "file_type": file_type,
            "total_found": len(results),
            "results": results,
            "cached": False
        }
    
    except Exception as e:
        logger.error(f"Error in search_files: {str(e)}")
        return {"error": f"Search failed: {str(e)}"}


@mcp.tool()
@with_rate_limit
@with_metrics("read_file_content")
@validate_path
def read_file_content(file_path: str, max_lines: int = 100) -> Dict[str, Any]:
    """
    Đọc nội dung file (WITH VALIDATION).
    
    Args:
        file_path: Đường dẫn tương đối từ project root
        max_lines: Số dòng tối đa đọc
        
    Returns:
        Dict chứa nội dung file
    """
    try:
        logger.info(f"Reading file: {file_path}")
        
        full_path = BASE_DIR / file_path
        
        if not full_path.exists():
            return {"error": f"File không tồn tại: {file_path}"}
        
        if not full_path.is_file():
            return {"error": f"Đường dẫn không phải là file: {file_path}"}
        
        # Check file size
        file_size = os.path.getsize(full_path)
        if file_size > config.MAX_FILE_SIZE:
            return {"error": f"File quá lớn: {file_size} bytes (max: {config.MAX_FILE_SIZE})"}
        
        # Đọc file
        with open(full_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        content_lines = lines[:max_lines]
        
        logger.info(f"Read {len(content_lines)}/{total_lines} lines")
        
        return {
            "file_path": file_path,
            "total_lines": total_lines,
            "lines_read": len(content_lines),
            "truncated": total_lines > max_lines,
            "content": "".join(content_lines),
            "size_bytes": file_size
        }
    
    except UnicodeDecodeError:
        return {"error": "File không phải text file hoặc encoding không hợp lệ"}
    except Exception as e:
        logger.error(f"Error reading file: {str(e)}")
        return {"error": f"Lỗi đọc file: {str(e)}"}


@mcp.tool()
@with_rate_limit
@with_metrics("list_directory")
@validate_path
def list_directory(dir_path: str = ".", include_hidden: bool = False) -> Dict[str, Any]:
    """
    Liệt kê nội dung thư mục (WITH VALIDATION).
    
    Args:
        dir_path: Đường dẫn thư mục (tương đối từ project root)
        include_hidden: Có hiển thị file/folder ẩn không
        
    Returns:
        Dict chứa danh sách files và folders
    """
    try:
        logger.info(f"Listing directory: {dir_path}")
        
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
        
        logger.info(f"Listed {len(files)} files, {len(folders)} folders")
        
        return {
            "directory": dir_path,
            "total_items": len(files) + len(folders),
            "folders": sorted(folders, key=lambda x: x["name"]),
            "files": sorted(files, key=lambda x: x["name"])
        }
    
    except Exception as e:
        logger.error(f"Error listing directory: {str(e)}")
        return {"error": f"Lỗi liệt kê thư mục: {str(e)}"}


@mcp.tool()
@with_cache(lambda: "project_info")
def get_project_info() -> Dict[str, Any]:
    """
    Lấy thông tin tổng quan về project (CACHED).
    
    Returns:
        Dict chứa thông tin project
    """
    try:
        logger.info("Getting project info")
        
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
            "services": sorted(services),
            "service_count": len(services),
            "structure": {
                "config": (BASE_DIR / "config").exists(),
                "services": (BASE_DIR / "services").exists(),
                "tests": (BASE_DIR / "tests").exists(),
                "docs": (BASE_DIR / "docs").exists(),
                "resources": (BASE_DIR / "resources").exists(),
                "local_data": (BASE_DIR / "local_data").exists()
            },
            "description": "Multi-service AI application với chatbot, document intelligence, image processing, và nhiều tính năng khác.",
            "cached": False
        }
    
    except Exception as e:
        logger.error(f"Error getting project info: {str(e)}")
        return {"error": f"Lỗi lấy thông tin project: {str(e)}"}


@mcp.tool()
@with_metrics("search_logs")
def search_logs(service: str = "all", level: str = "all", last_n_lines: int = 50) -> Dict[str, Any]:
    """
    Tìm kiếm và đọc logs từ các services (WITH ERROR HANDLING).
    
    Args:
        service: Tên service (all, chatbot, text2sql, etc.)
        level: Log level (all, error, warning, info)
        last_n_lines: Số dòng cuối cùng đọc từ log
        
    Returns:
        Dict chứa log entries
    """
    try:
        logger.info(f"Searching logs: service={service}, level={level}")
        
        logs_found = []
        
        if not LOGS_DIR.exists():
            return {"error": "Thư mục logs không tồn tại"}
        
        # Tìm log files
        for log_file in LOGS_DIR.glob("*.log"):
            if service != "all" and service.lower() not in log_file.name.lower():
                continue
            
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            except:
                continue
            
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
        
        logger.info(f"Found logs from {len(logs_found)} services")
        
        return {
            "service_filter": service,
            "level_filter": level,
            "logs_found": len(logs_found),
            "data": logs_found
        }
    
    except Exception as e:
        logger.error(f"Error searching logs: {str(e)}")
        return {"error": f"Lỗi đọc logs: {str(e)}"}


@mcp.tool()
@with_metrics("calculate")
def calculate(expression: str) -> Dict[str, Any]:
    """
    Thực hiện phép tính toán học (SAFE EVAL).
    
    Args:
        expression: Biểu thức toán học
        
    Returns:
        Dict chứa kết quả tính toán
    """
    import math
    
    try:
        logger.info(f"Calculating: {expression}")
        
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
        
        logger.info(f"Result: {result}")
        
        return {
            "expression": expression,
            "result": result,
            "type": type(result).__name__
        }
    
    except Exception as e:
        logger.error(f"Calculation error: {str(e)}")
        return {
            "expression": expression,
            "error": f"Lỗi tính toán: {str(e)}"
        }


# ==================== NEW TOOLS ====================

@mcp.tool()
@with_metrics("get_health")
def get_health() -> Dict[str, Any]:
    """
    Health check endpoint - kiểm tra trạng thái server.
    
    Returns:
        Dict chứa health status
    """
    try:
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics.get_stats(),
            "cache": {
                "enabled": config.CACHE_ENABLED,
                "items": len(cache.cache)
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@mcp.tool()
def clear_cache() -> Dict[str, Any]:
    """
    Clear toàn bộ cache.
    
    Returns:
        Dict confirmation
    """
    try:
        cache.clear()
        logger.info("Cache cleared by user request")
        return {
            "status": "success",
            "message": "Cache đã được xóa"
        }
    except Exception as e:
        return {"error": str(e)}


# ==================== RESOURCES (unchanged) ====================

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


# ==================== PROMPTS (unchanged) ====================

@mcp.prompt()
def code_review_prompt(file_path: str) -> str:
    """Prompt template để review code."""
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
    """Prompt template để debug lỗi."""
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
    """Prompt template để giải thích code."""
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
    print("="*60)
    print("🚀 AI-Assistant MCP Server - Enhanced Version")
    print("="*60)
    print(f"📁 Base Directory: {BASE_DIR}")
    print(f"🔧 Tools available: {len(mcp._tools)}")
    print(f"📦 Resources available: {len(mcp._resources)}")
    print(f"💬 Prompts available: {len(mcp._prompts)}")
    print(f"")
    print("✨ NEW FEATURES:")
    print(f"  ✅ Error handling & validation")
    print(f"  ✅ Logging system (mcp_server.log)")
    print(f"  ✅ Caching (TTL: {config.CACHE_TTL}s)")
    print(f"  ✅ Rate limiting ({config.RATE_LIMIT_REQUESTS} req/{config.RATE_LIMIT_WINDOW}s)")
    print(f"  ✅ Metrics tracking")
    print(f"  ✅ Health checks")
    print(f"")
    print("="*60)
    print("✅ Server is ready!")
    print("="*60)
    
    logger.info("MCP Server started successfully")
    
    # Run server
    try:
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        print("\n👋 Server stopped")
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        print(f"\n❌ Server error: {str(e)}")


if __name__ == "__main__":
    main()
