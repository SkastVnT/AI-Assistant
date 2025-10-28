# 🤖 AI ChatBot Assistant v1.5

**Ứng dụng chatbot AI đa năng** với khả năng trò chuyện thông minh, lập trình, và **tạo ảnh bằng Stable Diffusion**.

---

## ✨ Tính năng chính

### 🎯 Multi-Model AI Chat
- **3 mô hình AI mạnh mẽ:**
  - 🟢 **Gemini 2.0 Flash** (Google) - Nhanh, miễn phí, đa năng
  - 🔵 **GPT-4o Mini** (OpenAI) - Thông minh, chính xác
  - 🟣 **DeepSeek Chat** - Hiệu năng cao, giá rẻ

### 💬 4 Chế độ hội thoại (Context)
1. **Trò chuyện vui vẻ** - Chat thân thiện, thoải mái
2. **Tâm lý - Tâm sự** - Hỗ trợ tâm lý, empathy, lắng nghe
3. **Giải pháp đời sống** - Tư vấn công việc, học tập, mối quan hệ
4. **Lập trình (Programming)** - Senior Dev Mentor, debug, code review

### 🧠 Deep Thinking Mode
- Suy nghĩ sâu, phân tích đa chiều
- Câu trả lời chi tiết, toàn diện hơn
- Phù hợp cho các vấn đề phức tạp

### 🎨 **Text-to-Image AI (Mới v1.5)**
- Tích hợp **Stable Diffusion WebUI**
- Tool "🎨 Tạo ảnh" thông minh:
  - AI tự động tạo prompt chuyên nghiệp từ mô tả tiếng Việt/Anh
  - Hỗ trợ Deep Thinking để tạo prompt sáng tạo hơn
  - Cấu hình tối ưu: AnythingV4 model, 1024x1280, 10 steps
  - Tự động filter nội dung r18/nsfw
- Tạo ảnh thủ công trong modal với đầy đủ tùy chọn
- Random prompt/negative prompt generator

### 💾 Chat Session Management
- Tạo nhiều cuộc trò chuyện song song
- Lưu tự động vào localStorage (bao gồm cả ảnh!)
- **Storage quota: 200MB** - Đủ cho nhiều chat với ảnh 4K
- Tự động dọn dẹp khi hết dung lượng (giữ 5 chat gần nhất)
- Hiển thị dung lượng sử dụng theo thời gian thực
- Nút dọn dẹp thủ công trong sidebar
- Chuyển đổi giữa các chat dễ dàng
- Tự động đặt tên chat bằng AI
- Export chat history (JSON/TXT)

### 🛠️ Advanced Tools
- 🔍 **Google Search** - Tìm kiếm thông tin (Coming soon)
- 📂 **GitHub Integration** - Kết nối GitHub (Coming soon)
- 📎 **File Upload** - Upload tài liệu để phân tích

### 🎨 UI/UX Hiện đại
- Giao diện dark mode đẹp mắt
- Responsive design (mobile-friendly)
- Markdown rendering với syntax highlighting
- Copy message/table dễ dàng
- Auto-resize textarea
- Sidebar quản lý chat sessions

---

## 📋 Yêu cầu hệ thống

### Cho Chat Bot:
- Python 3.10+
- Flask
- Google Gemini API / OpenAI API / DeepSeek API

### Cho tính năng tạo ảnh:
- **Stable Diffusion WebUI** đang chạy
- NVIDIA GPU (RTX 3060 Ti trở lên khuyến nghị)
- CUDA 11.8+
- Model: **AnythingV4_v45.safetensors**

---

## 🚀 Cài đặt

### 1. Clone repository
```bash
git clone https://github.com/YourUsername/AI-Assistant.git
cd AI-Assistant/ChatBot
```

### 2. Cài đặt Python dependencies
```bash
pip install -r requirements.txt
```

**Dependencies chính:**
- Flask 3.0.0
- google-generativeai 0.3.2
- openai 1.12.0
- python-dotenv 1.0.0
- Pillow 10.4.0
- requests 2.31.0

### 3. Cấu hình API Keys

Tạo file `.env` (copy từ `.env.example`):
```env
# AI Model API Keys
OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE
DEEPSEEK_API_KEY=sk-YOUR_KEY_HERE
GEMINI_API_KEY_1=AIzaSyYOUR_KEY_HERE
GEMINI_API_KEY_2=AIzaSyYOUR_BACKUP_KEY

# Flask Config
FLASK_SECRET_KEY=your-secret-key-here

# Stable Diffusion API (optional)
SD_API_URL=http://127.0.0.1:7860
```

### 4. Cài đặt Stable Diffusion (Tùy chọn - cho tính năng tạo ảnh)

#### Windows:
```bash
# Chạy script tự động
.\scripts\startup\start_chatbot_with_sd.bat
```

Script sẽ:
- Khởi động Stable Diffusion WebUI với API enabled
- Khởi động ChatBot server
- Tự động cấu hình GPU (xFormers, medvram)

#### Thủ công:
```bash
# Terminal 1: Start Stable Diffusion
cd stable-diffusion-webui
python webui.py --api --xformers --no-half-vae --medvram

# Terminal 2: Start ChatBot
cd ChatBot
python app.py
```

---

## 🎯 Sử dụng

### Khởi động ứng dụng

**Cách 1: ChatBot đơn giản (không có tạo ảnh)**
```bash
python app.py
```

**Cách 2: Full features (ChatBot + Stable Diffusion)**
```bash
.\scripts\startup\start_chatbot_with_sd.bat
```

### Truy cập

- **ChatBot:** http://localhost:5000
- **Stable Diffusion WebUI:** http://localhost:7860 (nếu đã chạy)

---

## 📖 Hướng dẫn sử dụng

### 💬 Chat thông thường

1. **Chọn Model AI:** Gemini (miễn phí) / OpenAI / DeepSeek
2. **Chọn Context:** Casual / Psychological / Lifestyle / Programming
3. **Bật Deep Thinking** (tùy chọn) - cho câu trả lời sâu hơn
4. **Nhập tin nhắn** và nhấn Enter hoặc click "Gửi"

### 🎨 Tạo ảnh AI

#### Cách 1: Dùng Tool "Tạo ảnh" (Thông minh - Khuyến nghị)

1. Click nút **"🎨 Tạo ảnh"** (tool button dưới input)
2. Nhập mô tả bằng tiếng Việt hoặc Anh:
   ```
   Một cô gái anime với mái tóc dài màu xanh, đứng dưới cây anh đào
   ```
3. (Tùy chọn) Bật **Deep Thinking** để prompt sáng tạo hơn
4. Nhấn **Gửi**
5. AI sẽ tự động:
   - Phân tích mô tả của bạn
   - Tạo prompt chuyên nghiệp cho Stable Diffusion
   - Đổi sang model AnythingV4_v45
   - Tạo ảnh với cấu hình tối ưu
   - Hiển thị ảnh trong chat

**Cấu hình tự động:**
- Model: AnythingV4_v45.safetensors
- Size: 1024x1280 (portrait)
- Steps: 10 (fast)
- CFG: 8
- Sampler: DPM++ 2M Karras
- Auto-filter: r18, nsfw content

#### Cách 2: Tạo ảnh thủ công (Modal)

1. Click nút **"🖼️ Tạo ảnh"** (góc trên bên phải)
2. Điều chỉnh các tham số:
   - Prompt, Negative Prompt
   - Width, Height
   - Steps, CFG Scale
   - Sampler, Model checkpoint
3. Click **"🎨 Tạo ảnh"**
4. Chờ ảnh được tạo (10-30 giây)
5. Ảnh tự động xuất hiện trong chat

**Tip:** Dùng nút "🎲 Random" để tạo prompt/negative ngẫu nhiên!

### 💾 Quản lý Chat Sessions

- **➕ Mới:** Tạo cuộc trò chuyện mới
- Click vào chat trong sidebar để chuyển đổi
- **� Storage Display:** Xem dung lượng đã dùng (X MB / 200MB)
- **�🗑️ Dọn dẹp:** Nút dọn dẹp thủ công (giữ 5 chat gần nhất)
- **🗑️ Delete:** Xóa chat không cần (hover vào chat item)
- **📥 Tải về:** Export chat history (JSON/TXT)
- **Auto-cleanup:** Tự động dọn dẹp khi hết quota
- Tất cả chat (bao gồm ảnh) được lưu tự động!

**Màu sắc storage indicator:**
- 🟢 Xanh: 0-50% (còn nhiều dung lượng)
- 🟠 Cam: 50-80% (nên dọn dẹp)
- 🔴 Đỏ: 80-100% (gần đầy)

---

## 🔧 API Endpoints

### Chat Endpoints
```
POST /chat
  Body: { message, model, context, deep_thinking, tools }
  Response: { response, model, context, timestamp }

POST /clear
  Response: { message }

GET /history
  Response: { history: [...] }
```

### Stable Diffusion Endpoints
```
GET /api/sd-health
  Response: { status, api_url, current_model }

GET /api/sd-models
  Response: { models: [...], current_model }

POST /api/sd-change-model
  Body: { model_name }
  Response: { success, message }

POST /api/generate-image
  Body: { prompt, negative_prompt, width, height, steps, cfg_scale, ... }
  Response: { success, images: [base64, ...], info, parameters }

GET /api/sd-samplers
  Response: { samplers: [...] }

POST /api/sd-interrupt
  Response: { success }
```

---

## 📁 Cấu trúc thư mục

```
ChatBot/
├── app.py                          # Flask application chính
├── requirements.txt                # Python dependencies
├── .env                            # API keys configuration
├── README.md                       # Documentation (file này)
├── IMAGE_GENERATION_TOOL_GUIDE.md  # Hướng dẫn tạo ảnh
├── config/
│   └── __init__.py
├── src/
│   ├── __init__.py
│   ├── handlers/                   # Request handlers
│   └── utils/
│       ├── __init__.py
│       └── sd_client.py            # Stable Diffusion API client
└── templates/
    └── index.html                  # Frontend UI (Single Page App)
```

---

## 🎓 Tips & Best Practices

### Cho Chat Bot:
- Dùng **Gemini** cho hầu hết tác vụ (miễn phí, nhanh)
- Dùng **GPT-4o Mini** khi cần câu trả lời chính xác cao
- Dùng **DeepSeek** cho coding tasks (rẻ, mạnh)
- Bật **Deep Thinking** cho các vấn đề phức tạp, cần phân tích sâu

### Cho tạo ảnh:
- Dùng **Tool "Tạo ảnh"** thay vì modal (AI tạo prompt tốt hơn)
- Bật **Deep Thinking** khi tạo ảnh để prompt sáng tạo hơn
- Mô tả chi tiết hơn = kết quả tốt hơn
- Ví dụ tốt: "Cô gái anime với mái tóc dài màu xanh, mặc kimono, đứng dưới cây anh đào lúc hoàng hôn"
- Ví dụ xấu: "Vẽ 1 cô gái"

---

## 🐛 Troubleshooting

### Chat Bot không hoạt động?
- ✅ Kiểm tra API keys trong `.env`
- ✅ Kiểm tra internet connection
- ✅ Xem console log: `Ctrl + Shift + I` → Console tab

### Stable Diffusion không kết nối?
- ✅ Chạy SD WebUI với flag `--api`
- ✅ Kiểm tra SD đang chạy: http://127.0.0.1:7860
- ✅ Kiểm tra `SD_API_URL` trong `.env`

### Lỗi khi tạo ảnh?
- ✅ Đảm bảo có model `AnythingV4_v45.safetensors`
- ✅ Kiểm tra GPU memory (cần ít nhất 6GB VRAM)
- ✅ Giảm resolution xuống 512x512 nếu thiếu VRAM

### Chat sessions bị mất?
- ✅ Không xóa localStorage của browser
- ✅ Không dùng chế độ Incognito (sẽ xóa sau khi đóng)
- ✅ Export chat thường xuyên để backup
- ✅ Nếu hết quota, auto-cleanup sẽ giữ 5 chat gần nhất

### Storage quota exceeded?
- ✅ Kiểm tra storage display trong sidebar
- ✅ Click nút "🗑️ Dọn dẹp" để xóa chat cũ
- ✅ Auto-cleanup sẽ tự động kích hoạt khi đầy
- ✅ Limit hiện tại: 200MB (đủ cho ~50-100 chat với ảnh 4K)

---

## 🔄 Changelog

### v1.5.1 (2025-10-29)
- ✨ **NEW:** Storage Management System
  - Real-time storage usage display (200MB quota)
  - Auto-cleanup on quota exceeded (keeps 5 recent chats)
  - Manual cleanup button in sidebar
  - Color-coded storage indicator (green/orange/red)
- 🔧 **IMPROVED:** Increased storage limit from 10MB to 200MB
- 🎨 **UI:** Storage info display in sidebar header
- 📚 **DOCS:** Added STORAGE_MANAGEMENT.md

### v1.5 (2025-10-29)
- ✨ **NEW:** Tích hợp Stable Diffusion - Text-to-Image AI
- ✨ **NEW:** Tool "Tạo ảnh" thông minh với AI prompt generation
- ✨ **NEW:** Random prompt/negative prompt generator
- ✨ **NEW:** Auto-save images in chat sessions
- ✨ **NEW:** Support 4K image generation (up to 2560x2560)
- ✨ **NEW:** Infinite timeout for large image generation
- 🐛 **FIX:** Chat sessions không lưu ảnh khi tạo chat mới
- 🐛 **FIX:** Xóa welcome message spam khi refresh
- 🐛 **FIX:** Timeout issues with 4K image generation
- 🎨 **UI:** Thêm nút tool "🎨 Tạo ảnh"
- 📚 **DOCS:** Thêm IMAGE_GENERATION_TOOL_GUIDE.md

### v1.0 (2025-10-20)
- 🎉 Initial release
- Multi-model AI chat (Gemini, OpenAI, DeepSeek)
- 4 context modes
- Deep Thinking mode
- Chat session management
- Dark mode UI

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

MIT License - see LICENSE file for details

---

## 👨‍💻 Author

**AI Assistant Team**
- GitHub: [@SkastVnT](https://github.com/SkastVnT)

---

## 🙏 Acknowledgments

- [Google Gemini](https://deepmind.google/technologies/gemini/) - AI model
- [OpenAI](https://openai.com/) - GPT models
- [DeepSeek](https://www.deepseek.com/) - DeepSeek Chat model
- [Stable Diffusion WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui) - Image generation
- [Flask](https://flask.palletsprojects.com/) - Web framework
- [Marked.js](https://marked.js.org/) - Markdown parser
- [Highlight.js](https://highlightjs.org/) - Syntax highlighting

---

## 📞 Support

Nếu gặp vấn đề, vui lòng:
1. Xem mục **Troubleshooting** ở trên
2. Đọc **IMAGE_GENERATION_TOOL_GUIDE.md** (cho tính năng tạo ảnh)
3. Mở issue trên GitHub
4. Liên hệ qua email: [your-email@example.com]

---

**⭐ Star repo nếu bạn thấy hữu ích!**
