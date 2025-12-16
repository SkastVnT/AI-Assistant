"""
Advanced Tools cho MCP Server
==============================
Các tools nâng cao: Git, Database, Code Analysis, API Integration
"""

import subprocess
import sqlite3
import requests
from pathlib import Path
from typing import Dict, Any, List
import ast
import re

# ==================== GIT OPERATIONS ====================

def git_status() -> Dict[str, Any]:
    """
    Lấy git status của repository.
    
    Returns:
        Dict chứa git status info
    """
    try:
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        
        if result.returncode != 0:
            return {"error": "Not a git repository or git not installed"}
        
        lines = result.stdout.strip().split('\n')
        
        modified = []
        added = []
        deleted = []
        untracked = []
        
        for line in lines:
            if not line:
                continue
            status = line[:2]
            file_path = line[3:]
            
            if status.strip() == 'M':
                modified.append(file_path)
            elif status.strip() == 'A':
                added.append(file_path)
            elif status.strip() == 'D':
                deleted.append(file_path)
            elif status.strip() == '??':
                untracked.append(file_path)
        
        return {
            "modified": modified,
            "added": added,
            "deleted": deleted,
            "untracked": untracked,
            "total_changes": len(modified) + len(added) + len(deleted),
            "clean": len(lines) == 0 or (len(lines) == 1 and not lines[0])
        }
    
    except FileNotFoundError:
        return {"error": "Git not installed"}
    except Exception as e:
        return {"error": f"Git error: {str(e)}"}


def git_log(max_commits: int = 10) -> Dict[str, Any]:
    """
    Lấy git commit history.
    
    Args:
        max_commits: Số commits tối đa
        
    Returns:
        Dict chứa commit history
    """
    try:
        result = subprocess.run(
            ['git', 'log', f'-{max_commits}', '--pretty=format:%H|%an|%ae|%ad|%s'],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        
        if result.returncode != 0:
            return {"error": "Git log failed"}
        
        commits = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            parts = line.split('|')
            if len(parts) >= 5:
                commits.append({
                    "hash": parts[0],
                    "author": parts[1],
                    "email": parts[2],
                    "date": parts[3],
                    "message": parts[4]
                })
        
        return {
            "commits": commits,
            "total": len(commits)
        }
    
    except Exception as e:
        return {"error": f"Git log error: {str(e)}"}


def git_branch_info() -> Dict[str, Any]:
    """
    Lấy thông tin về git branches.
    
    Returns:
        Dict chứa branch info
    """
    try:
        # Current branch
        result = subprocess.run(
            ['git', 'branch', '--show-current'],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        
        current_branch = result.stdout.strip()
        
        # All branches
        result = subprocess.run(
            ['git', 'branch', '-a'],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        
        branches = [b.strip().replace('* ', '') for b in result.stdout.strip().split('\n')]
        
        return {
            "current_branch": current_branch,
            "all_branches": branches,
            "total_branches": len(branches)
        }
    
    except Exception as e:
        return {"error": f"Git branch error: {str(e)}"}


# ==================== DATABASE OPERATIONS ====================

def query_sqlite_database(db_path: str, query: str, params: tuple = ()) -> Dict[str, Any]:
    """
    Query SQLite database.
    
    Args:
        db_path: Đường dẫn đến database file
        query: SQL query
        params: Query parameters
        
    Returns:
        Dict chứa query results
    """
    try:
        base_dir = Path(__file__).parent.parent.parent
        full_path = base_dir / db_path
        
        if not full_path.exists():
            return {"error": f"Database not found: {db_path}"}
        
        conn = sqlite3.connect(full_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        cursor = conn.cursor()
        
        cursor.execute(query, params)
        
        # Check if it's a SELECT query
        if query.strip().upper().startswith('SELECT'):
            rows = cursor.fetchall()
            results = [dict(row) for row in rows]
            
            return {
                "query": query,
                "rows": len(results),
                "data": results
            }
        else:
            # INSERT, UPDATE, DELETE
            conn.commit()
            return {
                "query": query,
                "rows_affected": cursor.rowcount,
                "status": "success"
            }
    
    except sqlite3.Error as e:
        return {"error": f"Database error: {str(e)}"}
    except Exception as e:
        return {"error": f"Query error: {str(e)}"}
    finally:
        if conn:
            conn.close()


def list_database_tables(db_path: str) -> Dict[str, Any]:
    """
    Liệt kê tất cả tables trong SQLite database.
    
    Args:
        db_path: Đường dẫn đến database file
        
    Returns:
        Dict chứa danh sách tables
    """
    try:
        base_dir = Path(__file__).parent.parent.parent
        full_path = base_dir / db_path
        
        if not full_path.exists():
            return {"error": f"Database not found: {db_path}"}
        
        conn = sqlite3.connect(full_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        # Get table info
        table_info = []
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [{"name": col[1], "type": col[2]} for col in cursor.fetchall()]
            
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            row_count = cursor.fetchone()[0]
            
            table_info.append({
                "name": table,
                "columns": columns,
                "row_count": row_count
            })
        
        conn.close()
        
        return {
            "database": db_path,
            "tables": table_info,
            "total_tables": len(tables)
        }
    
    except Exception as e:
        return {"error": f"Database error: {str(e)}"}


# ==================== CODE ANALYSIS ====================

def analyze_python_file(file_path: str) -> Dict[str, Any]:
    """
    Phân tích Python file: functions, classes, imports.
    
    Args:
        file_path: Đường dẫn đến Python file
        
    Returns:
        Dict chứa phân tích code
    """
    try:
        base_dir = Path(__file__).parent.parent.parent
        full_path = base_dir / file_path
        
        if not full_path.exists():
            return {"error": f"File not found: {file_path}"}
        
        if not str(full_path).endswith('.py'):
            return {"error": "Not a Python file"}
        
        with open(full_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        tree = ast.parse(source)
        
        functions = []
        classes = []
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append({
                    "name": node.name,
                    "line": node.lineno,
                    "args": [arg.arg for arg in node.args.args],
                    "decorators": [d.id if isinstance(d, ast.Name) else str(d) for d in node.decorator_list]
                })
            elif isinstance(node, ast.ClassDef):
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                classes.append({
                    "name": node.name,
                    "line": node.lineno,
                    "methods": methods,
                    "bases": [b.id if isinstance(b, ast.Name) else str(b) for b in node.bases]
                })
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({"module": alias.name, "alias": alias.asname})
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append({"from": module, "import": alias.name, "alias": alias.asname})
        
        # Count lines
        lines = source.split('\n')
        total_lines = len(lines)
        code_lines = len([l for l in lines if l.strip() and not l.strip().startswith('#')])
        comment_lines = len([l for l in lines if l.strip().startswith('#')])
        
        return {
            "file": file_path,
            "functions": functions,
            "classes": classes,
            "imports": imports,
            "stats": {
                "total_lines": total_lines,
                "code_lines": code_lines,
                "comment_lines": comment_lines,
                "function_count": len(functions),
                "class_count": len(classes),
                "import_count": len(imports)
            }
        }
    
    except SyntaxError as e:
        return {"error": f"Syntax error in file: {str(e)}"}
    except Exception as e:
        return {"error": f"Analysis error: {str(e)}"}


def find_todos_in_code(directory: str = ".", pattern: str = r"#\s*TODO:?\s*(.+)") -> Dict[str, Any]:
    """
    Tìm tất cả TODO comments trong code.
    
    Args:
        directory: Thư mục để tìm
        pattern: Regex pattern cho TODO
        
    Returns:
        Dict chứa danh sách TODOs
    """
    try:
        base_dir = Path(__file__).parent.parent.parent
        search_dir = base_dir / directory
        
        todos = []
        
        for file_path in search_dir.rglob("*.py"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for i, line in enumerate(f, 1):
                        match = re.search(pattern, line, re.IGNORECASE)
                        if match:
                            todos.append({
                                "file": str(file_path.relative_to(base_dir)),
                                "line": i,
                                "todo": match.group(1).strip(),
                                "full_line": line.strip()
                            })
            except:
                continue
        
        return {
            "directory": directory,
            "total_todos": len(todos),
            "todos": todos
        }
    
    except Exception as e:
        return {"error": f"TODO search error: {str(e)}"}


# ==================== API INTEGRATION ====================

def fetch_github_repo_info(owner: str, repo: str) -> Dict[str, Any]:
    """
    Lấy thông tin GitHub repository (không cần API key).
    
    Args:
        owner: Repository owner
        repo: Repository name
        
    Returns:
        Dict chứa repo info
    """
    try:
        url = f"https://api.github.com/repos/{owner}/{repo}"
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            return {"error": f"GitHub API error: {response.status_code}"}
        
        data = response.json()
        
        return {
            "name": data.get("name"),
            "full_name": data.get("full_name"),
            "description": data.get("description"),
            "stars": data.get("stargazers_count"),
            "forks": data.get("forks_count"),
            "language": data.get("language"),
            "open_issues": data.get("open_issues_count"),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
            "url": data.get("html_url")
        }
    
    except requests.RequestException as e:
        return {"error": f"Network error: {str(e)}"}
    except Exception as e:
        return {"error": f"GitHub fetch error: {str(e)}"}


def search_stackoverflow(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Tìm kiếm câu hỏi trên StackOverflow.
    
    Args:
        query: Search query
        max_results: Số kết quả tối đa
        
    Returns:
        Dict chứa search results
    """
    try:
        url = "https://api.stackexchange.com/2.3/search"
        params = {
            "order": "desc",
            "sort": "relevance",
            "intitle": query,
            "site": "stackoverflow",
            "pagesize": max_results
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            return {"error": f"StackOverflow API error: {response.status_code}"}
        
        data = response.json()
        items = data.get("items", [])
        
        results = []
        for item in items:
            results.append({
                "title": item.get("title"),
                "link": item.get("link"),
                "score": item.get("score"),
                "answer_count": item.get("answer_count"),
                "is_answered": item.get("is_answered"),
                "tags": item.get("tags", [])
            })
        
        return {
            "query": query,
            "total_found": len(results),
            "results": results
        }
    
    except Exception as e:
        return {"error": f"StackOverflow search error: {str(e)}"}


# ==================== FILE OPERATIONS ====================

def count_lines_in_project(extensions: List[str] = [".py"]) -> Dict[str, Any]:
    """
    Đếm tổng số dòng code trong project.
    
    Args:
        extensions: Danh sách extensions để đếm
        
    Returns:
        Dict chứa thống kê
    """
    try:
        base_dir = Path(__file__).parent.parent.parent
        
        stats = {
            "total_files": 0,
            "total_lines": 0,
            "code_lines": 0,
            "comment_lines": 0,
            "blank_lines": 0,
            "by_extension": {}
        }
        
        for ext in extensions:
            ext_stats = {
                "files": 0,
                "lines": 0,
                "code": 0,
                "comments": 0,
                "blank": 0
            }
            
            for file_path in base_dir.rglob(f"*{ext}"):
                # Skip venv, node_modules
                if any(p in file_path.parts for p in ['.venv', 'venv', 'node_modules', '__pycache__']):
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    ext_stats["files"] += 1
                    ext_stats["lines"] += len(lines)
                    
                    for line in lines:
                        stripped = line.strip()
                        if not stripped:
                            ext_stats["blank"] += 1
                        elif stripped.startswith('#'):
                            ext_stats["comments"] += 1
                        else:
                            ext_stats["code"] += 1
                
                except:
                    continue
            
            stats["by_extension"][ext] = ext_stats
            stats["total_files"] += ext_stats["files"]
            stats["total_lines"] += ext_stats["lines"]
            stats["code_lines"] += ext_stats["code"]
            stats["comment_lines"] += ext_stats["comments"]
            stats["blank_lines"] += ext_stats["blank"]
        
        return stats
    
    except Exception as e:
        return {"error": f"Line count error: {str(e)}"}


# ==================== USAGE EXAMPLES ====================

if __name__ == "__main__":
    print("=== Advanced Tools Examples ===\n")
    
    # Git
    print("1. Git Status:")
    print(git_status())
    print()
    
    # Code Analysis
    print("2. Analyze Python File:")
    print(analyze_python_file("services/mcp-server/server.py"))
    print()
    
    # Line Count
    print("3. Count Lines:")
    print(count_lines_in_project([".py"]))
    print()
    
    # GitHub
    print("4. GitHub Repo Info:")
    print(fetch_github_repo_info("anthropic", "anthropic-sdk-python"))
