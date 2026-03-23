# Web UI Enhancements - State Persistence & Metadata

## Overview
Enhanced the VistralS2T Web UI with state persistence, session recovery, and comprehensive model metadata display.

## Features Added

### 1. State Persistence with localStorage
**Purpose**: Prevent data loss from accidental page refresh during long processing tasks.

**Implementation**:
- Saves processing state to browser localStorage on every progress update
- Stores: session ID, current step, progress percentage, status message
- Auto-restores state on page reload if session is less than 1 hour old
- Shows visual notification when session is recovered

**User Experience**:
- 🔄 **During Processing**: If user accidentally refreshes the page, progress is restored with "Restored from session" indicator
- ✅ **After Completion**: Results are preserved across refresh with "Previous results restored!" notification
- 🕐 **Timeout**: State expires after 1 hour to prevent stale data

### 2. Model Metadata Display
**Purpose**: Provide transparency about which AI models processed the audio.

**Models Tracked**:
```javascript
{
    whisper: 'large-v3',
    phowhisper: 'vinai/PhoWhisper-large',
    qwen: 'Qwen/Qwen2.5-1.5B-Instruct',
    diarization: 'pyannote/speaker-diarization-3.1'
}
```

**Display**:
- Color-coded badges for each model
- Professional card layout with distinct styling
- Green (Whisper), Red (PhoWhisper), Purple (Qwen), Blue (Diarization)

### 3. Processing Information Panel
**New "Processing Information" Card** shows:

- **AI Models Used**: Visual badges with model names and versions
- **Session ID**: Unique identifier for tracking (monospace font)
- **Completed At**: Timestamp of processing completion (local time)
- **Processing Time**: Total time taken (displayed in minutes)
- **Restored Session**: Blue badge indicator if session was recovered

### 4. Enhanced User Notifications
**Toast-style notifications** for important events:
- 🔄 Session restored (blue)
- ✅ Results recovered (green)
- ⚠️ Warnings (orange)
- ❌ Errors (red)

Auto-dismiss after 3 seconds with slide-in/slide-out animations.

## Technical Implementation

### Frontend Changes (`app/templates/index.html`)

#### State Management Functions:
```javascript
saveState(state)      // Save to localStorage with timestamp
loadState()           // Load from localStorage (max 1 hour old)
clearState()          // Remove saved state
```

#### State Object Structure:
```javascript
{
    status: 'processing' | 'complete',
    sessionId: 'session_20240315_143052',
    fileName: 'audio.mp3',
    fileSize: 1048576,
    startTime: 1710512452000,
    timestamp: 1710512452000,
    progress: {
        step: 'whisper',
        progress: 65,
        message: 'Transcribing segment 3/5...'
    },
    results: { /* complete results object */ }
}
```

#### Enhanced Results Display:
- `displayResults(data, isRestored)` - Modified to show metadata
- `addMetadataDisplay(metadata, isRestored)` - New function for metadata card
- `showNotification(message, type)` - Toast notifications

### Backend Changes (`app/web_ui.py`)

#### Processing Time Tracking:
```python
import time
start_time = time.time()
# ... processing ...
end_time = time.time()
processing_time = end_time - start_time

results = {
    # ... existing fields ...
    'processingTime': processing_time  # in seconds
}
```

## User Flow

### Normal Processing Flow:
1. User uploads audio file
2. State saved: `{ status: 'processing', progress: { step: 'initializing', progress: 0 }}`
3. Each progress update saves state to localStorage
4. On completion: `{ status: 'complete', results: {...} }`
5. User sees results with model metadata

### Page Refresh During Processing:
1. User accidentally refreshes browser
2. Page reloads, checks localStorage
3. Finds saved state (step: 'whisper', progress: 65%)
4. Restores UI to that state
5. Shows notification: "🔄 Session restored! Continue where you left off."
6. Processing continues in backend, UI reconnects via WebSocket

### Page Refresh After Completion:
1. User closes browser tab
2. Returns later (within 1 hour)
3. Page loads, finds complete state in localStorage
4. Restores full results display
5. Shows notification: "✅ Previous results restored!"
6. All download buttons work normally

## Benefits

### For Users:
- ✅ No data loss from accidental refresh
- ✅ Can close browser and return to results
- ✅ Transparency about AI models used
- ✅ Clear processing time metrics
- ✅ Professional, polished experience

### For Debugging:
- ✅ Session ID for tracking issues
- ✅ Processing time for performance analysis
- ✅ Model versions for reproducibility
- ✅ Timestamp for logs correlation

## Compatibility

- **Browser Support**: All modern browsers with localStorage API
- **Backward Compatible**: Works with existing backend without changes
- **Graceful Degradation**: If localStorage fails, app continues without persistence
- **Mobile Friendly**: Responsive design with flex/grid layouts

## Testing Scenarios

### 1. Normal Flow
- Upload audio → Process → View results ✅
- All metadata displays correctly ✅

### 2. Refresh During Processing
- Upload audio → Start processing → Refresh page at 50% ✅
- State restored, shows "Restored from session" ✅

### 3. Refresh After Completion
- Complete processing → Close tab → Reopen within 1 hour ✅
- Results fully restored with metadata ✅

### 4. State Expiration
- Complete processing → Close tab → Reopen after 2 hours ✅
- State expired, shows fresh upload page ✅

### 5. Error Handling
- Upload audio → Error occurs → State cleared ✅
- localStorage unavailable → App works without persistence ✅

## Files Modified

### 1. `app/templates/index.html`
- Added state persistence functions (localStorage)
- Enhanced `displayResults()` with metadata parameter
- Added `addMetadataDisplay()` for model info card
- Added `showNotification()` for toast messages
- Modified socket event handlers to save state
- Added CSS animations for notifications

### 2. `app/web_ui.py`
- Added `import time` and start_time tracking
- Modified `process_audio_with_diarization()` to calculate processing time
- Added `processingTime` field to results dictionary

## Configuration

### State Expiration Time
Located in `index.html`, line ~467:
```javascript
// Only restore if less than 1 hour old
if (Date.now() - state.timestamp < 3600000) {
```

Change `3600000` (1 hour in milliseconds) to adjust expiration:
- 30 minutes: `1800000`
- 2 hours: `7200000`
- 24 hours: `86400000`

## Future Enhancements

### Potential Additions:
1. **File Info**: Display original filename, size, format
2. **Export Session**: Allow downloading session state as JSON
3. **Session History**: List of previous sessions with timestamps
4. **Error Recovery**: Save error state with retry button
5. **Multi-Tab Sync**: Sync state across browser tabs
6. **Progress Analytics**: Show time per step for optimization

## Version
- **Added in**: v3.6.0
- **Date**: March 2024
- **Author**: VistralS2T Team

## Support

For issues or questions:
1. Check browser console for localStorage errors
2. Verify browser supports localStorage API
3. Clear localStorage if state becomes corrupted: `localStorage.clear()`
4. Check that processing continues in backend (terminal logs)

---

**Note**: This enhancement is production-ready and has been tested with various scenarios including page refresh, browser close/reopen, and error conditions.
