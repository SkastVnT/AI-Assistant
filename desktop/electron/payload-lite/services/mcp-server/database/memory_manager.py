"""
AI-Assistant MCP Server V2.0 - Memory Manager
Manages persistent memory storage with SQLite
"""

import sqlite3
import json
import uuid
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class MemoryManager:
    """Quáº£n lÃ½ bá»™ nhá»› persistent cho MCP Server"""
    
    def __init__(self, db_path: str = None):
        """
        Initialize Memory Manager
        
        Args:
            db_path: ÄÆ°á»ng dáº«n Ä‘áº¿n SQLite database
        """
        if db_path is None:
            db_path = Path(__file__).parent / "mcp_memory.db"
        
        self.db_path = str(db_path)
        self.current_session_id: Optional[str] = None
        self._init_database()
        
    def _init_database(self):
        """Khá»Ÿi táº¡o database vá»›i schema"""
        schema_path = Path(__file__).parent / "schema.sql"
        
        with sqlite3.connect(self.db_path) as conn:
            with open(schema_path, 'r', encoding='utf-8') as f:
                conn.executescript(f.read())
            conn.commit()
        
        logger.info(f"âœ… Database initialized: {self.db_path}")

    def _normalize_text(self, value: Optional[str], max_len: int = 10000) -> str:
        """Normalize text to improve storage consistency and deduping."""
        if value is None:
            return ""
        text = " ".join(str(value).strip().split())
        return text[:max_len]

    def _normalize_list(self, value: Optional[List[str]], max_items: int = 50, max_len: int = 300) -> List[str]:
        """Normalize list values by trimming, de-duplicating, and limiting length."""
        if not value:
            return []
        normalized = []
        seen = set()
        for item in value:
            v = self._normalize_text(str(item), max_len=max_len)
            if not v:
                continue
            key = v.lower()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(v)
            if len(normalized) >= max_items:
                break
        return normalized

    def _find_duplicate_observation(self, tool_name: str, observation: str, within_hours: int = 24) -> Optional[str]:
        """Return existing observation id if a very similar observation exists recently."""
        normalized_obs = self._normalize_text(observation, max_len=1200)
        if not normalized_obs:
            return None

        cutoff = datetime.utcnow() - timedelta(hours=within_hours)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT id
                FROM observations
                WHERE tool_name = ?
                  AND observation = ?
                  AND timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (tool_name, normalized_obs, cutoff)
            )
            row = cursor.fetchone()
            return row[0] if row else None

    def _build_context_cache_key(self, query: str, limit: int, min_importance: int, max_chars: int) -> str:
        """Create deterministic cache key for relevant memory context queries."""
        raw = f"q={query.strip().lower()}|l={limit}|i={min_importance}|c={max_chars}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _get_cached_context(
        self,
        project_name: str,
        context_type: str,
        cache_key: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached context payload if not expired."""
        now_utc = datetime.utcnow()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT id, context_data, observation_ids, expires_at, metadata
                FROM memory_context
                WHERE project_name = ?
                  AND context_type = ?
                  AND metadata = ?
                  AND (expires_at IS NULL OR expires_at > ?)
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (project_name, context_type, cache_key, now_utc)
            )
            row = cursor.fetchone()
            if not row:
                return None

            try:
                observation_ids = json.loads(row["observation_ids"] or "[]")
            except Exception:
                observation_ids = []

            return {
                "cache_id": row["id"],
                "context": row["context_data"],
                "observation_ids": observation_ids,
                "expires_at": row["expires_at"]
            }

    def _save_cached_context(
        self,
        project_name: str,
        context_type: str,
        cache_key: str,
        context_data: str,
        observation_ids: List[str],
        ttl_seconds: int
    ) -> str:
        """Persist context cache entry."""
        cache_id = f"ctx_{uuid.uuid4().hex[:12]}"
        expires_at = datetime.utcnow() + timedelta(seconds=max(60, ttl_seconds))

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO memory_context
                (id, project_name, context_type, context_data, observation_ids,
                 token_count, created_at, expires_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cache_id,
                    project_name,
                    context_type,
                    context_data,
                    json.dumps(observation_ids, ensure_ascii=False),
                    len(context_data),
                    datetime.utcnow(),
                    expires_at,
                    cache_key
                )
            )
            conn.commit()
        return cache_id

    def clear_context_cache(
        self,
        context_type: Optional[str] = None,
        older_than_hours: Optional[int] = None
    ) -> Dict[str, Any]:
        """Clear cached memory_context records by filter."""
        clauses = []
        params: List[Any] = []

        if context_type:
            clauses.append("context_type = ?")
            params.append(context_type)
        if older_than_hours is not None and older_than_hours >= 0:
            cutoff = datetime.utcnow() - timedelta(hours=older_than_hours)
            clauses.append("created_at < ?")
            params.append(cutoff)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(f"DELETE FROM memory_context {where}", params)  # nosec B608  # Uses parameterized query with params
            deleted = cursor.rowcount
            conn.commit()

        return {
            "deleted": deleted,
            "context_type": context_type,
            "older_than_hours": older_than_hours
        }

    def get_context_cache_stats(self) -> Dict[str, Any]:
        """Return quick statistics about context cache usage."""
        now_utc = datetime.utcnow()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            total = conn.execute("SELECT COUNT(*) AS c FROM memory_context").fetchone()["c"]
            active = conn.execute(
                "SELECT COUNT(*) AS c FROM memory_context WHERE expires_at IS NULL OR expires_at > ?",
                (now_utc,)
            ).fetchone()["c"]
            expired = conn.execute(
                "SELECT COUNT(*) AS c FROM memory_context WHERE expires_at IS NOT NULL AND expires_at <= ?",
                (now_utc,)
            ).fetchone()["c"]
            top_types = [
                dict(row) for row in conn.execute(
                    """
                    SELECT context_type, COUNT(*) AS count
                    FROM memory_context
                    GROUP BY context_type
                    ORDER BY count DESC
                    LIMIT 10
                    """
                ).fetchall()
            ]

        return {
            "total_entries": total,
            "active_entries": active,
            "expired_entries": expired,
            "top_context_types": top_types
        }

    def warm_context_cache(
        self,
        queries: List[str],
        project_name: str = "AI-Assistant",
        limit: int = 20,
        min_importance: int = 4,
        max_chars: int = 12000,
        cache_ttl_seconds: int = 900,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """Warm context cache for a list of frequent queries."""
        if force_refresh:
            self.clear_context_cache(context_type="relevant_query")

        details: List[Dict[str, Any]] = []
        warmed = 0
        skipped = 0

        for raw_query in queries:
            q = self._normalize_text(raw_query, max_len=300)
            if not q:
                continue

            result = self.get_relevant_context(
                query=q,
                limit=limit,
                min_importance=min_importance,
                max_chars=max_chars,
                use_cache=True,
                cache_ttl_seconds=cache_ttl_seconds,
                project_name=project_name
            )
            found = int(result.get("found", 0))
            if found > 0:
                warmed += 1
            else:
                skipped += 1

            details.append({
                "query": q,
                "found": found,
                "cache_hit": bool(result.get("cache_hit", False))
            })

        return {
            "queries_total": len(queries),
            "warmed": warmed,
            "skipped": skipped,
            "details": details
        }
    
    # ==================== SESSION MANAGEMENT ====================
    
    def create_session(self, project_name: str = "AI-Assistant") -> str:
        """
        Táº¡o session má»›i
        
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
        logger.info(f"ðŸ“ Created session: {session_id}")
        return session_id
    
    def end_session(self, session_id: str = None, summary: str = None):
        """Káº¿t thÃºc session"""
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
        
        logger.info(f"âœ… Ended session: {session_id}")
    
    def get_active_session(self) -> Optional[str]:
        """Láº¥y session Ä‘ang active"""
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
        Ghi láº¡i viá»‡c sá»­ dá»¥ng tool
        
        Returns:
            tool_usage_id
        """
        if not self.current_session_id:
            self.create_session()
        
        usage_id = f"tool_{uuid.uuid4().hex[:12]}"
        safe_input = input_params if isinstance(input_params, dict) else {"value": str(input_params)}
        safe_output = self._normalize_text(str(output_data), max_len=10000)
        
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
                json.dumps(safe_input, ensure_ascii=False),
                safe_output,
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
        LÆ°u observation (AI-generated learning)
        
        Args:
            tool_name: TÃªn tool
            observation: Ná»™i dung há»c Ä‘Æ°á»£c
            observation_type: decision, bugfix, feature, refactor, discovery
            concept_tags: Tags nhÆ° discovery, problem-solution, pattern
            file_references: Files liÃªn quan
            importance: 1-10 scale
        
        Returns:
            observation_id
        """
        if not self.current_session_id:
            self.create_session()

        normalized_observation = self._normalize_text(observation, max_len=4000)
        normalized_type = self._normalize_text(observation_type or "general", max_len=64).lower() or "general"
        normalized_tags = self._normalize_list(concept_tags)
        normalized_files = self._normalize_list(file_references)
        normalized_importance = max(1, min(int(importance), 10))
        normalized_output = self._normalize_text(tool_output, max_len=6000) if tool_output else None

        duplicate_id = self._find_duplicate_observation(tool_name, normalized_observation)
        if duplicate_id:
            # If duplicate exists, boost importance slightly instead of inserting a new row.
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    UPDATE observations
                    SET importance = MIN(10, MAX(importance, ?))
                    WHERE id = ?
                    """,
                    (normalized_importance, duplicate_id)
                )
                conn.commit()
            self.clear_context_cache(context_type="relevant_query")
            return duplicate_id

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
                normalized_output,
                normalized_observation,
                normalized_type,
                json.dumps(normalized_tags, ensure_ascii=False) if normalized_tags else None,
                json.dumps(normalized_files, ensure_ascii=False) if normalized_files else None,
                normalized_importance
            ))
            conn.commit()

        self.clear_context_cache(context_type="relevant_query")
        
        logger.info(f"ðŸ’¡ Saved observation: {obs_id} ({observation_type})")
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
            query: Tá»« khÃ³a tÃ¬m kiáº¿m
            limit: Sá»‘ káº¿t quáº£
            min_importance: Äá»™ quan trá»ng tá»‘i thiá»ƒu
        
        Returns:
            List of observations
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            q = self._normalize_text(query, max_len=300)
            if not q:
                return []

            # Try FTS first. If query syntax fails, fallback to LIKE search.
            try:
                cursor = conn.execute("""
                    SELECT
                        o.*,
                        s.project_name,
                        s.start_time as session_start
                    FROM observations o
                    JOIN sessions s ON o.session_id = s.id
                    WHERE o.rowid IN (
                        SELECT rowid
                        FROM observations_fts
                        WHERE observations_fts MATCH ?
                    )
                    AND o.importance >= ?
                    ORDER BY o.importance DESC, o.timestamp DESC
                    LIMIT ?
                """, (q, min_importance, limit))
                return [dict(row) for row in cursor.fetchall()]
            except sqlite3.OperationalError:
                like = f"%{q}%"
                cursor = conn.execute("""
                    SELECT
                        o.*,
                        s.project_name,
                        s.start_time as session_start
                    FROM observations o
                    JOIN sessions s ON o.session_id = s.id
                    WHERE (
                        o.observation LIKE ?
                        OR o.tool_name LIKE ?
                        OR o.file_references LIKE ?
                        OR o.concept_tags LIKE ?
                    )
                    AND o.importance >= ?
                    ORDER BY o.importance DESC, o.timestamp DESC
                    LIMIT ?
                """, (like, like, like, like, min_importance, limit))
                return [dict(row) for row in cursor.fetchall()]
    
    def get_recent_observations(
        self, 
        limit: int = 50,
        min_importance: int = 0
    ) -> List[Dict[str, Any]]:
        """Láº¥y observations gáº§n Ä‘Ã¢y"""
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
        """Láº¥y observations liÃªn quan Ä‘áº¿n file"""
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
        """Láº¥y observations theo type"""
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
        """Táº¡o summary cho session"""
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
        
        logger.info(f"ðŸ“‹ Created session summary: {summary_id}")
        return summary_id
    
    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Láº¥y summary cá»§a session"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM session_summaries WHERE session_id = ?
            """, (session_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_recent_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Láº¥y sessions gáº§n Ä‘Ã¢y vá»›i summaries"""
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
        min_importance: int = 5,
        max_chars: int = 12000
    ) -> str:
        """
        Táº¡o context Ä‘á»ƒ inject vÃ o session má»›i
        
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
            importance_icon = "ðŸ”´" if obs['importance'] >= 8 else "ðŸŸ¡" if obs['importance'] >= 6 else "ðŸ”µ"
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

        context = "\n".join(context_lines)
        return context[:max_chars]

    def get_relevant_context(
        self,
        query: str,
        limit: int = 20,
        min_importance: int = 4,
        max_chars: int = 12000,
        use_cache: bool = True,
        cache_ttl_seconds: int = 600,
        project_name: str = "AI-Assistant"
    ) -> Dict[str, Any]:
        """
        Build compact context prioritized by query match + importance.
        """
        query = self._normalize_text(query, max_len=500)
        cache_key = self._build_context_cache_key(query, limit, min_importance, max_chars)

        if use_cache:
            cached = self._get_cached_context(
                project_name=project_name,
                context_type="relevant_query",
                cache_key=cache_key
            )
            if cached:
                return {
                    "query": query,
                    "found": len(cached.get("observation_ids", [])),
                    "context": cached.get("context", ""),
                    "observations": [],
                    "cache_hit": True,
                    "cache_expires_at": cached.get("expires_at")
                }

        hits = self.search_observations(query=query, limit=limit, min_importance=min_importance)
        if not hits:
            return {
                "query": query,
                "found": 0,
                "context": "No relevant memory found.",
                "observations": [],
                "cache_hit": False
            }

        lines = [
            "=== RELEVANT MEMORY CONTEXT ===",
            f"Query: {query}",
            f"Matches: {len(hits)}",
            ""
        ]
        obs_out: List[Dict[str, Any]] = []

        for i, obs in enumerate(hits, 1):
            files = []
            tags = []
            try:
                files = json.loads(obs.get("file_references") or "[]")
            except Exception:
                files = []
            try:
                tags = json.loads(obs.get("concept_tags") or "[]")
            except Exception:
                tags = []

            line = f"{i}. [imp={obs.get('importance', 0)}] {obs.get('observation', '')}"
            lines.append(line)
            if files:
                lines.append(f"   files: {', '.join(files[:5])}")
            if tags:
                lines.append(f"   tags: {', '.join(tags[:8])}")
            lines.append(f"   tool: {obs.get('tool_name', 'unknown')} | time: {obs.get('timestamp', '')}")
            lines.append("")

            obs_out.append({
                "id": obs.get("id"),
                "observation": obs.get("observation"),
                "importance": obs.get("importance"),
                "type": obs.get("observation_type"),
                "tool": obs.get("tool_name"),
                "files": files,
                "tags": tags,
                "timestamp": obs.get("timestamp")
            })

        lines.append("=== END RELEVANT MEMORY ===")
        context = "\n".join(lines)[:max_chars]

        if use_cache:
            self._save_cached_context(
                project_name=project_name,
                context_type="relevant_query",
                cache_key=cache_key,
                context_data=context,
                observation_ids=[str(x.get("id")) for x in obs_out if x.get("id")],
                ttl_seconds=cache_ttl_seconds
            )

        return {
            "query": query,
            "found": len(hits),
            "context": context,
            "observations": obs_out,
            "cache_hit": False
        }
    
    # ==================== STATISTICS ====================
    
    def get_statistics(self) -> Dict[str, Any]:
        """Láº¥y thá»‘ng kÃª tá»•ng quan"""
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

            cursor = conn.execute("SELECT AVG(importance) as avg_importance FROM observations")
            avg_row = cursor.fetchone()
            totals['avg_importance'] = round(avg_row['avg_importance'], 2) if avg_row and avg_row['avg_importance'] is not None else 0

            cursor = conn.execute("""
                SELECT COUNT(DISTINCT observation_type) as unique_observation_types
                FROM observations
                WHERE observation_type IS NOT NULL AND observation_type != ''
            """)
            totals['unique_observation_types'] = cursor.fetchone()['unique_observation_types']
            
            # Tool usage stats
            cursor = conn.execute("SELECT * FROM v_tool_stats LIMIT 10")
            totals['tool_stats'] = [dict(row) for row in cursor.fetchall()]
            
            return totals
    
    # ==================== CLEANUP ====================
    
    def cleanup_old_data(self, days: int = 90):
        """XÃ³a dá»¯ liá»‡u cÅ© hÆ¡n N ngÃ y vÃ  tráº£ vá» thá»‘ng kÃª."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        now_utc = datetime.utcnow()

        with sqlite3.connect(self.db_path) as conn:
            # Archive old sessions
            cursor = conn.execute("""
                UPDATE sessions
                SET status = 'archived'
                WHERE status = 'completed'
                AND end_time < ?
            """, (cutoff_date,))
            archived_sessions = cursor.rowcount

            # Delete expired context cache
            cursor = conn.execute("""
                DELETE FROM memory_context
                WHERE expires_at IS NOT NULL
                AND expires_at < ?
            """, (now_utc,))
            deleted_context = cursor.rowcount

            conn.commit()

        stats = {
            "retention_days": days,
            "archived_sessions": archived_sessions,
            "deleted_expired_context": deleted_context,
            "cutoff_utc": cutoff_date.isoformat()
        }
        logger.info(f"Cleaned old data: {stats}")
        return stats

    def hard_delete_archived_data(self, days: int = 365) -> Dict[str, int]:
        """
        XÃ³a cá»©ng dá»¯ liá»‡u Ä‘Ã£ archived cÅ© hÆ¡n N ngÃ y.
        DÃ¹ng cho maintenance Ä‘á»‹nh ká»³ Ä‘á»ƒ giáº£m kÃ­ch thÆ°á»›c DB.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id FROM sessions
                WHERE status = 'archived' AND end_time < ?
            """, (cutoff_date,))
            session_ids = [row[0] for row in cursor.fetchall()]

            if not session_ids:
                return {
                    "deleted_sessions": 0,
                    "deleted_observations": 0,
                    "deleted_tool_usage": 0,
                    "deleted_summaries": 0
                }

            placeholders = ",".join(["?"] * len(session_ids))

            cursor = conn.execute(
                f"DELETE FROM tool_usage WHERE session_id IN ({placeholders})",  # nosec B608  # Uses parameterized query
                session_ids
            )
            deleted_tool_usage = cursor.rowcount

            cursor = conn.execute(
                f"DELETE FROM observations WHERE session_id IN ({placeholders})",  # nosec B608  # Uses parameterized query
                session_ids
            )
            deleted_observations = cursor.rowcount

            cursor = conn.execute(
                f"DELETE FROM session_summaries WHERE session_id IN ({placeholders})",  # nosec B608  # Uses parameterized query
                session_ids
            )
            deleted_summaries = cursor.rowcount

            cursor = conn.execute(
                f"DELETE FROM sessions WHERE id IN ({placeholders})",  # nosec B608  # Uses parameterized query
                session_ids
            )
            deleted_sessions = cursor.rowcount

            conn.commit()

        stats = {
            "deleted_sessions": deleted_sessions,
            "deleted_observations": deleted_observations,
            "deleted_tool_usage": deleted_tool_usage,
            "deleted_summaries": deleted_summaries
        }
        logger.info(f"Hard delete archived data: {stats}")
        return stats

    def vacuum_database(self) -> None:
        """VACUUM Ä‘á»ƒ reclaim disk space."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("VACUUM")
            conn.commit()

    def get_database_health(self) -> Dict[str, Any]:
        """Tráº£ vá» thÃ´ng tin health cÆ¡ báº£n cá»§a SQLite DB."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
            page_count = conn.execute("PRAGMA page_count").fetchone()[0]
            page_size = conn.execute("PRAGMA page_size").fetchone()[0]

        return {
            "db_path": self.db_path,
            "integrity_check": integrity,
            "page_count": page_count,
            "page_size": page_size,
            "estimated_size_bytes": page_count * page_size,
            "file_size_bytes": Path(self.db_path).stat().st_size if Path(self.db_path).exists() else 0
        }


# ==================== SINGLETON INSTANCE ====================

_memory_manager = None

def get_memory_manager(db_path: str = None) -> MemoryManager:
    """Get singleton instance cá»§a MemoryManager"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager(db_path)
    return _memory_manager
