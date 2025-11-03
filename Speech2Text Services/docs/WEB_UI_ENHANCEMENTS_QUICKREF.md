# Web UI Enhancements - Quick Reference

## 🎯 What's New

### 1. State Persistence (localStorage)
**Problem Solved**: Users lost progress when accidentally refreshing the page during long transcriptions.

**Solution**:
- ✅ Auto-saves processing state every progress update
- ✅ Restores state on page reload (if < 1 hour old)
- ✅ Shows notification: "🔄 Session restored! Continue where you left off."
- ✅ Preserves complete results after processing finishes

**Technical**:
```javascript
// State saved to: localStorage['vistral_s2t_state']
{
    status: 'processing' | 'complete',
    sessionId: 'session_20240315_143052',
    timestamp: 1710512452000,
    progress: { step: 'whisper', progress: 65, message: '...' },
    results: { /* full results */ }
}
```

### 2. Model Metadata Display
**Problem Solved**: Users had no visibility into which AI models processed their audio.

**Solution**:
- 🤖 **Whisper large-v3** - Speech recognition (English-optimized)
- 🇻🇳 **PhoWhisper-large** - Vietnamese-optimized transcription
- ✨ **Qwen2.5-1.5B** - Text enhancement and formatting
- 🔍 **pyannote.audio 3.1** - Speaker diarization

**Display**:
```
📊 Processing Information
┌─────────────────────────────────────────┐
│ 🤖 AI Models Used                       │
│ [Whisper: large-v3] [PhoWhisper: large] │
│ [Qwen: 2.5-1.5B] [Diarization: 3.1]    │
└─────────────────────────────────────────┘
```

### 3. Processing Metrics
**New Information Shown**:
- ⏱️ **Processing Time**: Total time from upload to completion (in minutes)
- 🆔 **Session ID**: Unique identifier for debugging/tracking
- 📅 **Completed At**: Timestamp with local timezone
- 🔄 **Session Recovery**: Badge if restored from localStorage

## 📋 Usage Scenarios

### Scenario 1: Normal Processing
```
User uploads audio → Processing starts → Completes
                      ↓
                 State saved every update
                      ↓
            Results shown with metadata
```

### Scenario 2: Accidental Refresh During Processing
```
User uploads audio → Processing at 65% → User refreshes page
                                             ↓
                                    localStorage restored
                                             ↓
                        UI shows: "🔄 Session restored!"
                                             ↓
                        Progress continues from 65%
```

### Scenario 3: Return After Closing Browser
```
Processing completes → User closes browser → User returns (< 1 hour)
                                                      ↓
                                            Results restored from localStorage
                                                      ↓
                                    Shows: "✅ Previous results restored!"
```

## 🎨 Visual Changes

### Before Enhancement:
```
┌─────────────────────────────────┐
│ ✅ Processing Complete!         │
│ Duration: 45.2s | Speakers: 2   │
│                                 │
│ 📄 Timeline Transcript          │
│ [Text content...]               │
│                                 │
│ ✨ Enhanced Transcript          │
│ [Text content...]               │
└─────────────────────────────────┘
```

### After Enhancement:
```
┌─────────────────────────────────┐
│ 📊 Processing Information       │  ← NEW CARD
│ 🤖 AI Models Used               │
│ [Whisper] [PhoWhisper]          │
│ [Qwen] [Diarization]            │
│                                 │
│ Session ID: session_20240315... │
│ Completed At: Oct 27, 11:32 AM │
│ Processing Time: 3.2 minutes    │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ ✅ Processing Complete!         │
│ Duration: 45.2s | Speakers: 2   │
│ ...                             │
└─────────────────────────────────┘
```

## 🔧 Configuration

### Adjust State Expiration (default: 1 hour)
Edit `app/templates/index.html` line ~467:
```javascript
if (Date.now() - state.timestamp < 3600000) {  // 1 hour
```

**Common Values**:
- 30 minutes: `1800000`
- 2 hours: `7200000`
- 24 hours: `86400000`

### Clear Saved State (Browser Console)
```javascript
localStorage.removeItem('vistral_s2t_state');
// or
localStorage.clear();
```

## 📊 Metadata Object Structure

### Frontend adds:
```javascript
metadata: {
    models: {
        whisper: 'large-v3',
        phowhisper: 'vinai/PhoWhisper-large',
        qwen: 'Qwen/Qwen2.5-1.5B-Instruct',
        diarization: 'pyannote/speaker-diarization-3.1'
    },
    completedAt: '2024-10-27T11:32:45.123Z'
}
```

### Backend provides:
```python
results = {
    'session_id': 'session_20241027_113245',
    'duration': 45.2,
    'num_speakers': 2,
    'num_segments': 15,
    'timeline': '...',
    'enhanced': '...',
    'processingTime': 192.5  # seconds
}
```

## 🐛 Troubleshooting

### State Not Restoring?
1. Check browser console for errors
2. Verify localStorage is enabled: `console.log(localStorage)`
3. Check state: `console.log(localStorage.getItem('vistral_s2t_state'))`
4. Verify timestamp: State expires after 1 hour

### Models Not Showing?
- Check browser console for JavaScript errors
- Verify metadata object in results: `console.log(data.metadata)`
- Refresh page to reload JavaScript

### Processing Time Shows as `null`?
- Backend needs restart to apply changes
- Check `web_ui.py` has `processingTime` in results
- Verify `import time` at top of `process_audio_with_diarization()`

## ✅ Testing Checklist

- [x] Upload audio, verify metadata displays
- [x] Refresh during processing, verify restoration
- [x] Complete processing, close tab, reopen, verify results
- [x] Wait > 1 hour, verify state expired
- [x] Test with localStorage disabled (graceful degradation)
- [x] Test on mobile device (responsive)
- [x] Test all 4 model badges display
- [x] Verify processing time calculation
- [x] Test download buttons still work

## 📝 Files Modified

1. **app/templates/index.html** (+200 lines)
   - State persistence functions
   - Metadata display functions
   - Toast notifications
   - CSS animations

2. **app/web_ui.py** (+5 lines)
   - Processing time tracking
   - Added `processingTime` to results

3. **docs/WEB_UI_ENHANCEMENTS.md** (NEW)
   - Comprehensive documentation

4. **docs/WEB_UI_ENHANCEMENTS_QUICKREF.md** (THIS FILE)
   - Quick reference guide

## 🚀 Next Steps

**Recommended Enhancements**:
1. Add file size/format to metadata
2. Export session state as JSON
3. Session history with timestamps
4. Progress bar for each model step
5. Error state persistence with retry button

## 📞 Support

**Common Issues**:
- localStorage quota exceeded → Clear old data
- State becomes corrupted → `localStorage.clear()`
- Models not loading → Check backend logs

**Debugging**:
```javascript
// Check saved state
console.log(JSON.parse(localStorage.getItem('vistral_s2t_state')));

// Monitor state changes
window.addEventListener('storage', (e) => {
    if (e.key === 'vistral_s2t_state') {
        console.log('State updated:', e.newValue);
    }
});
```

---

**Version**: v3.6.0  
**Last Updated**: October 27, 2024  
**Status**: ✅ Production Ready
