# AI ChatBot Assistant

Ứng dụng chatbot AI hỗ trợ tâm lý, tâm sự và giải pháp đời sống sử dụng nhiều mô hình AI.

## Tính năng

- 🤖 Hỗ trợ 3 mô hình AI: Gemini (Google), GPT-3.5 (OpenAI), DeepSeek
- 💬 3 chế độ chat:
  - Trò chuyện vui vẻ: Chat thân thiện, thoải mái
  - Tâm lý - Tâm sự: Hỗ trợ tâm lý, lắng nghe chia sẻ
  - Giải pháp đời sống: Tư vấn về công việc, học tập, mối quan hệ
- 📝 Lưu lịch sử chat
- 🎨 Giao diện đẹp, responsive
- 🔄 Chuyển đổi model và context dễ dàng

## Cài đặt

1. Cài đặt dependencies:
```bash
pip install -r requirements.txt
```

2. Cấu hình API keys trong file `.env`:
```
OPENAI_API_KEY=your_openai_key
DEEPSEEK_API_KEY=your_deepseek_key
GEMINI_API_KEY_1=your_gemini_key
FLASK_SECRET_KEY=your_secret_key
```

## Chạy ứng dụng

```bash
python app.py
```

Truy cập: http://localhost:5000

## Sử dụng

1. Chọn mô hình AI (Gemini, OpenAI, DeepSeek)
2. Chọn chế độ chat phù hợp
3. Nhập tin nhắn và nhấn Enter hoặc click Gửi
4. Trò chuyện thoải mái!

## API Endpoints

- `POST /chat` - Gửi tin nhắn chat
- `POST /clear` - Xóa lịch sử chat
- `GET /history` - Lấy lịch sử chat

## Mở rộng

Bạn có thể dễ dàng thêm:
- Nhiều mô hình AI khác
- Thêm context/chế độ chat
- Lưu lịch sử vào database
- Thêm tính năng voice chat
- Multi-user support

## License

MIT
