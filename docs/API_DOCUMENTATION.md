# 📚 API Documentation - AI Assistant Platform

## Overview

AI Assistant provides RESTful APIs for all services. This document details available endpoints, request/response formats, and usage examples.

---

## 🌐 Base URLs

| Service | Base URL | Port |
|---------|----------|------|
| Hub Gateway | `http://localhost:3000` | 3000 |
| ChatBot | `http://localhost:5001` | 5001 |
| Text2SQL | `http://localhost:5002` | 5002 |
| Speech2Text | `http://localhost:7860` | 7860 |
| Stable Diffusion | `http://localhost:7861` | 7861 |

---

## 🤖 ChatBot API

### 1. Send Message

**Endpoint:** `POST /chat`

**Description:** Send a message to the AI and get a response.

**Request Body:**
```json
{
  "message": "Hello, how are you?",
  "model": "gemini",  // Options: "gemini", "gpt4", "deepseek", "qwen"
  "context": "casual",  // Options: "casual", "psychological", "lifestyle", "programming"
  "session_id": "optional-session-id",
  "files": [
    {
      "name": "example.py",
      "content": "print('hello')",
      "type": "code"
    }
  ]
}
```

**Response:**
```json
{
  "response": "Hello! I'm doing well, thank you for asking...",
  "model": "gemini",
  "session_id": "abc123",
  "timestamp": "2025-11-04T10:30:00Z",
  "tokens_used": 150
}
```

**Status Codes:**
- `200 OK`: Success
- `400 Bad Request`: Invalid input
- `401 Unauthorized`: Missing API key
- `500 Internal Server Error`: Server error

**Example (cURL):**
```bash
curl -X POST http://localhost:5001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain Python decorators",
    "model": "gemini",
    "context": "programming"
  }'
```

**Example (Python):**
```python
import requests

response = requests.post('http://localhost:5001/chat', json={
    'message': 'Explain Python decorators',
    'model': 'gemini',
    'context': 'programming'
})

data = response.json()
print(data['response'])
```

---

### 2. Generate Image (Text-to-Image)

**Endpoint:** `POST /api/generate-image`

**Request Body:**
```json
{
  "prompt": "A beautiful sunset over mountains",
  "negative_prompt": "blurry, low quality",
  "steps": 30,
  "cfg_scale": 7.5,
  "width": 512,
  "height": 512,
  "sampler": "Euler a",
  "model": "sd_xl_base_1.0.safetensors",
  "lora": "",
  "vae": ""
}
```

**Response:**
```json
{
  "images": ["base64_encoded_image_data"],
  "info": {
    "prompt": "A beautiful sunset over mountains",
    "seed": 123456789,
    "model": "sd_xl_base_1.0.safetensors"
  }
}
```

---

### 3. Image-to-Image

**Endpoint:** `POST /api/img2img`

**Request Body:**
```json
{
  "init_image": "base64_encoded_image",
  "prompt": "Make it more vibrant",
  "denoising_strength": 0.7,
  "steps": 30,
  "cfg_scale": 7.5
}
```

---

### 4. Get Chat History

**Endpoint:** `GET /history`

**Query Parameters:**
- `session_id` (optional): Filter by session
- `limit` (optional): Number of conversations to return (default: 20)

**Response:**
```json
{
  "conversations": [
    {
      "id": "conv_123",
      "session_id": "session_abc",
      "timestamp": "2025-11-04T10:00:00Z",
      "preview": "Hello, how are you?",
      "messages_count": 5
    }
  ]
}
```

---

### 5. Export to PDF

**Endpoint:** `POST /export`

**Request Body:**
```json
{
  "conversation_id": "conv_123"
}
```

**Response:**
- Content-Type: `application/pdf`
- Returns PDF file for download

---

## 💾 Text2SQL API

### 1. Generate SQL Query

**Endpoint:** `POST /chat`

**Request Body:**
```json
{
  "question": "Show top 10 customers by revenue",
  "schema": "optional schema text or use uploaded schema",
  "database_type": "clickhouse",  // Options: clickhouse, mongodb, postgres, mysql, sqlserver
  "use_deep_thinking": true
}
```

**Response:**
```json
{
  "sql": "SELECT customer_id, customer_name, SUM(amount) as revenue FROM orders GROUP BY customer_id, customer_name ORDER BY revenue DESC LIMIT 10",
  "explanation": "This query groups customers by ID and calculates total revenue...",
  "confidence": 0.95,
  "from_knowledge_base": false
}
```

---

### 2. Upload Schema

**Endpoint:** `POST /upload`

**Content-Type:** `multipart/form-data`

**Form Data:**
- `file`: Schema file (.txt, .sql, .json, .jsonl)

**Response:**
```json
{
  "success": true,
  "message": "Schema uploaded successfully",
  "filename": "ecommerce_schema.sql",
  "tables_detected": 5
}
```

---

### 3. Generate Sample Questions

**Endpoint:** `POST /chat`

**Request Body:**
```json
{
  "question": "tạo câu hỏi",
  "schema": "table schema here"
}
```

**Response:**
```json
{
  "questions": [
    {
      "question": "Top 10 best-selling products",
      "sql": "SELECT product_name, SUM(quantity) as total_sold FROM orders JOIN products..."
    },
    // ... 4 more questions
  ]
}
```

---

### 4. Save to Knowledge Base

**Endpoint:** `POST /knowledge/save`

**Request Body:**
```json
{
  "question": "Top customers by revenue",
  "sql": "SELECT customer_id, SUM(amount) FROM orders GROUP BY customer_id ORDER BY 2 DESC"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Saved to knowledge base"
}
```

---

### 5. List Knowledge Base

**Endpoint:** `GET /knowledge/list`

**Response:**
```json
{
  "entries": [
    {
      "question": "Top customers by revenue",
      "sql": "SELECT ...",
      "learned_at": "2025-11-04T10:00:00Z"
    }
  ]
}
```

---

### 6. Test Database Connection

**Endpoint:** `POST /api/database/test-connection`

**Request Body:**
```json
{
  "database_type": "clickhouse",
  "host": "localhost",
  "port": 9000,
  "database": "default",
  "username": "default",
  "password": ""
}
```

**Response:**
```json
{
  "success": true,
  "message": "Connection successful",
  "version": "23.8.2.7"
}
```

---

## 🎙️ Speech2Text API

### 1. Upload Audio File

**Endpoint:** `POST /upload`

**Content-Type:** `multipart/form-data`

**Form Data:**
- `file`: Audio file (.mp3, .wav, .m4a, .flac)
- `enable_diarization`: Boolean (default: true)
- `enable_vad`: Boolean (default: true)
- `num_speakers`: Integer (0 = auto-detect)

**Response:**
```json
{
  "session_id": "session_20251104_103045",
  "status": "processing",
  "message": "Audio uploaded successfully"
}
```

---

### 2. Get Processing Status

**Endpoint:** `GET /status/<session_id>`

**Response:**
```json
{
  "session_id": "session_20251104_103045",
  "status": "processing",
  "progress": 65,
  "stage": "PhoWhisper transcription",
  "estimated_time_remaining": 45
}
```

**Status Values:**
- `queued`: Waiting to process
- `processing`: Currently processing
- `completed`: Finished successfully
- `failed`: Processing failed

---

### 3. Get Results

**Endpoint:** `GET /results/<session_id>`

**Response:**
```json
{
  "session_id": "session_20251104_103045",
  "transcript": "Full transcript text with speaker labels...",
  "metadata": {
    "duration": 180.5,
    "num_speakers": 2,
    "processing_time": 95.2,
    "models_used": ["whisper-large-v3", "phowhisper-large", "qwen2.5-1.5b"]
  },
  "timeline": [
    {
      "speaker": "Speaker_00",
      "start": 0.0,
      "end": 15.3,
      "text": "Chào buổi sáng..."
    }
  ]
}
```

---

### 4. Download Results

**Endpoint:** `GET /download/<session_id>/<format>`

**Format Options:**
- `txt`: Plain text with speaker labels
- `json`: Structured JSON with metadata
- `timeline`: Timeline format

**Response:**
- Content-Type: `text/plain` or `application/json`
- Returns file for download

---

## 🎨 Stable Diffusion API

### 1. Text-to-Image

**Endpoint:** `POST /sdapi/v1/txt2img`

**Request Body:**
```json
{
  "prompt": "A beautiful landscape",
  "negative_prompt": "blurry, low quality",
  "steps": 30,
  "cfg_scale": 7.5,
  "width": 512,
  "height": 512,
  "sampler_name": "Euler a",
  "seed": -1,
  "batch_size": 1
}
```

**Response:**
```json
{
  "images": ["base64_encoded_image"],
  "parameters": {
    "prompt": "A beautiful landscape",
    "seed": 123456789
  },
  "info": "{...}"
}
```

---

### 2. Image-to-Image

**Endpoint:** `POST /sdapi/v1/img2img`

**Request Body:**
```json
{
  "init_images": ["base64_encoded_image"],
  "prompt": "Make it more colorful",
  "denoising_strength": 0.7,
  "steps": 30
}
```

---

### 3. Get Models

**Endpoint:** `GET /sdapi/v1/sd-models`

**Response:**
```json
[
  {
    "title": "sd_xl_base_1.0.safetensors",
    "model_name": "sd_xl_base_1.0",
    "hash": "abc123"
  }
]
```

---

### 4. Get Samplers

**Endpoint:** `GET /sdapi/v1/samplers`

**Response:**
```json
[
  {"name": "Euler a"},
  {"name": "DPM++ 2M Karras"},
  {"name": "DDIM"}
]
```

---

## 🔐 Authentication

Most endpoints require API keys in the `.env` file. For external access, add API key to headers:

```
Authorization: Bearer YOUR_API_KEY
```

---

## 🚨 Error Handling

All APIs return consistent error format:

```json
{
  "error": true,
  "message": "Error description",
  "code": "ERROR_CODE",
  "details": {}
}
```

**Common Error Codes:**
- `INVALID_INPUT`: Bad request parameters
- `UNAUTHORIZED`: Missing or invalid API key
- `NOT_FOUND`: Resource not found
- `RATE_LIMITED`: Too many requests
- `SERVER_ERROR`: Internal server error

---

## 📊 Rate Limiting

| Service | Rate Limit |
|---------|------------|
| ChatBot | 60 requests/minute |
| Text2SQL | 30 requests/minute |
| Speech2Text | 10 files/hour |
| Stable Diffusion | 20 generations/hour |

---

## 🧪 Testing API

### Postman Collection

Download our Postman collection: [AI-Assistant.postman_collection.json](./postman/AI-Assistant.postman_collection.json)

### cURL Examples

See [examples/api_examples.sh](./examples/api_examples.sh) for complete cURL examples.

### Python SDK

```python
from ai_assistant import AIAssistant

client = AIAssistant(
    chatbot_url="http://localhost:5001",
    text2sql_url="http://localhost:5002",
    speech2text_url="http://localhost:7860"
)

# ChatBot
response = client.chatbot.send_message("Hello!")

# Text2SQL
sql = client.text2sql.generate_query("Top 10 customers")

# Speech2Text
transcript = client.speech2text.transcribe("audio.mp3")
```

---

## 📝 Changelog

See [CHANGELOG.md](./CHANGELOG.md) for API version history.

---

**Last Updated:** November 4, 2025  
**API Version:** 2.0.0
