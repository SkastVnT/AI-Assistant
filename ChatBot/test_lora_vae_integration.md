# ✅ Kiểm tra tích hợp Lora và VAE trong ChatBot

## 📋 Checklist tích hợp

### Backend (Python/Flask) ✅
- [x] `get_loras()` method trong `sd_client.py`
- [x] `get_vaes()` method trong `sd_client.py`
- [x] API endpoint `/api/sd-loras` trong `app.py`
- [x] API endpoint `/api/sd-vaes` trong `app.py`
- [x] `txt2img()` hỗ trợ parameters: `lora_models`, `vae`
- [x] `img2img()` hỗ trợ parameters: `lora_models`, `vae`
- [x] `/api/generate-image` gửi `lora_models` và `vae`
- [x] `/api/img2img` gửi `lora_models` và `vae`
- [x] `/api/img2img-advanced` gửi `lora_models` và `vae`

### Frontend (HTML/JavaScript) ✅
- [x] UI Section: Lora Selection trong Text2Img tab
- [x] UI Section: VAE Selection trong Text2Img tab
- [x] UI Section: Lora Selection trong Img2Img tab
- [x] UI Section: VAE Selection trong Img2Img tab
- [x] Function: `loadLoras()` - Load danh sách Loras từ API
- [x] Function: `loadVaes()` - Load danh sách VAEs từ API
- [x] Function: `addLoraSelection()` - Thêm Lora selector động
- [x] Function: `addImg2imgLoraSelection()` - Thêm Lora cho Img2Img
- [x] Function: `getSelectedLoras()` - Lấy Loras đã chọn
- [x] Function: `getImg2imgSelectedLoras()` - Lấy Loras cho Img2Img
- [x] Auto-load Loras/VAEs khi mở modal
- [x] Send Lora/VAE parameters trong `generateImage()`
- [x] Send Lora/VAE parameters trong `generateImg2Img()`

---

## 🧪 Test Cases

### Test 1: Khởi động và Load Models
```yaml
Steps:
1. Start Stable Diffusion WebUI
2. Start ChatBot (python app.py)
3. Mở browser: http://localhost:5000
4. Click nút "🎨 Tạo ảnh"

Expected Result:
✅ Modal mở
✅ Console log: "Loaded X Lora models"
✅ Console log: "Loaded X VAE models"
✅ VAE dropdown có options
```

---

### Test 2: Text2Img với 1 Lora + VAE
```yaml
Steps:
1. Mở modal → Tab Text2Img
2. Chọn VAE: kl-f8-anime2
3. Click "➕ Thêm Lora"
4. Chọn Lora: DetailTweaker
5. Set Weight: 0.7
6. Prompt: "1girl, beautiful"
7. Click "🎨 Tạo ảnh"

Expected Result:
✅ Request gửi đến /api/generate-image
✅ Body có: lora_models: [{name: "DetailTweaker", weight: 0.7}]
✅ Body có: vae: "kl-f8-anime2"
✅ Ảnh được tạo với Lora + VAE
```

---

### Test 3: Text2Img với nhiều Loras
```yaml
Steps:
1. Click "➕ Thêm Lora" lần 1 → Chọn Lora A (0.8)
2. Click "➕ Thêm Lora" lần 2 → Chọn Lora B (0.6)
3. Click "➕ Thêm Lora" lần 3 → Chọn Lora C (0.5)
4. Generate

Expected Result:
✅ Request có 3 Loras trong array
✅ Prompt có: <lora:A:0.8> <lora:B:0.6> <lora:C:0.5>
✅ Ảnh được tạo thành công
```

---

### Test 4: Img2Img với Lora + VAE
```yaml
Steps:
1. Tab Img2Img
2. Upload ảnh
3. Extract features
4. Chọn VAE: kl-f8-anime2
5. Click "➕ Thêm Lora" → BetterHands (0.9)
6. Generate

Expected Result:
✅ Request gửi đến /api/img2img-advanced
✅ Body có lora_models và vae
✅ Ảnh Img2Img được tạo với Lora/VAE
```

---

### Test 5: Remove Lora
```yaml
Steps:
1. Thêm 2 Loras
2. Click nút ❌ ở Lora thứ 1
3. Generate

Expected Result:
✅ Lora đầu bị xóa khỏi UI
✅ Request chỉ có 1 Lora còn lại
```

---

### Test 6: VAE = Automatic (None)
```yaml
Steps:
1. VAE dropdown chọn "Automatic"
2. Generate

Expected Result:
✅ Request có: vae: null
✅ SD API dùng VAE mặc định
```

---

## 🐛 Kiểm tra Error Handling

### Test 7: SD WebUI không chạy
```yaml
Steps:
1. Tắt SD WebUI
2. Mở modal tạo ảnh
3. Click "➕ Thêm Lora"

Expected Result:
✅ Console log error: "Error loading loras"
✅ availableLoras = []
✅ Dropdown Lora trống hoặc có placeholder
✅ App không crash
```

---

### Test 8: Lora không tồn tại
```yaml
Steps:
1. Chọn Lora đã bị xóa khỏi folder
2. Generate

Expected Result:
✅ SD API bỏ qua Lora không tồn tại
✅ Vẫn tạo ảnh được (không crash)
```

---

## 🔍 Debug Checklist

### Nếu không thấy Loras trong dropdown:

```bash
# 1. Check SD WebUI đang chạy
curl http://127.0.0.1:7860/sdapi/v1/loras

# 2. Check API endpoint
curl http://localhost:5000/api/sd-loras

# 3. Check browser console (F12)
# → Xem có error khi call loadLoras() không

# 4. Check file Loras có trong folder không
ls "c:\Users\Asus\Downloads\Compressed\AI-Assistant\stable-diffusion-webui\models\Lora"
```

---

### Nếu Loras không có effect:

```python
# Check prompt có chứa <lora:name:weight> không
# Debug trong sd_client.py, thêm print:

def txt2img(self, ..., lora_models=None, ...):
    final_prompt = prompt
    if lora_models:
        for lora in lora_models:
            lora_name = lora.get('name', '')
            lora_weight = lora.get('weight', 1.0)
            final_prompt = f"<lora:{lora_name}:{lora_weight}> {final_prompt}"
    
    print(f"[DEBUG] Final prompt with Loras: {final_prompt}")  # <-- ADD THIS
    
    payload = {
        "prompt": final_prompt,
        ...
    }
```

---

### Nếu VAE không có effect:

```python
# Check override_settings được gửi không
# Debug trong sd_client.py:

if vae:
    payload["override_settings"] = {
        "sd_vae": vae
    }
    print(f"[DEBUG] VAE override: {vae}")  # <-- ADD THIS
```

---

## 🎯 Manual Test Script

Chạy script này để test API trực tiếp:

```python
import requests
import json

# Test get Loras
print("Testing /api/sd-loras...")
response = requests.get('http://localhost:5000/api/sd-loras')
print(f"Status: {response.status_code}")
print(f"Loras: {len(response.json().get('loras', []))}")
print()

# Test get VAEs
print("Testing /api/sd-vaes...")
response = requests.get('http://localhost:5000/api/sd-vaes')
print(f"Status: {response.status_code}")
print(f"VAEs: {len(response.json().get('vaes', []))}")
print()

# Test generate with Lora + VAE
print("Testing /api/generate-image with Lora + VAE...")
payload = {
    "prompt": "1girl, beautiful",
    "negative_prompt": "bad quality",
    "width": 512,
    "height": 512,
    "steps": 20,
    "cfg_scale": 7,
    "lora_models": [
        {"name": "DetailTweaker", "weight": 0.7}
    ],
    "vae": "kl-f8-anime2.safetensors"
}

response = requests.post(
    'http://localhost:5000/api/generate-image',
    json=payload,
    timeout=300
)

print(f"Status: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print(f"Success: {result.get('success')}")
    print(f"Images: {len(result.get('images', []))}")
else:
    print(f"Error: {response.json()}")
```

---

## ✅ Kết luận

**TẤT CẢ ĐÃ ĐƯỢC TÍCH HỢP ĐẦY ĐỦ!**

### Các tính năng hoạt động:
- ✅ Load danh sách Loras từ SD WebUI
- ✅ Load danh sách VAEs từ SD WebUI
- ✅ Dynamic thêm/xóa Lora selections
- ✅ Chọn weight cho từng Lora (0.0 - 2.0)
- ✅ Chọn 1 VAE (hoặc Automatic)
- ✅ Text2Img với Lora + VAE
- ✅ Img2Img với Lora + VAE
- ✅ Multiple Loras support (nhiều Loras cùng lúc)
- ✅ Auto-apply Lora syntax: `<lora:name:weight>`
- ✅ VAE override qua `override_settings`

### Để sử dụng:
1. ✅ Start SD WebUI
2. ✅ Start ChatBot
3. ✅ Mở modal tạo ảnh
4. ✅ Chọn Loras và VAE
5. ✅ Generate!

---

**🎨 Enjoy creating beautiful images with Loras and VAEs! ✨**
