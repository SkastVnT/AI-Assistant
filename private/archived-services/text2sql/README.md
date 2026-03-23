# 🤖 Text2SQL AI - Natural Language to SQL Query Generator

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0+-black?style=flat-square&logo=flask)
![GROK](https://img.shields.io/badge/GROK-3-orange?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

**Transform natural language questions into precise SQL queries using AI**

[Features](#-features) • [Quick Start](#-quick-start) • [Installation](#️-installation) • [Documentation](#-documentation)

</div>

---

## ✨ Features

### 🎯 Core Features

- **🔄 Natural Language to SQL**: Convert plain English/Vietnamese to SQL queries
- **🗄️ Multi-Database Support**: ClickHouse, MongoDB, SQL Server, PostgreSQL, MySQL  
- **📤 Schema Upload**: Support .txt, .sql, .json, .jsonl files
- **🧠 Deep Thinking Mode**: Enhanced reasoning for complex queries
- **🎨 Beautiful UI**: Modern, responsive design with dark mode

### 🚀 Advanced Features (v2.0)

- **💡 Question Generation**: AI auto-generates 5 sample questions from your schema
- **🧠 AI Learning**: Save correct SQL queries to knowledge base
- **🔌 Database Connection**: Connect directly to ClickHouse/MongoDB (localhost & Atlas)
- **📚 Knowledge Base Manager**: Manage learned SQL queries
- **🔍 Schema Preview**: Interactive schema viewer
- **📥 Export History**: Download SQL query history

### 🤖 AI Models Supported

- ✅ **GROK-3** (xAI) - Primary, FREE
- ✅ **GPT-4o-mini** (OpenAI) - Fast & affordable
- ✅ **DeepSeek** - Most cost-effective

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- GROK API Key (required) - Get free at [xAI Console](https://console.x.ai/)

### Installation

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/text2sql-ai.git
cd "Text2SQL Services"

# Create virtual environment
python -m venv Text2SQL

# Activate virtual environment (Windows)
.\Text2SQL\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY_1

# Run application
python app_simple.py
```

Open browser: **http://localhost:5002**

---

## 🎯 Usage Examples

### Example 1: Generate SQL

```
User: "Show top 10 customers with highest revenue in 2024"

AI Output:
SELECT 
  customer_id,
  customer_name,
  SUM(order_amount) as total_revenue
FROM orders
WHERE YEAR(order_date) = 2024
GROUP BY customer_id, customer_name
ORDER BY total_revenue DESC
LIMIT 10;
```

### Example 2: Auto-Generate Questions

```
User: "Tạo câu hỏi cho schema này"

AI Output:
📝 5 Sample Questions Generated:
1. Top 10 best-selling products this month
2. Revenue by month in 2024
3. Customers with orders > $1000
... (with SQL for each)
```

### Example 3: Database Connection

```
1. Click "🔌 Database" button
2. Select: ClickHouse or MongoDB
3. Enter credentials
4. Click "🔍 Test Connection"
5. Click "💾 Save Connection"
```

---

## 🗂️ Project Structure

```
Text2SQL Services/
├── app_simple.py              # Main Flask app
├── requirements.txt           # Dependencies
├── .env                       # API keys
├── templates/
│   └── index_new.html        # Main UI
├── static/
│   ├── css/style.css         # Styles
│   └── js/app.js             # Frontend JS
├── data/
│   ├── knowledge_base/       # AI learned SQL
│   └── connections/          # DB connections
└── sample_schemas/           # Example schemas
```

---

## 📚 Documentation

- **[AI Learning Guide](AI_LEARNING_GUIDE.md)** - AI Learning features
- **[Features Complete](FEATURES_COMPLETE.md)** - All features
- **[Setup Guide](SETUP_COMPLETE.md)** - Detailed setup

---

## 🚀 Deployment

### Deploy to Render.com (FREE)

```bash
# 1. Push to GitHub
git push origin main

# 2. On Render.com:
# - Connect GitHub repo
# - Build: pip install -r requirements.txt
# - Start: python app_simple.py
# - Add env vars: GEMINI_API_KEY_1

# 3. Done! App live at: https://yourapp.onrender.com
```

---

## 🐛 Troubleshooting

**Issue: Port already in use**
```bash
# Change port in .env
PORT=5003
```

**Issue: Module not found**
```bash
pip install -r requirements.txt --upgrade
```

**Issue: Database connection failed**
- Check database is running
- Verify credentials
- For MongoDB Atlas: whitelist IP (0.0.0.0/0)

---

## 🤝 Contributing

Contributions welcome! Please open issues or pull requests.

---

## 📄 License

MIT License - see [LICENSE](../LICENSE) file

---

## 🙏 Acknowledgments

- **Google Gemini AI** - Primary AI model
- **Flask** - Web framework
- **ClickHouse** & **MongoDB** - Database support

---

<div align="center">

**Made with ❤️ using Python & AI**

⭐ **Star this repo if you find it helpful!** ⭐

</div>
