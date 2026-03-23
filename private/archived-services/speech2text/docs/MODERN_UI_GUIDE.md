# 🎙️ Speech2Text Modern UI - Hướng dẫn sử dụng

## ✨ Giới thiệu

Giao diện mới của Speech2Text Services được thiết kế theo phong cách ChatBot AI, mang lại trải nghiệm người dùng hiện đại và thân thiện hơn.

## 🚀 Cách sử dụng

### 1. Khởi động Server

```bash
cd "Speech2Text Services"
python app/web_ui.py
```

Server sẽ chạy tại: `http://localhost:5000`

### 2. Truy cập giao diện

- **Giao diện cũ (Original)**: `http://localhost:5000/`
- **Giao diện mới (Modern)**: `http://localhost:5000/modern` ⭐ RECOMMENDED

## 🎨 Tính năng giao diện mới

### 1. Upload File Audio
- Kéo thả file hoặc click để chọn
- Hỗ trợ: MP3, WAV, M4A, FLAC, OGG
- Hiển thị thông tin file đã chọn (tên + dung lượng)

### 2. Cấu hình Model
- **Model Transcription**:
  - PhoWhisper (Tiếng Việt tối ưu) ⭐
  - Whisper Large V3
  - Whisper Medium
  
- **Diarization Model**:
  - Pyannote 3.1 (Tốt nhất) ⭐
  - Simple Diarization

### 3. Tùy chọn xử lý
- ✅ **Nhận diện người nói**: Phân biệt các speaker khác nhau
- ✅ **Thêm timestamp**: Hiển thị thời gian bắt đầu/kết thúc
- ✅ **AI Enhancement**: Cải thiện văn bản với Qwen/Gemini

### 4. Theo dõi tiến trình (Real-time)
- Hiển thị từng bước xử lý
- Progress bar động cho mỗi bước
- Status realtime qua WebSocket

**Các bước xử lý:**
1. 📝 **Preprocessing**: Tiền xử lý audio (convert, normalize)
2. 👥 **Diarization**: Nhận diện và phân tách người nói
3. 🎙️ **Transcription**: Chuyển đổi giọng nói thành text
4. ✨ **Enhancement**: Cải thiện văn bản với AI (nếu bật)
5. ✅ **Finalization**: Hoàn thành và lưu kết quả

### 5. Kết quả chi tiết

#### Stats Dashboard
- 👥 **Số người nói**: Tổng số speaker được nhận diện
- ⏱️ **Thời lượng**: Độ dài audio
- 💬 **Đoạn hội thoại**: Số segment
- ⚡ **Thời gian xử lý**: Thời gian total

#### Transcript View
- Hiển thị từng đoạn hội thoại
- Phân biệt speaker với màu sắc
- Timestamp chính xác cho từng đoạn
- Hover effect để dễ đọc

#### Actions
- 📋 **Copy**: Sao chép toàn bộ transcript
- 💾 **Download**: Tải xuống file .txt
- 🔗 **Share**: Chia sẻ (nếu trình duyệt hỗ trợ)

## 🎯 So sánh với giao diện cũ

| Tính năng | Giao diện cũ | Giao diện mới |
|-----------|--------------|---------------|
| Design | Basic, gradient purple | Modern, dark theme (như ChatBot) |
| Responsive | Có | Có + Better mobile |
| Real-time progress | WebSocket | WebSocket + Better UI |
| Model selection | Không | Có (sidebar) |
| Options toggle | Không | Có (toggle switches) |
| Stats dashboard | Không | Có (4 stats cards) |
| Transcript view | Basic list | Speaker cards với hover |
| Actions | Basic | Copy, Download, Share |
| Empty state | Không | Có (icon + text) |

## 🔧 Yêu cầu kỹ thuật

### Python Dependencies
```bash
Flask>=2.3.0
flask-socketio>=5.3.0
flask-cors>=4.0.0
python-dotenv>=1.0.0
librosa>=0.10.0
soundfile>=0.12.0
```

### Frontend
- Socket.IO Client 4.6.0
- Font Awesome 6.4.0
- Modern browsers (Chrome, Firefox, Edge, Safari)

## 📱 Responsive Design

Giao diện tự động điều chỉnh theo kích thước màn hình:

- **Desktop (>1024px)**: Sidebar + Main content side-by-side
- **Tablet (768-1024px)**: Sidebar trên, Content dưới
- **Mobile (<768px)**: Single column, optimized touch

## 🎨 Color Scheme

```css
--primary-color: #667eea     /* Purple */
--secondary-color: #764ba2   /* Dark purple */
--success-color: #42b883     /* Green */
--danger-color: #e74c3c      /* Red */
--warning-color: #f39c12     /* Orange */
--dark-bg: #1a1a2e           /* Dark background */
--card-bg: #16213e           /* Card background */
```

## 🚀 Performance

- **WebSocket**: Real-time updates không cần polling
- **Async Processing**: Background threads không block UI
- **Optimized CSS**: Smooth animations với GPU acceleration
- **Lazy Loading**: Chỉ load kết quả khi cần

## 🔒 Security

- File validation (type + size)
- Secure filename sanitization
- CORS enabled cho cross-origin
- Session isolation

## 📝 API Endpoints

### POST `/api/process`
Upload và xử lý audio file

**Request (FormData):**
```javascript
{
  audio: File,                    // Audio file
  model: string,                  // 'phowhisper' | 'whisper-large-v3' | 'whisper-medium'
  enable_diarization: boolean,    // true | false
  enable_timestamp: boolean,      // true | false
  enable_ai: boolean,             // true | false
  session_id: string              // Unique session ID
}
```

**Response:**
```json
{
  "message": "Upload successful, processing started",
  "session_id": "session_20250104_123456",
  "filename": "audio.mp3"
}
```

### WebSocket Events

**Client → Server:**
- `connect`: Kết nối
- `cancel`: Hủy processing

**Server → Client:**
- `connected`: Kết nối thành công
- `progress`: Cập nhật tiến trình
- `complete`: Hoàn thành xử lý
- `error`: Lỗi xảy ra

## 🐛 Troubleshooting

### Lỗi "Already processing another file"
**Nguyên nhân**: Đang xử lý file khác  
**Giải pháp**: Đợi file hiện tại hoàn thành hoặc reload trang

### Lỗi "Invalid file type"
**Nguyên nhân**: File không đúng định dạng  
**Giải pháp**: Chỉ upload MP3, WAV, M4A, FLAC, OGG

### WebSocket không kết nối
**Nguyên nhân**: Firewall/Proxy block  
**Giải pháp**: 
- Check console logs
- Thử tắt antivirus tạm thời
- Chạy server với quyền admin

### Progress bị stuck
**Nguyên nhân**: Server crash hoặc timeout  
**Giải pháp**:
- Check server logs
- Reload trang
- Kiểm tra file audio có lỗi không

## 🎓 Tips & Tricks

1. **Chọn model phù hợp**:
   - Tiếng Việt → PhoWhisper
   - English/Multi-language → Whisper Large V3
   - Fast processing → Whisper Medium

2. **Tối ưu chất lượng**:
   - Bật "Nhận diện người nói" cho audio có nhiều speaker
   - Bật "AI Enhancement" để cải thiện văn bản
   - Upload file chất lượng cao (WAV lossless tốt hơn MP3)

3. **Tiết kiệm thời gian**:
   - Tắt diarization nếu chỉ có 1 người nói
   - Tắt AI enhancement nếu không cần
   - Sử dụng file audio đã được preprocess sẵn

## 📞 Support

- **Issues**: Report tại GitHub Issues
- **Documentation**: Check `/docs` folder
- **Contact**: [Your contact info]

## 🔄 Updates

### v2.0.0 (Current)
- ✨ Modern UI theo phong cách ChatBot
- 🎨 Dark theme với gradient
- 📊 Stats dashboard
- 🎯 Model selection
- ⚙️ Options toggles
- 📋 Copy/Download/Share actions

### v1.0.0 (Legacy)
- Basic UI với gradient purple
- WebSocket real-time
- Upload và processing

## 📄 License

MIT License - Free to use and modify

---

**Enjoy using Speech2Text Modern UI! 🎉**
