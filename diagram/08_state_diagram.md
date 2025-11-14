# 8️⃣ STATE DIAGRAM

> **Biểu đồ trạng thái hệ thống AI-Assistant**  
> Mô tả các trạng thái và transitions của các entities chính

---

## 📋 Mô tả

State Diagram thể hiện:
- **States:** Các trạng thái của entities (Conversation, Query, Transcription, etc.)
- **Transitions:** Sự chuyển đổi giữa các trạng thái
- **Events:** Sự kiện kích hoạt transitions
- **Actions:** Hành động xảy ra khi transition

---

## 🎯 Key State Machines

1. **Conversation State (ChatBot)**
2. **Message State (ChatBot)**
3. **SQL Query State (Text2SQL)**
4. **Transcription State (Speech2Text)**
5. **Image Generation State (Stable Diffusion)**
6. **Service State (System)**

---

## 1️⃣ Conversation State Machine (ChatBot)

```mermaid
stateDiagram-v2
    [*] --> New: User creates conversation
    
    New --> Active: First message sent
    
    Active --> Active: User/AI sends message
    Active --> Paused: User leaves page
    Active --> Archived: User archives
    Active --> Deleted: User deletes
    
    Paused --> Active: User returns
    Paused --> Archived: Auto-archive after 30 days
    Paused --> Deleted: User deletes
    
    Archived --> Active: User unarchives
    Archived --> Deleted: User deletes
    
    Deleted --> [*]
    
    note right of Active
        - total_messages++
        - total_tokens += n
        - updated_at = now()
    end note
    
    note right of Archived
        - is_archived = true
        - Cannot send new messages
        - Read-only mode
    end note
    
    note right of Deleted
        - Soft delete (recoverable)
        - OR hard delete (permanent)
        - CASCADE delete messages
    end note
```

### Conversation States:

| State | Description | Can Modify? | Auto-transition? |
|:------|:------------|:------------|:-----------------|
| **New** | Just created, no messages | ✅ | → Active (on first message) |
| **Active** | Currently in use | ✅ | → Paused (on inactivity) |
| **Paused** | User left, inactive | ✅ | → Archived (after 30 days) |
| **Archived** | Long-term storage | ❌ (read-only) | No |
| **Deleted** | Marked for deletion | ❌ | → Permanent delete (after 7 days) |

### State Transitions:

```python
# Example: Archive conversation
def archive_conversation(conv_id):
    conv = get_conversation(conv_id)
    if conv.state in ['Active', 'Paused']:
        conv.state = 'Archived'
        conv.is_archived = True
        conv.updated_at = datetime.now()
        save(conv)
        return True
    return False
```

---

## 2️⃣ Message State Machine (ChatBot)

```mermaid
stateDiagram-v2
    [*] --> Composing: User starts typing
    
    Composing --> Validating: User sends
    
    Validating --> Invalid: Validation failed
    Validating --> Pending: Validation passed
    
    Invalid --> Composing: User edits
    Invalid --> [*]: User cancels
    
    Pending --> Generating: AI processing
    
    Generating --> Generating: Streaming tokens
    Generating --> Completed: Generation finished
    Generating --> Stopped: User clicked Stop
    Generating --> Failed: API error
    
    Stopped --> Completed: Partial response saved
    
    Failed --> Retrying: Auto-retry (attempt < 3)
    Failed --> Completed: Manual retry
    Failed --> [*]: User cancels
    
    Retrying --> Generating: Retry attempt
    
    Completed --> Editing: User clicks Edit
    Completed --> Regenerating: User clicks Regenerate
    Completed --> Versioned: New version created
    
    Editing --> Validating: User saves edit
    
    Regenerating --> Generating: Create new version
    
    Versioned --> Completed: Version saved
    
    Completed --> [*]: Conversation continues
    
    note right of Generating
        - Show typing indicator
        - Stream tokens to UI
        - Allow Stop button
    end note
    
    note right of Stopped
        - Keep partial output
        - Mark as stopped
        - Allow continue later
    end note
    
    note right of Versioned
        - version++
        - parent_message_id = original
        - is_edited = true
    end note
```

### Message States:

| State | Description | User Actions | System Actions |
|:------|:------------|:-------------|:---------------|
| **Composing** | User typing | Type, paste, upload file | Auto-save draft |
| **Validating** | Checking input | Wait | Validate length, content |
| **Pending** | Queued for AI | Wait | Add to queue |
| **Generating** | AI creating response | Click Stop | Stream tokens, update UI |
| **Stopped** | Manually interrupted | View partial | Save partial response |
| **Failed** | Error occurred | Retry, cancel | Log error, retry logic |
| **Completed** | Finished successfully | Edit, regenerate, continue | Save to DB |
| **Editing** | User modifying | Save, cancel | Create new version |
| **Versioned** | New version created | View versions | Link to parent |

---

## 3️⃣ SQL Query State Machine (Text2SQL)

```mermaid
stateDiagram-v2
    [*] --> InputQuestion: User enters question
    
    InputQuestion --> Searching_KB: Check Knowledge Base
    
    Searching_KB --> KB_Hit: Found match (95%+)
    Searching_KB --> KB_Miss: No match found
    
    KB_Hit --> Displaying: Show saved SQL
    
    KB_Miss --> Analyzing_Schema: Parse schema
    
    Analyzing_Schema --> Building_Prompt: Schema parsed
    
    Building_Prompt --> Calling_API: Send to Gemini
    
    Calling_API --> Generating: API processing
    
    Generating --> Validating_SQL: Response received
    
    Validating_SQL --> Invalid_SQL: Syntax error
    Validating_SQL --> Valid_SQL: Valid syntax
    
    Invalid_SQL --> Regenerating: Auto-fix attempt
    
    Regenerating --> Calling_API: Retry with clarification
    
    Valid_SQL --> Displaying: Show generated SQL
    
    Displaying --> Awaiting_Feedback: User reviews
    
    Awaiting_Feedback --> Correct: User marks correct
    Awaiting_Feedback --> Wrong: User marks wrong
    Awaiting_Feedback --> Executing: User clicks Execute
    Awaiting_Feedback --> Editing: User modifies
    
    Correct --> Saving_to_KB: Save to Knowledge Base
    
    Wrong --> Regenerating: Generate again
    
    Editing --> Displaying: Show edited SQL
    
    Executing --> Connecting_DB: Connect to database
    
    Connecting_DB --> Connection_Failed: Connection error
    Connecting_DB --> Connected: Connection success
    
    Connection_Failed --> Awaiting_Feedback: Show error
    
    Connected --> Running_Query: Execute SQL
    
    Running_Query --> Query_Failed: SQL error, timeout
    Running_Query --> Query_Success: Results returned
    
    Query_Failed --> Awaiting_Feedback: Show error
    
    Query_Success --> Displaying_Results: Show data table
    
    Saving_to_KB --> Executing: Proceed to execute
    
    Displaying_Results --> [*]: Done
    
    note right of KB_Hit
        - usage_count++
        - last_used = now()
        - Fast: ~300ms
    end note
    
    note right of Saving_to_KB
        - question
        - sql_query
        - schema_hash
        - is_correct = true
    end note
    
    note right of Running_Query
        - Max timeout: 30s
        - Track execution_time
        - Limit rows: 1000
    end note
```

### Query States:

| State | Description | Duration | Next States |
|:------|:------------|:---------|:------------|
| **Searching_KB** | Check if question exists | 50-200ms | KB_Hit, KB_Miss |
| **KB_Hit** | Found in Knowledge Base | Instant | Displaying |
| **Analyzing_Schema** | Parse database schema | 100-500ms | Building_Prompt |
| **Calling_API** | Request to Gemini | 2-5s | Generating |
| **Generating** | AI creating SQL | 2-5s | Validating_SQL |
| **Validating_SQL** | Check SQL syntax | 50-100ms | Valid_SQL, Invalid_SQL |
| **Displaying** | Show SQL to user | - | Awaiting_Feedback |
| **Executing** | Running SQL query | 0.1-30s | Query_Success, Query_Failed |
| **Saving_to_KB** | Add to Knowledge Base | 50-100ms | Executing |

### Learning System Flow:

```
┌─────────────────────────────────────────────┐
│ Question → KB Check → Generate → Feedback  │
│                ↓                    ↓       │
│            Found (Fast)         Correct?    │
│                                    ↓        │
│                                  Yes        │
│                                    ↓        │
│                              Save to KB     │
│                                    ↓        │
│                           Reuse next time   │
└─────────────────────────────────────────────┘
```

---

## 4️⃣ Transcription State Machine (Speech2Text)

```mermaid
stateDiagram-v2
    [*] --> Uploading: User uploads audio
    
    Uploading --> Uploaded: Upload complete
    
    Uploaded --> Validating: Validate format
    
    Validating --> Invalid: Unsupported format
    Validating --> Valid: Supported format
    
    Invalid --> [*]: Show error
    
    Valid --> Queued: Add to processing queue
    
    Queued --> Preprocessing: Start processing
    
    Preprocessing --> Diarizing: Detect speakers
    
    Diarizing --> Diarization_Complete: Speakers found
    Diarizing --> Diarization_Skipped: No diarization
    
    Diarization_Complete --> Transcribing_Parallel
    Diarization_Skipped --> Transcribing_Parallel
    
    Transcribing_Parallel --> Whisper_Running
    Transcribing_Parallel --> PhoWhisper_Running
    
    Whisper_Running --> Whisper_Complete: Transcript 1 ready
    PhoWhisper_Running --> PhoWhisper_Complete: Transcript 2 ready
    
    Whisper_Complete --> Merging
    PhoWhisper_Complete --> Merging
    
    Merging --> Merged: Combined transcript
    
    Merged --> Enhancing: Qwen processing
    
    Enhancing --> Enhanced: Grammar fixed
    
    Enhanced --> Aligning: Align with speakers
    
    Aligning --> Aligned: Timeline created
    
    Aligned --> Saving: Save to database
    
    Saving --> Completed: Done
    
    Completed --> [*]
    
    Preprocessing --> Failed: Error occurred
    Diarizing --> Failed
    Whisper_Running --> Failed
    PhoWhisper_Running --> Failed
    Enhancing --> Failed
    
    Failed --> Retrying: Retry if possible
    Failed --> [*]: Max retries reached
    
    Retrying --> Queued: Requeue
    
    note right of Transcribing_Parallel
        - Whisper (60-90s)
        - PhoWhisper (60-90s)
        - Run in parallel
    end note
    
    note right of Merging
        - Weighted fusion
        - 60% Whisper
        - 40% PhoWhisper
    end note
    
    note right of Completed
        - transcript_raw
        - transcript_enhanced
        - speaker_timeline
        - accuracy_score
    end note
```

### Transcription States:

| State | Description | Progress | Duration (10min audio) |
|:------|:------------|:---------|:-----------------------|
| **Uploading** | File upload in progress | 0% | 1-5s |
| **Validating** | Check format & size | 5% | 0.5s |
| **Queued** | Waiting for processing | 10% | Variable |
| **Preprocessing** | Audio conversion, VAD | 15% | 10-15s |
| **Diarizing** | Speaker detection | 30% | 40-60s |
| **Transcribing_Parallel** | Dual-model transcription | 60% | 60-90s (parallel) |
| **Merging** | Combine transcripts | 80% | 2-5s |
| **Enhancing** | AI grammar improvement | 90% | 10-15s |
| **Aligning** | Align with speakers | 95% | 2-5s |
| **Completed** | Finished successfully | 100% | - |

---

## 5️⃣ Image Generation State Machine (Stable Diffusion)

```mermaid
stateDiagram-v2
    [*] --> Idle: Service running
    
    Idle --> Receiving_Request: User submits prompt
    
    Receiving_Request --> Validating_Input: Check parameters
    
    Validating_Input --> Invalid_Input: Missing required fields
    Validating_Input --> Valid_Input: All valid
    
    Invalid_Input --> Idle: Show error
    
    Valid_Input --> Loading_Model: Load SD model
    
    Loading_Model --> Model_Loaded: Model ready
    Loading_Model --> Model_Error: Model not found
    
    Model_Error --> Idle: Show error
    
    Model_Loaded --> Loading_LoRA: Apply LoRA (if selected)
    
    Loading_LoRA --> LoRA_Loaded: LoRA applied
    Loading_LoRA --> LoRA_Skipped: No LoRA
    
    LoRA_Loaded --> Loading_VAE
    LoRA_Skipped --> Loading_VAE: Load VAE (if selected)
    
    Loading_VAE --> VAE_Loaded: VAE applied
    Loading_VAE --> VAE_Skipped: No VAE
    
    VAE_Loaded --> Generating
    VAE_Skipped --> Generating: Start generation
    
    Generating --> Generating: Progress: Step N/Total
    Generating --> Interrupted: User clicked Stop
    Generating --> Generation_Complete: All steps done
    Generating --> Generation_Failed: OOM, CUDA error
    
    Interrupted --> Partial_Result: Save partial image
    
    Generation_Failed --> Idle: Show error
    
    Generation_Complete --> Post_Processing: Face restore, upscale
    
    Post_Processing --> Saving_Image: Save to disk
    
    Saving_Image --> Saved: Image saved
    
    Saved --> Sending_Response: Return to user
    
    Sending_Response --> Idle: Ready for next
    
    Partial_Result --> Idle
    
    note right of Generating
        - Show progress: 0-100%
        - Update every 1s
        - Allow interruption
    end note
    
    note right of Generation_Complete
        - 512x512: ~10s
        - 768x768: ~20s
        - 1024x1024: ~30s
    end note
    
    note right of Saved
        - Image file
        - Metadata (prompt, seed, etc.)
        - Hash for dedup
    end note
```

### Image Generation States:

| State | Description | GPU Usage | Can Interrupt? |
|:------|:------------|:----------|:---------------|
| **Idle** | Waiting for request | Low (VRAM: ~2GB) | N/A |
| **Loading_Model** | Loading SD checkpoint | High (VRAM: +4GB) | ❌ |
| **Loading_LoRA** | Applying LoRA weights | Medium | ❌ |
| **Generating** | Creating image (steps) | Very High (VRAM: 6-12GB) | ✅ |
| **Post_Processing** | Upscale, face restore | High | ❌ |
| **Saved** | Image saved to disk | Low | N/A |

### Generation Progress Tracking:

```
Step  1/30 ████░░░░░░░░░░░░░░░░░░░░░░░░  3%  (1s)
Step 10/30 ████████████░░░░░░░░░░░░░░░░ 33%  (10s)
Step 20/30 ████████████████████░░░░░░░░ 67%  (20s)
Step 30/30 ████████████████████████████ 100% (30s) ✅
```

---

## 6️⃣ Service State Machine (System-wide)

```mermaid
stateDiagram-v2
    [*] --> Stopped: Service not running
    
    Stopped --> Starting: Start command
    
    Starting --> Initializing: Load configs
    
    Initializing --> Loading_Dependencies: Import libraries
    
    Loading_Dependencies --> Loading_Models: Load AI models
    Loading_Dependencies --> Dependency_Error: Import failed
    
    Dependency_Error --> Stopped: Exit with error
    
    Loading_Models --> Models_Loaded: Models ready
    Loading_Models --> Model_Error: Model not found
    
    Model_Error --> Running_Without_AI: Degraded mode
    
    Models_Loaded --> Connecting_DB: Connect to database
    
    Connecting_DB --> DB_Connected: Connection success
    Connecting_DB --> DB_Failed: Connection failed
    
    DB_Failed --> Running_Without_DB: File-based fallback
    
    DB_Connected --> Running: Service ready
    Running_Without_AI --> Running
    Running_Without_DB --> Running
    
    Running --> Running: Processing requests
    Running --> Degraded: Partial failure
    Running --> Stopping: Stop command
    Running --> Crashed: Critical error
    
    Degraded --> Running: Issue resolved
    Degraded --> Stopping: Manual stop
    
    Crashed --> Restarting: Auto-restart (attempt < 3)
    Crashed --> Stopped: Max restarts reached
    
    Restarting --> Starting
    
    Stopping --> Cleanup: Graceful shutdown
    
    Cleanup --> Stopped: Shutdown complete
    
    note right of Running
        - Health: OK
        - Accepting requests
        - All features available
    end note
    
    note right of Degraded
        - Health: WARNING
        - Limited functionality
        - Some features disabled
    end note
    
    note right of Crashed
        - Health: ERROR
        - Not responding
        - Auto-restart triggered
    end note
```

### Service States:

| State | Health Status | Accepting Requests? | Features |
|:------|:--------------|:-------------------|:---------|
| **Stopped** | ⚫ Offline | ❌ | None |
| **Starting** | 🟡 Starting | ❌ | None |
| **Initializing** | 🟡 Starting | ❌ | Loading... |
| **Running** | 🟢 Healthy | ✅ | All |
| **Degraded** | 🟠 Warning | ⚠️ Partial | Limited |
| **Crashed** | 🔴 Error | ❌ | None |
| **Stopping** | 🟡 Stopping | ❌ | None |

### Health Check Response:

```json
{
  "service": "ChatBot",
  "state": "Running",
  "health": "Healthy",
  "uptime": "2d 5h 30m",
  "requests_served": 15234,
  "errors_last_hour": 2,
  "features": {
    "ai_models": "available",
    "database": "connected",
    "file_storage": "available",
    "external_apis": "available"
  },
  "resource_usage": {
    "cpu_percent": 15.2,
    "memory_mb": 2048,
    "disk_gb": 125.5
  }
}
```

---

## 🔄 State Transition Events

### Global Events (All State Machines):

| Event | Description | Trigger |
|:------|:------------|:--------|
| **created** | Entity created | User action, system trigger |
| **updated** | Entity modified | User edit, system update |
| **deleted** | Entity removed | User delete, auto-cleanup |
| **error** | Error occurred | Exception, validation failure |
| **timeout** | Operation timed out | Exceeds max duration |
| **retry** | Retry operation | Auto-retry logic |
| **cancelled** | Operation cancelled | User interruption |

---

## 📊 State Statistics (ChatBot Example)

### Conversation State Distribution:

```
Active:    45% ████████████████████░░░░░░░░░░░░░░░░░░░░
Paused:    30% ████████████████░░░░░░░░░░░░░░░░░░░░░░░░
Archived:  20% ██████████████░░░░░░░░░░░░░░░░░░░░░░░░░░
Deleted:    5% ███░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
```

### Average State Duration:

| State | Avg Duration | Min | Max |
|:------|:-------------|:----|:----|
| **Active** | 15 minutes | 1 min | 2 hours |
| **Paused** | 2 days | 5 min | 30 days |
| **Archived** | Indefinite | - | - |

---

## 🎯 State Validation Rules

### Conversation States:

```python
# Valid transitions
VALID_TRANSITIONS = {
    'New': ['Active', 'Deleted'],
    'Active': ['Active', 'Paused', 'Archived', 'Deleted'],
    'Paused': ['Active', 'Archived', 'Deleted'],
    'Archived': ['Active', 'Deleted'],
    'Deleted': []  # Terminal state
}

def can_transition(current_state, new_state):
    return new_state in VALID_TRANSITIONS.get(current_state, [])
```

### Business Rules:

1. **Cannot send messages in Archived state** → Must unarchive first
2. **Soft delete recoverable within 7 days** → After 7 days, hard delete
3. **Auto-archive after 30 days of inactivity** → Move Paused → Archived
4. **Max active conversations per user: 50** → Must archive old ones

---

## 🚀 Future State Enhancements

### Planned States:

1. **Conversation: Shared** → Allow multiple users to collaborate
2. **Query: Scheduled** → Run SQL query on schedule
3. **Transcription: Streaming** → Real-time transcription
4. **Image: Batch** → Generate multiple images in batch
5. **Service: Scaling** → Auto-scale based on load

---

<div align="center">

[⬅️ Previous: Activity Diagram](07_activity_diagram.md) | [Back to Index](README.md) | [➡️ Next: Deployment Diagram](09_deployment_diagram.md)

</div>
