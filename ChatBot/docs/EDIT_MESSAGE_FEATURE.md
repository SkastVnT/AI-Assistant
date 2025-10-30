# Tính năng Edit Message & Re-Response

## Mô tả
Tính năng cho phép người dùng chỉnh sửa tin nhắn đã gửi và tạo lại response từ AI với nội dung đã được chỉnh sửa, đồng thời giữ nguyên lịch sử chat trước đó.

## Cách sử dụng

### 1. Edit tin nhắn
- Mỗi tin nhắn của người dùng có nút **"✏️ Edit"**
- Click vào nút Edit để hiển thị form chỉnh sửa
- Nhập nội dung mới vào textarea
- Click **"💾 Lưu & Tạo lại response"** hoặc **"❌ Hủy"**

### 2. Khi lưu tin nhắn đã edit
- Tin nhắn gốc được cập nhật với nội dung mới
- Tất cả tin nhắn **sau** tin nhắn được edit sẽ bị xóa
- AI sẽ tạo lại response mới dựa trên:
  - Lịch sử chat **trước** tin nhắn được edit
  - Nội dung tin nhắn **sau khi edit**

### 3. Lưu ý
- Tính năng này cho phép "rewind" cuộc hội thoại
- Các response cũ sau tin nhắn được edit sẽ mất
- Model và context được sử dụng từ tin nhắn gốc (hoặc settings hiện tại)

## Ví dụ sử dụng

### Scenario 1: Sửa lỗi chính tả
```
User: Cho tôi biết về Python languge
AI: Python là ngôn ngữ lập trình...

[User clicks Edit on their message]
User (edited): Cho tôi biết về Python language
[AI generates new response based on corrected message]
```

### Scenario 2: Thay đổi câu hỏi
```
User: Viết code Python đọc file CSV
AI: [Code example for CSV]

[User clicks Edit]
User (edited): Viết code Python đọc file Excel
[AI generates new response for Excel instead]
```

### Scenario 3: Thêm chi tiết
```
User: Tạo một function
AI: [Basic function example]

[User clicks Edit]
User (edited): Tạo một function với error handling và logging
[AI generates new response with added requirements]
```

## Technical Details

### Frontend (index.html)
- **CSS Classes:**
  - `.edit-message-btn` - Nút Edit cho user messages
  - `.edit-form` - Form chỉnh sửa tin nhắn
  - `.edit-save-btn`, `.edit-cancel-btn` - Nút Save/Cancel

- **JavaScript Functions:**
  - `showEditForm(messageDiv, originalContent)` - Hiển thị form edit
  - `handleEditSave(messageDiv, newContent, originalContent)` - Xử lý khi save
  - Gửi history trước tin nhắn được edit đến backend

### Backend (app.py)
- **Updated Methods:**
  - `chat_with_gemini()` - Thêm param `history`
  - `chat_with_openai()` - Thêm param `history`
  - `chat_with_deepseek()` - Thêm param `history`
  - `chat()` - Xử lý history parameter

- **API Endpoint:**
  - `POST /chat` - Thêm field `history` (optional)
  ```json
  {
    "message": "edited message",
    "model": "gemini",
    "context": "casual",
    "deep_thinking": false,
    "history": [
      {"role": "user", "content": "..."},
      {"role": "assistant", "content": "..."}
    ]
  }
  ```

## Lợi ích
1. **Sửa lỗi dễ dàng** - Không cần gửi lại tin nhắn mới
2. **Thử nghiệm** - Test các phiên bản khác nhau của câu hỏi
3. **Tinh chỉnh** - Thêm chi tiết hoặc làm rõ yêu cầu
4. **Tiết kiệm thời gian** - Không cần bắt đầu cuộc hội thoại mới

## UI/UX
- **Edit button**: Màu cam (#ffa500) để dễ nhận biết
- **Edit form**: Có border màu cam, nổi bật trên message
- **Save button**: Màu xanh lá với icon 💾
- **Cancel button**: Màu xám với icon ❌
- **Loading state**: Hiển thị spinner khi đang generate response mới

## Tương thích
- ✅ Hoạt động với tất cả models (Gemini, OpenAI, DeepSeek, etc.)
- ✅ Hỗ trợ Dark Mode
- ✅ Responsive design (mobile-friendly)
- ✅ Tích hợp với chat history và localStorage
- ✅ Hoạt động với Deep Thinking mode

## Version
- **Added in**: v1.6.0
- **Date**: October 29, 2025
- **Status**: ✅ Implemented & Tested
