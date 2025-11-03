# Test Image Preview Feature

## Cách test:

### 1. Khởi động chatbot
```bash
cd ChatBot
python app.py
```

### 2. Mở browser và vào http://localhost:5000

### 3. Test với ảnh
Có 3 cách test:

#### Option A: Tạo ảnh bằng Image Generator
1. Bấm nút "🎨 Tạo ảnh"
2. Nhập prompt: "a cute cat"
3. Generate
4. Khi ảnh xuất hiện trong chat, click vào ảnh
5. ✅ Modal phải hiện lên với ảnh phóng to

#### Option B: Upload ảnh
1. Bấm "📎 Upload Files"
2. Chọn một file ảnh (.jpg, .png)
3. Gửi tin nhắn
4. Click vào ảnh trong chat
5. ✅ Modal phải hiện lên

#### Option C: Paste ảnh
1. Copy một ảnh (Ctrl+C)
2. Paste vào khung chat (Ctrl+V)
3. Gửi tin nhắn
4. Click vào ảnh trong chat
5. ✅ Modal phải hiện lên

### 4. Kiểm tra các tính năng của modal:

✅ **Modal phải có:**
- Background đen tối (95% opacity)
- Ảnh ở giữa màn hình
- Nút ✕ ở góc trên phải (màu trắng)
- Thông tin ảnh ở dưới (tên • width x height)

✅ **Đóng modal bằng:**
- Bấm nút ✕
- Click vào vùng tối bên ngoài ảnh
- Nhấn phím ESC

✅ **Cursor:**
- Hover vào ảnh trong chat: cursor = zoom-in (🔍)
- Hover vào modal: cursor = zoom-out

### 5. Xem Console logs
Mở Developer Tools (F12) → Console tab

Bạn sẽ thấy logs:
```
[Image Preview] Initializing event listeners...
[Image Preview] Modal click listener added
[Image Preview] Found X images
[Image Preview] Made clickable: http://...
[Image Preview] Image clicked: http://...
[Image Preview] Opening preview for: http://...
[Image Preview] Modal opened successfully
```

## Troubleshooting

### Nếu không hoạt động:

1. **Không có cursor zoom-in?**
   - Check console: có thấy "[Image Preview] Found X images"?
   - Nếu found 0 → ảnh chưa được render
   
2. **Click không có gì xảy ra?**
   - Check console: có thấy "[Image Preview] Image clicked"?
   - Nếu không → event listener chưa được attach
   
3. **Modal không hiện?**
   - Check console: có lỗi "[Image Preview] Modal not found"?
   - Check trong Elements tab (F12) xem có element `#imagePreviewModal` không
   
4. **Modal hiện nhưng không thấy ảnh?**
   - Check console: có log "[Image Preview] Opening preview"?
   - Check network tab xem ảnh có load được không

## Expected Results

### ✅ Success:
- Cursor thay đổi khi hover
- Click vào ảnh → modal xuất hiện
- Ảnh hiển thị rõ ràng ở giữa
- Có thể đóng modal bằng nhiều cách
- Smooth animation khi mở/đóng

### ❌ Fail:
- Click không có phản ứng
- Modal không hiện
- Ảnh không load
- Console có errors

## Debug Commands

```javascript
// Check if makeImagesClickable exists
console.log(typeof window.makeImagesClickable); // Should be "function"

// Check if modal exists
console.log(document.getElementById('imagePreviewModal')); // Should not be null

// Check images
console.log(document.querySelectorAll('.message-content img').length); // Should be > 0 if images exist

// Manually trigger
window.makeImagesClickable();
```
