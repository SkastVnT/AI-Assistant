# Tính năng Xem ảnh phóng to & Lịch sử chỉnh sửa

## 📅 Ngày cập nhật: 30/10/2025

## 🎯 Tổng quan

Đã thêm 2 tính năng mới vào chatbot:
1. **Xem ảnh phóng to kiểu Discord** - Bấm vào ảnh để xem ở kích thước lớn hơn
2. **Lịch sử chỉnh sửa tin nhắn** - Xem tất cả các phiên bản trước của tin nhắn đã chỉnh sửa

---

## ✨ Tính năng 1: Xem ảnh phóng to (Discord-style)

### Mô tả
- Khi có ảnh trong chat (từ tạo ảnh hoặc tool text-to-image), bạn có thể bấm vào ảnh để phóng to
- Modal hiển thị ảnh ở kích thước lớn với background tối (giống Discord)
- Hiển thị thông tin ảnh: tên + kích thước

### Cách sử dụng
1. Khi có ảnh xuất hiện trong chat, di chuột vào sẽ thấy con trỏ đổi thành 🔍 (zoom-in)
2. Bấm vào ảnh để mở modal xem phóng to
3. Đóng modal bằng cách:
   - Bấm nút ✕ ở góc trên bên phải
   - Bấm vào vùng tối bên ngoài ảnh
   - Nhấn phím ESC

### Tính năng kỹ thuật
- **Responsive**: Ảnh tự động scale để vừa màn hình (max 90% width/height)
- **Animation**: Fade-in mượt mà khi mở modal
- **Keyboard support**: Đóng bằng phím ESC
- **Dark overlay**: Background tối 95% opacity để tập trung vào ảnh

---

## ✨ Tính năng 2: Lịch sử chỉnh sửa tin nhắn (giống ChatGPT)

### Mô tả
- Khi bạn chỉnh sửa một tin nhắn (edit), hệ thống tự động lưu phiên bản cũ
- Nút "📜 Xem lịch sử" xuất hiện sau khi edit lần đầu
- Có thể xem tất cả các phiên bản của một tin nhắn đã edit
- **NEW**: Có thể khôi phục (restore) phiên bản cũ và tiếp tục chat từ đó (branch conversation)

### Cách sử dụng

#### Chỉnh sửa tin nhắn:
1. Bấm nút "✏️ Edit" ở tin nhắn của user
2. Chỉnh sửa nội dung
3. Bấm "💾 Lưu & Tạo lại response"
4. Tin nhắn được cập nhật và AI tạo response mới

#### Xem lịch sử:
1. Sau khi edit, nút "📜 Xem lịch sử" sẽ xuất hiện bên cạnh nút Edit
2. Bấm vào để mở modal hiển thị tất cả phiên bản
3. Modal hiển thị:
   - **Phiên bản hiện tại** (đánh dấu ✅)
   - **Các phiên bản trước** (theo thứ tự mới nhất → cũ nhất)
   - Thời gian của mỗi phiên bản
   - Nút **"↩️ Khôi phục & Chat từ đây"** cho mỗi phiên bản cũ

#### Khôi phục phiên bản cũ (Branch Conversation):
1. Trong modal lịch sử, chọn phiên bản muốn quay lại
2. Bấm nút "↩️ Khôi phục & Chat từ đây"
3. Xác nhận trong dialog
4. Hệ thống sẽ:
   - Lưu phiên bản hiện tại vào lịch sử
   - Khôi phục nội dung phiên bản cũ
   - Xóa tất cả tin nhắn sau tin nhắn đó
   - Tạo response mới từ AI
5. Bạn có thể tiếp tục chat từ phiên bản cũ này (tạo nhánh mới)

### Các tính năng kỹ thuật
- **Tự động lưu**: Mỗi lần edit, phiên bản hiện tại được lưu tự động
- **Không giới hạn số lần edit**: Có thể edit nhiều lần, mỗi lần đều được lưu lại
- **Timestamp**: Mỗi phiên bản có ghi nhận thời gian chỉnh sửa chính xác
- **Visual hierarchy**: 
  - Phiên bản hiện tại: viền xanh lá + icon ✅
  - Phiên bản cũ: viền tím + icon 📝
- **Markdown support**: Nội dung cũ cũng được render với markdown

---

## 🎨 Giao diện

### Image Preview Modal
```
┌────────────────────────────────────────────┐
│                    ✕                       │
│                                           │
│                                           │
│            [     IMAGE      ]             │
│                                           │
│                                           │
│     ┌─────────────────────────────┐      │
│     │ filename.png • 1024 x 768   │      │
│     └─────────────────────────────┘      │
└────────────────────────────────────────────┘
```

### History Modal (với tính năng Restore)
```
┌─────────────────────────────────────────────────┐
│  📜 Lịch sử chỉnh sửa              [Đóng]      │
├─────────────────────────────────────────────────┤
│ Tổng số phiên bản: 3                           │
│ 💡 Bấm "↩️ Khôi phục" để quay lại phiên bản cũ │
│                                                 │
│ ┌─────────────────────────────────────────────┐│
│ │ ✅ Phiên bản hiện tại                      ││
│ │ [nội dung hiện tại]                        ││
│ └─────────────────────────────────────────────┘│
│                                                 │
│ ┌─────────────────────────────────────────────┐│
│ │ 📝 Phiên bản 2 - 30/10/2025 10:33          ││
│ │ [nội dung cũ 2]                            ││
│ │ [↩️ Khôi phục & Chat từ đây]               ││
│ └─────────────────────────────────────────────┘│
│                                                 │
│ ┌─────────────────────────────────────────────┐│
│ │ 📝 Phiên bản 1 - 30/10/2025 10:30          ││
│ │ [nội dung cũ 1]                            ││
│ │ [↩️ Khôi phục & Chat từ đây]               ││
│ └─────────────────────────────────────────────┘│
└─────────────────────────────────────────────────┘
```

---

## 🔧 Chi tiết kỹ thuật

### CSS Classes mới
- `.image-preview-modal` - Container cho modal xem ảnh
- `.image-preview-content` - Ảnh được phóng to
- `.image-preview-close` - Nút đóng modal
- `.image-preview-info` - Thông tin ảnh (tên, kích thước)
- `.message-history-btn` - Nút xem lịch sử
- `.history-modal` - Container cho modal lịch sử
- `.history-modal-content` - Nội dung modal lịch sử
- `.history-version` - Một phiên bản trong lịch sử
- `.history-version-header` - Header của mỗi phiên bản

### JavaScript Functions mới
- `openImagePreview(imgElement)` - Mở modal xem ảnh
- `closeImagePreview()` - Đóng modal xem ảnh
- `makeImagesClickable()` - Gắn event click vào tất cả ảnh
- `addMessageVersion(messageId, content, timestamp)` - Lưu phiên bản vào lịch sử
- `showMessageHistory(messageId)` - Hiển thị modal lịch sử
- `closeHistoryModal()` - Đóng modal lịch sử
- **`restoreVersion(messageId, versionIndex)`** - Khôi phục phiên bản cũ và tạo branch mới

### Data Structures
```javascript
// Map lưu lịch sử: messageId -> array of versions
messageHistory = Map {
  "msg_123": [
    { content: "...", timestamp: "2025-10-30T10:30:00" },
    { content: "...", timestamp: "2025-10-30T10:33:00" }
  ]
}
```

---

## 🌙 Dark Mode Support

Cả 2 tính năng đều hỗ trợ đầy đủ dark mode:
- Image preview: Background tối hơn (95% opacity)
- History modal: Nền đen, text trắng, borders tối
- Buttons: Màu sắc thích nghi với dark mode

---

## 🎯 Use Cases

### Xem ảnh phóng to
1. **Xem chi tiết ảnh AI đã tạo**: Kiểm tra chất lượng, chi tiết ảnh
2. **Screenshot/diagram**: Xem rõ hơn các sơ đồ, code snippets trong ảnh
3. **So sánh ảnh**: Phóng to nhiều ảnh để so sánh

### Lịch sử chỉnh sửa
1. **So sánh các phiên bản**: Xem câu hỏi cũ vs mới
2. **Phục hồi nội dung**: Nhớ lại câu hỏi trước khi edit
3. **Tracking changes**: Theo dõi quá trình tinh chỉnh câu hỏi
4. **Learning**: Xem cách thay đổi câu hỏi ảnh hưởng đến câu trả lời

### Branch Conversation (Khôi phục phiên bản)
1. **Thử nhiều hướng khác nhau**: Edit câu hỏi, không thích response? Quay lại thử cách khác
2. **A/B Testing**: So sánh response từ 2 cách hỏi khác nhau
3. **Undo powerful**: Không chỉ undo, mà còn tạo nhánh mới từ bất kỳ điểm nào
4. **Experiment safely**: Thử nghiệm mà không sợ mất conversation cũ
5. **Multiple storylines**: Tạo nhiều nhánh chat khác nhau từ một điểm

---

## 📱 Responsive Design

### Desktop
- Image preview: Tối đa 90% viewport
- History modal: Tối đa 800px width, 80% height

### Mobile
- Image preview: Tự động scale theo màn hình nhỏ
- History modal: 90% width, có thể scroll

---

## ⌨️ Keyboard Shortcuts

- **ESC**: Đóng image preview hoặc history modal
- **Click outside**: Đóng cả 2 loại modal

---

## 🔄 Integration với các tính năng khác

### Tương thích với:
- ✅ Image Generation Tool
- ✅ Text-to-Image conversion
- ✅ File uploads
- ✅ PDF Export
- ✅ Memory System
- ✅ Chat History
- ✅ Dark Mode

### Auto-initialization:
- Tất cả ảnh mới được tự động thêm event listener
- Override `addMessage()` để apply tự động khi có message mới
- Load chat cũ cũng được re-apply event listeners

---

## 🐛 Known Limitations

### Image Preview:
- Chỉ hoạt động với ảnh trong `.message-content img`
- Không áp dụng cho ảnh trong modal khác (image generation modal)

### History:
- Lịch sử chỉ lưu trong session (không persist qua reload page)
- Chỉ áp dụng cho user messages (không áp dụng cho AI responses)

---

## 🚀 Future Enhancements

### Có thể thêm:
1. **Image preview**: 
   - Zoom in/out với mouse wheel
   - Pan/drag ảnh khi đã zoom
   - Download button trong modal
   - Gallery view (prev/next buttons)

2. **History**:
   - Persist lịch sử vào localStorage
   - Export/import history
   - ~~Restore phiên bản cũ trực tiếp~~ ✅ **ĐÃ CÓ**
   - Diff view (highlight changes giữa các phiên bản)
   - Visual tree view (xem cấu trúc branch như git)
   - Merge branches (kết hợp 2 nhánh chat)

---

## 📝 Notes

- Code được thêm vào cuối file `index.html` trước tag `</body>`
- CSS được thêm vào cuối block `<style>` trước tag `</style>`
- Không cần thay đổi backend code
- Hoàn toàn frontend-based features
