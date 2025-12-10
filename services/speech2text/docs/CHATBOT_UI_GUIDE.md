# 🎙️ Speech2Text ChatBot-Style UI

## Tổng quan

Giao diện mới của Speech2Text được thiết kế theo phong cách ChatBot với trải nghiệm người dùng hiện đại, trực quan và đầy đủ tính năng.

## ✨ Tính năng chính

### 1. 📋 Sidebar - Quản lý phiên làm việc
- **Lịch sử phiên**: Xem và quản lý tất cả các phiên transcription đã thực hiện
- **Trạng thái phiên**: 
  - ⏳ Processing (Đang xử lý)
  - ✅ Completed (Hoàn thành)
  - ❌ Failed (Thất bại)
  - ⏹️ Cancelled (Đã hủy)
- **Tạo phiên mới**: Button "+ Mới" để bắt đầu transcription mới
- **Xóa phiên**: Click icon 🗑️ để xóa phiên cụ thể

### 2. 💾 Quản lý bộ nhớ
- **Hiển thị dung lượng**: Progress bar trực quan
- **Cảnh báo dung lượng**:
  - 🟢 OK: < 70%
  - 🟠 Warning: 70-90%
  - 🔴 Full: > 90%
- **Cleanup nhanh**: Button "🗑️ Dọn dọn" để xóa toàn bộ sessions

### 3. 🎛️ Điều khiển xử lý
- **Model Selection**:
  - Dual (Whisper + PhoWhisper) ⭐ - Khuyến nghị
  - Whisper Large v3
  - PhoWhisper (Vietnamese)
  
- **Enhancement**:
  - Qwen (AI Enhancement) - Cải thiện văn bản với AI
  - None (Raw Transcript) - Giữ nguyên văn bản gốc
  
- **Tùy chọn**:
  - ☑️ Phân tách người nói (Speaker Diarization)

### 4. 📤 Upload & Xử lý
- **Drag & Drop**: Kéo thả file audio vào vùng upload
- **Click để chọn**: Click vào vùng upload để mở file browser
- **Định dạng hỗ trợ**: MP3, WAV, M4A, FLAC, OGG
- **Kích thước tối đa**: 500MB
- **Preview file**: Hiển thị tên và kích thước file đã chọn
- **Button "🚀 Bắt đầu xử lý"**: Khởi động quá trình transcription

### 5. 📊 Real-time Progress
- **Progress bar** với phần trăm hoàn thành
- **Step-by-step tracking**:
  - 🔄 Preprocessing (10-15%)
  - 🎭 Speaker Diarization (20-40%)
  - ✂️ Segmentation (45-50%)
  - 🎤 Whisper Transcription (55-75%)
  - 🇻🇳 PhoWhisper Transcription (78-88%)
  - ⏱️ Building Timeline (90%)
  - 🤖 AI Enhancement (92-98%)
  - ✅ Complete (100%)
- **Progress message**: Mô tả chi tiết từng bước
- **Button "⏹️ Hủy"**: Dừng xử lý bất cứ lúc nào

### 6. 📝 Hiển thị kết quả
- **Timeline Transcript Card**:
  - Văn bản theo timeline với timestamp
  - Phân tách theo người nói
  - Thống kê: Số người nói, số segments, thời lượng
  
- **Enhanced Transcript Card**:
  - Văn bản đã được AI cải thiện
  - Loại bỏ lỗi, chuẩn hóa format
  - Thống kê: Model sử dụng, thời gian xử lý
  
- **Processing Info Card**:
  - Session ID
  - Thời gian xử lý tổng cộng
  - Prompt version (để kiểm tra cache)

### 7. 📥 Export Results
- **📄 Timeline Transcript** (.txt)
- **✨ Enhanced Transcript** (.txt)
- **🎭 Speaker Segments** (.txt)
- **📦 All Files** (.zip) - Đang phát triển

### 8. 🌙 Dark Mode
- **Toggle Dark/Light mode**: Button 🌙
- **Tự động lưu preference**: Ghi nhớ qua các sessions
- **Smooth transitions**: Hiệu ứng chuyển đổi mượt mà

### 9. 🗑️ Xóa kết quả
- **Clear current results**: Xóa kết quả hiện tại
- **Keep sessions**: Giữ lại lịch sử phiên

## 🚀 Cách sử dụng

### Bước 1: Khởi động server
```bash
cd "Speech2Text Services"
python app/web_ui.py
```

### Bước 2: Truy cập giao diện
Mở trình duyệt và truy cập:
```
http://localhost:5001/chatbot
```

### Bước 3: Upload audio file
1. Kéo thả file vào vùng upload HOẶC click để chọn file
2. Chọn model và options phù hợp
3. Click "🚀 Bắt đầu xử lý"

### Bước 4: Theo dõi progress
- Xem real-time progress với % hoàn thành
- Đọc message để biết đang ở bước nào
- Có thể hủy bất cứ lúc nào

### Bước 5: Xem kết quả
- Kết quả hiển thị dưới dạng cards
- Copy nhanh với button 📋
- Export với các định dạng khác nhau

## 🎨 Giao diện

### Light Mode
- Gradient tím xanh (Purple-Blue gradient)
- Background trắng cho cards
- Text đen dễ đọc
- Border và shadow tinh tế

### Dark Mode
- Gradient tối (Dark gradient)
- Background đen cho cards
- Text trắng dễ nhìn
- Contrast cao hơn

## 🔧 Cấu trúc file

```
Speech2Text Services/
├── app/
│   ├── templates/
│   │   ├── index.html                      # UI cũ (Original)
│   │   ├── index_modern.html               # UI cũ (Modern)
│   │   └── index_chatbot_style.html        # UI mới ⭐
│   ├── static/
│   │   ├── css/
│   │   │   ├── style.css                   # CSS cũ
│   │   │   └── style_modern.css            # CSS mới ⭐
│   │   └── js/
│   │       └── app_modern.js               # JavaScript mới ⭐
│   └── web_ui.py                           # Flask routes
```

## 🌐 Routes

- `/` - Original UI
- `/modern` - Old Modern UI
- `/chatbot` hoặc `/chatbot-ui` - **New ChatBot-Style UI** ⭐

## 📱 Responsive Design

Giao diện được thiết kế responsive cho nhiều kích thước màn hình:

- **Desktop** (> 768px): Full sidebar + main content
- **Mobile** (< 768px): 
  - Sidebar ẩn mặc định
  - Toggle button để mở sidebar
  - Layout single column
  - Touch-friendly buttons

## 🎯 So sánh với ChatBot

### Giống nhau:
- ✅ Sidebar với session management
- ✅ Storage indicator
- ✅ Dark mode support
- ✅ Progress tracking
- ✅ Result cards
- ✅ Export functionality
- ✅ Responsive design
- ✅ Modern UI/UX

### Khác nhau:
- 🎙️ Audio upload thay vì text input
- 📊 Progress với multiple steps (diarization, transcription, enhancement)
- 🎭 Speaker diarization features
- ⏱️ Timeline transcript với timestamps
- 🤖 Dual model support (Whisper + PhoWhisper)
- ✨ AI Enhancement với Qwen

## 🐛 Troubleshooting

### WebSocket không kết nối
- Kiểm tra server đang chạy: `http://localhost:5001`
- Kiểm tra firewall/antivirus
- Xem console log trong browser (F12)

### Upload file không hoạt động
- Kiểm tra định dạng file (MP3, WAV, M4A, FLAC, OGG)
- Kiểm tra kích thước file (< 500MB)
- Xem network tab trong browser để debug

### Progress không cập nhật
- Refresh page
- Kiểm tra WebSocket connection
- Xem server logs

### Kết quả không hiển thị
- Kiểm tra session ID
- Xem browser console
- Kiểm tra server logs

## 📝 Notes

### Local Storage
App sử dụng localStorage để lưu:
- `s2t_sessions`: Danh sách sessions
- `s2t_dark_mode`: Dark mode preference

### Sessions Persistence
- Sessions được lưu trên server tại `data/results/sessions/`
- Mỗi session có folder riêng với tất cả files
- Cleanup sẽ xóa toàn bộ sessions từ server VÀ localStorage

### Performance
- WebSocket cho real-time updates
- Async processing không block UI
- Smooth animations và transitions
- Lazy loading cho session list

## 🔮 Future Enhancements

### Planned Features:
- [ ] ZIP export cho tất cả files
- [ ] Playback audio với highlighting
- [ ] Edit transcript trực tiếp
- [ ] Share session via link
- [ ] Advanced search trong sessions
- [ ] Batch processing multiple files
- [ ] Custom prompt templates
- [ ] Integration với Cloud Storage

## 🤝 Contributing

Nếu bạn muốn đóng góp:
1. Fork repo
2. Tạo branch mới
3. Commit changes
4. Push và tạo Pull Request

## 📄 License

MIT License - Xem file LICENSE để biết thêm chi tiết

## 👤 Author

**SkastVnT**
- GitHub: [@SkastVnT](https://github.com/SkastVnT)
- Project: [AI-Assistant/Speech2Text Services](https://github.com/SkastVnT/AI-Assistant/tree/master/Speech2Text%20Services)

---

**Enjoy your new Speech2Text ChatBot-Style UI! 🎉**
