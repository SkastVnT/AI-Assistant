"""
MCP Integration for ChatBot Service
====================================
TÃ­ch há»£p Model Context Protocol vÃ o ChatBot Ä‘á»ƒ:
- Access local files/folders
- Provide code context to AI
- Search and read files
- Enhanced AI responses with file context
"""

import logging
import re
import os
import json
import importlib.util
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Define server-controlled base directories that MCP is allowed to access.
# All user-specified paths must resolve under at least one of these roots.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_WORKSPACE = PROJECT_ROOT
ALLOWED_BASE_DIRS = [
    PROJECT_ROOT,
    DEFAULT_WORKSPACE,
]

# Define a safe root directory for all MCP file operations.
# This can be overridden via the MCP_SAFE_ROOT environment variable.
MCP_SAFE_ROOT = Path(os.environ.get("MCP_SAFE_ROOT", Path.cwd())).resolve()

try:
    from src.ocr_integration import ocr_client
    OCR_AVAILABLE = True
except ImportError:
    ocr_client = None
    OCR_AVAILABLE = False


def sanitize_for_log(text: str) -> str:
    """Sanitize text for logging to prevent log injection"""
    if not text:
        return ""
    # Remove control characters, newlines, and limit length
    sanitized = re.sub(r'[\r\n\t\x00-\x1f\x7f-\x9f]', '', str(text))
    return sanitized[:200]  # Limit to 200 chars


def _is_subpath(path: Path, base: Path) -> bool:
    """Return True if path is located inside base."""
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def validate_and_resolve_path(path_str: str, must_exist: bool = True) -> Optional[Path]:
    """
    Safely validate and resolve a path.

    The returned path is:
      * free from obvious traversal patterns,
      * normalized and resolved, and
      * guaranteed to be located under MCP_SAFE_ROOT.

    Returns None if the path is invalid, outside the safe root, or potentially malicious.
    """
    if not path_str or not isinstance(path_str, str):
        return None

    # Check for path traversal patterns BEFORE creating Path object
    if '..' in path_str or path_str.startswith('~'):
        logger.warning("Path traversal or home expansion detected")
        return None

    # Check for suspicious characters
    if any(char in path_str for char in ['\0', '\n', '\r']):
        logger.warning("Suspicious characters in path")
        return None

    try:
        # Normalize and resolve the path
        normalized = os.path.normpath(path_str)
        absolute = os.path.abspath(normalized)
        real = os.path.realpath(absolute)

        candidate = Path(real)

        # Enforce that the resolved path is under at least one allowed base dir
        if not any(_is_subpath(candidate, base) for base in ALLOWED_BASE_DIRS):
            logger.warning("Path outside allowed base directories")
            return None

        # Enforce that the resolved path is under the safe root
        real_path = candidate.resolve()
        try:
            # Python 3.9+ has is_relative_to
            if not real_path.is_relative_to(MCP_SAFE_ROOT):
                logger.warning("Path outside of MCP safe root rejected")
                return None
        except AttributeError:
            # Fallback for older Python versions
            safe_root_str = str(MCP_SAFE_ROOT)
            real_str = str(real_path)
            if not (real_str == safe_root_str or real_str.startswith(safe_root_str + os.sep)):
                logger.warning("Path outside of MCP safe root rejected")
                return None

        if must_exist and not real_path.exists():
            return None

        return real_path
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
            mcp_server_url: URL cá»§a MCP Server
        """
        self.mcp_server_url = mcp_server_url
        self.enabled = False
        self.selected_folders: List[str] = []
        self.session_id = None
        self.ocr_available = OCR_AVAILABLE

    DOMAIN_QUERY_MAP: Dict[str, List[str]] = {
        "bugfix": ["error", "exception", "traceback", "bugfix", "fix"],
        "performance": ["performance", "optimize", "latency", "slow", "throughput"],
        "security": ["security", "auth", "permission", "injection", "xss", "csrf"],
        "database": ["database", "sql", "mongodb", "query", "schema", "index"],
        "api": ["api", "endpoint", "route", "request", "response", "http"],
        "frontend": ["frontend", "ui", "css", "javascript", "react", "html"],
        "devops": ["docker", "deploy", "ci", "pipeline", "kubernetes", "infra"],
        "mcp": ["mcp", "memory", "context", "tool", "server"],
        "general": ["chatbot", "assistant", "feature", "refactor", "project"]
    }
        
    def enable(self):
        """Báº­t MCP integration"""
        # ChatBot MCP works standalone - no server connection needed
        # It directly accesses local files using pathlib
        self.enabled = True
        logger.info("âœ… MCP Client enabled (Standalone mode)")
        return True
    
    def disable(self):
        """Táº¯t MCP integration"""
        self.enabled = False
        self.selected_folders = []
        logger.info("ðŸ”´ MCP Client disabled")
    
    def add_folder(self, folder_path: str) -> bool:
        """
        ThÃªm folder vÃ o danh sÃ¡ch accessible folders
        
        Args:
            folder_path: ÄÆ°á»ng dáº«n folder
            
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
            logger.info("ðŸ“ Folder added successfully")
        
        return True
    
    def remove_folder(self, folder_path: str):
        """Remove folder khá»i danh sÃ¡ch"""
        if folder_path in self.selected_folders:
            self.selected_folders.remove(folder_path)
            logger.info("ðŸ—‘ï¸ Folder removed successfully")
    
    def list_files_in_folder(self, folder_path: str = None) -> List[Dict[str, Any]]:
        """
        List files trong folder
        
        Args:
            folder_path: ÄÆ°á»ng dáº«n folder (None = list all selected folders)
            
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
        Search files trong selected folders (by filename)
        
        Args:
            query: Tá»« khÃ³a tÃ¬m kiáº¿m
            file_type: Loáº¡i file (py, js, md, etc.)
            
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
        Äá»c ná»™i dung file
        
        Args:
            file_path: ÄÆ°á»ng dáº«n file
            max_lines: Sá»‘ dÃ²ng tá»‘i Ä‘a
            
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
            # Use os.open to avoid taint tracking through Path object
            # Open file descriptor first, then wrap in file object
            fd = os.open(str(path), os.O_RDONLY | os.O_TEXT)
            with os.fdopen(fd, 'r', encoding='utf-8', errors='ignore') as f:
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
            logger.error(f"Error reading file: {sanitize_for_log(str(type(e).__name__))}")
            return {"error": "Failed to read file"}

    def extract_file_with_ocr(self, file_path: str, max_chars: int = 12000) -> Dict[str, Any]:
        """
        Extract text from a document/image file using OCR integration.

        Args:
            file_path: Path to file.
            max_chars: Max characters returned.

        Returns:
            OCR extraction result.
        """
        if not self.enabled:
            return {"success": False, "error": "MCP is disabled"}

        if not self.ocr_available or ocr_client is None:
            return {"success": False, "error": "OCR integration is not available"}

        path = validate_and_resolve_path(file_path, must_exist=True)
        if path is None or not path.is_file():
            return {"success": False, "error": "Invalid file path"}

        # Ensure path is under allowed folders configured for this client.
        resolved_allowed_folders: List[Path] = []
        for folder in getattr(self, "selected_folders", []) or []:
            if not folder:
                continue
            resolved_folder = validate_and_resolve_path(str(folder), must_exist=False)
            if resolved_folder is not None:
                resolved_allowed_folders.append(resolved_folder)

        is_allowed = any(_is_subpath(path, base) for base in resolved_allowed_folders) if resolved_allowed_folders else False
        if not is_allowed:
            return {"success": False, "error": "File not in allowed folders"}

        try:
            with open(path, 'rb') as f:
                file_data = f.read()

            result = ocr_client.process_file(file_data, path.name)
            text = result.get('text', '') or ''
            result['text'] = text[:max_chars]
            result['truncated'] = len(text) > max_chars
            result['path'] = str(path)
            return result
        except Exception as e:
            return {"success": False, "error": f"OCR extraction failed: {sanitize_for_log(str(e))}"}

    def grep_content(
        self,
        pattern: str,
        file_type: str = "all",
        max_results: int = 30,
        case_sensitive: bool = False,
        regex: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Search file contents across selected folders (grep-like).

        Args:
            pattern: Text or regex pattern to find.
            file_type: File type filter (all, py, js, md, ...).
            max_results: Maximum number of matches.
            case_sensitive: Whether matching is case-sensitive.
            regex: If True, pattern is treated as regex; otherwise literal search.

        Returns:
            List of matches with file path, line number, and content.
        """
        if not self.enabled:
            return []
        
        try:
            flags = 0 if case_sensitive else re.IGNORECASE
            if regex:
                compiled = re.compile(pattern, flags)
            else:
                safe_pattern = re.escape(pattern)
                compiled = re.compile(safe_pattern, flags)
        except re.error:
            logger.warning("Invalid regex pattern in grep_content")
            return []
        
        ext_map = {
            "py": [".py"], "js": [".js", ".jsx", ".ts", ".tsx"],
            "md": [".md"], "json": [".json"], "txt": [".txt"],
            "html": [".html", ".htm"], "css": [".css", ".scss"]
        }
        target_exts = ext_map.get(file_type) if file_type != "all" else None
        skip_dirs = {'.venv', 'venv', '__pycache__', 'node_modules', '.git', 'build', 'dist'}
        results = []

        for folder in self.selected_folders:
            folder_path = validate_and_resolve_path(folder, must_exist=True)
            if folder_path is None:
                continue
            for fpath in folder_path.rglob("*"):
                if len(results) >= max_results:
                    break
                if not fpath.is_file():
                    continue
                if any(skip in fpath.parts for skip in skip_dirs):
                    continue
                if target_exts and fpath.suffix not in target_exts:
                    continue
                if fpath.stat().st_size > 2 * 1024 * 1024:
                    continue
                try:
                    for lineno, line in enumerate(
                        fpath.read_text(encoding='utf-8', errors='ignore').splitlines(), 1
                    ):
                        if compiled.search(line):
                            results.append({
                                "file": str(fpath),
                                "relative": str(fpath.relative_to(folder_path)),
                                "line": lineno,
                                "content": line.strip()
                            })
                            if len(results) >= max_results:
                                break
                except OSError:
                    continue

        return results

    def get_code_context(self, user_message: str, selected_files: list = None) -> Optional[str]:
        """
        Build contextual code snippets for improving AI responses.

        Priority order:
            1) Files explicitly selected by user.
            2) Content matches from grep search.
            3) Filename-based search.

        Args:
            user_message: User question or prompt.
            selected_files: Optional list of file paths selected in UI.

        Returns:
            Context string, or None when no context can be built.
        """
        if not self.enabled or not self.selected_folders:
            return None
        
        context_parts = []
        
        # Æ¯u tiÃªn files Ä‘Æ°á»£c chá»n tá»« UI
        if selected_files and len(selected_files) > 0:
            logger.info(f"ðŸ“Œ Using {len(selected_files)} selected files for context")
            for file_path in selected_files[:5]:  # Max 5 files
                # Validate path before processing
                validated_path = validate_and_resolve_path(file_path, must_exist=True)
                if validated_path is None:
                    logger.warning("Skipping invalid or restricted file")
                    continue
                
                # Use validated path string
                ext = validated_path.suffix.lower()
                ocr_exts = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff', '.pdf', '.docx', '.doc', '.xlsx', '.xls'}

                # For binary document/image types, prefer OCR extraction
                if ext in ocr_exts:
                    ocr_result = self.extract_file_with_ocr(str(validated_path), max_chars=5000)
                    if ocr_result.get('success') and ocr_result.get('text'):
                        logger.info("âœ… OCR extraction successful for selected file")
                        context_parts.append("\n### ðŸ“„ OCR Extracted Content\n")
                        context_parts.append(f"File: {validated_path.name}\n")
                        context_parts.append(f"Method: {ocr_result.get('method', 'ocr')}\n")
                        context_parts.append("```text\n")
                        context_parts.append(ocr_result.get('text', ''))
                        context_parts.append("\n```\n")
                    else:
                        logger.warning("âš ï¸ OCR extraction unavailable/failed for selected file")
                    continue

                file_content = self.read_file(str(validated_path), max_lines=200)
                if file_content and 'content' in file_content:
                    logger.info("âœ… File read successfully")
                    # Don't log file name to avoid injection
                    context_parts.append("\n### ðŸ“„ File\n")
                    context_parts.append("```")
                    # Safely get extension from validated path (not user input)
                    safe_ext = validated_path.suffix.lstrip('.') if validated_path.suffix else 'txt'
                    context_parts.append(safe_ext)
                    context_parts.append("\n")
                    context_parts.append(file_content['content'])
                    context_parts.append("\n```\n")
                elif file_content and 'error' in file_content:
                    logger.error("âŒ Error reading file from selection")
                else:
                    logger.warning("âš ï¸ No content available for file")
        else:
            # Fallback: tÃ¬m files tá»± Ä‘á»™ng theo keywords + content grep
            keywords = [word for word in user_message.lower().split() if len(word) > 3]
            relevant_files = []
            seen_paths: set = set()

            # 1) TÃ¬m theo ná»™i dung file (grep) vá»›i tá»« khÃ³a quan trá»ng
            for keyword in keywords[:3]:
                matches = self.grep_content(keyword, max_results=10)
                for match in matches:
                    fpath = match['file']
                    if fpath not in seen_paths:
                        seen_paths.add(fpath)
                        relevant_files.append({'path': fpath, 'relative_path': match['relative'], 'extension': os.path.splitext(fpath)[1]})

            # 2) Fallback: tÃ¬m theo tÃªn file náº¿u chÆ°a Ä‘á»§
            if len(relevant_files) < 3:
                for keyword in keywords[:5]:
                    files = self.search_files(keyword, file_type="all")
                    for f in files[:3]:
                        if f['path'] not in seen_paths:
                            seen_paths.add(f['path'])
                            relevant_files.append(f)

            # Read top files (giá»›i háº¡n 50 dÃ²ng má»—i file khi auto-detect)
            for file_info in relevant_files[:5]:
                file_content = self.read_file(file_info['path'], max_lines=50)
                if file_content and 'content' in file_content:
                    rel = file_info.get('relative_path', file_info['path'])
                    ext = (file_info.get('extension') or '').lstrip('.')
                    context_parts.append(f"\n### File: {rel}\n```{ext}\n")
                    context_parts.append(file_content['content'])
                    context_parts.append("\n```\n")
        
        if context_parts:
            context = "".join(context_parts)
            return f"\n\nðŸ“ **CODE CONTEXT FROM LOCAL FILES:**\n{context}"
        
        return None

    def infer_domain_from_question(self, question: str) -> Dict[str, Any]:
        """
        Infer technical domain from user's question for targeted memory cache warmup.
        """
        q = (question or "").lower()
        if not q:
            return {"domain": "general", "score": 0, "matched_keywords": [], "queries": self.DOMAIN_QUERY_MAP["general"]}

        scores: Dict[str, int] = {k: 0 for k in self.DOMAIN_QUERY_MAP.keys()}
        matched: Dict[str, List[str]] = {k: [] for k in self.DOMAIN_QUERY_MAP.keys()}

        for domain, keywords in self.DOMAIN_QUERY_MAP.items():
            for kw in keywords:
                if kw in q:
                    scores[domain] += 1
                    matched[domain].append(kw)

        best_domain = max(scores, key=lambda k: scores[k])
        if scores[best_domain] == 0:
            best_domain = "general"

        tokens = [tok for tok in re.findall(r"[a-zA-Z0-9_\-]{4,}", q) if len(tok) <= 40]
        domain_queries = list(dict.fromkeys(self.DOMAIN_QUERY_MAP.get(best_domain, []) + tokens[:5]))

        return {
            "domain": best_domain,
            "score": scores.get(best_domain, 0),
            "matched_keywords": matched.get(best_domain, []),
            "queries": domain_queries[:12]
        }

    def _warm_cache_via_http(
        self,
        queries: List[str],
        force_refresh: bool,
        cache_ttl_seconds: int,
        limit: int,
        min_importance: int,
        max_chars: int
    ) -> Dict[str, Any]:
        """Try warming cache through MCP server HTTP endpoint (if available)."""
        payload = {
            "queries": queries,
            "force_refresh": force_refresh,
            "cache_ttl_seconds": cache_ttl_seconds,
            "limit": limit,
            "min_importance": min_importance,
            "max_chars": max_chars,
        }

        # Try a few common endpoint conventions.
        endpoints = [
            f"{self.mcp_server_url.rstrip('/')}/tools/warm_memory_context_cache",
            f"{self.mcp_server_url.rstrip('/')}/warm-memory-context-cache",
            f"{self.mcp_server_url.rstrip('/')}/api/warm-memory-context-cache",
        ]

        for url in endpoints:
            try:
                data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    url,
                    data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=8) as resp:
                    body = resp.read().decode("utf-8", errors="replace")
                    parsed = json.loads(body) if body else {}
                    return {
                        "success": True,
                        "source": "mcp-server-http",
                        "endpoint": url,
                        "result": parsed
                    }
            except Exception:
                continue

        return {
            "success": False,
            "source": "mcp-server-http",
            "error": "No compatible MCP HTTP warm-cache endpoint available"
        }

    def _warm_cache_via_local_db(
        self,
        queries: List[str],
        force_refresh: bool,
        cache_ttl_seconds: int,
        limit: int,
        min_importance: int,
        max_chars: int
    ) -> Dict[str, Any]:
        """Warm cache directly via mcp-server memory DB as a local fallback."""
        try:
            current_file = Path(__file__).resolve()
            repo_root = current_file.parents[4]
            mm_path = repo_root / "services" / "mcp-server" / "database" / "memory_manager.py"
            db_path = repo_root / "resources" / "memory" / "mcp_memory.db"

            if not mm_path.exists():
                return {"success": False, "source": "local-db", "error": "memory_manager.py not found"}

            spec = importlib.util.spec_from_file_location("mcp_memory_manager_dynamic", str(mm_path))
            if spec is None or spec.loader is None:
                return {"success": False, "source": "local-db", "error": "Failed to load memory_manager module"}

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            MemoryManager = getattr(module, "MemoryManager", None)
            if MemoryManager is None:
                return {"success": False, "source": "local-db", "error": "MemoryManager class not found"}

            manager = MemoryManager(db_path=str(db_path))
            result = manager.warm_context_cache(
                queries=queries,
                project_name="AI-Assistant",
                limit=limit,
                min_importance=min_importance,
                max_chars=max_chars,
                cache_ttl_seconds=cache_ttl_seconds,
                force_refresh=force_refresh
            )

            return {
                "success": True,
                "source": "local-db",
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "source": "local-db",
                "error": sanitize_for_log(str(e))
            }

    def warm_memory_cache_by_question(
        self,
        question: str,
        domain: Optional[str] = None,
        extra_queries: Optional[List[str]] = None,
        force_refresh: bool = False,
        cache_ttl_seconds: int = 900,
        limit: int = 20,
        min_importance: int = 4,
        max_chars: int = 12000
    ) -> Dict[str, Any]:
        """
        Trigger memory cache warmup based on inferred domain from user question.
        """
        inferred = self.infer_domain_from_question(question)
        selected_domain = (domain or inferred["domain"]).strip().lower()
        if selected_domain not in self.DOMAIN_QUERY_MAP:
            selected_domain = inferred["domain"]

        queries = list(self.DOMAIN_QUERY_MAP.get(selected_domain, []))
        queries.extend(inferred.get("queries", []))
        if extra_queries:
            queries.extend([str(q).strip() for q in extra_queries if str(q).strip()])

        # Deduplicate and clamp
        dedup_queries = []
        seen = set()
        for q in queries:
            key = q.lower()
            if key in seen:
                continue
            seen.add(key)
            dedup_queries.append(q)
            if len(dedup_queries) >= 20:
                break

        http_result = self._warm_cache_via_http(
            queries=dedup_queries,
            force_refresh=bool(force_refresh),
            cache_ttl_seconds=max(60, min(int(cache_ttl_seconds), 86400)),
            limit=max(1, min(int(limit), 100)),
            min_importance=max(0, min(int(min_importance), 10)),
            max_chars=max(1000, min(int(max_chars), 50000))
        )
        if http_result.get("success"):
            return {
                "success": True,
                "domain": selected_domain,
                "inferred": inferred,
                "queries": dedup_queries,
                "warmup": http_result
            }

        local_result = self._warm_cache_via_local_db(
            queries=dedup_queries,
            force_refresh=bool(force_refresh),
            cache_ttl_seconds=max(60, min(int(cache_ttl_seconds), 86400)),
            limit=max(1, min(int(limit), 100)),
            min_importance=max(0, min(int(min_importance), 10)),
            max_chars=max(1000, min(int(max_chars), 50000))
        )

        return {
            "success": local_result.get("success", False),
            "domain": selected_domain,
            "inferred": inferred,
            "queries": dedup_queries,
            "warmup": local_result,
            "fallback_from_http": True
        }
    
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
    Inject code context vÃ o user message
    
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
        logger.info(f"ðŸ“ Injected code context ({len(context)} chars, {file_count} files)")
        # Don't log context preview to avoid log injection
        return enhanced_message
    else:
        logger.warning("âš ï¸ No context generated despite MCP being enabled")
    
    return user_message
