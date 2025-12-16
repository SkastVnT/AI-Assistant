-- ============================================================================
-- AI-Assistant MCP Server V2.0 - Database Schema
-- Memory System with SQLite + FTS5 Full-Text Search
-- ============================================================================

-- ============================================================================
-- SESSIONS TABLE - Track conversation sessions
-- ============================================================================
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    project_name TEXT NOT NULL,
    start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    end_time DATETIME,
    user_id TEXT DEFAULT 'default_user',
    summary TEXT,
    tool_count INTEGER DEFAULT 0,
    tokens_used INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active', -- active, completed, archived
    metadata TEXT -- JSON data
);

CREATE INDEX IF NOT EXISTS idx_sessions_start_time ON sessions(start_time DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project_name);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);

-- ============================================================================
-- OBSERVATIONS TABLE - AI-generated learnings from tool usage
-- ============================================================================
CREATE TABLE IF NOT EXISTS observations (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    tool_name TEXT NOT NULL,
    tool_input TEXT, -- JSON
    tool_output TEXT, -- Compressed/summarized output
    observation TEXT NOT NULL, -- AI-generated learning
    observation_type TEXT, -- decision, bugfix, feature, refactor, discovery, change
    concept_tags TEXT, -- JSON array: discovery, problem-solution, pattern, etc.
    file_references TEXT, -- JSON array of file paths
    importance INTEGER DEFAULT 5, -- 1-10 scale
    tokens INTEGER DEFAULT 0,
    metadata TEXT -- JSON data
);

CREATE INDEX IF NOT EXISTS idx_observations_session ON observations(session_id);
CREATE INDEX IF NOT EXISTS idx_observations_timestamp ON observations(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_observations_tool ON observations(tool_name);
CREATE INDEX IF NOT EXISTS idx_observations_type ON observations(observation_type);
CREATE INDEX IF NOT EXISTS idx_observations_importance ON observations(importance DESC);

-- ============================================================================
-- FULL-TEXT SEARCH (FTS5) - Fast semantic search
-- ============================================================================
CREATE VIRTUAL TABLE IF NOT EXISTS observations_fts USING fts5(
    observation,
    tool_input,
    file_references,
    concept_tags,
    content='observations',
    content_rowid='rowid'
);

-- Triggers to keep FTS index in sync
CREATE TRIGGER IF NOT EXISTS observations_ai AFTER INSERT ON observations BEGIN
    INSERT INTO observations_fts(rowid, observation, tool_input, file_references, concept_tags)
    VALUES (new.rowid, new.observation, new.tool_input, new.file_references, new.concept_tags);
END;

CREATE TRIGGER IF NOT EXISTS observations_ad AFTER DELETE ON observations BEGIN
    DELETE FROM observations_fts WHERE rowid = old.rowid;
END;

CREATE TRIGGER IF NOT EXISTS observations_au AFTER UPDATE ON observations BEGIN
    DELETE FROM observations_fts WHERE rowid = old.rowid;
    INSERT INTO observations_fts(rowid, observation, tool_input, file_references, concept_tags)
    VALUES (new.rowid, new.observation, new.tool_input, new.file_references, new.concept_tags);
END;

-- ============================================================================
-- TOOL_USAGE TABLE - Track all tool executions
-- ============================================================================
CREATE TABLE IF NOT EXISTS tool_usage (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    observation_id TEXT, -- NULL until observation is created
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    tool_name TEXT NOT NULL,
    input_params TEXT, -- JSON
    output_data TEXT, -- Full output (can be large)
    duration_ms INTEGER,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    metadata TEXT -- JSON data
);

CREATE INDEX IF NOT EXISTS idx_tool_usage_session ON tool_usage(session_id);
CREATE INDEX IF NOT EXISTS idx_tool_usage_timestamp ON tool_usage(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_tool_usage_tool ON tool_usage(tool_name);

-- ============================================================================
-- SESSION_SUMMARIES TABLE - AI-generated session summaries
-- ============================================================================
CREATE TABLE IF NOT EXISTS session_summaries (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL UNIQUE,
    summary TEXT NOT NULL,
    key_achievements TEXT, -- JSON array
    files_modified TEXT, -- JSON array
    decisions_made TEXT, -- JSON array
    next_steps TEXT, -- JSON array
    tags TEXT, -- JSON array
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT -- JSON data
);

CREATE INDEX IF NOT EXISTS idx_summaries_session ON session_summaries(session_id);
CREATE INDEX IF NOT EXISTS idx_summaries_created ON session_summaries(created_at DESC);

-- ============================================================================
-- MEMORY_CONTEXT TABLE - Pre-computed context for fast injection
-- ============================================================================
CREATE TABLE IF NOT EXISTS memory_context (
    id TEXT PRIMARY KEY,
    project_name TEXT NOT NULL,
    context_type TEXT NOT NULL, -- recent, important, by_file, by_concept
    context_data TEXT NOT NULL, -- Pre-formatted context string
    observation_ids TEXT, -- JSON array of observation IDs
    token_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME, -- NULL = never expires
    metadata TEXT -- JSON data
);

CREATE INDEX IF NOT EXISTS idx_context_project ON memory_context(project_name);
CREATE INDEX IF NOT EXISTS idx_context_type ON memory_context(context_type);
CREATE INDEX IF NOT EXISTS idx_context_expires ON memory_context(expires_at);

-- ============================================================================
-- USER_PROMPTS TABLE - Track user questions/requests
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_prompts (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    prompt TEXT NOT NULL,
    context_provided TEXT, -- What context was available
    tokens INTEGER DEFAULT 0,
    metadata TEXT -- JSON data
);

CREATE INDEX IF NOT EXISTS idx_prompts_session ON user_prompts(session_id);
CREATE INDEX IF NOT EXISTS idx_prompts_timestamp ON user_prompts(timestamp DESC);

-- ============================================================================
-- STATISTICS TABLE - Track overall metrics
-- ============================================================================
CREATE TABLE IF NOT EXISTS statistics (
    id TEXT PRIMARY KEY,
    stat_date DATE DEFAULT (DATE('now')),
    total_sessions INTEGER DEFAULT 0,
    total_observations INTEGER DEFAULT 0,
    total_tools_used INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    avg_session_length INTEGER DEFAULT 0,
    most_used_tool TEXT,
    metadata TEXT -- JSON data
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_stats_date ON statistics(stat_date);

-- ============================================================================
-- INITIAL DATA
-- ============================================================================

-- Create default project entry
INSERT OR IGNORE INTO statistics (id, stat_date, total_sessions)
VALUES ('default', DATE('now'), 0);

-- ============================================================================
-- VIEWS - Convenient queries
-- ============================================================================

-- Recent sessions with summaries
CREATE VIEW IF NOT EXISTS v_recent_sessions AS
SELECT 
    s.id,
    s.project_name,
    s.start_time,
    s.end_time,
    s.tool_count,
    s.tokens_used,
    s.status,
    ss.summary,
    ss.key_achievements,
    COUNT(DISTINCT o.id) as observation_count
FROM sessions s
LEFT JOIN session_summaries ss ON s.id = ss.session_id
LEFT JOIN observations o ON s.id = o.session_id
GROUP BY s.id
ORDER BY s.start_time DESC;

-- Important observations by file
CREATE VIEW IF NOT EXISTS v_observations_by_file AS
SELECT 
    o.id,
    o.session_id,
    o.timestamp,
    o.observation,
    o.observation_type,
    o.file_references,
    o.importance,
    s.project_name
FROM observations o
JOIN sessions s ON o.session_id = s.id
WHERE o.importance >= 7
ORDER BY o.importance DESC, o.timestamp DESC;

-- Tool usage statistics
CREATE VIEW IF NOT EXISTS v_tool_stats AS
SELECT 
    tool_name,
    COUNT(*) as usage_count,
    AVG(duration_ms) as avg_duration,
    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as error_count
FROM tool_usage
GROUP BY tool_name
ORDER BY usage_count DESC;

-- ============================================================================
-- CLEANUP PROCEDURES
-- ============================================================================

-- Delete expired context cache
-- Run periodically: DELETE FROM memory_context WHERE expires_at < CURRENT_TIMESTAMP;

-- Archive old sessions (older than 90 days)
-- UPDATE sessions SET status = 'archived' 
-- WHERE status = 'completed' 
-- AND end_time < DATE('now', '-90 days');

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
