# Chatbot Database Migration Guide

> **Complete guide for migrating Chatbot service from file-based to MongoDB storage**

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Backup Procedure](#backup-procedure)
3. [Database Setup](#database-setup)
4. [Running Migration](#running-migration)
5. [Validation](#validation)
6. [Rollback Procedure](#rollback-procedure)
7. [Common Issues](#common-issues)
8. [Performance Tuning](#performance-tuning)

---

## Prerequisites

### System Requirements
```yaml
MongoDB: 7.0+ (or 5.0+ minimum)
Redis: 7.0+ (optional, for caching)
Python: 3.10+
RAM: 4GB minimum (8GB recommended)
Disk: 10GB free space
```

### Required Python Packages
```bash
pip install pymongo redis python-dotenv
```

### Environment Variables
Create `.env` file in `services/chatbot/`:
```env
# MongoDB
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=ai_assistant

# Redis (optional)
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=your_password

# Environment
ENVIRONMENT=production
LOG_LEVEL=INFO
```

---

## Backup Procedure

### 1. Backup Existing Data

**Windows:**
```batch
cd AI-Assistant
mkdir backups
powershell Compress-Archive -Path "services\chatbot\Storage\*" -DestinationPath "backups\chatbot_backup_%date:~10,4%%date:~4,2%%date:~7,2%.zip"
```

**Linux/Mac:**
```bash
cd AI-Assistant
mkdir -p backups
tar -czf backups/chatbot_backup_$(date +%Y%m%d).tar.gz services/chatbot/Storage
```

### 2. Verify Backup
```bash
# Windows
powershell -Command "Get-ChildItem backups | Sort-Object LastWriteTime -Descending | Select-Object -First 5"

# Linux
ls -lt backups | head -5
```

### 3. Document Current State
```bash
cd services/chatbot
python -c "
import os
import json
storage_path = 'Storage/conversations'
if os.path.exists(storage_path):
    files = os.listdir(storage_path)
    print(f'Total conversation files: {len(files)}')
"
```

---

## Database Setup

### 1. Start MongoDB

**Using Docker:**
```bash
docker-compose up -d mongodb
```

**Manual Installation:**
- Download from https://www.mongodb.com/try/download/community
- Start mongod service

### 2. Create Database and Collections

```bash
cd services/chatbot
python -c "
from config.mongodb_helpers import get_mongo_client

client = get_mongo_client()
db = client['ai_assistant']

# Create collections
db.create_collection('conversations')
db.create_collection('messages')
db.create_collection('memories')

print('Collections created successfully')
"
```

### 3. Create Indexes

```bash
python -c "
from database.utils.optimizer import IndexManager
from config.mongodb_helpers import get_mongo_client

client = get_mongo_client()
db = client['ai_assistant']

IndexManager.ensure_indexes(db)
print('Indexes created successfully')
"
```

### 4. Verify Setup

```bash
python -c "
from database import ConversationRepository, MessageRepository, MemoryRepository
from database.cache import ChatbotCache

print('✓ Database modules loaded')
print(f'✓ Cache available: {ChatbotCache.get_stats().get(\"backend\", \"memory\")}')
"
```

---

## Running Migration

### 1. Dry Run (Test Mode)

```bash
cd services/chatbot
python scripts/migrate_to_mongodb.py --dry-run
```

Expected output:
```
Migration Dry Run Report
========================
Files found: 150
Valid files: 148
Invalid files: 2
Estimated time: 5 minutes
```

### 2. Full Migration

```bash
# Run migration
python scripts/migrate_to_mongodb.py

# Or with options
python scripts/migrate_to_mongodb.py --batch-size 100 --skip-validation
```

### 3. Monitor Progress

During migration, check logs:
```bash
# In another terminal
tail -f logs/chatbot.json.log | jq .
```

---

## Validation

### 1. Count Verification

```bash
python -c "
from config.mongodb_helpers import get_mongo_client

client = get_mongo_client()
db = client['ai_assistant']

print(f'Conversations: {db.conversations.count_documents({})}')
print(f'Messages: {db.messages.count_documents({})}')
print(f'Memories: {db.memories.count_documents({})}')
"
```

### 2. Data Integrity Check

```bash
python -c "
from database import ConversationRepository

# Test load a conversation
repo = ConversationRepository()
convs = repo.get_user_conversations('test_user', limit=5)
print(f'Sample conversations loaded: {len(convs)}')
"
```

### 3. Run Tests

```bash
cd services/chatbot
python -m pytest tests/test_repositories.py tests/test_integration.py -v
```

### 4. Check Health

```bash
curl http://localhost:5000/health/detailed
```

---

## Rollback Procedure

### Quick Rollback (< 5 minutes)

**Windows:**
```batch
scripts\rollback-chatbot.bat
```

**Linux/Mac:**
```bash
./scripts/rollback-chatbot.sh
```

### Manual Rollback

1. **Stop Service**
```bash
# Find and stop Flask process
pkill -f "python.*app.py"
```

2. **Restore Backup**
```bash
# Windows
powershell Expand-Archive -Path "backups\chatbot_backup_YYYYMMDD.zip" -DestinationPath "services\chatbot\Storage" -Force

# Linux
tar -xzf backups/chatbot_backup_YYYYMMDD.tar.gz -C services/chatbot/
```

3. **Restart Service**
```bash
cd services/chatbot
python app.py
```

---

## Common Issues

### Issue 1: MongoDB Connection Failed

**Error:**
```
pymongo.errors.ServerSelectionTimeoutError: localhost:27017
```

**Solution:**
```bash
# Check if MongoDB is running
docker ps | grep mongodb

# Start MongoDB
docker-compose up -d mongodb

# Verify connection
mongosh mongodb://localhost:27017
```

### Issue 2: Import Errors

**Error:**
```
ModuleNotFoundError: No module named 'database'
```

**Solution:**
```bash
cd services/chatbot
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or add to code:
import sys
sys.path.insert(0, '/path/to/services/chatbot')
```

### Issue 3: Cache Connection Failed

**Error:**
```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**Solution:**
- Cache is optional - system will use memory fallback
- To fix Redis:
```bash
docker-compose up -d redis
```

### Issue 4: Slow Queries

**Error:**
```
WARNING - Slow query: get_user_conversations took 523.45ms
```

**Solution:**
```bash
# Ensure indexes exist
python -c "
from database.utils.optimizer import IndexManager
from config.mongodb_helpers import get_mongo_client

db = get_mongo_client()['ai_assistant']
IndexManager.ensure_indexes(db)
"
```

### Issue 5: Memory Issues

**Error:**
```
MemoryError: Unable to allocate array
```

**Solution:**
- Reduce batch size in migration
- Increase system RAM
- Enable compression:
```python
from database.utils.cache_optimizer import CacheCompressor
# Compression is automatic for values > 1KB
```

---

## Performance Tuning

### 1. MongoDB Optimization

**Connection Pool:**
```python
from database.utils.optimizer import ConnectionPool

# Default settings (already optimized)
client = ConnectionPool.get_client(
    maxPoolSize=50,
    minPoolSize=10
)
```

**Indexes:**
```python
from database.utils.optimizer import IndexManager

# Analyze current indexes
analysis = IndexManager.analyze_indexes(db, 'conversations')
print(analysis)

# Create missing indexes
IndexManager.ensure_indexes(db)
```

### 2. Cache Optimization

**Enable Compression:**
```python
from database.utils.cache_optimizer import CacheCompressor

# Automatic for large values
data = {'large': 'x' * 10000}
compressed = CacheCompressor.compress(data)
# ~90% size reduction for repetitive data
```

**Batch Operations:**
```python
from database.utils.cache_optimizer import RedisPipeline

with RedisPipeline(redis_client) as pipe:
    pipe.set('key1', value1, ttl=3600)
    pipe.set('key2', value2, ttl=3600)
    # Executes all in single round-trip
```

### 3. Query Optimization

**Use Projections:**
```python
# Only fetch needed fields
projection = {'_id': 1, 'title': 1, 'updated_at': 1}
cursor = db.conversations.find({}, projection)
```

**Bulk Operations:**
```python
from database.utils.optimizer import BulkOperations

with BulkOperations(collection, batch_size=1000) as bulk:
    for item in items:
        bulk.add_insert(item)
    # Automatically batches and flushes
```

### 4. Monitoring

**Check Metrics:**
```bash
curl http://localhost:5000/metrics/json
```

**Check Health:**
```bash
curl http://localhost:5000/health/detailed
```

---

## Post-Migration Checklist

- [ ] All data migrated successfully
- [ ] Tests passing (45/45)
- [ ] Health checks green
- [ ] Cache working
- [ ] Indexes created
- [ ] Backup verified
- [ ] Documentation updated
- [ ] Team notified

---

## Support

For issues not covered here:

1. Check logs: `logs/chatbot.json.log`
2. Check error logs: `logs/chatbot.error.log`
3. Run health check: `curl localhost:5000/health/detailed`
4. Review documentation: `docs/PHASE*_COMPLETE.md`

---

**Last Updated:** December 2025  
**Version:** 2.2.0
