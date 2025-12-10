# 🧠 AI Learning & Memory Feature

## Tính năng "AI học tập"
Cho phép lưu trữ các đoạn hội thoại quan trọng làm "bài học" mà AI có thể sử dụng lại trong các cuộc trò chuyện sau.

## Cách sử dụng

### 1. Lưu bài học mới
1. Click nút **"🧠 AI học tập"** ở thanh controls
2. Panel Memory sẽ hiện ra
3. Chat với AI như bình thường
4. Khi muốn lưu, click **"💾 Lưu chat này"**
5. Nhập tiêu đề cho bài học
6. (Optional) Nhập tags phân cách bằng dấu phẩy
7. Bài học được lưu vào `./ChatBot/data/memory/`

### 2. Sử dụng bài học đã lưu
1. Mở panel Memory bằng nút **"🧠 AI học tập"**
2. Tick checkbox các bài học muốn kích hoạt
3. Các bài học đã chọn sẽ được thêm vào **Knowledge Base** của AI
4. AI sẽ sử dụng kiến thức từ các bài học này khi trả lời

### 3. Quản lý bài học
- **Xem danh sách**: Mở panel Memory
- **Chọn/bỏ chọn**: Click checkbox
- **Xóa bài học**: Click nút 🗑️ bên cạnh bài học

## Cấu trúc Memory File

Mỗi memory được lưu dưới dạng JSON:

```json
{
  "id": "uuid-string",
  "title": "Tiêu đề bài học",
  "content": "Nội dung đầy đủ của conversation",
  "tags": ["tag1", "tag2"],
  "created_at": "2025-10-29T10:00:00",
  "updated_at": "2025-10-29T10:00:00"
}
```

## Ví dụ sử dụng

### Scenario 1: Dạy AI về dự án của bạn
```
1. Chat với AI về cấu trúc dự án, tech stack, coding conventions
2. Lưu conversation với title: "Dự án XYZ - Architecture"
3. Các lần sau, tick checkbox "Dự án XYZ" để AI nhớ context
```

### Scenario 2: Lưu kiến thức chuyên môn
```
1. Hỏi AI về một topic phức tạp (ví dụ: Docker networking)
2. AI giải thích chi tiết
3. Lưu với title: "Docker Networking Basics"
4. Sau này hỏi câu nâng cao, tick memory này để AI có context
```

### Scenario 3: Personal preferences
```
1. Nói với AI về coding style, preferences của bạn
2. Lưu với title: "My Coding Preferences"
3. Mỗi lần code, tick memory này để AI code theo style bạn
```

## API Endpoints

### POST /api/memory/save
Lưu memory mới
```json
{
  "title": "string",
  "content": "string",
  "tags": ["string"]
}
```

### GET /api/memory/list
Lấy danh sách tất cả memories

### GET /api/memory/get/<memory_id>
Lấy một memory cụ thể

### DELETE /api/memory/delete/<memory_id>
Xóa memory

### PUT /api/memory/update/<memory_id>
Cập nhật memory

## Lưu ý kỹ thuật

### Backend (app.py)
- Memories được inject vào **system prompt**
- Format: `=== KNOWLEDGE BASE ===`
- Hỗ trợ: Gemini, OpenAI, DeepSeek
- Không ảnh hưởng conversation history

### Frontend (index.html)
- `selectedMemories` - Set chứa IDs đã chọn
- `allMemories` - Array chứa tất cả memories
- Auto-load khi mở panel
- Checkbox state được maintain

### Storage
- Location: `./ChatBot/data/memory/`
- Format: JSON files
- Naming: `{uuid}.json`
- Encoding: UTF-8

## Lợi ích

1. **Persistent Knowledge** - AI nhớ thông tin lâu dài
2. **Multi-context** - Chọn nhiều bài học cùng lúc
3. **Reusable** - Dùng lại kiến thức cho nhiều chat khác nhau
4. **Organized** - Quản lý theo title và tags
5. **No token waste** - Chỉ load khi cần

## Best Practices

1. **Title rõ ràng**: Đặt tên dễ hiểu cho bài học
2. **Content focused**: Lưu những conversation có giá trị
3. **Use tags**: Phân loại bài học bằng tags
4. **Regular cleanup**: Xóa bài học không còn dùng
5. **Selective loading**: Chỉ tick những memory cần thiết

## Version
- **Added in**: v1.7.0
- **Date**: October 29, 2025
- **Status**: ✅ Implemented & Ready
