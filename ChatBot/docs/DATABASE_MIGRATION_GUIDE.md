# Database Migration Guide

This guide walks you through migrating the chatbot from file-based storage to PostgreSQL database.

## Prerequisites

- PostgreSQL 15+ installed and running
- Redis 7+ installed and running
- Python 3.10+
- Docker (optional, for containerized setup)

## Migration Steps

### Step 1: Setup Database

1. **Create Database and User:**
```sql
-- Connect to PostgreSQL as superuser
psql -U postgres

-- Create database and user
CREATE DATABASE chatbot_db;
CREATE USER chatbot_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE chatbot_db TO chatbot_user;

-- Grant schema privileges
\c chatbot_db
GRANT ALL ON SCHEMA public TO chatbot_user;
GRANT ALL ON SCHEMA chatbot TO chatbot_user;
```

2. **Enable Required Extensions:**
```sql
-- Connect to chatbot_db
\c chatbot_db

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For full-text search
```

### Step 2: Configure Environment

1. **Create `.env` file:**
```bash
# Database Configuration
DATABASE_URL=postgresql://chatbot_user:your_secure_password@localhost:5432/chatbot_db
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
DB_POOL_RECYCLE=3600
DB_POOL_PRE_PING=true
DB_ECHO=false

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_SSL=false

# Cache Settings
CACHE_ENABLED=true
CACHE_DEFAULT_TTL=3600
CACHE_QUERY_TTL=300
CACHE_SESSION_TTL=7200

# Application Settings
SECRET_KEY=your_secret_key_here
FLASK_ENV=production
DEBUG=false
```

2. **Load environment variables:**
```python
from dotenv import load_dotenv
load_dotenv()
```

### Step 3: Initialize Database Schema

1. **Run schema initialization:**
```bash
# Using Python
python -c "from ChatBot.database.database import init_db; init_db()"

# Or using the CLI
python ChatBot/database/scripts/init_database.py
```

2. **Verify tables created:**
```bash
psql -U chatbot_user -d chatbot_db -c "\dt chatbot.*"
```

Expected tables:
- chatbot.users
- chatbot.conversations
- chatbot.messages
- chatbot.memory
- chatbot.files

### Step 4: Optimize Database

1. **Run index optimization:**
```bash
psql -U chatbot_user -d chatbot_db -f ChatBot/database/scripts/optimize_indexes.sql
```

2. **Verify indexes created:**
```sql
SELECT schemaname, tablename, indexname 
FROM pg_indexes 
WHERE schemaname = 'chatbot'
ORDER BY tablename, indexname;
```

Should see 32+ indexes across all tables.

### Step 5: Migrate Existing Data

1. **Run migration tool:**
```bash
python ChatBot/database/scripts/migrate_to_database.py \
    --storage-dir "ChatBot/Storage" \
    --batch-size 100 \
    --create-default-user
```

2. **Monitor migration progress:**
```bash
# Check logs
tail -f migration.log

# Verify data migrated
psql -U chatbot_user -d chatbot_db -c "
SELECT 
    (SELECT COUNT(*) FROM chatbot.conversations) as conversations,
    (SELECT COUNT(*) FROM chatbot.messages) as messages,
    (SELECT COUNT(*) FROM chatbot.memory) as memories,
    (SELECT COUNT(*) FROM chatbot.files) as files;
"
```

### Step 6: Update Application Code

1. **Update imports:**
```python
# Old (file-based)
from ChatBot.src.conversation_handler import save_conversation_to_file

# New (database)
from ChatBot.database.services.conversation_service import ConversationService
```

2. **Update function calls:**
```python
# Old
save_conversation_to_file(conv_id, messages)

# New
service = ConversationService(db.session)
service.save_conversation(user_id, conv_id, messages)
```

3. **Use dependency injection in Flask routes:**
```python
from ChatBot.database.api.dependencies import get_conversation_service

@app.route('/api/conversations', methods=['POST'])
def create_conversation():
    service = get_conversation_service()
    conversation = service.create_conversation(
        user_id=current_user.id,
        title="New Conversation"
    )
    return jsonify(conversation.to_dict())
```

### Step 7: Performance Tuning

1. **Monitor connection pool:**
```python
from ChatBot.database.utils.connection_monitoring import ConnectionPoolMonitor

# Check pool health
health = ConnectionPoolMonitor.get_pool_health_score()
print(f"Pool health: {health}/100")

# View pool status
status = ConnectionPoolMonitor.get_pool_status()
print(f"Connections: {status['checked_out']}/{status['size']}")
```

2. **Monitor query performance:**
```python
from ChatBot.database.utils.query_optimization import analyze_query, log_query_plan

# Analyze query for issues
query = db.session.query(Conversation).filter_by(user_id=user_id)
issues = analyze_query(query)
for issue in issues:
    print(f"Warning: {issue}")

# View execution plan
log_query_plan(db.session, query)
```

3. **Monitor Redis cache:**
```python
from ChatBot.database.utils.redis_optimization import RedisMemoryOptimizer

# Check memory usage
memory_info = RedisMemoryOptimizer.get_memory_info()
print(f"Redis memory: {memory_info['used_memory_human']}")

# Find large keys
large_keys = RedisMemoryOptimizer.analyze_large_keys(limit=10)
for key, size in large_keys:
    print(f"{key}: {size} bytes")
```

### Step 8: Testing

1. **Run integration tests:**
```bash
# Run all tests
pytest ChatBot/tests/

# Run database tests only
pytest ChatBot/tests/test_database.py -v

# Run with coverage
pytest --cov=ChatBot/database --cov-report=html
```

2. **Run performance tests:**
```bash
python ChatBot/tests/test_performance.py
```

Expected performance:
- Query time: <100ms (without cache)
- Query time: <10ms (with cache)
- Cache hit rate: >85%
- Connection pool health: >80/100

### Step 9: Backup Old Data

1. **Backup file-based data:**
```bash
# Create backup directory
mkdir -p ChatBot/Storage_backup_$(date +%Y%m%d)

# Copy old data
cp -r ChatBot/Storage/* ChatBot/Storage_backup_$(date +%Y%m%d)/

# Compress backup
tar -czf storage_backup_$(date +%Y%m%d).tar.gz ChatBot/Storage_backup_$(date +%Y%m%d)/
```

2. **Export database backup:**
```bash
# Full database backup
pg_dump -U chatbot_user -d chatbot_db -F c -f chatbot_backup_$(date +%Y%m%d).dump

# Schema only
pg_dump -U chatbot_user -d chatbot_db -s -f chatbot_schema_$(date +%Y%m%d).sql

# Data only
pg_dump -U chatbot_user -d chatbot_db -a -f chatbot_data_$(date +%Y%m%d).sql
```

### Step 10: Production Deployment

1. **Use Docker Compose (recommended):**
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service health
docker-compose ps
```

2. **Or run manually:**
```bash
# Start PostgreSQL (if not running)
sudo systemctl start postgresql

# Start Redis (if not running)
sudo systemctl start redis

# Start application
python ChatBot/app.py
```

## Post-Migration Checklist

- [ ] All tables created with correct schema
- [ ] All indexes created (32+ indexes)
- [ ] Data migrated successfully (conversations, messages, memory, files)
- [ ] Connection pool configured (size=20, max_overflow=30)
- [ ] Redis cache enabled (TTL=3600s)
- [ ] All tests passing (unit + integration)
- [ ] Performance benchmarks met (<100ms queries)
- [ ] Old data backed up
- [ ] Application using database (not files)
- [ ] Monitoring enabled (connection pool, queries, cache)

## Rollback Procedure

If migration fails or issues occur:

1. **Stop application:**
```bash
docker-compose down  # If using Docker
# Or kill Python process
```

2. **Restore from backup:**
```bash
# Restore database
pg_restore -U chatbot_user -d chatbot_db -c chatbot_backup.dump

# Or restore files
rm -rf ChatBot/Storage
tar -xzf storage_backup.tar.gz
mv Storage_backup_* ChatBot/Storage
```

3. **Revert code changes:**
```bash
git checkout main  # Or previous commit
```

4. **Restart with old configuration:**
```bash
# Remove database config from .env
# Restart application with file-based storage
```

## Troubleshooting

### Connection Issues

**Problem:** `psycopg2.OperationalError: could not connect to server`

**Solution:**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check connection settings
psql -U chatbot_user -d chatbot_db

# Verify pg_hba.conf allows connections
sudo nano /etc/postgresql/15/main/pg_hba.conf
# Add line: host chatbot_db chatbot_user 127.0.0.1/32 md5
```

### Migration Errors

**Problem:** `IntegrityError: duplicate key value violates unique constraint`

**Solution:**
```python
# Clean database before migration
from ChatBot.database.database import db
db.drop_all()
db.create_all()

# Re-run migration
python ChatBot/database/scripts/migrate_to_database.py
```

### Performance Issues

**Problem:** Slow queries (>1s response time)

**Solution:**
```sql
-- Check missing indexes
SELECT * FROM pg_stat_user_tables WHERE schemaname = 'chatbot' AND idx_scan = 0;

-- Analyze query plans
EXPLAIN ANALYZE SELECT * FROM chatbot.conversations WHERE user_id = 1;

-- Run ANALYZE to update statistics
ANALYZE chatbot.conversations;
```

### Memory Issues

**Problem:** High Redis memory usage

**Solution:**
```python
from ChatBot.database.utils.redis_optimization import RedisMemoryOptimizer

# Find large keys
large_keys = RedisMemoryOptimizer.analyze_large_keys(limit=20)

# Enable compression
from ChatBot.database.utils.redis_optimization import cache_with_compression
cache_with_compression('my_key', large_data, ttl=3600)

# Cleanup expired keys
RedisMemoryOptimizer.cleanup_expired_keys()
```

## Performance Tuning

### Database Optimization

```sql
-- Tune PostgreSQL settings (postgresql.conf)
shared_buffers = 256MB              # 25% of RAM
effective_cache_size = 1GB          # 50% of RAM
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 4MB
min_wal_size = 1GB
max_wal_size = 4GB
```

### Connection Pool Tuning

```python
# Adjust based on load
DB_POOL_SIZE = 20              # Concurrent connections
DB_MAX_OVERFLOW = 30           # Additional connections under load
DB_POOL_RECYCLE = 3600         # Recycle connections after 1 hour
DB_POOL_PRE_PING = true        # Check connection health before use
```

### Cache Tuning

```python
# Adjust TTL based on data volatility
CACHE_QUERY_TTL = 300          # 5 minutes for query results
CACHE_SESSION_TTL = 7200       # 2 hours for session data
CACHE_STATIC_TTL = 86400       # 24 hours for static data

# Enable compression for large values
CACHE_COMPRESSION_ENABLED = true
CACHE_COMPRESSION_THRESHOLD = 1024  # Compress values > 1KB
```

## Maintenance

### Daily Tasks

```bash
# Analyze tables (update statistics)
psql -U chatbot_user -d chatbot_db -c "ANALYZE;"

# Check connection pool health
python -c "
from ChatBot.database.utils.connection_monitoring import ConnectionPoolMonitor
ConnectionPoolMonitor.log_pool_status()
"

# Monitor cache hit rate
python -c "
from ChatBot.database.utils.cache import cache_client
info = cache_client.info('stats')
print(f\"Hit rate: {info.get('keyspace_hits', 0) / (info.get('keyspace_hits', 0) + info.get('keyspace_misses', 1)) * 100:.2f}%\")
"
```

### Weekly Tasks

```bash
# Vacuum database (reclaim space)
psql -U chatbot_user -d chatbot_db -c "VACUUM ANALYZE;"

# Check for unused indexes
psql -U chatbot_user -d chatbot_db -f ChatBot/database/scripts/optimize_indexes.sql

# Backup database
pg_dump -U chatbot_user -d chatbot_db -F c -f weekly_backup.dump
```

### Monthly Tasks

```bash
# Reindex tables (rebuild indexes)
psql -U chatbot_user -d chatbot_db -c "REINDEX DATABASE chatbot_db;"

# Check table bloat
psql -U chatbot_user -d chatbot_db -c "
SELECT 
    schemaname, tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables 
WHERE schemaname = 'chatbot'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"

# Review slow queries
psql -U chatbot_user -d chatbot_db -c "
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    max_time
FROM pg_stat_statements
WHERE query LIKE '%chatbot%'
ORDER BY mean_time DESC
LIMIT 10;
"
```

## Support

For issues or questions:
1. Check logs: `tail -f logs/chatbot.log`
2. Review documentation: `docs/DATABASE_CURRENT_STATE.md`
3. Run diagnostics: `python scripts/check_system.py`
4. Contact: [Your contact information]
