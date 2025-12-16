"""
AI-Assistant MCP Server V2.0 - Memory Manager
Manages persistent memory storage with SQLite
"""

import sqlite3
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class MemoryManager:
    """Quản lý bộ nhớ persistent cho MCP Server"""
    
    def __init__(self, db_path: str = None):
        """
        Initialize Memory Manager
        
        Args:
            db_path: Đường dẫn đến SQLite database
        """
        if db_path is None:
            db_path = Path(__file__).parent / "mcp_memory.db"
        
        self.db_path = str(db_path)
        self.current_session_id: Optional[str] = None
        self._init_database()
        
    def _init_database(self):
        """Khởi tạo database với schema"""
        schema_path = Path(__file__).parent / "schema.sql"
        
        with sqlite3.connect(self.db_path) as conn:
            with open(schema_path, 'r', encoding='utf-8') as f:
                conn.executescript(f.read())
            conn.commit()
        
        logger.info(f"✅ Database initialized: {self.db_path}")
    
    # ==================== SESSION MANAGEMENT ====================
    
    def create_session(self, project_name: str = "AI-Assistant") -> str:
        """
        Tạo session mới
        
        Returns:
            session_id
        """
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO sessions (id, project_name, start_time, status)
                VALUES (?, ?, ?, 'active')
            """, (session_id, project_name, datetime.now()))
            conn.commit()
        
        self.current_session_id = session_id
        logger.info(f"📝 Created session: {session_id}")
        return session_id
    
    def end_session(self, session_id: str = None, summary: str = None):
        """Kết thúc session"""
        if session_id is None:
            session_id = self.current_session_id
        
        if not session_id:
            return
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE sessions 
                SET end_time = ?, status = 'completed', summary = ?
                WHERE id = ?
            """, (datetime.now(), summary, session_id))
            conn.commit()
        
        logger.info(f"✅ Ended session: {session_id}")
    
    def get_active_session(self) -> Optional[str]:
        """Lấy session đang active"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id FROM sessions 
                WHERE status = 'active' 
                ORDER BY start_time DESC 
                LIMIT 1
            """)
            row = cursor.fetchone()
            return row[0] if row else None
    
    # ==================== TOOL USAGE TRACKING ====================
    
    def log_tool_usage(
        self, 
        tool_name: str,
        input_params: Dict[str, Any],
        output_data: Any,
        duration_ms: int = 0,
        success: bool = True,
        error_message: str = None
    ) -> str:
        """
        Ghi lại việc sử dụng tool
        
        Returns:
            tool_usage_id
        """
        if not self.current_session_id:
            self.create_session()
        
        usage_id = f"tool_{uuid.uuid4().hex[:12]}"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO tool_usage 
                (id, session_id, timestamp, tool_name, input_params, output_data, 
                 duration_ms, success, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                usage_id,
                self.current_session_id,
                datetime.now(),
                tool_name,
                json.dumps(input_params),
                str(output_data)[:10000],  # Limit output size
                duration_ms,
                success,
                error_message
            ))
            
            # Update session tool count
            conn.execute("""
                UPDATE sessions 
                SET tool_count = tool_count + 1
                WHERE id = ?
            """, (self.current_session_id,))
            
            conn.commit()
        
        return usage_id
    
    # ==================== OBSERVATIONS (AI LEARNINGS) ====================
    
    def save_observation(
        self,
        tool_name: str,
        observation: str,
        observation_type: str = "general",
        concept_tags: List[str] = None,
        file_references: List[str] = None,
        importance: int = 5,
        tool_input: Dict[str, Any] = None,
        tool_output: str = None
    ) -> str:
        """
        Lưu observation (AI-generated learning)
        
        Args:
            tool_name: Tên tool
            observation: Nội dung học được
            observation_type: decision, bugfix, feature, refactor, discovery
            concept_tags: Tags như discovery, problem-solution, pattern
            file_references: Files liên quan
            importance: 1-10 scale
        
        Returns:
            observation_id
        """
        if not self.current_session_id:
            self.create_session()
        
        obs_id = f"obs_{uuid.uuid4().hex[:12]}"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO observations
                (id, session_id, timestamp, tool_name, tool_input, tool_output,
                 observation, observation_type, concept_tags, file_references, importance)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                obs_id,
                self.current_session_id,
                datetime.now(),
                tool_name,
                json.dumps(tool_input) if tool_input else None,
                tool_output,
                observation,
                observation_type,
                json.dumps(concept_tags) if concept_tags else None,
                json.dumps(file_references) if file_references else None,
                importance
            ))
            conn.commit()
        
        logger.info(f"💡 Saved observation: {obs_id} ({observation_type})")
        return obs_id
    
    # ==================== SEARCH & RETRIEVAL ====================
    
    def search_observations(
        self, 
        query: str, 
        limit: int = 10,
        min_importance: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Full-text search qua observations
        
        Args:
            query: Từ khóa tìm kiếm
            limit: Số kết quả
            min_importance: Độ quan trọng tối thiểu
        
        Returns:
            List of observations
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT 
                    o.*,
                    s.project_name,
                    s.start_time as session_start
                FROM observations o
                JOIN sessions s ON o.session_id = s.id
                WHERE o.id IN (
                    SELECT content_rowid 
                    FROM observations_fts 
                    WHERE observations_fts MATCH ?
                )
                AND o.importance >= ?
                ORDER BY o.importance DESC, o.timestamp DESC
                LIMIT ?
            """, (query, min_importance, limit))
            
            results = []
            for row in cursor.fetchall():
                results.append(dict(row))
            
            return results
    
    def get_recent_observations(
        self, 
        limit: int = 50,
        min_importance: int = 0
    ) -> List[Dict[str, Any]]:
        """Lấy observations gần đây"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT 
                    o.*,
                    s.project_name
                FROM observations o
                JOIN sessions s ON o.session_id = s.id
                WHERE o.importance >= ?
                ORDER BY o.timestamp DESC
                LIMIT ?
            """, (min_importance, limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_observations_by_file(
        self, 
        file_path: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Lấy observations liên quan đến file"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT 
                    o.*,
                    s.project_name
                FROM observations o
                JOIN sessions s ON o.session_id = s.id
                WHERE o.file_references LIKE ?
                ORDER BY o.importance DESC, o.timestamp DESC
                LIMIT ?
            """, (f'%{file_path}%', limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_observations_by_type(
        self,
        obs_type: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Lấy observations theo type"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT 
                    o.*,
                    s.project_name
                FROM observations o
                JOIN sessions s ON o.session_id = s.id
                WHERE o.observation_type = ?
                ORDER BY o.importance DESC, o.timestamp DESC
                LIMIT ?
            """, (obs_type, limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    # ==================== SESSION SUMMARIES ====================
    
    def create_session_summary(
        self,
        session_id: str,
        summary: str,
        key_achievements: List[str] = None,
        files_modified: List[str] = None,
        decisions_made: List[str] = None,
        next_steps: List[str] = None,
        tags: List[str] = None
    ) -> str:
        """Tạo summary cho session"""
        summary_id = f"summ_{uuid.uuid4().hex[:12]}"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO session_summaries
                (id, session_id, summary, key_achievements, files_modified,
                 decisions_made, next_steps, tags, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                summary_id,
                session_id,
                summary,
                json.dumps(key_achievements) if key_achievements else None,
                json.dumps(files_modified) if files_modified else None,
                json.dumps(decisions_made) if decisions_made else None,
                json.dumps(next_steps) if next_steps else None,
                json.dumps(tags) if tags else None,
                datetime.now()
            ))
            conn.commit()
        
        logger.info(f"📋 Created session summary: {summary_id}")
        return summary_id
    
    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Lấy summary của session"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM session_summaries WHERE session_id = ?
            """, (session_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_recent_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Lấy sessions gần đây với summaries"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM v_recent_sessions LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    # ==================== CONTEXT GENERATION ====================
    
    def get_context_for_session(
        self, 
        max_observations: int = 30,
        min_importance: int = 5
    ) -> str:
        """
        Tạo context để inject vào session mới
        
        Returns:
            Formatted context string
        """
        observations = self.get_recent_observations(
            limit=max_observations,
            min_importance=min_importance
        )
        
        if not observations:
            return "No previous context available."
        
        # Format context
        context_lines = [
            "=== PREVIOUS CONTEXT FROM MEMORY ===\n",
            f"Found {len(observations)} relevant observations:\n"
        ]
        
        for i, obs in enumerate(observations, 1):
            importance_icon = "🔴" if obs['importance'] >= 8 else "🟡" if obs['importance'] >= 6 else "🔵"
            type_label = obs['observation_type'].upper() if obs['observation_type'] else "GENERAL"
            
            context_lines.append(
                f"\n{i}. [{importance_icon} {type_label}] {obs['observation']}"
            )
            
            if obs['file_references']:
                files = json.loads(obs['file_references'])
                context_lines.append(f"   Files: {', '.join(files)}")
            
            # Add timestamp
            timestamp = obs['timestamp']
            context_lines.append(f"   Time: {timestamp}")
        
        context_lines.append("\n=== END CONTEXT ===\n")
        
        return "\n".join(context_lines)
    
    # ==================== STATISTICS ====================
    
    def get_statistics(self) -> Dict[str, Any]:
        """Lấy thống kê tổng quan"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Total counts
            cursor = conn.execute("""
                SELECT 
                    COUNT(DISTINCT id) as total_sessions,
                    SUM(tool_count) as total_tools,
                    SUM(tokens_used) as total_tokens
                FROM sessions
            """)
            totals = dict(cursor.fetchone())
            
            # Observation count
            cursor = conn.execute("SELECT COUNT(*) as count FROM observations")
            totals['total_observations'] = cursor.fetchone()['count']
            
            # Tool usage stats
            cursor = conn.execute("SELECT * FROM v_tool_stats LIMIT 10")
            totals['tool_stats'] = [dict(row) for row in cursor.fetchall()]
            
            return totals
    
    # ==================== CLEANUP ====================
    
    def cleanup_old_data(self, days: int = 90):
        """Xóa dữ liệu cũ hơn N ngày"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            # Archive old sessions
            conn.execute("""
                UPDATE sessions 
                SET status = 'archived'
                WHERE status = 'completed' 
                AND end_time < ?
            """, (cutoff_date,))
            
            # Delete expired context cache
            conn.execute("""
                DELETE FROM memory_context 
                WHERE expires_at < ?
            """, (datetime.now(),))
            
            conn.commit()
        
        logger.info(f"🧹 Cleaned up data older than {days} days")


# ==================== SINGLETON INSTANCE ====================

_memory_manager = None

def get_memory_manager(db_path: str = None) -> MemoryManager:
    """Get singleton instance của MemoryManager"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager(db_path)
    return _memory_manager
