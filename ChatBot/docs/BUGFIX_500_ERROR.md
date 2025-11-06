# 🐛 Bug Fix: POST /chat 500 Error

## ❌ Problem

```
[04/Nov/2025 12:53:53] "POST /chat HTTP/1.1" 500 -
```

## 🔍 Root Cause

**Mismatch between client and server data format:**
- **Client** (`api-service.js`): Sending `FormData` (multipart/form-data)
- **Server** (`app.py`): Expecting `request.json` (application/json)

This caused Flask to fail when trying to parse `request.json` from a FormData request.

## ✅ Solution Applied

### 1. **Fixed `api-service.js`**
   - Now sends **JSON** when there are no files
   - Uses **FormData** only when files are attached
   - Properly sets `Content-Type: application/json` header

### 2. **Updated `app.py`**
   - Now handles **both** JSON and FormData requests
   - Checks `Content-Type` header to determine format
   - Properly parses FormData fields and files

## 📝 Code Changes

### `static/js/modules/api-service.js`

**Before:**
```javascript
async sendMessage(message, model, context, tools = [], ...) {
    const formData = new FormData();
    formData.append('message', message);
    // Always sent FormData
    
    const response = await fetch('/chat', {
        method: 'POST',
        body: formData  // ❌ Always multipart
    });
}
```

**After:**
```javascript
async sendMessage(message, model, context, tools = [], ...) {
    if (files && files.length > 0) {
        // Use FormData for file uploads
        const formData = new FormData();
        // ... append fields
        response = await fetch('/chat', {
            method: 'POST',
            body: formData
        });
    } else {
        // Use JSON for text-only
        response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ... })  // ✅ JSON format
        });
    }
}
```

### `app.py`

**Before:**
```python
@app.route('/chat', methods=['POST'])
def chat():
    data = request.json  # ❌ Only handled JSON
    message = data.get('message', '')
    # ...
```

**After:**
```python
@app.route('/chat', methods=['POST'])
def chat():
    # Check content type
    if 'multipart/form-data' in request.content_type:
        # ✅ Handle FormData
        data = request.form
        tools = json.loads(data.get('tools', '[]'))
        files = request.files.getlist('files')
    else:
        # ✅ Handle JSON
        data = request.json
        tools = data.get('tools', [])
    
    message = data.get('message', '')
    # ...
```

## 🧪 Testing

### Test 1: Text-only chat (JSON)
1. Open http://localhost:5000
2. Type: "Hello AI"
3. Click "Gửi"
4. ✅ Should work - sends JSON

### Test 2: Chat with file upload (FormData)
1. Click 📎 (attach file)
2. Select an image
3. Type: "What's in this image?"
4. Click "Gửi"
5. ✅ Should work - sends FormData

### Test 3: Chat with tools (JSON)
1. Click 🌐 (Google Search)
2. Type: "Current weather"
3. Click "Gửi"
4. ✅ Should work - sends JSON with tools array

## 📊 Status

| Component | Status | Notes |
|-----------|--------|-------|
| `api-service.js` | ✅ Fixed | Smart format detection |
| `app.py` | ✅ Fixed | Handles both formats |
| Error 500 | ✅ Resolved | Should work now |

## 🚀 Next Steps

1. **Restart Flask server** (if still running old code):
   ```powershell
   # Stop current server (Ctrl+C)
   # Then restart:
   python app.py
   ```

2. **Clear browser cache** (to load new JS):
   ```
   Ctrl + Shift + Delete → Clear cache
   or
   Ctrl + Shift + R (hard reload)
   ```

3. **Test the fix**:
   - Send a simple text message
   - Should get response without 500 error
   - Check browser console (F12) for any errors

## 🐛 If Still Not Working

### Check Flask Logs
Look for detailed error in terminal where `python app.py` is running:
```
Traceback (most recent call last):
  File "...", line X, in chat
    ...
```

### Check Browser Console (F12)
```javascript
// Should see:
POST http://localhost:5000/chat 200 OK

// Not:
POST http://localhost:5000/chat 500 Internal Server Error
```

### Enable Debug Mode
In `app.py`, at the bottom:
```python
if __name__ == '__main__':
    app.run(debug=True, port=5000)  # debug=True for detailed errors
```

## 📞 Common Errors After Fix

### "Cannot read property 'get' of null"
**Cause:** `request.json` is None  
**Fix:** Already handled - checks content type first

### "TypeError: string indices must be integers"
**Cause:** Trying to parse string as dict  
**Fix:** Use `json.loads()` for FormData strings

### "KeyError: 'message'"
**Cause:** Missing required field  
**Fix:** Already handled - uses `.get()` with defaults

---

**Fix Applied:** November 4, 2025  
**Files Modified:** 
- `static/js/modules/api-service.js`
- `app.py`

The error should now be resolved! 🎉
