# 🔌 RAG Services - API Documentation

> **Complete API reference for RAG Services**  
> **Version:** 1.0.0  
> **Base URL:** `http://localhost:5003`  
> **Last Updated:** November 6, 2025

---

## 📋 OVERVIEW

RAG Services cung cấp RESTful API để tương tác với hệ thống RAG, bao gồm query processing, document management, và system monitoring.

### Base URL

```
Development: http://localhost:5003
Production:  https://api.yourdomain.com
```

### Authentication

Hiện tại API không yêu cầu authentication (development mode).

**Production sẽ có**:
```http
Authorization: Bearer <your_api_token>
```

---

## 📚 ENDPOINTS

### 1. Query Processing

#### POST `/api/query`

Gửi câu hỏi và nhận câu trả lời từ RAG system.

**Request**:

```http
POST /api/query
Content-Type: application/json

{
  "query": "Câu hỏi của bạn?",
  "session_id": "optional-session-id",
  "options": {
    "model": "gpt-4",
    "max_tokens": 500,
    "temperature": 0.7,
    "use_cache": true
  }
}
```

**Request Parameters**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string | Yes | User's question |
| `session_id` | string | No | Session ID for context |
| `options.model` | string | No | LLM model (default: gpt-4) |
| `options.max_tokens` | integer | No | Max response tokens (default: 500) |
| `options.temperature` | float | No | Creativity (0-1, default: 0.7) |
| `options.use_cache` | boolean | No | Use cached response (default: true) |

**Response**:

```json
{
  "success": true,
  "data": {
    "answer": "Đây là câu trả lời...",
    "sources": [
      {
        "document": "doc1.pdf",
        "page": 5,
        "relevance": 0.95,
        "excerpt": "Relevant text excerpt..."
      }
    ],
    "metadata": {
      "model": "gpt-4",
      "tokens_used": 450,
      "response_time": 1.23,
      "cache_hit": false,
      "confidence": 0.89
    }
  },
  "session_id": "abc123",
  "timestamp": "2025-11-06T10:30:00Z"
}
```

**Error Response**:

```json
{
  "success": false,
  "error": {
    "code": "INVALID_QUERY",
    "message": "Query cannot be empty",
    "details": {}
  },
  "timestamp": "2025-11-06T10:30:00Z"
}
```

**Error Codes**:

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_QUERY` | 400 | Query is empty or invalid |
| `LLM_ERROR` | 502 | LLM API error |
| `RATE_LIMIT` | 429 | Too many requests |
| `SERVER_ERROR` | 500 | Internal server error |

**Example**:

```bash
curl -X POST http://localhost:5003/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Thủ đô của Việt Nam là gì?",
    "options": {
      "model": "gpt-4",
      "temperature": 0.7
    }
  }'
```

---

### 2. Chat History

#### GET `/api/history`

Lấy lịch sử conversation của session.

**Request**:

```http
GET /api/history?session_id=abc123&limit=20&offset=0
```

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `session_id` | string | Yes | Session ID |
| `limit` | integer | No | Messages per page (default: 20) |
| `offset` | integer | No | Pagination offset (default: 0) |

**Response**:

```json
{
  "success": true,
  "data": {
    "messages": [
      {
        "id": "msg001",
        "role": "user",
        "content": "Thủ đô Việt Nam là gì?",
        "timestamp": "2025-11-06T10:25:00Z"
      },
      {
        "id": "msg002",
        "role": "assistant",
        "content": "Thủ đô của Việt Nam là Hà Nội.",
        "sources": [...],
        "timestamp": "2025-11-06T10:25:02Z"
      }
    ],
    "total": 50,
    "session_info": {
      "session_id": "abc123",
      "created_at": "2025-11-06T10:00:00Z",
      "message_count": 50
    }
  }
}
```

**Example**:

```bash
curl http://localhost:5003/api/history?session_id=abc123&limit=10
```

---

#### DELETE `/api/history/clear`

Xóa lịch sử conversation.

**Request**:

```http
DELETE /api/history/clear
Content-Type: application/json

{
  "session_id": "abc123"
}
```

**Response**:

```json
{
  "success": true,
  "message": "History cleared successfully",
  "deleted_count": 50
}
```

**Example**:

```bash
curl -X DELETE http://localhost:5003/api/history/clear \
  -H "Content-Type: application/json" \
  -d '{"session_id": "abc123"}'
```

---

### 3. Document Management

#### POST `/api/document/upload`

Upload document vào knowledge base.

**Request**:

```http
POST /api/document/upload
Content-Type: multipart/form-data

file: [binary file]
metadata: {
  "title": "Document Title",
  "category": "Technical",
  "tags": ["python", "ai"]
}
```

**Supported Formats**:
- PDF (`.pdf`)
- Text (`.txt`)
- Markdown (`.md`)
- Word (`.docx`)
- HTML (`.html`)

**Max File Size**: 50 MB

**Response**:

```json
{
  "success": true,
  "data": {
    "document_id": "doc_123",
    "filename": "document.pdf",
    "size": 1048576,
    "pages": 10,
    "chunks": 45,
    "indexed_at": "2025-11-06T10:30:00Z"
  }
}
```

**Example**:

```bash
curl -X POST http://localhost:5003/api/document/upload \
  -F "file=@document.pdf" \
  -F 'metadata={"title":"My Document","category":"Technical"}'
```

---

#### GET `/api/documents`

Lấy danh sách documents trong knowledge base.

**Request**:

```http
GET /api/documents?page=1&limit=20&category=Technical
```

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page` | integer | No | Page number (default: 1) |
| `limit` | integer | No | Items per page (default: 20) |
| `category` | string | No | Filter by category |
| `search` | string | No | Search in titles |

**Response**:

```json
{
  "success": true,
  "data": {
    "documents": [
      {
        "id": "doc_123",
        "title": "Python Guide",
        "filename": "python.pdf",
        "size": 1048576,
        "pages": 100,
        "chunks": 450,
        "category": "Technical",
        "tags": ["python", "programming"],
        "uploaded_at": "2025-11-06T10:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 100,
      "total_pages": 5
    }
  }
}
```

---

#### DELETE `/api/document/:id`

Xóa document khỏi knowledge base.

**Request**:

```http
DELETE /api/document/doc_123
```

**Response**:

```json
{
  "success": true,
  "message": "Document deleted successfully",
  "document_id": "doc_123"
}
```

---

### 4. System Monitoring

#### GET `/api/stats`

Lấy system statistics và metrics.

**Request**:

```http
GET /api/stats?timeframe=24h
```

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `timeframe` | string | No | Time window (1h, 24h, 7d, 30d) |

**Response**:

```json
{
  "success": true,
  "data": {
    "requests": {
      "total": 1000,
      "successful": 950,
      "failed": 50,
      "rate": 41.67
    },
    "performance": {
      "avg_response_time": 1.23,
      "p95_response_time": 2.45,
      "p99_response_time": 3.67
    },
    "cache": {
      "hit_rate": 0.72,
      "total_hits": 720,
      "total_misses": 280
    },
    "llm_usage": {
      "total_tokens": 500000,
      "prompt_tokens": 300000,
      "completion_tokens": 200000,
      "estimated_cost": 12.50
    },
    "documents": {
      "total": 50,
      "total_chunks": 2500,
      "total_size": 52428800
    },
    "uptime": 86400,
    "timestamp": "2025-11-06T10:30:00Z"
  }
}
```

**Example**:

```bash
curl http://localhost:5003/api/stats?timeframe=24h
```

---

#### GET `/health`

Health check endpoint.

**Request**:

```http
GET /health
```

**Response**:

```json
{
  "status": "healthy",
  "checks": {
    "api": "ok",
    "database": "ok",
    "cache": "ok",
    "llm": {
      "openai": "ok",
      "deepseek": "ok",
      "gemini": "ok"
    }
  },
  "uptime": 86400,
  "version": "1.0.0",
  "timestamp": "2025-11-06T10:30:00Z"
}
```

**Status Values**:
- `healthy`: All systems operational
- `degraded`: Some non-critical issues
- `unhealthy`: Critical issues

---

### 5. Configuration

#### GET `/api/config`

Lấy cấu hình hiện tại (không bao gồm sensitive data).

**Request**:

```http
GET /api/config
```

**Response**:

```json
{
  "success": true,
  "data": {
    "models": {
      "default": "gpt-4",
      "available": ["gpt-4", "gpt-3.5-turbo", "deepseek", "gemini"]
    },
    "limits": {
      "max_tokens": 4000,
      "max_context": 10,
      "max_file_size": 52428800,
      "rate_limit": 100
    },
    "features": {
      "cache_enabled": true,
      "vietnamese_support": true,
      "multi_llm": true
    }
  }
}
```

---

#### POST `/api/config`

Cập nhật configuration (admin only).

**Request**:

```http
POST /api/config
Content-Type: application/json
Authorization: Bearer <admin_token>

{
  "default_model": "gpt-4",
  "cache_enabled": true,
  "max_tokens": 4000
}
```

**Response**:

```json
{
  "success": true,
  "message": "Configuration updated successfully",
  "updated_fields": ["default_model", "cache_enabled"]
}
```

---

## 🔐 RATE LIMITING

### Limits

| Plan | Requests/minute | Requests/hour | Requests/day |
|------|-----------------|---------------|--------------|
| Free | 10 | 100 | 1000 |
| Pro | 60 | 1000 | 10000 |
| Enterprise | Unlimited | Unlimited | Unlimited |

### Headers

**Response Headers**:
```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1699272000
```

**Rate Limit Exceeded**:
```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Please try again in 60 seconds.",
    "retry_after": 60
  }
}
```

---

## 📊 RESPONSE FORMAT

### Success Response

```json
{
  "success": true,
  "data": { /* Response data */ },
  "metadata": { /* Additional metadata */ },
  "timestamp": "2025-11-06T10:30:00Z"
}
```

### Error Response

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": { /* Error details */ }
  },
  "timestamp": "2025-11-06T10:30:00Z"
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_REQUEST` | 400 | Invalid request format |
| `UNAUTHORIZED` | 401 | Authentication required |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `SERVER_ERROR` | 500 | Internal server error |
| `LLM_ERROR` | 502 | LLM API error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |

---

## 🧪 TESTING

### Using cURL

```bash
# Query
curl -X POST http://localhost:5003/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Test query"}'

# Get stats
curl http://localhost:5003/api/stats

# Health check
curl http://localhost:5003/health
```

### Using Python

```python
import requests

# Query
response = requests.post(
    "http://localhost:5003/api/query",
    json={
        "query": "Thủ đô Việt Nam là gì?",
        "options": {
            "model": "gpt-4",
            "temperature": 0.7
        }
    }
)
data = response.json()
print(data["data"]["answer"])

# Get history
response = requests.get(
    "http://localhost:5003/api/history",
    params={"session_id": "abc123", "limit": 10}
)
history = response.json()
```

### Using JavaScript

```javascript
// Query
const response = await fetch('http://localhost:5003/api/query', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    query: 'Thủ đô Việt Nam là gì?',
    options: {
      model: 'gpt-4',
      temperature: 0.7
    }
  })
});

const data = await response.json();
console.log(data.data.answer);
```

---

## 📝 WEBHOOKS (Coming Soon)

### Event Types

- `query.completed` - Query processed successfully
- `document.uploaded` - Document indexed
- `error.occurred` - Error detected

### Webhook Payload

```json
{
  "event": "query.completed",
  "data": {
    "session_id": "abc123",
    "query": "User question",
    "answer": "Generated answer",
    "timestamp": "2025-11-06T10:30:00Z"
  }
}
```

---

## 🔧 SDK & LIBRARIES

### Official SDKs (Planned)

- Python SDK
- JavaScript/TypeScript SDK
- Java SDK
- Go SDK

### Community Libraries

Check [GitHub repository](https://github.com/SkastVnT/AI-Assistant) for community-contributed libraries.

---

## 📚 EXAMPLES

### Complete Query Flow

```python
import requests

BASE_URL = "http://localhost:5003"

# 1. Create session
session_id = "my_session_123"

# 2. Send query
response = requests.post(
    f"{BASE_URL}/api/query",
    json={
        "query": "Giải thích về machine learning",
        "session_id": session_id,
        "options": {
            "model": "gpt-4",
            "max_tokens": 500,
            "temperature": 0.7
        }
    }
)

if response.status_code == 200:
    data = response.json()
    print("Answer:", data["data"]["answer"])
    print("Sources:", len(data["data"]["sources"]))
    print("Tokens used:", data["data"]["metadata"]["tokens_used"])
else:
    print("Error:", response.json()["error"]["message"])

# 3. Get conversation history
history_response = requests.get(
    f"{BASE_URL}/api/history",
    params={"session_id": session_id, "limit": 10}
)

history = history_response.json()
print(f"Total messages: {history['data']['total']}")

# 4. Check system stats
stats_response = requests.get(f"{BASE_URL}/api/stats")
stats = stats_response.json()
print(f"Cache hit rate: {stats['data']['cache']['hit_rate']:.2%}")
```

---

## 🆘 SUPPORT

### Need Help?

- 📖 [Full Documentation](../README.md)
- 💬 [Discord Community](https://discord.gg/ai-assistant)
- 🐛 [Report Issues](https://github.com/SkastVnT/AI-Assistant/issues)
- 📧 Email: api-support@ai-assistant.com

---

<div align="center">

## 🎉 API DOCUMENTATION COMPLETE

**Build amazing applications with RAG Services API!**

---

**📅 Created:** November 6, 2025  
**👤 Author:** SkastVnT  
**🔄 Version:** 1.0.0  
**📍 Location:** `RAG Services/docs/API_DOCUMENTATION.md`  
**🏷️ Tags:** #api #documentation #rest #endpoints

[🏠 Back to Main Docs](../README.md) | [🚀 Quick Start](../README.md#-quick-start)

</div>
