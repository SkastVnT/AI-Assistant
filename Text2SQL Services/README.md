# Text2SQL Service - AI Assistant

Natural Language to SQL query conversion service powered by Google Gemini AI.

## 🌟 Features

- **Natural Language Processing**: Convert plain English to SQL queries
- **Database Support**: ClickHouse database integration
- **Schema Understanding**: Automatic table and column analysis
- **Query Validation**: SQL syntax checking and validation
- **Data Visualization**: Query results with visualization support
- **Multi-table Queries**: Support for complex joins and relationships
- **Query History**: Track and reuse previous queries

## 📋 Requirements

- Python 3.10.6
- ClickHouse database (local or remote)
- Google Gemini API key
- 4GB+ RAM

## 🚀 Quick Start

### 1. Setup Virtual Environment

```bash
# Create virtual environment
python -m venv venv_text2sql

# Activate (Windows)
.\venv_text2sql\Scripts\activate

# Activate (Linux/Mac)
source venv_text2sql/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy example environment file
copy .env.example .env

# Edit .env and add:
GOOGLE_API_KEY=your_gemini_api_key
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8123
CLICKHOUSE_DATABASE=default
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=
```

### 4. Run Application

```bash
python app.py
```

Access at: http://localhost:5001

## 📁 Project Structure

```
Text2SQL Services/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── .env.example       # Environment variables template
├── templates/
│   └── index.html     # Web UI
├── src/
│   └── utils/         # Utility functions
├── sample/
│   └── uploaded/      # Sample data files
├── data/
│   └── raw/
│       └── spider/    # Training data
└── tools/
    └── spider_to_dataset.py  # Data conversion tools
```

## 🔧 Configuration

### Environment Variables (.env)

```env
# Google Gemini API
GOOGLE_API_KEY=your_api_key

# ClickHouse Configuration
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8123
CLICKHOUSE_DATABASE=default
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=

# Server
FLASK_PORT=5001
FLASK_DEBUG=False
```

### Database Setup

1. **Install ClickHouse** (if not already installed):
   ```bash
   # Windows: Download from https://clickhouse.com/
   # Linux: 
   sudo apt-get install clickhouse-server clickhouse-client
   ```

2. **Start ClickHouse**:
   ```bash
   sudo service clickhouse-server start
   ```

3. **Create tables** (upload schema via UI or CLI)

## 📖 Usage Guide

### Basic Query Conversion

1. Enter your natural language question
2. System analyzes available tables and columns
3. Gemini generates SQL query
4. Review and execute query
5. View results

### Example Queries

```
Natural Language → SQL Query

"Show all customers" 
→ SELECT * FROM customers

"Count orders by status"
→ SELECT status, COUNT(*) FROM orders GROUP BY status

"Top 10 products by revenue"
→ SELECT product_name, SUM(amount) as revenue 
  FROM sales 
  GROUP BY product_name 
  ORDER BY revenue DESC 
  LIMIT 10
```

### Advanced Features

- **Schema Upload**: Upload Excel/CSV with table schemas
- **Multi-table Joins**: Automatic relationship detection
- **Aggregations**: SUM, COUNT, AVG, etc.
- **Filtering**: WHERE conditions
- **Sorting**: ORDER BY clauses
- **Grouping**: GROUP BY with HAVING

## 🐛 Troubleshooting

### API Key Issues

```bash
# Verify API key is valid:
# Visit: https://makersuite.google.com/app/apikey
# Generate new key if needed
```

### Database Connection Issues

```bash
# Test ClickHouse connection:
curl http://localhost:8123/ping

# Check if ClickHouse is running:
sudo service clickhouse-server status

# View logs:
tail -f /var/log/clickhouse-server/clickhouse-server.log
```

### Query Generation Issues

1. **Verify table schemas** are uploaded correctly
2. **Check column names** match database
3. **Review error messages** from Gemini API
4. **Try simpler queries** first

## 📚 Documentation

- [Spider Dataset](data/raw/spider/README.txt) - Training data format
- [ClickHouse Docs](https://clickhouse.com/docs) - Database documentation

## 🔄 Development

### Running Tests

```bash
pytest test.py
```

### Code Formatting

```bash
black app.py src/
flake8 app.py src/
```

### Adding New Features

1. Update `app.py` with new endpoints
2. Add UI components in `templates/index.html`
3. Update requirements if needed
4. Test thoroughly before deploying

## 📊 Performance Tips

1. **Index your tables** for faster queries
2. **Limit result sets** with appropriate LIMIT clauses
3. **Use query cache** for repeated queries
4. **Optimize schema** with proper data types

## 🔐 Security

- Never commit `.env` file
- Use strong database passwords
- Limit API key permissions
- Validate all user inputs
- Use parameterized queries

## 📝 License

Part of AI-Assistant project. See root LICENSE file.

## 🤝 Contributing

This is a sub-service of AI-Assistant project. For contributions, please refer to the main project repository.

## 📧 Support

For issues and questions, please create an issue in the main AI-Assistant repository.

## 🌐 Resources

- [Google Gemini API](https://ai.google.dev/)
- [ClickHouse](https://clickhouse.com/)
- [Flask Documentation](https://flask.palletsprojects.com/)
