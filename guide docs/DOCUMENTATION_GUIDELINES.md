# 📚 DOCUMENTATION GUIDELINES

> **Hướng dẫn chuẩn hóa việc lưu trữ và tổ chức documentation cho AI-Assistant Project**  
> **Version:** 1.0  
> **Last Updated:** November 6, 2025

---

## 🎯 MỤC ĐÍCH

Document này định nghĩa chuẩn cho:
- ✅ Cách đặt tên files
- ✅ Cấu trúc thư mục
- ✅ Format nội dung
- ✅ Quy trình archive
- ✅ Best practices

---

## 📁 CẤU TRÚC THỦ MỤC DOCS

### Cấu trúc tổng thể

```
docs/
├── README.md                           # Index chính của documentation
├── GETTING_STARTED.md                  # Quick start guide
├── API_DOCUMENTATION.md                # API reference
├── PROJECT_STRUCTURE.md                # Cấu trúc dự án
├── DATABASE_CURRENT_STATE.md           # Phân tích database hiện tại
├── QUICK_REFERENCE.md                  # Tham khảo nhanh
│
├── archives/                           # Lưu trữ theo thời gian
│   ├── 2025-11-06/                    # Theo ngày (YYYY-MM-DD)
│   │   ├── PROJECT_ANALYSIS_2025-11-06.md
│   │   ├── CHATBOT_MIGRATION_ROADMAP.md
│   │   └── README.md                  # Index của archive ngày
│   ├── 2025-11/                       # Hoặc theo tháng (YYYY-MM)
│   │   └── MONTHLY_SUMMARY_2025-11.md
│   └── 2025/                          # Hoặc theo năm (YYYY)
│       └── YEARLY_REVIEW_2025.md
│
├── guides/                            # Hướng dẫn chi tiết
│   ├── IMAGE_GENERATION_GUIDE.md
│   ├── QUICK_START_IMAGE_GEN.md
│   ├── FIX_SD_ERROR.md
│   └── ...
│
├── setup/                             # Hướng dẫn setup
│   ├── SETUP_COMPLETED.md
│   ├── FINAL_STEP.md
│   └── ...
│
└── 04/                               # Legacy structure (cũ)
    └── 11/
        └── 2025/
            └── ...
```

---

## 📝 QUY TẮC ĐẶT TÊN FILE

### 1. Format tên file

```
[TYPE]_[DESCRIPTION]_[DATE].md

Ví dụ:
- PROJECT_ANALYSIS_2025-11-06.md
- CHATBOT_MIGRATION_ROADMAP.md
- DATABASE_DESIGN_PROPOSAL_2025-11-06.md
- API_DOCUMENTATION.md
- BUGFIX_IMAGE_GENERATION.md
```

### 2. Các loại TYPE phổ biến

| Type | Mô tả | Ví dụ |
|------|-------|-------|
| `PROJECT` | Phân tích/tổng quan dự án | `PROJECT_ANALYSIS_2025-11-06.md` |
| `ROADMAP` | Kế hoạch phát triển | `CHATBOT_MIGRATION_ROADMAP.md` |
| `GUIDE` | Hướng dẫn | `SETUP_GUIDE.md` |
| `API` | Tài liệu API | `API_DOCUMENTATION.md` |
| `DATABASE` | Thiết kế database | `DATABASE_DESIGN.md` |
| `BUGFIX` | Sửa lỗi | `BUGFIX_TEXT2IMG_FINAL.md` |
| `FEATURE` | Tính năng mới | `FEATURE_REDIS_CACHE.md` |
| `TESTING` | Testing & QA | `TESTING_GUIDE.md` |
| `DEPLOYMENT` | Deploy | `DEPLOYMENT_CHECKLIST.md` |
| `SECURITY` | Bảo mật | `SECURITY_AUDIT_2025-11.md` |
| `REFACTORING` | Tái cấu trúc | `REFACTORING_COMPLETE_VI.md` |
| `CHANGELOG` | Lịch sử thay đổi | `CHANGELOG.md` |
| `README` | Tổng quan | `README.md` |

### 3. Quy tắc đặt tên

✅ **ĐÚNG:**
```
PROJECT_ANALYSIS_2025-11-06.md
CHATBOT_MIGRATION_ROADMAP.md
DATABASE_DESIGN_POSTGRESQL.md
API_DOCUMENTATION_V2.md
BUGFIX_IMAGE_GEN_FINAL.md
```

❌ **SAI:**
```
project analysis.md              # Có space, không uppercase
chatbot-migration.md            # Không có TYPE rõ ràng
doc-11-06.md                    # Tên không rõ nghĩa
database_design.MD              # Extension không lowercase
my_notes_temp_123.md            # Tên không professional
```

---

## 📂 QUY TRÌNH LƯU TRỮ DOCUMENTS

### 1. Documents hàng ngày (Daily Docs)

**Mục đích:** Lưu phân tích, báo cáo, roadmap theo ngày

**Vị trí:** `docs/archives/YYYY-MM-DD/`

**Quy trình:**

```bash
# 1. Tạo thư mục theo ngày
mkdir -p docs/archives/2025-11-06

# 2. Tạo file document
touch docs/archives/2025-11-06/PROJECT_ANALYSIS_2025-11-06.md

# 3. Viết nội dung (xem template bên dưới)

# 4. Tạo README.md cho archive
touch docs/archives/2025-11-06/README.md
```

**README.md của archive (Template):**

````markdown
# 📅 Archive - November 6, 2025

## Documents trong archive này:

### 1. PROJECT_ANALYSIS_2025-11-06.md
- **Type:** Project Analysis
- **Purpose:** Comprehensive analysis of AI-Assistant project
- **Size:** ~15,000 words
- **Sections:**
  - Executive Summary
  - System Architecture
  - Service Analysis (5 services)
  - Storage Analysis
  - Performance Metrics
  - Recommendations

### 2. CHATBOT_MIGRATION_ROADMAP.md
- **Type:** Migration Roadmap
- **Purpose:** Step-by-step guide for PostgreSQL + Redis migration
- **Duration:** 4 weeks (7 phases)
- **Tasks:** 30+ detailed tasks

## Quick Links
- [Project Analysis](./PROJECT_ANALYSIS_2025-11-06.md)
- [Migration Roadmap](./CHATBOT_MIGRATION_ROADMAP.md)
- [Back to Main Docs](../../README.md)

## Stats
- **Total Files:** 2
- **Total Size:** ~50KB
- **Last Updated:** 2025-11-06
````

### 2. Documents hàng tháng (Monthly Docs)

**Mục đích:** Tổng hợp, review, summary của tháng

**Vị trí:** `docs/archives/YYYY-MM/`

**Ví dụ:**

```
docs/archives/2025-11/
├── README.md
├── MONTHLY_SUMMARY_2025-11.md
├── FEATURE_RELEASES_2025-11.md
└── PERFORMANCE_REPORT_2025-11.md
```

### 3. Documents hàng năm (Yearly Docs)

**Mục đích:** Review lớn, roadmap năm mới

**Vị trí:** `docs/archives/YYYY/`

**Ví dụ:**

```
docs/archives/2025/
├── README.md
├── YEARLY_REVIEW_2025.md
├── ROADMAP_2026.md
└── METRICS_2025.md
```

### 4. Documents chính (Main Docs)

**Mục đích:** Tài liệu luôn cập nhật, không archive

**Vị trí:** `docs/` (root)

**Các file chính:**

```
docs/
├── README.md                      # Luôn cập nhật
├── GETTING_STARTED.md            # Quick start
├── API_DOCUMENTATION.md          # API reference
├── PROJECT_STRUCTURE.md          # Architecture
├── DATABASE_CURRENT_STATE.md     # Database design
└── QUICK_REFERENCE.md            # Cheat sheet
```

**Cập nhật:** Thường xuyên, KHÔNG archive trừ khi có major version change

### 5. Documents theo service

**Vị trí:** `[ServiceName]/docs/` hoặc `[ServiceName]/` (root của service)

**Ví dụ:**

```
ChatBot/
├── README.md
├── CHANGELOG.md
├── TESTING_GUIDE.md
├── BUGFIX_500_ERROR.md
└── REFACTORING_COMPLETE.md

Text2SQL Services/
├── README.md
├── FEATURES_COMPLETE.md
└── AI_LEARNING_GUIDE.md
```

---

## 📄 TEMPLATE DOCUMENT CHUẨN

### Template 1: Analysis/Report Document

````markdown
# 📊 [TITLE IN UPPERCASE]

> **[Brief Description]**  
> **Date:** YYYY-MM-DD  
> **Version:** X.Y  
> **Type:** [Analysis/Report/Guide]

---

## 📋 EXECUTIVE SUMMARY

[Tóm tắt 3-5 câu về nội dung chính]

### Key Points
- ✅ Point 1
- ✅ Point 2
- ✅ Point 3

---

## 🎯 [SECTION 1]

### Subsection 1.1

[Content...]

#### Details

[More details...]

---

## 🔍 [SECTION 2]

### Subsection 2.1

[Content...]

---

## 📊 [SECTION 3: DATA/METRICS]

### Metrics Table

| Metric | Value | Target |
|--------|-------|--------|
| Metric 1 | 100 | 150 |
| Metric 2 | 95% | 90% |

---

## ✅ RECOMMENDATIONS

### Immediate Actions
1. [ ] Action 1
2. [ ] Action 2

### Long-term Actions
1. [ ] Action 1
2. [ ] Action 2

---

## 📚 REFERENCES

- [Link 1](./path/to/doc1.md)
- [Link 2](./path/to/doc2.md)

---

<div align="center">

**📅 Created:** YYYY-MM-DD  
**👤 Author:** [Your Name]  
**🔄 Last Updated:** YYYY-MM-DD  
**📍 Location:** `docs/archives/YYYY-MM-DD/FILENAME.md`

[Back to Archive Index](./README.md) | [Back to Main Docs](../../README.md)

</div>
````

### Template 2: Roadmap/Planning Document

````markdown
# 🚀 [FEATURE/SERVICE] - [ACTION] ROADMAP

> **[Brief Description]**  
> **Duration:** X weeks/months  
> **Start Date:** YYYY-MM-DD  
> **Status:** [Planning/In Progress/Completed]

---

## 📋 OVERVIEW

### Current State
```yaml
Status: [Current status]
Issues:
  - Issue 1
  - Issue 2
```

### Target State
```yaml
Status: [Desired status]
Features:
  - Feature 1
  - Feature 2
```

---

## 🎯 PHASES OVERVIEW

| Phase | Tasks | Duration | Status |
|-------|-------|----------|--------|
| Phase 1 | Setup | 2 days | 🔲 Not Started |
| Phase 2 | Development | 5 days | 🔲 Not Started |
| Phase 3 | Testing | 3 days | 🔲 Not Started |

---

## 📦 PHASE 1: [PHASE NAME] (Days X-Y)

### Day X: [Task Group]

#### 🎯 Goals
- Goal 1
- Goal 2

#### ✅ Tasks

##### Task 1.1: [Task Name]
```bash
# Location: path/to/file
Status: 🔲 To Do
Priority: 🔴 Critical
Time: X hours
```

**Deliverable:**
```python
# Code example or description
```

**Acceptance Criteria:**
- [ ] Criterion 1
- [ ] Criterion 2

---

## ✅ SUCCESS CRITERIA

### Must Have
- [ ] Requirement 1
- [ ] Requirement 2

### Should Have
- [ ] Requirement 3
- [ ] Requirement 4

---

## 📅 TIMELINE SUMMARY

| Week | Days | Phase | Deliverables |
|------|------|-------|--------------|
| Week 1 | 1-7 | Phase 1 | Deliverable 1 |
| Week 2 | 8-14 | Phase 2 | Deliverable 2 |

**Total Duration:** X days/weeks

---

<div align="center">

**📅 Created:** YYYY-MM-DD  
**👤 Owner:** [Team/Person]  
**🔄 Status:** [Planning/In Progress/Completed]  
**📍 Location:** `docs/archives/YYYY-MM-DD/FILENAME.md`

</div>
````

### Template 3: Guide Document

````markdown
# 📖 [GUIDE TITLE]

> **[Brief Description]**  
> **Difficulty:** [Beginner/Intermediate/Advanced]  
> **Duration:** [Estimated time]  
> **Prerequisites:** [Required knowledge/tools]

---

## 🎯 WHAT YOU'LL LEARN

After completing this guide, you will be able to:
- ✅ Skill 1
- ✅ Skill 2
- ✅ Skill 3

---

## 📋 PREREQUISITES

- [ ] Prerequisite 1
- [ ] Prerequisite 2
- [ ] Prerequisite 3

---

## 🚀 STEP 1: [STEP NAME]

### What you'll do
[Brief description]

### Instructions

1. **First action**
   ```bash
   # Command or code
   ```

2. **Second action**
   ```bash
   # Command or code
   ```

### Verification
```bash
# How to verify this step worked
```

**Expected output:**
```
Output example
```

---

## 🔍 TROUBLESHOOTING

### Problem 1: [Problem description]

**Symptoms:**
- Symptom 1
- Symptom 2

**Solution:**
```bash
# Solution code
```

---

## ✅ CHECKLIST

- [ ] Step 1 completed
- [ ] Step 2 completed
- [ ] All tests passing

---

## 📚 NEXT STEPS

- [Next Guide](./path/to/next-guide.md)
- [Related Documentation](./path/to/related.md)

---

<div align="center">

**📅 Last Updated:** YYYY-MM-DD  
**👤 Maintainer:** [Name]  
**🆘 Support:** [Link to support]

</div>
````

---

## 🎨 FORMATTING BEST PRACTICES

### 1. Headings

```markdown
# H1 - Document Title (only once)
## H2 - Major Sections
### H3 - Subsections
#### H4 - Details
```

**Emojis for headings:**
```markdown
## 📋 Overview
## 🎯 Goals
## ✅ Tasks
## 🔍 Details
## 📊 Metrics
## 🚀 Deployment
## 🐛 Troubleshooting
## 📚 References
```

### 2. Lists

**Unordered:**
```markdown
- Item 1
- Item 2
  - Subitem 2.1
  - Subitem 2.2
```

**Ordered:**
```markdown
1. First step
2. Second step
3. Third step
```

**Checklists:**
```markdown
- [ ] Task not done
- [x] Task completed
```

### 3. Code Blocks

````markdown
```bash
# Bash commands
npm install
```

```python
# Python code
def hello():
    print("Hello")
```

```yaml
# YAML config
key: value
```
````

### 4. Tables

```markdown
| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Value 1  | Value 2  | Value 3  |
| Value 4  | Value 5  | Value 6  |
```

**Alignment:**
```markdown
| Left | Center | Right |
|:-----|:------:|------:|
| L    | C      | R     |
```

### 5. Links

```markdown
[Link text](./relative/path/to/file.md)
[External link](https://example.com)
[Link with title](./file.md "Hover title")
```

### 6. Images

```markdown
![Alt text](./images/screenshot.png)
![With caption](./images/diagram.png "Diagram caption")
```

### 7. Alerts/Callouts

```markdown
> **⚠️ WARNING:** Important warning message

> **ℹ️ INFO:** Informational message

> **✅ TIP:** Helpful tip

> **🔴 CRITICAL:** Critical information
```

### 8. Horizontal Rules

```markdown
---
```

### 9. Badges (if supported)

```markdown
![Status](https://img.shields.io/badge/status-active-green)
![Version](https://img.shields.io/badge/version-2.0-blue)
```

---

## 🔄 VERSION CONTROL FOR DOCS

### 1. Git Commit Messages cho Docs

**Format:**
```
docs: [type] description

Types:
- docs: add - Thêm document mới
- docs: update - Cập nhật document
- docs: fix - Sửa lỗi trong document
- docs: refactor - Tái cấu trúc docs
- docs: archive - Archive old docs
```

**Ví dụ:**
```bash
git add docs/archives/2025-11-06/PROJECT_ANALYSIS_2025-11-06.md
git commit -m "docs: add comprehensive project analysis for 2025-11-06"

git add docs/DATABASE_CURRENT_STATE.md
git commit -m "docs: update database analysis with Redis recommendations"

git add docs/archives/2025-11-06/README.md
git commit -m "docs: add index for 2025-11-06 archive"
```

### 2. Version trong Document

**Thêm version ở header:**
```markdown
# Document Title

> **Version:** 1.0  
> **Last Updated:** 2025-11-06  
> **Status:** Draft/Review/Final
```

**Changelog trong document:**
```markdown
## 📝 CHANGELOG

### Version 1.2 (2025-11-10)
- Added section on Redis caching
- Updated performance metrics
- Fixed typos

### Version 1.1 (2025-11-08)
- Added troubleshooting section
- Improved code examples

### Version 1.0 (2025-11-06)
- Initial release
```

### 3. Archive Old Versions

**Khi có major change:**

```bash
# 1. Copy old version to archive
cp docs/API_DOCUMENTATION.md docs/archives/2025-11/API_DOCUMENTATION_V1.md

# 2. Update main document
vim docs/API_DOCUMENTATION.md

# 3. Commit
git add docs/API_DOCUMENTATION.md docs/archives/2025-11/API_DOCUMENTATION_V1.md
git commit -m "docs: update API documentation to V2, archive V1"
```

---

## 📊 DOCUMENT METADATA

### Thêm metadata ở cuối document

```markdown
---

<div align="center">

## 📊 DOCUMENT INFO

| Property | Value |
|----------|-------|
| **Document Type** | Analysis/Guide/Roadmap |
| **Version** | 1.0 |
| **Author** | SkastVnT |
| **Created** | 2025-11-06 |
| **Last Updated** | 2025-11-06 |
| **Status** | Draft/Final |
| **Location** | docs/archives/2025-11-06/ |
| **Related Docs** | [Link 1](./doc1.md), [Link 2](./doc2.md) |
| **Tags** | #analysis #database #migration |

---

**📅 Next Review Date:** 2025-12-06  
**👥 Reviewers:** [@user1, @user2]  
**🔗 Related Issues:** #123, #456

</div>
```

---

## 📁 EXAMPLE WORKFLOW

### Scenario: Tạo Analysis Document mới

```bash
# 1. Create archive folder for today
mkdir -p docs/archives/2025-11-06

# 2. Create analysis document
touch docs/archives/2025-11-06/PROJECT_ANALYSIS_2025-11-06.md

# 3. Write content using template
vim docs/archives/2025-11-06/PROJECT_ANALYSIS_2025-11-06.md

# 4. Create archive README
touch docs/archives/2025-11-06/README.md
vim docs/archives/2025-11-06/README.md

# 5. Update main docs README to link to archive
vim docs/README.md
# Add: - [Archive 2025-11-06](./archives/2025-11-06/README.md)

# 6. Git commit
git add docs/archives/2025-11-06/
git commit -m "docs: add comprehensive project analysis for 2025-11-06"
git push origin master
```

---

## ✅ CHECKLIST KHI TẠO DOCUMENT MỚI

### Pre-creation
- [ ] Xác định loại document (Analysis/Guide/Roadmap/etc.)
- [ ] Chọn vị trí phù hợp (archives/guides/setup/root)
- [ ] Kiểm tra đã có document tương tự chưa

### During creation
- [ ] Sử dụng template phù hợp
- [ ] Đặt tên file theo quy chuẩn
- [ ] Thêm metadata đầy đủ (date, version, author)
- [ ] Format markdown đúng chuẩn
- [ ] Thêm table of contents nếu document dài
- [ ] Code examples có syntax highlighting
- [ ] Links hoạt động chính xác

### Post-creation
- [ ] Tạo/cập nhật README.md của thư mục chứa
- [ ] Cập nhật docs/README.md (main index)
- [ ] Git commit với message rõ ràng
- [ ] Review lại formatting trên GitHub
- [ ] Thông báo cho team (nếu cần)

---

## 🚨 COMMON MISTAKES TO AVOID

### ❌ Sai lầm thường gặp

1. **Tên file không chuẩn**
   ```
   ❌ my notes.md
   ❌ temp-doc-123.md
   ✅ PROJECT_ANALYSIS_2025-11-06.md
   ```

2. **Không có metadata**
   ```
   ❌ # Document Title
       Content...
   
   ✅ # Document Title
       > **Date:** 2025-11-06
       > **Version:** 1.0
       Content...
   ```

3. **Không tạo README cho archive**
   ```
   ❌ archives/2025-11-06/
       └── doc1.md
   
   ✅ archives/2025-11-06/
       ├── README.md
       └── doc1.md
   ```

4. **Code blocks không có syntax highlighting**
   ```
   ❌ ```
       python code here
       ```
   
   ✅ ```python
       python code here
       ```
   ```

5. **Links bị broken**
   ```
   ❌ [Link](../../wrong/path.md)
   ✅ [Link](../../correct/path.md)
   ```

---

## 📚 REFERENCE DOCUMENTS

### Các document mẫu tốt trong project

1. **Analysis:**
   - [PROJECT_ANALYSIS_2025-11-06.md](./docs/archives/2025-11-06/PROJECT_ANALYSIS_2025-11-06.md)
   - [DATABASE_CURRENT_STATE.md](./docs/DATABASE_CURRENT_STATE.md)

2. **Roadmap:**
   - [CHATBOT_MIGRATION_ROADMAP.md](./docs/archives/2025-11-06/CHATBOT_MIGRATION_ROADMAP.md)

3. **Guide:**
   - [GETTING_STARTED.md](./docs/GETTING_STARTED.md)
   - [IMAGE_GENERATION_GUIDE.md](./docs/guides/IMAGE_GENERATION_GUIDE.md)

4. **API:**
   - [API_DOCUMENTATION.md](./docs/API_DOCUMENTATION.md)

5. **README:**
   - [README.md](./README.md) (root)
   - [ChatBot/README.md](./ChatBot/README.md)

---

## 🎯 SUMMARY

### Key Takeaways

1. **Naming:** `[TYPE]_[DESCRIPTION]_[DATE].md`
2. **Location:** 
   - Daily: `docs/archives/YYYY-MM-DD/`
   - Main: `docs/`
   - Service: `[ServiceName]/`
3. **Format:** Use templates, add metadata, proper markdown
4. **Archive:** Always create README.md in archive folders
5. **Git:** Clear commit messages with "docs:" prefix

### Quick Reference

```bash
# Create new analysis for today
mkdir -p docs/archives/$(date +%Y-%m-%d)
touch docs/archives/$(date +%Y-%m-%d)/PROJECT_ANALYSIS_$(date +%Y-%m-%d).md

# Create archive README
touch docs/archives/$(date +%Y-%m-%d)/README.md

# Commit
git add docs/archives/$(date +%Y-%m-%d)/
git commit -m "docs: add analysis for $(date +%Y-%m-%d)"
git push
```

---

<div align="center">

## 🎉 DOCUMENTATION GUIDELINES COMPLETE

**Sử dụng document này như reference khi tạo docs mới!**

Có câu hỏi? Tham khảo [examples trong project](./docs/archives/) hoặc hỏi team! 💬

---

**📅 Created:** November 6, 2025  
**👤 Author:** AI-Assistant Team  
**🔄 Version:** 1.0  
**📍 Location:** `./DOCUMENTATION_GUIDELINES.md`  
**🏷️ Tags:** #documentation #guidelines #best-practices #standards

[📖 View Main Docs](./docs/README.md) | [📂 View Archives](./docs/archives/)

</div>
