-- ============================================================
-- DATABASE INDEX OPTIMIZATION
-- ============================================================
-- Run this after Phase 0-6 to optimize query performance
-- Target: 10x faster queries with proper indexes

-- ============================================================
-- ANALYZE EXISTING INDEXES
-- ============================================================

-- Show all indexes in chatbot schema
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'chatbot'
ORDER BY tablename, indexname;

-- Show index usage statistics
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
WHERE schemaname = 'chatbot'
ORDER BY idx_scan DESC;

-- Find unused indexes (candidates for removal)
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan
FROM pg_stat_user_indexes
WHERE schemaname = 'chatbot'
AND idx_scan = 0
AND indexname NOT LIKE '%_pkey';


-- ============================================================
-- OPTIMIZED INDEXES FOR CONVERSATIONS
-- ============================================================

-- Primary indexes (if not already created)
CREATE INDEX IF NOT EXISTS idx_conversations_user_id 
ON chatbot.conversations(user_id);

CREATE INDEX IF NOT EXISTS idx_conversations_created_at 
ON chatbot.conversations(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_conversations_updated_at 
ON chatbot.conversations(updated_at DESC);

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_conversations_user_active 
ON chatbot.conversations(user_id, is_archived, updated_at DESC)
WHERE is_archived = FALSE;

CREATE INDEX IF NOT EXISTS idx_conversations_user_pinned 
ON chatbot.conversations(user_id, is_pinned, updated_at DESC)
WHERE is_pinned = TRUE;

-- Index for UUID lookups
CREATE INDEX IF NOT EXISTS idx_conversations_uuid 
ON chatbot.conversations(conversation_uuid);

-- Index for title search
CREATE INDEX IF NOT EXISTS idx_conversations_title_trgm 
ON chatbot.conversations USING gin(title gin_trgm_ops);


-- ============================================================
-- OPTIMIZED INDEXES FOR MESSAGES
-- ============================================================

-- Primary foreign key index
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id 
ON chatbot.messages(conversation_id);

-- Timestamp index for ordering
CREATE INDEX IF NOT EXISTS idx_messages_created_at 
ON chatbot.messages(created_at);

-- Composite index for conversation + timestamp
CREATE INDEX IF NOT EXISTS idx_messages_conv_created 
ON chatbot.messages(conversation_id, created_at DESC);

-- Composite index for conversation + sequence
CREATE INDEX IF NOT EXISTS idx_messages_conv_sequence 
ON chatbot.messages(conversation_id, sequence_number);

-- Full-text search index for content
CREATE INDEX IF NOT EXISTS idx_messages_content_search 
ON chatbot.messages USING gin(to_tsvector('english', content));

-- Index for role filtering
CREATE INDEX IF NOT EXISTS idx_messages_role 
ON chatbot.messages(role);

-- Partial index for edited messages
CREATE INDEX IF NOT EXISTS idx_messages_edited 
ON chatbot.messages(conversation_id, is_edited)
WHERE is_edited = TRUE;


-- ============================================================
-- OPTIMIZED INDEXES FOR MEMORY
-- ============================================================

-- Primary foreign key indexes
CREATE INDEX IF NOT EXISTS idx_memory_user_id 
ON chatbot.chatbot_memory(user_id);

CREATE INDEX IF NOT EXISTS idx_memory_conversation_id 
ON chatbot.chatbot_memory(conversation_id);

-- Composite index for user memory queries
CREATE INDEX IF NOT EXISTS idx_memory_user_created 
ON chatbot.chatbot_memory(user_id, created_at DESC);

-- Full-text search for questions
CREATE INDEX IF NOT EXISTS idx_memory_question_search 
ON chatbot.chatbot_memory USING gin(to_tsvector('english', question));

-- Full-text search for answers
CREATE INDEX IF NOT EXISTS idx_memory_answer_search 
ON chatbot.chatbot_memory USING gin(to_tsvector('english', answer));

-- Combined full-text search
CREATE INDEX IF NOT EXISTS idx_memory_qa_search 
ON chatbot.chatbot_memory USING gin(
    to_tsvector('english', coalesce(question, '') || ' ' || coalesce(answer, ''))
);

-- Tags array index
CREATE INDEX IF NOT EXISTS idx_memory_tags 
ON chatbot.chatbot_memory USING gin(tags);

-- Importance rating index
CREATE INDEX IF NOT EXISTS idx_memory_importance 
ON chatbot.chatbot_memory(importance DESC)
WHERE importance IS NOT NULL;


-- ============================================================
-- OPTIMIZED INDEXES FOR UPLOADED FILES
-- ============================================================

-- Primary foreign key indexes
CREATE INDEX IF NOT EXISTS idx_files_user_id 
ON chatbot.uploaded_files(user_id);

CREATE INDEX IF NOT EXISTS idx_files_conversation_id 
ON chatbot.uploaded_files(conversation_id);

-- Composite index for user file queries
CREATE INDEX IF NOT EXISTS idx_files_user_created 
ON chatbot.uploaded_files(user_id, created_at DESC);

-- File type index for filtering
CREATE INDEX IF NOT EXISTS idx_files_type 
ON chatbot.uploaded_files(file_type);

-- Index for filename search
CREATE INDEX IF NOT EXISTS idx_files_filename 
ON chatbot.uploaded_files USING gin(original_filename gin_trgm_ops);

-- Index for processed files
CREATE INDEX IF NOT EXISTS idx_files_processed 
ON chatbot.uploaded_files(is_processed, conversation_id)
WHERE is_processed = TRUE;


-- ============================================================
-- OPTIMIZED INDEXES FOR USERS (public schema)
-- ============================================================

-- Username unique index (should already exist)
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username 
ON public.users(username);

-- Email unique index (should already exist)
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email 
ON public.users(email);

-- Active users index
CREATE INDEX IF NOT EXISTS idx_users_active_login 
ON public.users(is_active, last_login DESC)
WHERE is_active = TRUE;


-- ============================================================
-- ANALYZE TABLES FOR QUERY PLANNER
-- ============================================================

-- Update table statistics for better query planning
ANALYZE chatbot.conversations;
ANALYZE chatbot.messages;
ANALYZE chatbot.chatbot_memory;
ANALYZE chatbot.uploaded_files;
ANALYZE public.users;


-- ============================================================
-- VACUUM TABLES TO RECLAIM SPACE
-- ============================================================

-- Vacuum to reclaim storage and update statistics
VACUUM ANALYZE chatbot.conversations;
VACUUM ANALYZE chatbot.messages;
VACUUM ANALYZE chatbot.chatbot_memory;
VACUUM ANALYZE chatbot.uploaded_files;
VACUUM ANALYZE public.users;


-- ============================================================
-- CHECK INDEX BLOAT
-- ============================================================

-- Query to check index bloat
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch,
    CASE 
        WHEN idx_scan = 0 THEN 'Never used'
        WHEN idx_scan < 100 THEN 'Rarely used'
        WHEN idx_scan < 1000 THEN 'Occasionally used'
        ELSE 'Frequently used'
    END as usage_category
FROM pg_stat_user_indexes
WHERE schemaname IN ('chatbot', 'public')
ORDER BY pg_relation_size(indexrelid) DESC;


-- ============================================================
-- QUERY PERFORMANCE TIPS
-- ============================================================

/*
1. ALWAYS filter by user_id first in queries
   - This will use the user index and reduce result set

2. Use LIMIT for large result sets
   - Don't load all messages at once
   - Pagination is your friend

3. Use EXISTS instead of COUNT when checking existence
   - EXISTS stops at first match, COUNT scans all rows

4. Add indexes for your most common queries
   - Analyze slow query log
   - Create composite indexes for multi-column WHERE clauses

5. Use partial indexes for filtered queries
   - Example: WHERE is_archived = FALSE
   - Smaller index = faster queries

6. Keep indexes updated
   - Run ANALYZE regularly
   - Run VACUUM to reclaim space

7. Monitor index usage
   - Remove unused indexes
   - They slow down INSERT/UPDATE operations
*/


-- ============================================================
-- PERFORMANCE MONITORING QUERIES
-- ============================================================

-- Show slowest queries (requires pg_stat_statements extension)
-- CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- SELECT 
--     query,
--     calls,
--     total_time,
--     mean_time,
--     max_time
-- FROM pg_stat_statements
-- WHERE query LIKE '%chatbot%'
-- ORDER BY mean_time DESC
-- LIMIT 20;


-- Show table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) as index_size
FROM pg_tables
WHERE schemaname IN ('chatbot', 'public')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;


-- ============================================================
-- MAINTENANCE SCHEDULE
-- ============================================================

/*
Daily:
- ANALYZE most active tables

Weekly:
- VACUUM ANALYZE all tables
- Check slow query log
- Review index usage

Monthly:
- VACUUM FULL (requires downtime)
- REINDEX if needed
- Review and optimize queries
- Remove unused indexes

Quarterly:
- Full database performance review
- Consider partitioning large tables
- Review and update indexes based on usage patterns
*/
