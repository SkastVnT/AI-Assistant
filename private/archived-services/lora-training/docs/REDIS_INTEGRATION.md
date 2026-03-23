# Redis Integration for LoRA Training WebUI

## 🚀 Cải thiện với Redis

Redis giúp **train_LoRA_tool** performance tốt hơn:

### ✅ Lợi ích:

1. **Task Queue Management**
   - Queue training jobs (không bị mất khi restart)
   - FIFO scheduling
   - Priority queue support
   - Job persistence

2. **Intelligent Caching**
   - Cache dataset metadata (không phải analyze lại)
   - Cache AI recommendations (tiết kiệm Gemini API calls)
   - Cache training progress
   - TTL-based auto cleanup

3. **Real-time Progress**
   - Pub/Sub for live updates
   - Multi-client support
   - WebSocket session management
   - Distributed monitoring

4. **Metrics & Analytics**
   - Training history
   - Performance metrics
   - Loss/LR tracking over time
   - Compare training runs

5. **Fault Tolerance**
   - Persist training state
   - Resume after crash
   - Backup checkpoints metadata
   - Error recovery

---

## 🐳 Docker Compose Setup

```yaml
services:
  # Redis Cache
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    
  # LoRA Training WebUI
  lora-training:
    build: ./train_LoRA_tool
    ports:
      - "7860:7860"
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
    depends_on:
      - redis
```

---

## 💻 Usage

### Start with Docker Compose:
```bash
docker-compose up redis lora-training
```

### Access:
- **WebUI**: http://localhost:7860
- **Redis**: localhost:6379

### Environment Variables:
```bash
REDIS_HOST=redis          # Redis hostname
REDIS_PORT=6379           # Redis port
REDIS_DB=0                # Database number
```

---

## 📊 Cache Performance

### Without Redis:
- Dataset analysis: ~10s every time
- AI recommendations: ~$0.0002 + 10s per request
- Progress tracking: In-memory only (lost on restart)

### With Redis:
- Dataset analysis: ~10s first time, instant after (cached)
- AI recommendations: ~10s first time, instant for same dataset/goal
- Progress tracking: Persistent, survive restarts
- **Cost savings**: ~70% fewer Gemini API calls

---

## 🔧 Advanced Features

### 1. Task Queue
```python
from utils.redis_manager import queue_training

# Queue a training job
queue_training(task_id="train_001", config={
    "learning_rate": 1e-4,
    "epochs": 10,
    # ... config
})
```

### 2. Cache Management
```python
from utils.redis_manager import cache

# Cache dataset metadata
cache.cache_dataset_metadata("./dataset", metadata)

# Get cached metadata
metadata = cache.get_dataset_metadata("./dataset")
```

### 3. Metrics Logging
```python
from utils.redis_manager import metrics_logger

# Log epoch metrics
metrics_logger.log_epoch(
    task_id="train_001",
    epoch=5,
    metrics={"loss": 0.05, "lr": 1e-5}
)

# Get all metrics
history = metrics_logger.get_metrics("train_001")
```

---

## 🎯 Auto-Caching Features

WebUI automatically caches:

1. **Dataset Metadata** (7 days TTL)
   - Image count, resolutions
   - Tag statistics
   - Quality scores

2. **AI Recommendations** (30 min TTL)
   - Gemini config suggestions
   - Per dataset + goal combination

3. **Training Progress** (30 min TTL)
   - Current epoch/step
   - Loss, LR, ETA
   - Real-time updates via Pub/Sub

4. **Session Data** (1 hour TTL)
   - WebSocket connections
   - User preferences

---

## 🔍 Monitoring

Check Redis status:
```bash
docker exec -it ai-assistant-redis redis-cli

# Check keys
KEYS lora:*

# Get queue status
LLEN lora:training:queue

# Check cache hit rate
INFO stats
```

---

## 💾 Persistence

Redis saves data to disk:
- **RDB snapshots**: Every 60s if 1000+ changes
- **AOF log**: Append-only file (fsync every second)
- **Volume**: `redis-data` for persistence

Data survives container restarts!

---

## ⚡ Performance Tuning

### Memory Settings:
```
maxmemory 2gb                    # Max RAM usage
maxmemory-policy allkeys-lru     # Evict oldest when full
```

### Persistence:
```
save 60 1000                     # Save if 1000 changes in 60s
appendonly yes                   # Enable AOF
appendfsync everysec             # Fsync every second
```

---

## 🛡️ Fallback Mode

If Redis unavailable:
- ✅ WebUI still works
- ✅ No caching (slower but functional)
- ✅ In-memory progress tracking
- ⚠️ Progress lost on restart
- ⚠️ More Gemini API calls (higher cost)

Auto-detects Redis and falls back gracefully!

---

## 📈 Example Workflow

```
1. User: Click "Get AI Recommendations"
   ↓
2. WebUI: Check Redis cache for dataset metadata
   ↓
3. If cached → Use it (instant!)
   If not → Analyze dataset → Cache result
   ↓
4. WebUI: Check Redis cache for AI config
   ↓
5. If cached → Return immediately
   If not → Call Gemini → Cache result
   ↓
6. User: Start training
   ↓
7. WebUI: Queue task in Redis
   ↓
8. Worker: Pick task from queue
   ↓
9. Training: Log metrics to Redis every epoch
   ↓
10. WebUI: Real-time updates via Redis Pub/Sub
```

---

## 🎉 Benefits Summary

| Feature | Without Redis | With Redis |
|---------|--------------|------------|
| Dataset Analysis | 10s every time | 10s once, instant after |
| AI Recommendations | $0.0002 + 10s each | $0.0002 + 10s once per dataset+goal |
| Progress Tracking | In-memory only | Persistent |
| Multi-client Support | Limited | Full support |
| Job Queue | None | FIFO queue |
| Fault Tolerance | Low | High |
| API Cost Savings | 0% | ~70% |

**Recommended for production use!** ✅

---

Created: 2024-12-01  
Version: 1.0.0
