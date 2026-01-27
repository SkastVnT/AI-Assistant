# 5️⃣.1 CARDINALITY DIAGRAMS — 1–1, 1–N, N–N (Project Examples)

> Các sơ đồ quan hệ theo bội số (cardinality) rút gọn, bám đúng vào dữ liệu của dự án.

---

## 1️⃣ 1–1 (One-to-One)

Ví dụ: User ↔ User Settings (mỗi user có đúng một cấu hình)

```mermaid
erDiagram
  USERS ||--o| USER_SETTINGS : has

  USERS {
    ObjectId _id PK
    string username UK
    string email UK
  }

  USER_SETTINGS {
    ObjectId _id PK
    string user_id UK
    object settings
  }
```

Notes:
- user_id trong USER_SETTINGS là duy nhất, đảm bảo 1–1.

---

## 2️⃣ 1–N (One-to-Many)

Ví dụ A: User → Conversations (một user có nhiều phiên chat)  
Ví dụ B: Conversation → Messages (một hội thoại có nhiều tin nhắn)

```mermaid
erDiagram
  USERS ||--o{ CONVERSATIONS : creates
  CONVERSATIONS ||--|{ MESSAGES : contains

  USERS {
    ObjectId _id PK
    string username
  }

  CONVERSATIONS {
    ObjectId _id PK
    string user_id
    string title
  }

  MESSAGES {
    ObjectId _id PK
    ObjectId conversation_id
    string role
  }
```

Notes:
- CONVERSATIONS.user_id tham chiếu USER._id  
- MESSAGES.conversation_id tham chiếu CONVERSATIONS._id

---

## 3️⃣ N–N (Many-to-Many)

Trong MongoDB của dự án, quan hệ N–N thường biểu diễn bằng mảng lồng (embedded array) hoặc tham chiếu, không dùng bảng nối. Dưới đây là hai cách trình bày để dễ chụp màn hình:

### 3A. N–N (Logical) — Messages ↔ Images (embedded array)

```mermaid
erDiagram
  MESSAGES }o--o{ IMAGES : uses

  MESSAGES {
    ObjectId _id PK
    array images
  }

  IMAGES {
    string cloud_url
    string url
  }
```

Ghi chú: IMAGES là thực thể logic (ảnh nằm ngoài DB, chỉ lưu metadata trong mảng images của MESSAGES).

### 3B. N–N (Conceptual with junction) — If normalized as join

```mermaid
erDiagram
  MESSAGES ||--o{ MESSAGE_IMAGE_LINKS : has
  IMAGES  ||--o{ MESSAGE_IMAGE_LINKS : has

  MESSAGES {
    ObjectId _id PK
  }

  IMAGES {
    string cloud_url PK
  }

  MESSAGE_IMAGE_LINKS {
    ObjectId id PK
    ObjectId message_id
    string image_cloud_url
  }
```

Ghi chú: Đây là mô hình khái niệm nếu cần tách bảng nối. Trong dự án hiện tại, bạn đang dùng mảng images[] trong MESSAGES.

---

## 🔚 NAVIGATION

[⬅️ Full System ER](05_er_diagram_all.md) | [MongoDB ER](05_er_diagram_mongodb.md) | [Database Design](04_database_design.md)
