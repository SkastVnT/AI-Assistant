# -*- coding: utf-8 -*-
"""
Text2SQL Service - Simplified Version for Testing
AI Assistant - Natural Language to SQL Query Conversion
With AI Learning & Question Generation Features
"""

import os
import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import google.generativeai as genai
import openai

# Load environment variables
load_dotenv()

# Configure Gemini - load all 4 API keys
GEMINI_API_KEY_1 = os.getenv("GEMINI_API_KEY_1")
GEMINI_API_KEY_2 = os.getenv("GEMINI_API_KEY_2")
GEMINI_API_KEY_3 = os.getenv("GEMINI_API_KEY_3")
GEMINI_API_KEY_4 = os.getenv("GEMINI_API_KEY_4")
# Try first available key for initial config
GEMINI_API_KEY = GEMINI_API_KEY_1 or GEMINI_API_KEY_2 or os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Configure OpenAI and DeepSeek
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# Flask app
app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = "uploads"
KNOWLEDGE_BASE_DIR = Path("data/knowledge_base")
CONNECTIONS_DIR = Path("data/connections")
ALLOWED_EXTENSIONS = {"txt", "sql", "json", "jsonl"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
KNOWLEDGE_BASE_DIR.mkdir(parents=True, exist_ok=True)
CONNECTIONS_DIR.mkdir(parents=True, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Global state
uploaded_schemas = []
current_session_questions = []  # Store generated questions for current session
current_session_name = None
active_db_connection = None  # Store active database connection

# ============================================
# Helper Functions
# ============================================

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_sql(text):
    """Extract SQL from response text"""
    if not text:
        return ""
    
    # Remove code fences
    text = re.sub(r"```+[a-zA-Z]*\n", "", text)
    text = re.sub(r"```+", "", text)
    
    # Find SQL keywords
    match = re.search(r"(?i)\b(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\b[\s\S]*$", text)
    if match:
        return match.group(0).strip()
    
    return text.strip()

def generate_sql_gemini(schema_text, question, db_type="clickhouse", deep_thinking=False):
    """Generate SQL using Gemini with API key retry (4 keys)"""
    import time
    
    # List of Gemini API keys to try
    gemini_keys = [
        GEMINI_API_KEY_1,
        GEMINI_API_KEY_2,
        GEMINI_API_KEY_3,
        GEMINI_API_KEY_4
    ]
    # Filter out None/empty keys
    gemini_keys = [k for k in gemini_keys if k]
    
    thinking_instruction = ""
    if deep_thinking:
        thinking_instruction = """
Think step by step:
1. Identify the tables and columns involved
2. Determine the relationships and joins needed
3. Consider filters, aggregations, and sorting
4. Optimize the query for performance
"""
    
    prompt = f"""{thinking_instruction}
You are an expert SQL developer specializing in {db_type.upper()}.

Database Schema:
{schema_text}

User Question: {question}

Generate a precise SQL query that answers the question.
Requirements:
- Use {db_type.upper()} syntax
- Include LIMIT 100 for SELECT queries unless specified
- Return ONLY the SQL query, no explanations

SQL Query:"""
    
    last_error = None
    for idx, api_key in enumerate(gemini_keys):
        try:
            # Configure with current API key
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            sql = extract_sql(response.text)
            
            # Success!
            if idx > 0:
                print(f"✅ Gemini success with API Key #{idx+1}")
            return sql, "success"
            
        except Exception as e:
            error_msg = str(e)
            last_error = error_msg
            
            # Check if quota exceeded
            if "429" in error_msg or "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                print(f"⚠️ Gemini quota exceeded - API Key #{idx+1}")
                
                # If not the last key, try next
                if idx < len(gemini_keys) - 1:
                    print(f"🔄 Trying next Gemini API key...")
                    time.sleep(1)
                    continue
            # Other errors - return immediately
            return None, error_msg
    
    # All keys exhausted
    return None, f"All Gemini API keys exhausted. Last error: {last_error}"

def generate_sql_openai(schema_text, question, db_type="clickhouse", deep_thinking=False):
    """Generate SQL using OpenAI"""
    if not OPENAI_API_KEY:
        return None, "OpenAI API key not configured"
    
    thinking_instruction = ""
    if deep_thinking:
        thinking_instruction = """Think step by step:
1. Identify the tables and columns involved
2. Determine the relationships and joins needed
3. Consider filters, aggregations, and sorting
4. Optimize the query for performance\n\n"""
    
    prompt = f"""{thinking_instruction}You are an expert SQL developer specializing in {db_type.upper()}.

Database Schema:
{schema_text}

User Question: {question}

Generate a precise SQL query that answers the question.
Requirements:
- Use {db_type.upper()} syntax
- Include LIMIT 100 for SELECT queries unless specified
- Return ONLY the SQL query, no explanations

SQL Query:"""
    
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"You are an expert {db_type.upper()} SQL developer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        sql = extract_sql(response.choices[0].message.content)
        return sql, "success"
    except Exception as e:
        return None, str(e)

def generate_sql_deepseek(schema_text, question, db_type="clickhouse", deep_thinking=False):
    """Generate SQL using DeepSeek"""
    if not DEEPSEEK_API_KEY:
        return None, "DeepSeek API key not configured"
    
    thinking_instruction = ""
    if deep_thinking:
        thinking_instruction = """Think step by step:
1. Identify the tables and columns involved
2. Determine the relationships and joins needed
3. Consider filters, aggregations, and sorting
4. Optimize the query for performance\n\n"""
    
    prompt = f"""{thinking_instruction}You are an expert SQL developer specializing in {db_type.upper()}.

Database Schema:
{schema_text}

User Question: {question}

Generate a precise SQL query that answers the question.
Requirements:
- Use {db_type.upper()} syntax
- Include LIMIT 100 for SELECT queries unless specified
- Return ONLY the SQL query, no explanations

SQL Query:"""
    
    try:
        client = openai.OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com/v1"
        )
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": f"You are an expert {db_type.upper()} SQL developer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        sql = extract_sql(response.choices[0].message.content)
        return sql, "success"
    except Exception as e:
        return None, str(e)

def generate_questions_from_schema(schema_text, db_type="clickhouse", model="gemini"):
    """Generate 5 sample questions with SQL queries from schema"""
    import time
    
    prompt = f"""You are an expert SQL developer specializing in {db_type.upper()}.

Given this database schema:
{schema_text}

Generate exactly 5 diverse and practical questions that can be answered using this schema.
For each question, provide the corresponding SQL query.

Think about:
1. Simple data retrieval
2. Aggregations and grouping
3. Filtering and conditions
4. Joins between tables (if applicable)
5. Complex analytical queries

Format your response as JSON:
{{
  "questions": [
    {{
      "question": "question text in Vietnamese",
      "sql": "corresponding SQL query"
    }},
    ...
  ]
}}

Return ONLY the JSON, no other text."""
    
    try:
        if model == "gemini":
            # Try all 4 Gemini API keys
            gemini_keys = [GEMINI_API_KEY_1, GEMINI_API_KEY_2, GEMINI_API_KEY_3, GEMINI_API_KEY_4]
            gemini_keys = [k for k in gemini_keys if k]
            
            last_error = None
            for idx, api_key in enumerate(gemini_keys):
                try:
                    genai.configure(api_key=api_key)
                    model_obj = genai.GenerativeModel("gemini-1.5-flash")
                    response = model_obj.generate_content(prompt)
                    text = response.text.strip()
                    
                    if idx > 0:
                        print(f"✅ Gemini questions generation success with API Key #{idx+1}")
                    break  # Success!
                    
                except Exception as e:
                    error_msg = str(e)
                    last_error = error_msg
                    
                    if "429" in error_msg or "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                        print(f"⚠️ Gemini quota exceeded - API Key #{idx+1}")
                        if idx < len(gemini_keys) - 1:
                            print(f"🔄 Trying next Gemini API key...")
                            time.sleep(1)
                            continue
                    raise e
            
            if last_error and not text:
                raise Exception(f"All Gemini API keys exhausted: {last_error}")
        elif model == "openai":
            if not OPENAI_API_KEY:
                raise Exception("OpenAI API key not configured")
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": f"You are an expert {db_type.upper()} SQL developer."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=2000
            )
            text = response.choices[0].message.content.strip()
        elif model == "deepseek":
            if not DEEPSEEK_API_KEY:
                raise Exception("DeepSeek API key not configured")
            client = openai.OpenAI(
                api_key=DEEPSEEK_API_KEY,
                base_url="https://api.deepseek.com/v1"
            )
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": f"You are an expert {db_type.upper()} SQL developer."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=2000
            )
            text = response.choices[0].message.content.strip()
        else:
            raise Exception(f"Unsupported model: {model}")
        
        # Extract JSON from response
        text = re.sub(r"```+json\s*", "", text)
        text = re.sub(r"```+", "", text)
        
        # Parse JSON
        result = json.loads(text)
        return result.get("questions", []), "success"
        
    except Exception as e:
        return None, str(e)

def detect_question_generation_intent(message):
    """Detect if user wants to generate questions from schema"""
    keywords = [
        "tạo câu hỏi", "câu hỏi", "generate questions", "sample questions",
        "ví dụ", "examples", "mẫu", "gợi ý", "suggest", "tạo ra",
        "cho tôi", "give me", "show me", "các câu", "query examples"
    ]
    
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in keywords)

def detect_sql_learning_intent(message):
    """Detect if user is providing correct SQL for learning"""
    keywords = [
        "câu sql", "sql này", "query này", "tôi có câu sql",
        "đây là sql", "this is sql", "correct sql", "sql đúng",
        "học", "learn", "lưu", "save", "nhớ", "remember"
    ]
    
    message_lower = message.lower()
    
    # Check if message contains SQL keywords
    has_sql = bool(re.search(r'\b(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER)\b', message, re.I))
    has_keyword = any(keyword in message_lower for keyword in keywords)
    
    return has_sql and has_keyword

def save_learned_sql(question, sql):
    """Save learned SQL to knowledge base"""
    global current_session_name
    
    if not current_session_name:
        # Create new session
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        current_session_name = f"session_{timestamp}"
    
    # Save to file
    kb_file = KNOWLEDGE_BASE_DIR / f"{current_session_name}.txt"
    
    entry = {
        "question": question,
        "sql": sql,
        "learned_at": datetime.now().isoformat()
    }
    
    with open(kb_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    return current_session_name

def load_knowledge_base():
    """Load all learned questions and SQLs from knowledge base"""
    knowledge = []
    
    if not KNOWLEDGE_BASE_DIR.exists():
        return knowledge
    
    for kb_file in KNOWLEDGE_BASE_DIR.glob("*.txt"):
        try:
            with open(kb_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entry = json.loads(line)
                        knowledge.append(entry)
        except Exception as e:
            print(f"Error loading {kb_file}: {e}")
    
    return knowledge

# ============================================
# Routes
# ============================================

@app.route("/")
def index():
    """Home page"""
    return render_template("index_new.html")

@app.route("/upload", methods=["POST"])
def upload_schemas():
    """Upload schema files"""
    global uploaded_schemas
    
    if "files" not in request.files:
        return jsonify({"status": "error", "message": "No files provided"}), 400
    
    files = request.files.getlist("files")
    
    if not files or files[0].filename == "":
        return jsonify({"status": "error", "message": "No files selected"}), 400
    
    uploaded_schemas = []
    
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)
            
            # Read content
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            
            uploaded_schemas.append({
                "filename": filename,
                "filepath": filepath,
                "content": content[:1000],  # Preview first 1000 chars
                "size": len(content)
            })
    
    return jsonify({
        "status": "success",
        "message": f"Uploaded {len(uploaded_schemas)} schema file(s)",
        "schemas": uploaded_schemas
    })

@app.route("/chat", methods=["POST"])
def chat():
    """Process chat message and generate SQL"""
    global uploaded_schemas, current_session_questions
    
    data = request.get_json()
    message = data.get("message", "").strip()
    model = data.get("model", "gemini")
    db_type = data.get("db_type", "clickhouse")
    deep_thinking = data.get("deep_thinking", False)
    
    if not message:
        return jsonify({"status": "error", "message": "Empty message"}), 400
    
    if not uploaded_schemas:
        return jsonify({
            "status": "error",
            "message": "Please upload schema files first"
        }), 400
    
    # Combine all schemas
    schema_text = "\n\n---\n\n".join([
        f"-- File: {s['filename']}\n{s['content']}"
        for s in uploaded_schemas
    ])
    
    # Check if user wants to generate questions
    if detect_question_generation_intent(message):
        if model in ["gemini", "openai", "deepseek"]:
            questions, result = generate_questions_from_schema(schema_text, db_type, model)
            
            if result == "success" and questions:
                # Store questions for this session
                current_session_questions = questions
                
                return jsonify({
                    "status": "success",
                    "type": "questions",
                    "questions": questions,
                    "message": f"Đã tạo {len(questions)} câu hỏi mẫu từ schema",
                    "model": model,
                    "db_type": db_type
                })
            else:
                return jsonify({
                    "status": "error",
                    "message": f"Failed to generate questions: {result}"
                }), 500
    
    # Check if user is providing SQL for learning
    if detect_sql_learning_intent(message):
        # Extract SQL from message
        sql_match = re.search(r'(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER)[\s\S]+', message, re.I)
        
        if sql_match:
            provided_sql = extract_sql(sql_match.group(0))
            
            # Try to match with current session questions
            learned_for = None
            for q in current_session_questions:
                # Simple matching - could be improved
                question_text = q.get("question", "")
                if question_text:
                    learned_for = question_text
                    break
            
            if not learned_for:
                # Use a generic description
                learned_for = "Câu SQL được cung cấp"
            
            # Save to knowledge base
            session_name = save_learned_sql(learned_for, provided_sql)
            
            return jsonify({
                "status": "success",
                "type": "learned",
                "message": f"✅ Đã học SQL cho câu hỏi: {learned_for}",
                "session": session_name,
                "question": learned_for,
                "sql": provided_sql
            })
    
    # Generate SQL normally
    sql = None
    result = None
    
    if model == "gemini":
        sql, result = generate_sql_gemini(schema_text, message, db_type, deep_thinking)
    elif model == "openai":
        sql, result = generate_sql_openai(schema_text, message, db_type, deep_thinking)
    elif model == "deepseek":
        sql, result = generate_sql_deepseek(schema_text, message, db_type, deep_thinking)
    else:
        return jsonify({
            "status": "error",
            "message": f"Model {model} not supported. Supported models: gemini, openai, deepseek"
        }), 400
    
    if result == "success" and sql:
        return jsonify({
            "status": "success",
            "type": "sql",
            "sql": sql,
            "explanation": f"Generated SQL query for: {message}",
            "model": model,
            "db_type": db_type
        })
    else:
        return jsonify({
            "status": "error",
            "message": f"Failed to generate SQL: {result}"
        }), 500

@app.route("/schema", methods=["GET"])
def get_schemas():
    """Get uploaded schemas"""
    return jsonify({
        "status": "success",
        "schemas": uploaded_schemas
    })

@app.route("/clear", methods=["POST"])
def clear_schemas():
    """Clear uploaded schemas"""
    global uploaded_schemas
    uploaded_schemas = []
    
    # Clear upload folder
    for filename in os.listdir(UPLOAD_FOLDER):
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.isfile(filepath):
            os.remove(filepath)
    
    return jsonify({
        "status": "success",
        "message": "Schemas cleared"
    })

@app.route("/health", methods=["GET"])
def health_check():
    """Health check"""
    return jsonify({
        "status": "ok",
        "service": "Text2SQL",
        "api_configured": bool(GEMINI_API_KEY),
        "schemas_loaded": len(uploaded_schemas)
    })

@app.route("/knowledge/list", methods=["GET"])
def list_knowledge():
    """List all learned SQL queries"""
    knowledge = load_knowledge_base()
    
    return jsonify({
        "status": "success",
        "knowledge": knowledge,
        "count": len(knowledge)
    })

@app.route("/knowledge/save", methods=["POST"])
def save_knowledge():
    """Manually save SQL to knowledge base"""
    data = request.get_json()
    question = data.get("question", "").strip()
    sql = data.get("sql", "").strip()
    
    if not question or not sql:
        return jsonify({
            "status": "error",
            "message": "Question and SQL are required"
        }), 400
    
    session_name = save_learned_sql(question, sql)
    
    return jsonify({
        "status": "success",
        "message": f"Saved to knowledge base",
        "session": session_name
    })

@app.route("/knowledge/clear", methods=["POST"])
def clear_knowledge():
    """Clear all knowledge base"""
    global current_session_name, current_session_questions
    
    try:
        # Remove all knowledge base files
        for kb_file in KNOWLEDGE_BASE_DIR.glob("*.txt"):
            kb_file.unlink()
        
        current_session_name = None
        current_session_questions = []
        
        return jsonify({
            "status": "success",
            "message": "Knowledge base cleared"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route("/questions/current", methods=["GET"])
def get_current_questions():
    """Get current session questions"""
    return jsonify({
        "status": "success",
        "questions": current_session_questions,
        "count": len(current_session_questions)
    })

# ============================================
# Database Connection Routes
# ============================================

@app.route("/api/database/test-connection", methods=["POST"])
def test_database_connection():
    """Test database connection"""
    try:
        data = request.json
        db_type = data.get("db_type")
        connection_type = data.get("connection_type")
        
        if db_type == "clickhouse":
            # Test ClickHouse connection
            import clickhouse_connect
            
            if connection_type == "localhost":
                host = data.get("host", "localhost")
                port = int(data.get("port", 8123))
                username = data.get("username", "default")
                password = data.get("password", "")
                database = data.get("database", "default")
                
                client = clickhouse_connect.get_client(
                    host=host,
                    port=port,
                    username=username,
                    password=password,
                    database=database
                )
            else:
                return jsonify({
                    "status": "error",
                    "message": "ClickHouse chỉ hỗ trợ localhost connection"
                }), 400
            
            # Test query
            result = client.query("SELECT version()")
            version = result.result_rows[0][0]
            client.close()
            
            return jsonify({
                "status": "success",
                "message": f"✅ Kết nối ClickHouse thành công! Version: {version}",
                "version": version
            })
            
        elif db_type == "mongodb":
            # Test MongoDB connection
            from pymongo import MongoClient
            from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
            
            if connection_type == "atlas":
                uri = data.get("uri")
                if not uri:
                    return jsonify({
                        "status": "error",
                        "message": "URI không được để trống cho MongoDB Atlas"
                    }), 400
                
                client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            else:  # localhost
                host = data.get("host", "localhost")
                port = int(data.get("port", 27017))
                username = data.get("username", "")
                password = data.get("password", "")
                database = data.get("database", "admin")
                
                if username and password:
                    uri = f"mongodb://{username}:{password}@{host}:{port}/{database}"
                else:
                    uri = f"mongodb://{host}:{port}/"
                
                client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            
            # Test connection
            client.admin.command('ping')
            server_info = client.server_info()
            version = server_info.get('version', 'Unknown')
            client.close()
            
            return jsonify({
                "status": "success",
                "message": f"✅ Kết nối MongoDB thành công! Version: {version}",
                "version": version
            })
        
        else:
            return jsonify({
                "status": "error",
                "message": f"Database type không được hỗ trợ: {db_type}"
            }), 400
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"❌ Lỗi kết nối: {str(e)}"
        }), 500


@app.route("/api/database/save-connection", methods=["POST"])
def save_database_connection():
    """Save database connection config"""
    try:
        data = request.json
        connection_name = data.get("connection_name", f"connection_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        connection_id = str(uuid.uuid4())
        
        connection_config = {
            "id": connection_id,
            "name": connection_name,
            "db_type": data.get("db_type"),
            "connection_type": data.get("connection_type"),
            "host": data.get("host"),
            "port": data.get("port"),
            "username": data.get("username"),
            "password": data.get("password"),  # Note: In production, encrypt this!
            "database": data.get("database"),
            "uri": data.get("uri"),
            "created_at": datetime.now().isoformat()
        }
        
        # Save to file
        connection_file = CONNECTIONS_DIR / f"{connection_id}.json"
        with open(connection_file, "w", encoding="utf-8") as f:
            json.dump(connection_config, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            "status": "success",
            "message": "💾 Đã lưu connection config",
            "connection": connection_config
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Lỗi lưu connection: {str(e)}"
        }), 500


@app.route("/api/database/connections", methods=["GET"])
def list_database_connections():
    """List all saved database connections"""
    try:
        connections = []
        
        for conn_file in CONNECTIONS_DIR.glob("*.json"):
            with open(conn_file, "r", encoding="utf-8") as f:
                conn = json.load(f)
                # Don't expose password in list
                conn_safe = conn.copy()
                conn_safe["password"] = "***" if conn.get("password") else ""
                connections.append(conn_safe)
        
        # Sort by created_at descending
        connections.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return jsonify({
            "status": "success",
            "connections": connections,
            "count": len(connections)
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/api/database/use-connection/<connection_id>", methods=["POST"])
def use_database_connection(connection_id):
    """Set active database connection"""
    global active_db_connection
    
    try:
        connection_file = CONNECTIONS_DIR / f"{connection_id}.json"
        
        if not connection_file.exists():
            return jsonify({
                "status": "error",
                "message": "Connection không tồn tại"
            }), 404
        
        with open(connection_file, "r", encoding="utf-8") as f:
            connection_config = json.load(f)
        
        # Test connection before activating
        test_result = test_connection_internal(connection_config)
        
        if test_result["status"] == "success":
            active_db_connection = connection_config
            return jsonify({
                "status": "success",
                "message": f"✅ Đang sử dụng connection: {connection_config['name']}",
                "connection": connection_config
            })
        else:
            return jsonify({
                "status": "error",
                "message": test_result["message"]
            }), 500
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/api/database/delete-connection/<connection_id>", methods=["DELETE"])
def delete_database_connection(connection_id):
    """Delete a saved connection"""
    global active_db_connection
    
    try:
        connection_file = CONNECTIONS_DIR / f"{connection_id}.json"
        
        if not connection_file.exists():
            return jsonify({
                "status": "error",
                "message": "Connection không tồn tại"
            }), 404
        
        # Clear active connection if it's being deleted
        if active_db_connection and active_db_connection.get("id") == connection_id:
            active_db_connection = None
        
        connection_file.unlink()
        
        return jsonify({
            "status": "success",
            "message": "🗑️ Đã xóa connection"
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


def test_connection_internal(connection_config):
    """Internal function to test connection"""
    try:
        db_type = connection_config.get("db_type")
        connection_type = connection_config.get("connection_type")
        
        if db_type == "clickhouse":
            import clickhouse_connect
            
            client = clickhouse_connect.get_client(
                host=connection_config.get("host", "localhost"),
                port=int(connection_config.get("port", 8123)),
                username=connection_config.get("username", "default"),
                password=connection_config.get("password", ""),
                database=connection_config.get("database", "default")
            )
            
            result = client.query("SELECT version()")
            client.close()
            
            return {"status": "success", "message": "Connected"}
            
        elif db_type == "mongodb":
            from pymongo import MongoClient
            
            if connection_type == "atlas":
                uri = connection_config.get("uri")
                client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            else:
                host = connection_config.get("host", "localhost")
                port = int(connection_config.get("port", 27017))
                username = connection_config.get("username", "")
                password = connection_config.get("password", "")
                database = connection_config.get("database", "admin")
                
                if username and password:
                    uri = f"mongodb://{username}:{password}@{host}:{port}/{database}"
                else:
                    uri = f"mongodb://{host}:{port}/"
                
                client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            
            client.admin.command('ping')
            client.close()
            
            return {"status": "success", "message": "Connected"}
        
        return {"status": "error", "message": "Unsupported database type"}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================
# Main
# ============================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5002))
    print(f"\n{'='*60}")
    print(f"🗄️  Text2SQL Service Starting...")
    print(f"{'='*60}")
    print(f"📍 URL: http://localhost:{port}")
    print(f"🤖 Model: Gemini (Google)")
    print(f"🗄️  Databases: ClickHouse, MongoDB, SQL Server, PostgreSQL, MySQL")
    print(f"{'='*60}\n")
    
    app.run(host="0.0.0.0", port=port, debug=True)
