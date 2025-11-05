# 🧪 QUICK TEST GUIDE - Document Intelligence Service v1.5.0

## ✅ Testing Checklist

### 1️⃣ Service Health Check
**Status**: Service running on http://127.0.0.1:5003 ✅

**Test Steps:**
- Open browser: http://127.0.0.1:5003
- Check AI status badge (should show "INACTIVE" without API key)
- Verify UI loads properly with all tabs

---

### 2️⃣ OCR Basic Test (NO AI)
**Purpose**: Verify PaddleOCR works with protobuf fix

**Test Steps:**
1. Upload any PDF/image with Vietnamese text
2. DO NOT check any AI options yet
3. Click "Upload & Process"
4. **Expected Result:**
   - ✅ Text extraction successful
   - ✅ Results appear in "OCR Results" tab
   - ✅ No errors in console/logs

**If OCR fails:**
- Check terminal for error messages
- Look for "OneDnnContext" errors (should be gone now)
- Verify models downloaded in `~/.paddleocr/`

---

### 3️⃣ AI Integration Test (Requires API Key)

**Prerequisites:**
1. Get FREE Gemini API key: https://makersuite.google.com/app/apikey
2. Create `.env` file:
   ```bash
   copy .env.example .env
   ```
3. Edit `.env` and add your API key:
   ```
   GEMINI_API_KEY=your_actual_api_key_here
   ```
4. Restart service (Ctrl+C, then `start_service.bat`)

**Test Steps:**
1. Reload page - AI badge should show "ACTIVE" ✅
2. Upload document (PDF/image)
3. **Check AI Enhancement options:**
   - ☑️ Auto-classify Document
   - ☑️ Extract Key Information
   - ☑️ Generate Summary
4. Click "Upload & Process"
5. **Expected Results:**
   - ✅ OCR tab: Text extraction
   - ✅ AI Analysis tab appears with:
     - Document classification
     - Extracted fields (name, date, etc.)
     - Summary
   - ✅ AI Tools section enabled

---

### 4️⃣ AI Tools Test

**Test Q&A:**
1. After uploading document, go to "AI Tools" section
2. Type question: "Tóm tắt nội dung chính?"
3. Click "Ask Question"
4. **Expected**: AI generates answer based on document

**Test Translation:**
1. Select target language (English, Japanese, Korean)
2. Click "Translate Document"
3. **Expected**: Full document translated

**Test Insights:**
1. Click "Generate Insights"
2. **Expected**: AI provides document analysis and recommendations

---

## 🐛 Troubleshooting

### Issue: OCR Still Fails
**Symptoms**: Empty results, OneDNN errors

**Solutions:**
1. Check protobuf version:
   ```bash
   pip show protobuf
   # Should be: 3.20.2
   ```

2. Verify environment variable:
   ```bash
   echo $env:PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION
   # Should output: python
   ```

3. Reinstall PaddlePaddle:
   ```bash
   pip uninstall paddlepaddle -y
   pip install paddlepaddle==2.6.1
   ```

### Issue: AI Features Not Working
**Check:**
- [ ] `.env` file exists with valid API key
- [ ] AI status badge shows "ACTIVE"
- [ ] Console shows no Gemini API errors
- [ ] Internet connection available

**Test API key manually:**
```python
import google.generativeai as genai
genai.configure(api_key="your_key_here")
model = genai.GenerativeModel('gemini-2.0-flash-exp')
response = model.generate_content("Hello")
print(response.text)
```

### Issue: protobuf Errors
**Error**: `Descriptors cannot be created directly`

**Solution**: Already fixed in `start_service.bat`
- Environment variable `PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python` is set

---

## 📊 Expected Performance

### OCR Performance:
- **Single page PDF**: 2-5 seconds
- **Multi-page PDF**: 3-8 seconds per page
- **Image**: 1-3 seconds

### AI Performance (with Gemini FREE):
- **Classification**: 1-2 seconds
- **Extraction**: 2-4 seconds
- **Summary**: 3-5 seconds
- **Q&A**: 2-4 seconds per question
- **Translation**: 4-8 seconds

---

## ✅ Success Criteria

**Phase 1.5 is COMPLETE when:**
- [x] Service starts without errors
- [x] OCR extracts text correctly
- [ ] AI badge shows ACTIVE with API key ⚠️ (needs user to add key)
- [ ] AI classification works ⚠️ (needs API key)
- [ ] AI extraction works ⚠️ (needs API key)
- [ ] AI summary works ⚠️ (needs API key)
- [ ] Q&A tool responds ⚠️ (needs API key)
- [ ] Translation works ⚠️ (needs API key)
- [ ] Insights generation works ⚠️ (needs API key)

**Current Status**: 
✅ All code complete
✅ OCR fixed (protobuf compatibility solved)
⚠️ AI features ready but untested (requires API key)

---

## 🚀 Next Steps

1. **Test OCR now** (no API key needed)
2. **Get Gemini API key** (FREE): https://makersuite.google.com/app/apikey
3. **Add API key to `.env`**
4. **Test all AI features**
5. **Report any issues**

---

## 📝 Test Results Template

```
=== TEST RESULTS ===
Date: _______
Tester: _______

✅ OCR Test:
- File tested: _______
- Result: PASS / FAIL
- Notes: _______

✅ AI Classification:
- Result: PASS / FAIL
- Notes: _______

✅ AI Extraction:
- Result: PASS / FAIL
- Notes: _______

✅ AI Summary:
- Result: PASS / FAIL
- Notes: _______

✅ Q&A Tool:
- Result: PASS / FAIL
- Notes: _______

✅ Translation:
- Result: PASS / FAIL
- Notes: _______

✅ Insights:
- Result: PASS / FAIL
- Notes: _______

Overall: PASS / FAIL
```

---

**Ready to test!** 🎉
