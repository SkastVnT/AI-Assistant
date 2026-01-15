# Phase 6: Deployment & Monitoring - Complete ✅

## Summary
Phase 6 của Chatbot Migration Roadmap đã hoàn thành. Hệ thống monitoring, health checks, logging và deployment scripts đã được thiết lập.

## Files Created

### 1. Health Check Module
**File:** `services/chatbot/utils/health.py`

| Component | Description |
|-----------|-------------|
| `HealthChecker` | Singleton class for health monitoring |
| `liveness()` | Basic alive check (for K8s liveness probe) |
| `readiness()` | Dependency check (DB, Cache) |
| `detailed()` | Full system status with timing |
| `create_health_blueprint()` | Flask blueprint for /health endpoints |

**Endpoints:**
```
GET /health          → Liveness probe
GET /health/live     → Liveness probe  
GET /health/ready    → Readiness probe (checks DB, cache)
GET /health/detailed → Full status with system info
```

**Example Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-12-31T08:00:00.000Z",
  "uptime_seconds": 3600.5,
  "version": "2.2.0",
  "checks": {
    "database": {
      "status": "healthy",
      "latency_ms": 5.2,
      "message": "MongoDB connected"
    },
    "cache": {
      "status": "healthy",
      "latency_ms": 0.8,
      "message": "Cache OK (memory)",
      "backend": "memory"
    }
  }
}
```

---

### 2. Structured Logging
**File:** `services/chatbot/utils/logger.py`

| Component | Description |
|-----------|-------------|
| `JsonFormatter` | JSON output for log aggregators |
| `ColoredFormatter` | Color console output (dev) |
| `ChatbotLogger.setup()` | Configure logging with rotation |
| `LogOperation` | Context manager for timed operations |
| `LogEvents` | Pre-defined logging events |

**Features:**
- ✅ JSON structured logs (production)
- ✅ Colored console (development)
- ✅ Log rotation (10MB, 5 backups)
- ✅ Separate error log file
- ✅ Operation timing context manager

**Log Files:**
```
logs/
├── chatbot.json.log      # All logs (JSON)
├── chatbot.error.log     # Errors only
└── chatbot.log.1-5       # Rotated backups
```

**Usage:**
```python
from utils import get_logger, LogOperation, LogEvents

logger = get_logger()

# Simple logging
logger.info("User logged in", extra={"user_id": "123"})

# Timed operation
with LogOperation("Creating conversation", user_id="123"):
    # do something
    pass

# Pre-defined events
LogEvents.conversation_created(logger, "user_123", "conv_456", "grok")
```

---

### 3. Metrics Collection
**File:** `services/chatbot/utils/metrics.py`

| Metric Type | Examples |
|-------------|----------|
| **Counters** | conversations_created, messages_sent, cache_hits |
| **Gauges** | active_conversations, active_users, cache_size |
| **Histograms** | response_time, db_query_time, ai_response_time |

**Endpoints:**
```
GET /metrics      → Prometheus format
GET /metrics/json → JSON format
```

**Pre-defined Metrics (16 total):**
```python
# Counters
chatbot_conversations_created_total
chatbot_messages_sent_total
chatbot_messages_received_total
chatbot_cache_hits_total
chatbot_cache_misses_total
chatbot_db_queries_total
chatbot_errors_total
chatbot_api_requests_total

# Gauges
chatbot_active_conversations
chatbot_active_users
chatbot_cache_size
chatbot_db_connections

# Histograms
chatbot_response_time_seconds
chatbot_db_query_time_seconds
chatbot_ai_response_time_seconds
chatbot_cache_operation_time_seconds
```

**Usage:**
```python
from utils import conversations_created, response_time, track_time

# Manual tracking
conversations_created.inc()

# Decorator
@track_time(response_time)
def handle_request():
    pass
```

---

### 4. Deployment Scripts

| Script | Platform | Description |
|--------|----------|-------------|
| `scripts/deploy-chatbot.bat` | Windows | Full deployment with backup |
| `scripts/deploy-chatbot.sh` | Linux/Mac | Full deployment with backup |
| `scripts/rollback-chatbot.bat` | Windows | Interactive rollback |
| `scripts/rollback-chatbot.sh` | Linux/Mac | Interactive rollback |

**Deployment Steps:**
1. Create backup of current state
2. Check Python environment
3. Install dependencies
4. Verify database connection
5. Run health checks
6. Run smoke tests

**Rollback Features:**
- Lists available backups
- Interactive selection
- Automatic service stop
- Backup restoration
- Verification

---

### 5. Docker Compose Updates
**File:** `docker-compose.yml`

Added health check for chatbot service:
```yaml
chatbot:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 40s
```

---

### 6. Utils Package
**File:** `services/chatbot/utils/__init__.py`

Exports all utilities:
```python
from utils import (
    # Health
    get_health_checker,
    create_health_blueprint,
    
    # Logging
    get_logger,
    setup_logger,
    LogOperation,
    
    # Metrics
    get_all_metrics,
    create_metrics_blueprint,
    track_time
)
```

---

## Integration with Flask App

Add to `app.py`:
```python
from utils import (
    create_health_blueprint,
    create_metrics_blueprint,
    setup_logger
)

# Setup logging
setup_logger(log_level="INFO", json_output=True)

# Register blueprints
app.register_blueprint(create_health_blueprint())
app.register_blueprint(create_metrics_blueprint())
```

---

## Running Deployment

### Windows
```batch
cd AI-Assistant
scripts\deploy-chatbot.bat
```

### Linux/Mac
```bash
cd AI-Assistant
chmod +x scripts/deploy-chatbot.sh
./scripts/deploy-chatbot.sh
```

### Docker
```bash
docker-compose up -d chatbot
docker-compose ps  # Check health status
```

---

## Monitoring Dashboard

### Prometheus Configuration
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'chatbot'
    static_configs:
      - targets: ['localhost:5000']
    metrics_path: '/metrics'
```

### Health Check Monitoring
```bash
# Liveness (every 30s)
curl http://localhost:5000/health/live

# Readiness (before routing traffic)
curl http://localhost:5000/health/ready

# Detailed (for dashboards)
curl http://localhost:5000/health/detailed
```

---

## Verification

```bash
cd services/chatbot

# Test utils imports
python -c "from utils import get_logger, get_health_checker, get_all_metrics; \
  print('Logger:', get_logger()); \
  print('Health:', get_health_checker()); \
  print('Metrics:', len(get_all_metrics()))"

# Output:
# Logger: <Logger chatbot (INFO)>
# Health: <utils.health.HealthChecker object at 0x...>
# Metrics: 16
```

---

## Phase 6 Completion Checklist

- [x] Health check endpoints (liveness, readiness, detailed)
- [x] Structured JSON logging with rotation
- [x] Prometheus-compatible metrics
- [x] Deployment scripts (Windows + Linux)
- [x] Rollback scripts
- [x] Docker health checks
- [x] Utils package export

---

## Next Steps (Phase 7)

1. **Optimization**
   - Query optimization
   - Connection pooling
   - Cache tuning

2. **Cleanup**
   - Remove deprecated code
   - Update documentation
   - Code review

---

## Migration Progress

| Phase | Status |
|-------|--------|
| Phase 0: Environment Setup | ✅ Completed |
| Phase 1: Database Design | ✅ Completed |
| Phase 2: Redis Setup | ✅ Completed |
| Phase 3: Data Migration | ✅ Completed |
| Phase 4: Code Refactoring | ✅ Completed |
| Phase 5: Testing & Validation | ✅ Completed |
| Phase 6: Deployment & Monitoring | ✅ Completed |
| Phase 7: Optimization & Cleanup | 🔲 Not Started |
