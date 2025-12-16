"""
MCP Integration for ChatBot Service
====================================
Tích hợp Model Context Protocol vào ChatBot để:
- Access local files/folders
- Provide code context to AI
- Search and read files
- Enhanced AI responses with file context
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


def sanitize_for_log(text: str) -> str:
    """Sanitize text for logging to prevent log injection"""
    if not text:
        return ""
    # Remove control characters, newlines, and limit length
    sanitized = re.sub(r'[\r\n\t\x00-\x1f\x7f-\x9f]', '', str(text))
    return sanitized[:200]  # Limit to 200 chars


def validate_and_resolve_path(path_str: str, must_exist: bool = True) -> Optional[Path]:
    """
    Safely validate and resolve a path
    Returns None if path is invalid or potentially malicious
    """
    if not path_str or not isinstance(path_str, str):
        return None
    
    # Check for path traversal patterns BEFORE creating Path object
    if '..' in path_str or path_str.startswith('.'):
        logger.warning("Path traversal attempt detected")
        return None
    
    # Check for suspicious characters
    if any(char in path_str for char in ['\0', '\n', '\r']):
        logger.warning("Suspicious characters in path")
        return None
    
    try:
        # Now safe to create Path object with pre-validated string
        resolved = Path(path_str).resolve(strict=must_exist)
        
        # Double-check after resolution
        if '..' in resolved.parts:
            logger.warning("Path traversal in resolved path")
            return None
            
        return resolved
    except (ValueError, OSError, RuntimeError):
        return None


class MCPClient:
    """
    MCP Client for ChatBot to communicate with MCP Server
    """
    
    def __init__(self, mcp_server_url: str = "http://localhost:37778"):
        """
        Initialize MCP Client
        
        Args:
            mcp_server_url: URL của MCP Server
        """
        self.mcp_server_url = mcp_server_url
        self.enabled = False
        self.selected_folders: List[str] = []
        self.session_id = None
        
    def enable(self):
        """Bật MCP integration"""
        # ChatBot MCP works standalone - no server connection needed
        # It directly accesses local files using pathlib
        self.enabled = True
        logger.info("✅ MCP Client enabled (Standalone mode)")
        return True
    
    def disable(self):
        """Tắt MCP integration"""
        self.enabled = False
        self.selected_folders = []
        logger.info("🔴 MCP Client disabled")
    
    def add_folder(self, folder_path: str) -> bool:
        """
        Thêm folder vào danh sách accessible folders
        
        Args:
            folder_path: Đường dẫn folder
            
        Returns:
            True if success
        """
        # Validate and resolve path safely
        path = validate_and_resolve_path(folder_path, must_exist=True)
        if path is None:
            logger.error("Invalid or suspicious folder path provided")
            return False
            
        if not path.is_dir():
            logger.error("Path is not a directory")
            return False
        
        folder_abs = str(path)
        if folder_abs not in self.selected_folders:
            self.selected_folders.append(folder_abs)
            # Don't log user-provided paths
            logger.info("📁 Folder added successfully")
        
        return True
    
    def remove_folder(self, folder_path: str):
        """Remove folder khỏi danh sách"""
        if folder_path in self.selected_folders:
            self.selected_folders.remove(folder_path)
            logger.info("🗑️ Folder removed successfully")
    
    def list_files_in_folder(self, folder_path: str = None) -> List[Dict[str, Any]]:
        """
        List files trong folder
        
        Args:
            folder_path: Đường dẫn folder (None = list all selected folders)
            
        Returns:
            List of file info
        """
        if not self.enabled:
            return []
        
        folders_to_scan = [folder_path] if folder_path else self.selected_folders
        all_files = []
        
        for folder in folders_to_scan:
            # Validate path before using
            validated_path = validate_and_resolve_path(folder, must_exist=True)
            if validated_path is None:
                logger.warning("Skipping invalid folder in scan")
                continue
            
            try:
                for file_path in validated_path.rglob("*"):
                    if file_path.is_file():
                        # Skip certain files
                        if any(skip in str(file_path) for skip in [
                            '.venv', '__pycache__', 'node_modules', '.git', 
                            '.pyc', '.pyo', '.so', '.dll'
                        ]):
                            continue
                        
                        all_files.append({
                            'path': str(file_path),
                            'relative_path': str(file_path.relative_to(validated_path)),
                            'name': file_path.name,
                            'extension': file_path.suffix,
                            'size': file_path.stat().st_size,
                            'modified': file_path.stat().st_mtime
                        })
            except Exception:
                logger.error("Error scanning folder")
        
        return all_files
    
    def search_files(self, query: str, file_type: str = "all") -> List[Dict[str, Any]]:
        """
        Search files trong selected folders
        
        Args:
            query: Từ khóa tìm kiếm
            file_type: Loại file (py, js, md, etc.)
            
        Returns:
            List of matching files
        """
        if not self.enabled:
            return []
        
        all_files = self.list_files_in_folder()
        
        # Filter by file type
        if file_type != "all":
            all_files = [f for f in all_files if f['extension'] == f".{file_type}"]
        
        # Filter by query
        results = [
            f for f in all_files
            if query.lower() in f['name'].lower() or query.lower() in f['path'].lower()
        ]
        
        return results[:50]  # Limit results
    
    def read_file(self, file_path: str, max_lines: int = 500) -> Optional[Dict[str, Any]]:
        """
        Đọc nội dung file
        
        Args:
            file_path: Đường dẫn file
            max_lines: Số dòng tối đa
            
        Returns:
            Dict with file content
        """
        if not self.enabled:
            return None
        
        # Validate and resolve path safely
        path = validate_and_resolve_path(file_path, must_exist=True)
        if path is None:
            logger.warning("Invalid or suspicious file path")
            return {"error": "Invalid file path"}
        
        # Check if file is within allowed folders
        path_str = str(path)
        is_allowed = any(
            path_str.startswith(str(validate_and_resolve_path(folder, must_exist=False) or ""))
            for folder in self.selected_folders
        )
        
        if not is_allowed:
            logger.warning("File not in allowed folders")
            return {"error": "File not in allowed folders"}
            
        if not path.is_file():
            return {"error": "Not a file"}
        
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            total_lines = len(lines)
            content_lines = lines[:max_lines] if len(lines) > max_lines else lines
            
            return {
                'path': str(path),
                'name': path.name,
                'total_lines': total_lines,
                'returned_lines': len(content_lines),
                'content': ''.join(content_lines),
                'truncated': total_lines > max_lines
            }
        except Exception as e:
            logger.error(f"❌ Error reading file: {sanitize_for_log(str(type(e).__name__))}")
            return {"error": "Failed to read file"}
    
    def get_code_context(self, user_message: str, selected_files: list = None) -> Optional[str]:
        """
        Tạo context từ code files để enhance AI response
        
        Args:
            user_message: Câu hỏi của user
            selected_files: List of file paths được chọn từ UI
            
        Returns:
            Context string hoặc None
        """
        if not self.enabled or not self.selected_folders:
            return None
        
        context_parts = []
        
        # Ưu tiên files được chọn từ UI
        if selected_files and len(selected_files) > 0:
            logger.info(f"📌 Using {len(selected_files)} selected files for context")
            for file_path in selected_files[:5]:  # Max 5 files
                # Validate path before processing
                validated_path = validate_and_resolve_path(file_path, must_exist=True)
                if validated_path is None:
                    logger.warning("Skipping invalid or restricted file")
                    continue
                
                # Use validated path string
                file_content = self.read_file(str(validated_path), max_lines=200)
                if file_content and 'content' in file_content:
                    logger.info("✅ File read successfully")
                    # Don't log file name to avoid injection
                    context_parts.append("\n### 📄 File\n")
                    context_parts.append("```")
                    # Safely get extension from validated path (not user input)
                    safe_ext = validated_path.suffix.lstrip('.') if validated_path.suffix else 'txt'
                    context_parts.append(safe_ext)
                    context_parts.append("\n")
                    context_parts.append(file_content['content'])
                    context_parts.append("\n```\n")
                elif file_content and 'error' in file_content:
                    logger.error("❌ Error reading file from selection")
                else:
                    logger.warning("⚠️ No content available for file")
        else:
            # Fallback: tìm files tự động theo keywords
            keywords = [word for word in user_message.lower().split() if len(word) > 3]
            relevant_files = []
            
            for keyword in keywords[:5]:  # Limit to 5 keywords
                files = self.search_files(keyword, file_type="all")
                relevant_files.extend(files[:3])  # Top 3 per keyword
            
            # Remove duplicates
            seen = set()
            unique_files = []
            for f in relevant_files:
                if f['path'] not in seen:
                    seen.add(f['path'])
                    unique_files.append(f)
            
            # Read top files
            for file_info in unique_files[:5]:  # Max 5 files
                file_content = self.read_file(file_info['path'], max_lines=50)
                if file_content and 'content' in file_content:
                    context_parts.append(f"\n### File: {file_info['relative_path']}\n")
                    context_parts.append("```")
                    context_parts.append(file_info['extension'][1:] if file_info['extension'] else "")
                    context_parts.append("\n")
                    context_parts.append(file_content['content'])
                    context_parts.append("\n```\n")
        
        if context_parts:
            context = "".join(context_parts)
            return f"\n\n📁 **CODE CONTEXT FROM LOCAL FILES:**\n{context}"
        
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get MCP client status"""
        return {
            'enabled': self.enabled,
            'folders_count': len(self.selected_folders),
            'folders': self.selected_folders,
            'server_url': self.mcp_server_url
        }


# Singleton instance
_mcp_client = None

def get_mcp_client(mcp_server_url: str = "http://localhost:37778") -> MCPClient:
    """Get singleton MCP client instance"""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient(mcp_server_url)
    return _mcp_client


def inject_code_context(user_message: str, mcp_client: MCPClient = None, selected_files: list = None) -> str:
    """
    Inject code context vào user message
    
    Args:
        user_message: Original message
        mcp_client: MCP client instance
        selected_files: List of selected file paths from UI
        
    Returns:
        Enhanced message with code context
    """
    if mcp_client is None:
        mcp_client = get_mcp_client()
    
    if not mcp_client.enabled:
        return user_message
    
    context = mcp_client.get_code_context(user_message, selected_files)
    
    if context:
        # Prepend context to message
        enhanced_message = f"{context}\n\n---\n\n**USER QUESTION:**\n{user_message}"
        file_count = len(selected_files) if selected_files else 0
        logger.info(f"📝 Injected code context ({len(context)} chars, {file_count} files)")
        # Don't log context preview to avoid log injection
        return enhanced_message
    else:
        logger.warning("⚠️ No context generated despite MCP being enabled")
    
    return user_message
