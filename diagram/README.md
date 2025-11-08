# 📐 BIỂU ĐỒ THIẾT KẾ HỆ THỐNG AI-ASSISTANT

> **Tài liệu thiết kế UML & Database cho dự án AI-Assistant**  
> **Cập nhật:** 06/11/2025  
> **Deadline:** 30/11/2025 (Tuần 11)

---

## 📚 Danh sách tài liệu

| STT | Tên biểu đồ | File | Mô tả |
|:---:|:------------|:-----|:------|
| 1️⃣ | **Use Case Diagram** | [01_usecase_diagram.md](01_usecase_diagram.md) | Biểu đồ ca sử dụng - tương tác người dùng với hệ thống |
| 2️⃣ | **Class Diagram** | [02_class_diagram.md](02_class_diagram.md) | Biểu đồ lớp - cấu trúc hướng đối tượng |
| 3️⃣ | **Sequence Diagrams** | [03_sequence_diagrams.md](03_sequence_diagrams.md) | Biểu đồ tuần tự - 3 chức năng quan trọng |
| 4️⃣ | **Database Design** | [04_database_design.md](04_database_design.md) | Thiết kế cơ sở dữ liệu - Schema & Indexes |
| 5️⃣ | **ER Diagram** | [05_er_diagram.md](05_er_diagram.md) | Biểu đồ thực thể liên kết |

---

## 🎯 Mục đích

Các biểu đồ này được tạo ra để:

✅ **Phân tích & thiết kế hệ thống** - Hiểu rõ kiến trúc dự án  
✅ **Tài liệu hóa** - Dễ dàng onboard thành viên mới  
✅ **Chuẩn bị mở rộng** - Foundation cho các tính năng mới  
✅ **Đáp ứng deadline** - Hoàn thành sườn dự án trước 30/11/2025  

---

## 🛠️ Công nghệ sử dụng

- **Ngôn ngữ biểu đồ:** Mermaid (render native trên GitHub)
- **Database:** PostgreSQL (thiết kế đề xuất)
- **Chuẩn UML:** Use Case, Class, Sequence, ER Diagrams

---

## 📖 Hướng dẫn xem biểu đồ

### Trên GitHub:
1. Mở file `.md` trực tiếp trên GitHub
2. GitHub sẽ tự động render Mermaid diagrams

### Trên VS Code:
1. Cài extension: [Markdown Preview Mermaid Support](https://marketplace.visualstudio.com/items?itemName=bierner.markdown-mermaid)
2. Mở file `.md` và nhấn `Ctrl+Shift+V` để preview

### Export sang hình ảnh:
1. Truy cập [Mermaid Live Editor](https://mermaid.live)
2. Copy code từ file `.md`
3. Export sang PNG/SVG

---

## 🏗️ Cấu trúc dự án

```
AI-Assistant/
├── diagram/                      # 📐 Thư mục này
│   ├── README.md                 # Tài liệu tổng quan
│   ├── 01_usecase_diagram.md     # Use Case
│   ├── 02_class_diagram.md       # Class Diagram
│   ├── 03_sequence_diagrams.md   # Sequence Diagrams
│   ├── 04_database_design.md     # Database Design
│   └── 05_er_diagram.md          # ER Diagram
├── ChatBot/                      # 🤖 ChatBot Service
├── Text2SQL Services/            # 📊 Text2SQL Service
├── Speech2Text Services/         # 🎙️ Speech2Text Service
├── stable-diffusion-webui/       # 🎨 Stable Diffusion
└── src/                          # 🎯 Hub Gateway
```

---

## 📝 Ghi chú

### Hiện trạng dự án:
- ✅ 4 core services hoạt động độc lập
- ✅ Hub Gateway đang phát triển (Port 3000)
- ⚠️ Chưa có database tập trung (đang dùng file system)
- 🚧 Đề xuất migrate sang PostgreSQL (trong 04_database_design.md)

### Kế hoạch mở rộng:
1. **Phase 1** (Đến 30/11): Hoàn thiện sườn dự án
2. **Phase 2**: Implement database design
3. **Phase 3**: Add user authentication
4. **Phase 4**: Build admin dashboard

---

## 🤝 Đóng góp

Mọi góp ý về thiết kế xin gửi qua:
- **GitHub Issues:** [SkastVnT/AI-Assistant/issues](https://github.com/SkastVnT/AI-Assistant/issues)
- **Email:** (thêm email nếu có)

---

<div align="center">

**Made with ❤️ by SkastVnT**

[⬅️ Back to Main README](../README.md)

</div>
