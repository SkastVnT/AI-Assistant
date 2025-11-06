# 🚀 Text2SQL - Tính Năng Mới: AI Learning & Question Generation

## 📌 Tổng Quan Tính Năng Mới

Đã thêm 3 tính năng mạnh mẽ vào Text2SQL:

### 1. 📝 **Tạo Câu Hỏi Từ Schema** (Question Generation)
- AI tự động tạo 5 câu hỏi mẫu từ schema
- Mỗi câu hỏi có SQL query tương ứng
- Giúp khám phá khả năng của database

### 2. 🧠 **AI Học SQL Từ User** (SQL Learning)
- User cung cấp SQL đúng cho câu hỏi
- System lưu vào Knowledge Base
- AI sẽ nhớ và tái sử dụng sau này

### 3. 📚 **Knowledge Base Management**
- Xem tất cả SQL đã học
- Quản lý và xóa dữ liệu học
- Export knowledge base

---

## 🎯 Hướng Dẫn Sử Dụng Chi Tiết

### Tính Năng 1: Tạo Câu Hỏi Mẫu

#### Cách Sử Dụng:

**Bước 1:** Upload schema file
```
Click "📤 Upload Schema" → Chọn file → Upload
```

**Bước 2:** Yêu cầu tạo câu hỏi

Gõ một trong các câu sau:
```
✅ "Tạo câu hỏi cho schema này"
✅ "Cho tôi một vài câu hỏi mẫu"
✅ "Gợi ý câu hỏi"
✅ "Generate questions"
✅ "Tạo ví dụ"
✅ "Câu hỏi nào có thể dùng với schema này"
```

**Kết Quả:**
- AI sẽ tạo 5 câu hỏi đa dạng
- Mỗi câu có SQL query tương ứng
- Hiển thị đẹp với syntax highlighting
- Có button Copy cho từng SQL

#### Ví Dụ Thực Tế:

**Input Schema:** `ecommerce_clickhouse.sql`

**User gõ:** "Tạo câu hỏi cho tôi"

**Output:**
```
📝 Câu hỏi mẫu từ Schema:

1. Top 10 sản phẩm bán chạy nhất trong tháng này
   SELECT product_id, SUM(quantity) as total_sold
   FROM order_items oi
   JOIN orders o ON oi.order_id = o.order_id
   WHERE toMonth(o.order_date) = toMonth(now())
   GROUP BY product_id
   ORDER BY total_sold DESC
   LIMIT 10;

2. Doanh thu theo từng tháng năm 2024
   SELECT 
     toMonth(order_date) as month,
     SUM(final_amount) as revenue
   FROM orders
   WHERE toYear(order_date) = 2024
   GROUP BY month
   ORDER BY month;

... (3 câu nữa)
```

---

### Tính Năng 2: AI Học SQL Từ User

#### Cách Sử Dụng:

**Scenario 1: Sau khi tạo câu hỏi**

User đã tạo 5 câu hỏi mẫu, giờ muốn cung cấp SQL đúng hơn:

```
User gõ:
"Câu SQL đúng: SELECT user_id, COUNT(*) FROM orders GROUP BY user_id"
```

Hoặc:

```
"Tôi có câu SQL: 
SELECT p.product_name, SUM(oi.quantity) 
FROM products p 
JOIN order_items oi ON p.product_id = oi.product_id 
GROUP BY p.product_name"
```

**Kết Quả:**
```
✅ Đã học SQL cho câu hỏi: [câu hỏi tương ứng]

Saved to Knowledge Base
```

**Scenario 2: Học SQL mới**

```
User gõ:
"Học câu SQL này: SELECT * FROM users WHERE country = 'Vietnam'"
```

System sẽ lưu vào knowledge base với mô tả generic.

#### Keywords Để AI Nhận Diện:

Câu của bạn cần có:
- **SQL keywords**: SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER
- **Learning keywords**: 
  - "câu sql", "sql này", "query này"
  - "tôi có câu sql", "đây là sql"
  - "học", "learn", "lưu", "save"
  - "nhớ", "remember"

---

### Tính Năng 3: Quản Lý Knowledge Base

#### Mở Knowledge Base:

Click nút **"🧠 AI Learning"** trên toolbar

#### Giao Diện:

```
┌─────────────────────────────────────┐
│ 🧠 AI Learning - Knowledge Base     │
│                                   ✕ │
├─────────────────────────────────────┤
│ 5 câu SQL đã học                    │
├─────────────────────────────────────┤
│                                     │
│ 1. Top 10 khách hàng...            │
│    SELECT user_id, SUM(...)        │
│    Học lúc: 03/11/2025 11:30       │
│                                     │
│ 2. Doanh thu theo tháng...         │
│    SELECT toMonth(order_date)...   │
│    Học lúc: 03/11/2025 11:32       │
│                                     │
│ ...                                 │
│                                     │
├─────────────────────────────────────┤
│ [🔄 Refresh]  [🗑️ Xóa tất cả]     │
└─────────────────────────────────────┘
```

#### Chức Năng:

1. **🔄 Refresh:** Tải lại knowledge base
2. **🗑️ Xóa tất cả:** Xóa toàn bộ (có confirm)

---

## 📂 Cấu Trúc Dữ Liệu

### Knowledge Base Files:

```
Text2SQL Services/
└── data/
    └── knowledge_base/
        ├── session_20251103_113045.txt
        ├── session_20251103_114521.txt
        └── session_20251103_120034.txt
```

### File Format (JSON Lines):

```json
{"question": "Top 10 khách hàng", "sql": "SELECT...", "learned_at": "2025-11-03T11:30:45"}
{"question": "Doanh thu theo tháng", "sql": "SELECT...", "learned_at": "2025-11-03T11:32:12"}
```

---

## 🎬 Demo Workflow Hoàn Chỉnh

### Workflow 1: Khám Phá Database

```
1️⃣ Upload schema
   → Click "📤 Upload Schema"
   → Chọn ecommerce_clickhouse.sql
   → Upload thành công

2️⃣ Tạo câu hỏi mẫu
   User: "Tạo câu hỏi cho tôi"
   AI: Tạo 5 câu hỏi + SQL

3️⃣ Test với câu hỏi khác
   User: "Top 20 sản phẩm bán chạy nhất"
   AI: Tạo SQL query

4️⃣ Cải thiện SQL (nếu cần)
   User: "Câu SQL đúng: SELECT product_id, SUM(quantity)..."
   AI: ✅ Đã học SQL cho câu hỏi...
```

### Workflow 2: Xây Dựng Knowledge Base

```
1️⃣ Upload multiple schemas
   → orders_schema.sql
   → users_schema.sql
   → products_schema.sql

2️⃣ Tạo câu hỏi cho từng schema
   User: "Tạo câu hỏi"
   AI: 5 câu hỏi + SQL

3️⃣ Đóng góp SQL tốt hơn
   User: "Tôi có câu SQL tối ưu: SELECT..."
   AI: ✅ Đã học

4️⃣ Xem knowledge base
   Click "🧠 AI Learning"
   → Thấy tất cả SQL đã học
   → Export nếu cần
```

---

## 🔧 API Endpoints

### 1. Chat (với features mới)

```http
POST /chat
Content-Type: application/json

{
  "message": "Tạo câu hỏi cho tôi",
  "model": "gemini",
  "db_type": "clickhouse",
  "deep_thinking": false,
  "schemas": [...]
}
```

**Response (Questions):**
```json
{
  "status": "success",
  "type": "questions",
  "questions": [
    {
      "question": "...",
      "sql": "..."
    }
  ],
  "message": "Đã tạo 5 câu hỏi mẫu",
  "model": "gemini"
}
```

**Response (Learned):**
```json
{
  "status": "success",
  "type": "learned",
  "message": "✅ Đã học SQL cho câu hỏi: ...",
  "session": "session_20251103_113045",
  "question": "...",
  "sql": "..."
}
```

### 2. List Knowledge

```http
GET /knowledge/list
```

**Response:**
```json
{
  "status": "success",
  "knowledge": [
    {
      "question": "...",
      "sql": "...",
      "learned_at": "2025-11-03T11:30:45"
    }
  ],
  "count": 10
}
```

### 3. Save Knowledge (Manual)

```http
POST /knowledge/save
Content-Type: application/json

{
  "question": "Top users by spending",
  "sql": "SELECT user_id, SUM(amount) FROM orders GROUP BY user_id"
}
```

### 4. Clear Knowledge

```http
POST /knowledge/clear
```

### 5. Get Current Session Questions

```http
GET /questions/current
```

---

## 💡 Tips & Best Practices

### 1. Tạo Câu Hỏi Hiệu Quả

✅ **DO:**
- Upload schema đầy đủ với comments
- Dùng deep thinking khi schema phức tạp
- Review và chọn câu hỏi hay

❌ **DON'T:**
- Upload schema thiếu thông tin
- Tạo quá nhiều câu hỏi cho schema đơn giản

### 2. Học SQL Thông Minh

✅ **DO:**
- Cung cấp SQL đã test và chạy được
- Thêm comments giải thích
- Optimize query trước khi dạy AI

❌ **DON'T:**
- Dạy SQL lỗi hoặc chưa test
- Quên context của câu hỏi

### 3. Quản Lý Knowledge Base

✅ **DO:**
- Review định kỳ
- Xóa SQL cũ/lỗi thời
- Export backup thường xuyên

❌ **DON'T:**
- Để tích lũy quá nhiều SQL trùng lặp
- Quên clean up

---

## 🎯 Use Cases Thực Tế

### Use Case 1: Onboarding Nhân Viên Mới

**Tình huống:** Nhân viên mới cần học queries phổ biến

**Solution:**
1. Upload company database schema
2. Generate 20-30 câu hỏi mẫu
3. Lưu vào knowledge base
4. Share file knowledge base
5. Nhân viên mới import và học

### Use Case 2: Data Analysis Team

**Tình huống:** Team cần standardize queries

**Solution:**
1. Mỗi analyst đóng góp queries tốt nhất
2. Dùng "Học SQL" để lưu
3. Team review trong knowledge base
4. Export thành documentation

### Use Case 3: Database Migration

**Tình huống:** Chuyển từ MySQL sang ClickHouse

**Solution:**
1. Upload MySQL schema → Generate questions
2. Upload ClickHouse schema → Generate questions
3. So sánh SQL syntax differences
4. Học cả 2 để AI biết convert

---

## 🐛 Troubleshooting

### Vấn đề 1: AI không tạo câu hỏi

**Nguyên nhân:**
- Schema quá đơn giản
- Không có table definition

**Giải pháp:**
- Upload schema có CREATE TABLE
- Thêm comments mô tả tables

### Vấn đề 2: AI không nhận diện "học SQL"

**Nguyên nhân:**
- Thiếu keywords
- SQL không hợp lệ

**Giải pháp:**
- Dùng keywords: "câu sql:", "tôi có sql:"
- Đảm bảo SQL có SELECT/INSERT/...

### Vấn đề 3: Knowledge base rỗng

**Nguyên nhân:**
- Chưa học SQL nào
- File bị xóa

**Giải pháp:**
- Click "🔄 Refresh"
- Check folder `data/knowledge_base/`

---

## 📊 Statistics & Analytics

### Knowledge Base Stats:

Hiển thị trong modal:
- **Total SQL learned:** 25 queries
- **Most recent:** 2 minutes ago
- **Sessions:** 5 active sessions
- **Top question:** "Top users by revenue"

### Future Analytics (Coming Soon):

- Most used queries
- Query performance metrics
- Learning trends over time
- User contribution leaderboard

---

## 🚀 Next Steps

### Phase 1: ✅ HOÀN THÀNH
- ✅ Question generation from schema
- ✅ SQL learning from user
- ✅ Knowledge base management
- ✅ UI with AI Learning modal

### Phase 2: Đang Phát Triển
- 🔄 Auto-suggest from knowledge base
- 🔄 Query similarity matching
- 🔄 Multi-user knowledge sharing
- 🔄 Export/Import knowledge base

### Phase 3: Tương Lai
- 📅 Query performance tracking
- 📅 AI fine-tuning from knowledge
- 📅 Collaborative learning
- 📅 Query recommendation engine

---

## 🎉 Tổng Kết

### Đã Có:
✅ Tạo câu hỏi tự động từ schema  
✅ AI học SQL từ user  
✅ Knowledge base management  
✅ Beautiful UI với modal  
✅ Full CRUD operations  

### Cách Sử Dụng:
1. Upload schema
2. Gõ "tạo câu hỏi"
3. Gõ "câu sql: ..." để dạy AI
4. Click "🧠 AI Learning" để quản lý

### Files:
- `app_simple.py` - Backend với AI learning
- `static/js/app.js` - Frontend logic
- `static/css/style.css` - Styling
- `templates/index_new.html` - UI với modal

**READY TO USE! 🎊**

---

**Happy Learning! 🧠✨**
