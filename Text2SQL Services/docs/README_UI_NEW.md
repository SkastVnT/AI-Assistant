# Text2SQL Service - UI Mới 🚀

## 📌 Tổng Quan

**Text2SQL** là dịch vụ chuyển đổi câu hỏi ngôn ngữ tự nhiên thành SQL queries chính xác, hỗ trợ nhiều loại database.

### ✨ Tính Năng Chính

1. **🎨 UI Hiện Đại** - Giao diện đẹp giống ChatBot với:
   - Sidebar lịch sử SQL queries
   - Upload multiple schema files
   - Chat interface trực quan
   - Dark mode
   - Responsive design

2. **📤 Upload Schema** - Hỗ trợ upload nhiều file:
   - `.txt` - Text schema files
   - `.sql` - SQL dump files
   - `.json` - JSON schema
   - `.jsonl` - JSON Lines format

3. **🧠 Suy Luận Sâu** - Tối ưu hóa SQL query generation:
   - Phân tích từng bước
   - Xác định tables và columns
   - Tối ưu joins và filters
   - Cải thiện performance

4. **🗄️ Hỗ Trợ Đa Database**:
   - ClickHouse
   - MongoDB
   - SQL Server
   - PostgreSQL
   - MySQL

5. **🤖 Multiple AI Models**:
   - Gemini (Google) - FREE
   - GPT-4o-mini (OpenAI)
   - DeepSeek

## 🚀 Cài Đặt & Chạy

### 1. Cài đặt thư viện

```bash
cd "Text2SQL Services"
.\Text2SQL\Scripts\activate
pip install -r requirements.txt
```

### 2. Cấu hình .env

File `.env` đã có sẵn các API keys:
- `GEMINI_API_KEY_1` - Google Gemini API
- `OPENAI_API_KEY` - OpenAI API
- `DEEPSEEK_API_KEY` - DeepSeek API

### 3. Chạy ứng dụng

```bash
# Chạy phiên bản đơn giản (khuyên dùng để test)
python app_simple.py

# Hoặc chạy phiên bản đầy đủ
python app.py
```

Truy cập: **http://localhost:5002**

## 📖 Hướng Dẫn Sử Dụng

### Bước 1: Upload Schema

1. Click nút **"📤 Upload Schema"**
2. Chọn file schema của database (.txt, .sql, .json)
3. Click **"✅ Upload & Phân tích"**
4. Schema sẽ được phân tích và hiển thị

### Bước 2: Đặt Câu Hỏi

Ví dụ các câu hỏi:

```
- Hiển thị top 10 khách hàng có doanh thu cao nhất trong tháng 10
- Tìm tất cả orders có giá trị > 1000$ trong năm 2024
- Đếm số lượng users theo từng quốc gia
- Liệt kê các sản phẩm bán chạy nhất trong tuần qua
```

### Bước 3: Nhận SQL Query

- AI sẽ phân tích schema và tạo SQL query chính xác
- SQL được hiển thị với syntax highlighting
- Click **"📋 Copy"** để copy SQL

### Bước 4: Tùy Chọn

- **Model**: Chọn AI model (Gemini, OpenAI, DeepSeek)
- **Database**: Chọn loại database (ClickHouse, MongoDB, SQL Server...)
- **🧠 Suy luận sâu**: Bật để tối ưu hóa SQL generation
- **Dark Mode**: Toggle 🌙 button

## 🎯 Ví Dụ Thực Tế

### Ví dụ 1: ClickHouse Schema

**Upload file:** `orders_schema.sql`

```sql
CREATE TABLE orders (
    order_id UInt32,
    customer_id UInt32,
    order_date Date,
    total_amount Decimal(10,2),
    status String
) ENGINE = MergeTree()
ORDER BY order_date;
```

**Câu hỏi:** "Tổng doanh thu theo tháng trong năm 2024"

**SQL Output:**
```sql
SELECT 
    toMonth(order_date) as month,
    sum(total_amount) as total_revenue
FROM orders
WHERE toYear(order_date) = 2024
GROUP BY month
ORDER BY month
LIMIT 100;
```

### Ví dụ 2: MongoDB Schema

**Upload file:** `users_schema.json`

```json
{
  "collection": "users",
  "fields": {
    "_id": "ObjectId",
    "name": "String",
    "email": "String",
    "age": "Number",
    "country": "String",
    "created_at": "Date"
  }
}
```

**Câu hỏi:** "Đếm số users theo từng quốc gia"

**SQL Output:**
```javascript
db.users.aggregate([
  {
    $group: {
      _id: "$country",
      count: { $sum: 1 }
    }
  },
  {
    $sort: { count: -1 }
  },
  {
    $limit: 100
  }
])
```

## 🛠️ Cấu Trúc Project

```
Text2SQL Services/
├── app_simple.py          # Backend đơn giản (khuyên dùng)
├── app.py                 # Backend đầy đủ (advanced)
├── requirements.txt       # Python dependencies
├── .env                   # API keys configuration
├── templates/
│   ├── index_new.html     # UI mới (đang dùng)
│   └── index.html         # UI cũ
├── static/
│   ├── css/
│   │   └── style.css      # Stylesheet mới
│   └── js/
│       └── app.js         # JavaScript logic
├── uploads/               # Thư mục chứa schema files
└── Text2SQL/              # Virtual environment
```

## 🎨 Tính Năng UI

### 1. Sidebar Lịch Sử
- Lưu trữ các SQL queries đã tạo
- Click để xem lại
- Hiển thị thời gian và preview
- Auto-save vào localStorage

### 2. Upload Modal
- Drag & drop hoặc click chọn file
- Hiển thị danh sách file đã chọn
- Preview file size
- Xóa từng file trước khi upload

### 3. Chat Interface
- Messages với màu sắc phân biệt
- SQL code block với syntax highlighting
- Copy button cho mỗi SQL query
- Auto-scroll to latest message

### 4. Schema Preview
- Floating panel bên phải
- Hiển thị schema đã upload
- Có thể đóng/mở bất kỳ lúc nào
- Preview content của từng file

## 🔧 Cấu Hình Nâng Cao

### Thay đổi Port

Sửa trong `.env`:
```env
PORT=5002
```

### Thêm API Keys

Thêm vào `.env`:
```env
GEMINI_API_KEY_1=your_gemini_key
OPENAI_API_KEY=your_openai_key
DEEPSEEK_API_KEY=your_deepseek_key
```

### Deep Thinking Mode

Khi bật "🧠 Suy luận sâu", AI sẽ:
1. Phân tích tables và columns
2. Xác định relationships và joins
3. Tối ưu filters và aggregations
4. Cải thiện performance

## 📊 So Sánh Versions

| Feature | app_simple.py | app.py |
|---------|---------------|---------|
| Upload Schema | ✅ Multiple files | ✅ Advanced bundling |
| Generate SQL | ✅ Gemini | ✅ Multi-model |
| Deep Thinking | ✅ Basic | ✅ Advanced |
| Memory/Learning | ❌ | ✅ |
| Pretrain Dataset | ❌ | ✅ |
| SQL Execution | ❌ | ✅ ClickHouse |
| Refine Query | ❌ | ✅ |

**Khuyến nghị:** Dùng `app_simple.py` để test UI và tính năng cơ bản trước.

## 🐛 Troubleshooting

### Lỗi: "No module named 'google.generativeai'"
```bash
pip install google-generativeai
```

### Lỗi: "GEMINI_API_KEY not found"
Kiểm tra file `.env` có chứa key:
```env
GEMINI_API_KEY_1=AIzaSy...
```

### Lỗi: "Port 5002 already in use"
Thay đổi port trong code hoặc dừng process đang chạy:
```bash
# Tìm process
netstat -ano | findstr :5002
# Kill process (Windows)
taskkill /PID <process_id> /F
```

### UI không load CSS/JS
Xóa cache trình duyệt hoặc hard refresh:
- Chrome: `Ctrl + Shift + R`
- Firefox: `Ctrl + F5`

## 🎯 Next Steps

Sau khi test UI và tính năng cơ bản, bạn có thể:

1. ✅ **Tích hợp app.py đầy đủ** - Thêm các tính năng advanced
2. ✅ **Thêm SQL execution** - Chạy query và hiển thị kết quả
3. ✅ **Memory/Learning** - AI học từ các query đã duyệt
4. ✅ **Export results** - Xuất kết quả ra Excel/CSV
5. ✅ **Query history** - Lưu và quản lý lịch sử chi tiết hơn

## 📝 Notes

- File `app_simple.py` là phiên bản đơn giản cho test
- File `app.py` là phiên bản đầy đủ với nhiều tính năng
- UI đã được thiết kế responsive cho mobile
- Dark mode được lưu vào localStorage
- Chat history được lưu vào localStorage (max 50 queries)

## 🙏 Credits

- UI Design: Inspired by ChatBot project
- AI Models: Google Gemini, OpenAI, DeepSeek
- Framework: Flask + Vanilla JavaScript

---

**🎉 Enjoy using Text2SQL! 🚀**
