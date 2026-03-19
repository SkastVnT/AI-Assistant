# -*- coding: utf-8 -*-
# =======================================================================
# ============================== Config library ================================
# =======================================================================
"""
gpt41.py â€” Flask backend cho Text-to-SQL + Memory
- Há»— trá»£ upload nhiá»u schema (txt/json/jsonl/csv) -> ghÃ©p láº¡i Ä‘Æ°a vÃ o prompt
- Flow chat:
    1) TÃ¬m cÃ¢u há»i trong dataset (base + memory). CÃ³ -> tráº£ SQL ngay.
    2) KhÃ´ng cÃ³ -> tráº£ lá»i há»i xÃ¡c nháº­n (needs_confirmation=true).
    3) Náº¿u user tráº£ "cÃ³/Ä‘á»“ng Ã½" -> má»›i gá»i GROK generate SQL -> tráº£ vá» kÃ¨m needs_check=true.
    4) Frontend cÃ³ thá»ƒ gá»i /check Ä‘á»ƒ approve -> lÆ°u vÃ o knowledge_base/memory_sample.txt

- CÃ³ /evaluate: Ä‘á»c data/eval.jsonl Ä‘á»ƒ tÃ­nh Exact Match Accuracy (so sÃ¡nh chuá»—i).

YÃŠU Cáº¦U:
- ENV: GROK_API_KEY (Gemini Ä‘Ã£ bá»‹ xÃ³a)
- ThÆ° má»¥c: uploads/, data/, knowledge_base/
"""

import json
import os
import random
import re

# NOTE: Gemini Ä‘Ã£ bá»‹ xÃ³a - khÃ´ng import google.genai
import requests
try:
    from services.shared_env import load_shared_env
except ModuleNotFoundError:
    import sys
    from pathlib import Path

    for _parent in Path(__file__).resolve().parents:
        if (_parent / "services" / "shared_env.py").exists():
            if str(_parent) not in sys.path:
                sys.path.insert(0, str(_parent))
            break
    from services.shared_env import load_shared_env
from flask import Flask, jsonify, render_template, request
from sklearn.metrics import accuracy_score
from werkzeug.utils import secure_filename

try:
    from clickhouse_connect import get_client
except Exception:
    get_client = None

# ====== Load env & SDK ======
# Load .env from root directory (2 levels up)
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
load_shared_env(__file__)
REQUIRE_KNOWN_TABLE = os.getenv("SQLCODER_REQUIRE_KNOWN_TABLE", "1") == "1"
# Use DeepSeek as default (cheaper & more reliable than GROK)
SQLCODER_BACKEND = os.getenv("SQLCODER_BACKEND", "hf").lower()
SQLCODER_MODEL = os.getenv("SQLCODER_MODEL", "defog/sqlcoder-7b-2")
REFINE_STRATEGY = os.getenv("REFINE_STRATEGY", "deepseek").lower()

# ====== GROK API Configuration (deprecated, use DeepSeek instead) ======
GROK_API_KEY = os.getenv("GROK_API_KEY")
GROK_API_BASE = "https://api.x.ai/v1"
DEFAULT_MODEL = os.getenv("DEFAULT_SQL_MODEL", "deepseek")  # Default to DeepSeek (cheaper & reliable)

# ====== OpenAI API Configuration ======
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ====== DeepSeek API Configuration ======
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_BASE = "https://api.deepseek.com"

# Debug: Print API key status
print(f"[CONFIG] GROK_API_KEY: {'âœ“ Loaded' if GROK_API_KEY else 'âœ— Missing'}")
print(f"[CONFIG] OPENAI_API_KEY: {'âœ“ Loaded' if OPENAI_API_KEY else 'âœ— Missing'}")
print(f"[CONFIG] DEEPSEEK_API_KEY: {'âœ“ Loaded' if DEEPSEEK_API_KEY else 'âœ— Missing'}")
print(f"[CONFIG] DEFAULT_MODEL: {DEFAULT_MODEL}")

# Import OpenAI SDK
import openai


# ====== Flask app & constants ======
app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"txt", "json", "jsonl", "csv", "sql"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

PRETRAIN_DIR = os.path.join("pretrain")
os.makedirs(PRETRAIN_DIR, exist_ok=True)

DATA_DIR = "data"
MEMORY_DIR = os.path.join("knowledge_base", "memory")
DATASET_FILE = os.path.join(DATA_DIR, "dataset_base.jsonl")
EVAL_FILE = os.path.join(DATA_DIR, "eval.jsonl")
SAMPLE_UPLOADING_DIR = os.path.join("sample", "uploading")
SAMPLE_UPLOADED_DIR = os.path.join("sample", "uploaded")
os.makedirs(SAMPLE_UPLOADING_DIR, exist_ok=True)
os.makedirs(SAMPLE_UPLOADED_DIR, exist_ok=True)

# ==== State ====
SCHEMA_FILES: list[str] = []  # danh sÃ¡ch file schema Ä‘Ã£ upload
KNOWN_TABLES: set[str] = set()  # táº­p tÃªn báº£ng phÃ¡t hiá»‡n Ä‘Æ°á»£c
LAST_TABLE_UPLOADED: str | None = (
    None  # tÃªn báº£ng cuá»‘i cÃ¹ng phÃ¡t hiá»‡n Ä‘Æ°á»£c (Ä‘á»ƒ fallback há»£p lÃ½)
)
YES_WORDS = ["cÃ³", "Ä‘á»“ng Ã½", "yes", "ok", "oke", "okay"]
NO_WORDS = ["khÃ´ng", "khÃ´ng cáº§n", "no", "ko", "khong"]
pending_question: str | None = None  # cÃ¢u há»i chá» xÃ¡c nháº­n generate

# =======================================================================
# ============================== Helpers ================================
# =======================================================================


# ====== Schema Upload & Read ======
def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# Chuáº©n hÃ³a tÃªn báº£ng
def _normalize_table_name(raw: str) -> str:
    """Chuáº©n hÃ³a tÃªn: bá» backtick/quote, láº¥y pháº§n sau cÃ¹ng náº¿u cÃ³ schema.db.table"""
    raw = raw.strip().strip('`"')
    if "." in raw:
        raw = raw.split(".")[-1]
    return re.sub(r"[^\w]+", "_", raw)  # chá»‰ giá»¯ a-zA-Z0-9_


# TÃ¬m tÃªn báº£ng tá»« CREATE TABLE trong text
def parse_tables_from_text(text: str) -> list[str]:
    """
    TÃ¬m tÃªn báº£ng tá»« CREATE TABLE.
    Há»— trá»£: CREATE TABLE [db.]`name` ( ...  hoáº·c  CREATE TABLE name(
    """
    tables = []
    for m in re.finditer(r"CREATE\s+TABLE\s+([`\"\w\.]+)\s*\(", text, flags=re.I):
        t = _normalize_table_name(m.group(1))
        if t:
            tables.append(t)
    return tables


# Äá»c & ghÃ©p ná»™i dung táº¥t cáº£ schema Ä‘Ã£ upload
def read_all_schemas() -> str:
    texts = []
    for f in SCHEMA_FILES:
        if os.path.exists(f):
            with open(f, "r", encoding="utf-8") as fp:
                texts.append(fp.read())
    return "\n\n---\n\n".join(texts)


# ====== Dataset ======
def load_dataset(active_tables: set[str] | None = None) -> list[dict]:
    """
    Tráº£ list [{question, sql, _src}], trong Ä‘Ã³:
    - _src = "base" cho dataset gá»‘c
    - _src = "memory:<table>" cho memory 1 báº£ng
    - _src = "memories" cho file memories_01+02+...
    Chá»‰ Ä‘á»c Ä‘Ãºng file memory tÆ°Æ¡ng á»©ng bá»™ upload hiá»‡n táº¡i.
    """
    dataset = []
    # dataset gá»‘c
    if os.path.exists(DATASET_FILE):
        with open(DATASET_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    obj = json.loads(line)
                    obj["_src"] = "base"
                    dataset.append(obj)

    # memory 1 báº£ng
    if ACTIVE_AGG_FILE is None and ACTIVE_PRIMARY_TABLE:
        path = os.path.join(MEMORY_DIR, f"memory_{ACTIVE_PRIMARY_TABLE}.txt")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        if line.strip():
                            obj = json.loads(line)
                            obj["_src"] = f"memory:{ACTIVE_PRIMARY_TABLE}"
                            dataset.append(obj)
                    except:
                        pass

    # memories_... (multi)
    if ACTIVE_AGG_FILE and os.path.exists(ACTIVE_AGG_FILE):
        with open(ACTIVE_AGG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    if line.strip():
                        obj = json.loads(line)
                        obj["_src"] = "memories"
                        dataset.append(obj)
                except:
                    pass

    return dataset


def find_in_dataset(question: str) -> str | None:
    q = (question or "").strip().lower()
    for item in load_dataset(ACTIVE_TABLES):
        if (item.get("question") or "").strip().lower() == q:
            sql = (item.get("sql") or "").strip()
            if sql:
                return sql
    return None


# ====== Memory ======
def save_to_memory(question: str, sql: str) -> None:
    """LÆ°u cáº·p Q&A Ä‘Ã£ Ä‘Æ°á»£c duyá»‡t vÃ o memory."""
    with open(MEMORY_FILE, "a", encoding="utf-8") as f:
        f.write(
            json.dumps({"question": question, "sql": sql}, ensure_ascii=False) + "\n"
        )


# ====== Dataset lookup ======
def find_in_dataset(question: str) -> str | None:
    q = (question or "").strip().lower()
    for item in load_dataset(ACTIVE_TABLES):
        if (item.get("question") or "").strip().lower() == q:
            sql = (item.get("sql") or "").strip()
            if sql:
                return sql
    return None


# NOTE: Gemini Ä‘Ã£ bá»‹ xÃ³a - sá»­ dá»¥ng GROK thay tháº¿
def generate_sql_with_gemini(schema_text: str, question: str) -> str:
    """Deprecated: Redirect to GROK"""
    return generate_sql_with_grok(schema_text, question)


# ====== Generate SQL with GROK (Default) ======
def generate_sql_with_grok(schema_text: str, question: str) -> str:
    """Generate SQL using GROK API (xAI) - Default model"""
    if not GROK_API_KEY:
        raise ValueError("GROK_API_KEY not configured")
    
    prompt = f"""You are an expert SQL engineer specialized in ClickHouse.

Database schema(s):
{schema_text}

User question: {question}

Write a valid SQL query for ClickHouse.
- Return ONLY the SQL query, no explanation.
- If it's a SELECT without explicit LIMIT, add LIMIT 20.
- Use proper ClickHouse syntax.
"""
    
    client = openai.OpenAI(
        api_key=GROK_API_KEY,
        base_url=GROK_API_BASE
    )
    
    response = client.chat.completions.create(
        model="grok-3",
        messages=[
            {"role": "system", "content": "You are an expert SQL engineer. Output ONLY valid SQL queries without any explanation or markdown."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1,
        max_tokens=1000
    )
    
    return response.choices[0].message.content.strip()


# ====== Generate SQL with OpenAI GPT-4 ======
def generate_sql_with_openai(schema_text: str, question: str) -> str:
    """
    Gá»i OpenAI GPT-4 API Ä‘á»ƒ táº¡o SQL query.
    """
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not configured")
    
    prompt = f"""You are an expert SQL query generator. Given the following database schema and question, generate a valid SQL query.

Database Schema:
{schema_text}

Question: {question}

Generate ONLY the SQL query without any explanation. The query should be valid and optimized."""
    
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert SQL query generator."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise Exception(f"OpenAI API error: {str(e)}")


# ====== Generate SQL with DeepSeek ======
def generate_sql_with_deepseek(schema_text: str, question: str) -> str:
    """
    Gá»i DeepSeek API Ä‘á»ƒ táº¡o SQL query.
    """
    if not DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY not configured")
    
    prompt = f"""You are an expert SQL query generator. Given the following database schema and question, generate a valid SQL query.

Database Schema:
{schema_text}

Question: {question}

Generate ONLY the SQL query without any explanation. The query should be valid and optimized."""
    
    try:
        client = openai.OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_API_BASE
        )
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are an expert SQL query generator."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise Exception(f"DeepSeek API error: {str(e)}")


# ====== Generate Refined SQL with GROK ======
def generate_refined_sql_with_grok(
    schema_text: str, question: str, prev_sql: str, feedback: str, extra_context: str
) -> str:
    """Refine SQL using GROK API"""
    if not GROK_API_KEY:
        raise ValueError("GROK_API_KEY not configured")
    
    fb = (feedback or "").strip()
    extra = (extra_context or "").strip()
    
    prompt = f"""You are an advanced SQL engineer specialized in ClickHouse.

Database schema(s):
{schema_text}

User question:
{question}

Previous SQL (needs fix):
{prev_sql}

Short critique of what's wrong:
{fb if fb else "The previous SQL did not fully answer the question."}

Additional user notes / constraints to apply:
{extra if extra else "(no additional notes)"}

Revise the SQL so that it correctly answers the question.
Constraints:
- Use ClickHouse SQL dialect.
- Keep it as a single final query if possible.
- Return ONLY the final SQL, no explanation.
"""
    
    client = openai.OpenAI(
        api_key=GROK_API_KEY,
        base_url=GROK_API_BASE
    )
    
    response = client.chat.completions.create(
        model="grok-3",
        messages=[
            {"role": "system", "content": "You are an expert SQL engineer. Output ONLY valid SQL queries without any explanation or markdown."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1,
        max_tokens=1000
    )
    
    return response.choices[0].message.content.strip()


# NOTE: Gemini Ä‘Ã£ bá»‹ xÃ³a - hÃ m nÃ y redirect sang GROK
def generate_refined_sql(
    schema_text: str, question: str, prev_sql: str, feedback: str, extra_context: str
) -> str:
    """Deprecated: Redirect to GROK refine"""
    return generate_refined_sql_with_grok(schema_text, question, prev_sql, feedback, extra_context)


def infer_table_from_sql(sql: str) -> str | None:
    """TÃ¬m tÃªn báº£ng cÃ³ trong SQL dá»±a trÃªn KNOWN_TABLES."""
    if not sql:
        return None
    cand = None
    # Æ¯u tiÃªn tÃªn dÃ i hÆ¡n (trÃ¡nh trÃ¹ng prefix)
    for t in sorted(KNOWN_TABLES, key=len, reverse=True):
        # match theo tá»«/cá»™t hoáº·c cÃ³ backtick/quote
        pattern = rf"(?<!\w)`?{re.escape(t)}`?(?!\w)"
        if re.search(pattern, sql, flags=re.I):
            cand = t
            break
    return cand


# ====== Save to memory per table ======
def save_to_memory_per_table(question: str, sql: str) -> tuple[bool, str]:
    """
    - Náº¿u upload 1 schema: lÆ°u vÃ o memory_<table>.txt (table = ACTIVE_PRIMARY_TABLE hoáº·c tÃªn file duy nháº¥t).
    - Náº¿u upload nhiá»u schema: lÆ°u vÃ o ACTIVE_AGG_FILE (memories_01+02+... .txt).
    """
    # Multi-schema â†’ dÃ¹ng file memories_...
    if ACTIVE_AGG_FILE and ACTIVE_UPLOAD_ORDER and ACTIVE_IDMAP:
        os.makedirs(MEMORY_DIR, exist_ok=True)
        with open(ACTIVE_AGG_FILE, "a", encoding="utf-8") as f:
            f.write(
                json.dumps({"question": question, "sql": sql}, ensure_ascii=False)
                + "\n"
            )
        mapping = ", ".join(f"{ACTIVE_IDMAP[t]}={t}" for t in ACTIVE_UPLOAD_ORDER)
        return True, f"ÄÃ£ lÆ°u vÃ o {ACTIVE_AGG_FILE} (mapping: {mapping})"

    # Single-schema â†’ cá»‘ gáº¯ng láº¥y báº£ng â€œÄ‘ang hoáº¡t Ä‘á»™ngâ€
    table = ACTIVE_PRIMARY_TABLE

    # Fallback 1: suy tá»« SQL (nhÆ°ng chá»‰ khi trÃ¹ng ACTIVE_TABLES náº¿u cÃ³)
    if not table:
        t_from_sql = infer_table_from_sql(sql)
        if not ACTIVE_TABLES or (t_from_sql in ACTIVE_TABLES):
            table = t_from_sql

    # Fallback 2: Ä‘Ãºng 1 file Ä‘Ã£ upload â†’ láº¥y base name lÃ m báº£ng
    if not table and len(SCHEMA_FILES) == 1:
        base = os.path.splitext(os.path.basename(SCHEMA_FILES[0]))[0]
        table = _normalize_table_name(base)

    if not table:
        return False, "â— KhÃ´ng xÃ¡c Ä‘á»‹nh Ä‘Æ°á»£c báº£ng Ä‘ang hoáº¡t Ä‘á»™ng, nÃªn khÃ´ng lÆ°u."

    os.makedirs(MEMORY_DIR, exist_ok=True)
    path = os.path.join(MEMORY_DIR, f"memory_{table}.txt")
    with open(path, "a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {"question": question, "sql": sql, "table": table}, ensure_ascii=False
            )
            + "\n"
        )
    return True, f"ÄÃ£ lÆ°u vÃ o {path}"


# ====== ClickHouse Client & SQL Execution ======
def get_ch_client():
    if get_client is None:
        return None
    try:
        return get_client(
            host=os.getenv("CLICKHOUSE_HOST", "103.232.122.212"),
            port=int(os.getenv("CLICKHOUSE_PORT", "8123")),
            username=os.getenv("CLICKHOUSE_USER", "thanhnguyen"),
            password=os.getenv("CLICKHOUSE_PASSWORD", "thanhnguyen@123"),
            database=os.getenv("CLICKHOUSE_DB", "cdn"),
        )
    except Exception:
        return None


# ====== SQL Execution ======
def try_execute_sql(sql: str | None):
    if not sql:
        return None, "NO_SQL"
    cli = get_ch_client()
    if cli is None:
        return None, "NO_DB"
    try:
        q = cli.query(sql)
        rows = q.result_rows or []
        cols = q.column_names or []
        if not rows:
            return None, "OK_EMPTY"
        data = [dict(zip(cols, r)) for r in rows]
        return data, "OK"
    except Exception as e:
        return None, f"ERR:{e}"


# ====== Result Preview ======
def preview_result_text(data):
    if data is None:
        return "null"
    try:
        return json.dumps(
            data[:5] if isinstance(data, list) else data, ensure_ascii=False
        )
    except Exception:
        return "null"


# ====== Empty Dir ======
def _empty_dir(path: str):
    try:
        if not os.path.isdir(path):
            os.makedirs(path, exist_ok=True)
            return
        for name in os.listdir(path):
            try:
                p = os.path.join(path, name)
                if os.path.isfile(p):
                    os.remove(p)
                elif os.path.isdir(p):
                    import shutil

                    shutil.rmtree(p, ignore_errors=True)
            except:
                pass
    except:
        pass


# ====== Call SQLCoder on HF ======
def _sqlcoder_prompt(schema_text, question):
    return f"""You are SQLCoder specialized in ClickHouse.
Schema:
{schema_text}

Question: {question}

Return ONLY one SQL statement. 
If it's a SELECT and no pagination is specified, add LIMIT 20 to preview data.
Do not include any explanations or markdown fences."""


# Gá»i SQLCoder qua HF Inference API
def call_sqlcoder_hf(schema_text: str, question: str) -> str | None:
    token = os.getenv("HF_API_TOKEN", "")
    if not token:
        return None
    url = f"https://api-inference.huggingface.co/models/{SQLCODER_MODEL}"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "inputs": _sqlcoder_prompt(schema_text, question),
        "options": {"wait_for_model": True},
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        # HF cÃ³ thá»ƒ tráº£ list[{'generated_text': '...'}] hoáº·c text Ä‘Æ¡n
        if isinstance(data, list) and data and "generated_text" in data[0]:
            return data[0]["generated_text"].strip()
        if isinstance(data, dict) and "generated_text" in data:
            return data["generated_text"].strip()
        # CÃ¡c pipeline khÃ¡c:
        if isinstance(data, str):
            return data.strip()
    except Exception:
        return None
    return None


# Gá»i SQLCoder qua Ollama API
def call_sqlcoder_ollama(schema_text: str, question: str) -> str | None:
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    try:
        r = requests.post(
            f"{host}/api/generate",
            json={
                "model": SQLCODER_MODEL,
                "prompt": _sqlcoder_prompt(schema_text, question),
                "stream": False,
            },
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        return (data.get("response") or "").strip()
    except Exception:
        return None


# ====== Few-shot Prompt for SQLCoder ======
def build_few_shot_prompt(schema_text: str, question: str, n_examples=3):
    few = []
    if os.path.exists(DATASET_FILE):
        with open(DATASET_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if len(few) >= n_examples:
                    break
                obj = json.loads(line)
                q = obj.get("question")
                s = obj.get("sql")
                if q and s:
                    few.append((q, s))
    # fallback generic examples
    while len(few) < n_examples:
        few.append(
            ("Hiá»ƒn thá»‹ 5 dÃ²ng Ä‘áº§u tiÃªn cá»§a báº£ng users", "SELECT * FROM users LIMIT 5")
        )
    examples_text = "\n\n".join([f"Example:\nQuestion: {q}\nSQL: {s}" for q, s in few])
    prompt = f"""{examples_text}

Schema:
{schema_text}

Question: {question}

Return ONLY the SQL query. If it's a SELECT without LIMIT, append "LIMIT 20".
"""
    return prompt


# Gá»i SQLCoder qua vLLM API
def call_sqlcoder_vllm(schema_text: str, question: str) -> str | None:
    base = os.getenv("VLLM_BASE_URL", "")
    model = os.getenv("VLLM_MODEL", SQLCODER_MODEL)
    if not base:
        return None
    try:
        r = requests.post(
            f"{base}/chat/completions",
            json={
                "model": model,
                "messages": [
                    {"role": "user", "content": _sqlcoder_prompt(schema_text, question)}
                ],
                "temperature": 0,
            },
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        text = data["choices"][0]["message"]["content"]
        return (text or "").strip()
    except Exception:
        return None


# ====== Generate SQL with SQLCoder (HF / Ollama / vLLM) ======

# Regex Ä‘á»ƒ tÃ¬m code-fence ``` ... ```
SQL_FENCE_RE = re.compile(r"```+[a-zA-Z]*\s*([\s\S]*?)```", re.I)


def strip_prompt_prefix(prompt: str, text: str) -> str:
    if not prompt or not text:
        return text or ""
    return text[len(prompt) :].lstrip() if text.startswith(prompt) else text


def extract_sql(text: str) -> str:
    if not text:
        return ""
    m = SQL_FENCE_RE.search(text)
    if m:
        text = m.group(1)
    text = re.sub(r"(?im)^status\s*:\s*.*$", "", text)
    text = re.sub(r"(?im)^result\s*:\s*.*$", "", text)
    text = re.sub(r"(?i)^\s*(sql\s*Ä‘Æ°á»£c\s*táº¡o|sql|query)\s*[:\-]*", "", text).strip()
    m2 = re.search(r"(?is)\b(select|insert|update|delete)\b[\s\S]*$", text)
    if m2:
        text = text[m2.start() :].strip()
    text = re.sub(r"`{3,}", "", text).strip()
    return text


# Extract SQL from text
def generate_sql_with_sqlcoder(schema_text: str, question: str) -> str | None:
    prompt = _sqlcoder_prompt(schema_text, question)

    if SQLCODER_BACKEND == "ollama":
        raw = call_sqlcoder_ollama(schema_text, question)
    elif SQLCODER_BACKEND == "vllm":
        raw = call_sqlcoder_vllm(schema_text, question)
    else:
        raw = call_sqlcoder_hf(schema_text, question)

    if not raw:
        return None
    # HF thÆ°á»ng echo láº¡i prompt -> cáº¯t Ä‘i
    raw = strip_prompt_prefix(prompt, raw)
    sql = extract_sql(raw)
    return sql or None


# Extract SQL from text
def generate_refined_sql_with_sqlcoder(
    schema_text: str, question: str, prev_sql: str, feedback: str, extra: str
) -> str | None:
    prompt = f"""You are SQLCoder specialized in ClickHouse.

Database schema(s):
{schema_text}

User question:
{question}

Previous SQL (needs fix):
{prev_sql}

What's wrong with the previous SQL:
{feedback or "The previous SQL did not fully answer the question."}

Additional constraints/notes:
{extra or "(none)"}

Revise the SQL so it correctly answers the question.
Return ONLY the final SQL. No markdown fences, no explanation.
"""
    out = generate_sql_with_sqlcoder(schema_text, prompt)  # tÃ¡i dÃ¹ng caller SQLCoder
    return extract_sql(out or "")


# Extract SQL from text
def hybrid_refine_sql(
    schema_text: str, question: str, prev_sql: str, feedback: str, extra: str, model: str = None
) -> tuple[str, str]:
    """
    Tráº£ vá» (sql, source):
      source in {"refined_grok","refined_sqlcoder","refined_sqlcoder+grok"}
    """
    model = model or DEFAULT_MODEL
    
    # GROK - Default and preferred
    if model == "grok":
        try:
            sql = generate_refined_sql_with_grok(schema_text, question, prev_sql, feedback, extra)
            return extract_sql(sql), "refined_grok"
        except Exception as e:
            # Fallback to SQLCoder
            print(f"Grok refine error: {e}, falling back to SQLCoder")
            sql = generate_refined_sql_with_sqlcoder(schema_text, question, prev_sql, feedback, extra) or ""
            return sql, "refined_sqlcoder"
    
    if model == "sqlcoder" or REFINE_STRATEGY == "sqlcoder":
        sql1 = (
            generate_refined_sql_with_sqlcoder(
                schema_text, question, prev_sql, feedback, extra
            )
            or ""
        )
        return sql1, "refined_sqlcoder"

    # Default to GROK
    sql2 = extract_sql(
        generate_refined_sql_with_grok(schema_text, question, prev_sql, feedback, extra)
    )
    return sql2, "refined_grok"


# =====================================================#
# ------- Router: SQLCoder â†’ (fallback) GROK -------

# ====== Hybrid Strategy ======
HYBRID_STRATEGY = os.getenv("HYBRID_STRATEGY", "cascade").lower()


def looks_valid_sql(sql: str) -> bool:
    if not sql:
        return False
    if len(sql) < 10:
        return False
    if not re.search(r"\bselect\b|\binsert\b|\bupdate\b|\bdelete\b", sql, flags=re.I):
        return False
    # chá»‰ yÃªu cáº§u cÃ³ tÃªn báº£ng náº¿u báº­t cá»
    if REQUIRE_KNOWN_TABLE and KNOWN_TABLES:
        hit = any(
            re.search(rf"\b{re.escape(t)}\b", sql, flags=re.I) for t in KNOWN_TABLES
        )
        if not hit:
            return False
    return True


# ====== Hybrid Generate SQL ======
def hybrid_generate_sql(schema_text: str, question: str, model: str = None) -> tuple[str, str]:
    """
    Tráº£ (sql, source): source in {"grok","openai","deepseek","sqlcoder","sqlcoder+grok","cascade"}
    model: "grok" (default), "openai", "deepseek", "sqlcoder", "cascade"
    """
    model = model or DEFAULT_MODEL
    
    # GROK - Default and preferred
    if model == "grok":
        try:
            print(f"[DEBUG] Using Grok-3 for SQL generation...")
            sql = generate_sql_with_grok(schema_text, question)
            print(f"[DEBUG] Grok-3 success! SQL: {sql[:100]}...")
            return extract_sql(sql), "grok"
        except Exception as e:
            # Fallback to DeepSeek or OpenAI instead of Gemini
            print(f"[ERROR] Grok error: {e}")
            if DEEPSEEK_API_KEY:
                try:
                    print(f"[DEBUG] Falling back to DeepSeek...")
                    sql = generate_sql_with_deepseek(schema_text, question)
                    return extract_sql(sql), "deepseek"
                except Exception as e2:
                    print(f"[ERROR] DeepSeek also failed: {e2}")
            if OPENAI_API_KEY:
                try:
                    print(f"[DEBUG] Falling back to OpenAI...")
                    sql = generate_sql_with_openai(schema_text, question)
                    return extract_sql(sql), "openai"
                except Exception as e3:
                    print(f"[ERROR] OpenAI also failed: {e3}")
            raise Exception("All models failed. Please check API keys.")
    
    # OpenAI GPT-4
    if model == "openai":
        try:
            print(f"[DEBUG] Using OpenAI GPT-4 for SQL generation...")
            sql = generate_sql_with_openai(schema_text, question)
            print(f"[DEBUG] OpenAI success! SQL: {sql[:100]}...")
            return extract_sql(sql), "openai"
        except Exception as e:
            print(f"[ERROR] OpenAI error: {e}, falling back to DeepSeek")
            if DEEPSEEK_API_KEY:
                sql = generate_sql_with_deepseek(schema_text, question)
                return extract_sql(sql), "deepseek"
            raise Exception("OpenAI and DeepSeek not available")
    
    # DeepSeek
    if model == "deepseek":
        try:
            sql = generate_sql_with_deepseek(schema_text, question)
            return extract_sql(sql), "deepseek"
        except Exception as e:
            print(f"DeepSeek error: {e}, falling back to Grok")
            if GROK_API_KEY:
                sql = generate_sql_with_grok(schema_text, question)
                return extract_sql(sql), "grok"
            raise Exception("DeepSeek and Grok not available")
    
    # Redirect gemini to grok (Gemini Ä‘Ã£ bá»‹ xÃ³a)
    if model == "gemini" or HYBRID_STRATEGY == "gemini_only":
        return generate_sql_with_grok(schema_text, question), "grok"

    if model == "sqlcoder" or HYBRID_STRATEGY == "sqlcoder_only":
        sql1 = generate_sql_with_sqlcoder(schema_text, question)
        return (sql1 or ""), "sqlcoder"

    # cascade (model == "cascade")
    sql1 = generate_sql_with_sqlcoder(schema_text, question)  # Ä‘Ã£ extract_sql
    if sql1 and looks_valid_sql(sql1):
        return sql1, "sqlcoder"

    # náº¿u sql1 None/rá»—ng -> gá»i GROK
    sql2 = generate_sql_with_grok(schema_text, question)
    return sql2, ("sqlcoder+grok" if sql1 else "grok")


# ===== Pretrain helpers =====
PRETRAIN_ON_UPLOAD = os.getenv("PRETRAIN_ON_UPLOAD", "1") == "1"
PRETRAIN_ROUNDS = int(os.getenv("PRETRAIN_ROUNDS", "15"))
PRETRAIN_STRATEGY = os.getenv("PRETRAIN_STRATEGY", "sqlcoder").lower()


# ====== Active Schema & Tables ======
def parse_table_columns_map(schema_text: str) -> dict[str, list[str]]:
    """
    TÃ¡ch map {table: [cols]} tá»« DDL Ä‘Æ¡n giáº£n: CREATE TABLE name ( ... ).
    KhÃ´ng báº¯t buá»™c chÃ­nh xÃ¡c 100%, nhÆ°ng Ä‘á»§ Ä‘á»ƒ gá»£i Ã½ cÃ¢u há»i.
    """
    m = {}
    for mm in re.finditer(
        r"CREATE\s+TABLE\s+([`\"\w\.]+)\s*\((.*?)\)", schema_text, flags=re.I | re.S
    ):
        t = _normalize_table_name(mm.group(1))
        block = mm.group(2)
        cols = []
        for cm in re.finditer(r"^\s*`?(\w+)`?\s+\w+", block, flags=re.M):
            cols.append(cm.group(1))
        if t:
            m[t] = cols
    return m


# ====== Synthesize Questions ======
def synthesize_questions(schema_text: str, limit: int = 15) -> list[tuple[str, str]]:
    """
    Sinh list [(question, table_guess)] tá»‘i Ä‘a 'limit' cÃ¢u, Æ°u tiÃªn má»—i báº£ng vÃ i cÃ¢u.
    """
    table_cols = parse_table_columns_map(schema_text)
    tables = (
        list(table_cols.keys())
        or list(ACTIVE_TABLES)
        or ([ACTIVE_PRIMARY_TABLE] if ACTIVE_PRIMARY_TABLE else [])
    )
    tables = [t for t in tables if t] or []

    if not tables:
        return []

    qs: list[tuple[str, str]] = []

    def pick(cols, *names):
        for n in names:
            for c in cols:
                if c.lower() == n.lower():
                    return c
        return None

    for t in tables:
        cols = table_cols.get(t, [])
        id_col = pick(cols, "id", f"{t}_id")
        time_col = pick(
            cols,
            "created_at",
            "create_time",
            "created_time",
            "date",
            "dt",
            "ts",
            "timestamp",
        )
        user_col = pick(cols, "user_id", "account_id")
        shop_col = pick(cols, "shop_id")
        conv_col = pick(cols, "conversation_id", "ticket_id", "order_id")

        qs.extend(
            [
                (f"Hiá»ƒn thá»‹ 20 dÃ²ng Ä‘áº§u tiÃªn cá»§a báº£ng {t}", t),
                (f"Äáº¿m tá»•ng sá»‘ báº£n ghi trong báº£ng {t}", t),
            ]
        )

        if id_col:
            qs.append((f"Äáº¿m sá»‘ báº£n ghi theo {id_col} trong báº£ng {t}", t))
        if time_col:
            qs.append(
                (
                    f"Äáº¿m sá»‘ báº£n ghi theo ngÃ y dá»±a trÃªn {time_col} trong 7 ngÃ y gáº§n nháº¥t cá»§a báº£ng {t}",
                    t,
                )
            )
        if shop_col:
            qs.append((f"Äáº¿m sá»‘ lÆ°á»£ng shop_id khÃ¡c nhau trong báº£ng {t}", t))
            qs.append((f"Top 10 shop_id cÃ³ nhiá»u báº£n ghi nháº¥t trong báº£ng {t}", t))
        if user_col:
            qs.append((f"Top 10 {user_col} cÃ³ nhiá»u báº£n ghi nháº¥t trong báº£ng {t}", t))
        if conv_col:
            qs.append((f"Äáº¿m sá»‘ {conv_col} khÃ¡c nhau trong báº£ng {t}", t))

    # cáº¯t vá» Ä‘Ãºng sá»‘ lÆ°á»£ng
    uniq = []
    seen = set()
    for q, t in qs:
        if q not in seen:
            uniq.append((q, t))
            seen.add(q)
        if len(uniq) >= limit:
            break
    return uniq


# ====== Pretrain after upload ======
def pretrain_after_upload(
    schema_text: str, rounds: int | None = None, strategy: str | None = None
) -> dict:
    rounds = int(rounds or PRETRAIN_ROUNDS)
    strategy = (strategy or PRETRAIN_STRATEGY).lower()

    base_pairs = synthesize_questions(schema_text, limit=rounds * 4)
    seen = collect_seen_questions_for_active()
    pool = [(q, t) for (q, t) in base_pairs if q not in seen]
    random.shuffle(pool)
    pairs = pool[:rounds] if pool else []

    log_path = current_pretrain_log_path()
    tried = saved = 0
    preview_items = []
    all_items = []

    for question, _tbl in pairs:
        tried += 1
        raw = None
        src = None
        if strategy == "grok":
            raw = generate_sql_with_grok(schema_text, question)
            src = "grok"
        elif strategy == "cascade":
            raw, _ = hybrid_generate_sql(schema_text, question)
            src = "cascade"
        else:
            raw = generate_sql_with_sqlcoder(schema_text, question)
            src = "sqlcoder"

        sql_txt = extract_sql(raw or "")
        if not sql_txt:
            item = {
                "question": question,
                "raw": raw,
                "sql": None,
                "exec_status": "NO_SQL",
                "saved": False,
                "source": src,
            }
        else:
            data, st = try_execute_sql(sql_txt)
            ok, msg = save_to_memory_per_table(question, sql_txt)
            item = {
                "question": question,
                "raw": raw,
                "sql": sql_txt,
                "exec_status": st,
                "saved": ok,
                "message": msg,
                "source": src,
            }
            if ok:
                saved += 1

        all_items.append(item)
        if len(preview_items) < 5:
            preview_items.append(item)

        if log_path:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

        if saved >= rounds:
            break

    # write human readable file
    bundle_base = current_bundle_base() or "pretrain_latest"
    display_base = re.sub(r"^bundle_", "", bundle_base)
    pretrain_path = os.path.join(PRETRAIN_DIR, f"{display_base}.txt")

    try:
        with open(pretrain_path, "w", encoding="utf-8") as pf:
            pf.write(f"Pretrain for bundle: {bundle_base}\n")
            pf.write(f"Rounds requested: {rounds}\n")
            pf.write(f"Strategy: {strategy}\n")
            pf.write(f"Generated: {len(all_items)}, saved={saved}\n")
            pf.write("=" * 60 + "\n\n")
            for i, it in enumerate(all_items, start=1):
                pf.write(f"#{i}\n")
                pf.write(f"Q: {it.get('question')}\n")
                pf.write(f"SQL: {it.get('sql') or '(NO_SQL)'}\n")
                src = it.get("source") or ""
                pretty = (
                    "SQLCoder-7B-2"
                    if src == "sqlcoder"
                    else (
                        "GROK"
                        if src == "grok"
                        else (
                            "SQLCoder-7B-2 â†’ GROK (cascade)"
                            if src == "cascade"
                            else src
                        )
                    )
                )
                pf.write(f"Model: {pretty}\n")
                pf.write(f"Status: {it.get('exec_status') or ''}\n")
                pf.write(f"Saved: {'âœ“' if it.get('saved') else 'Ã—'}\n")
                if it.get("message"):
                    pf.write(f"Message: {it.get('message')}\n")
                if it.get("raw"):
                    raw_short = (
                        it.get("raw")
                        if len(it.get("raw")) <= 1000
                        else it.get("raw")[:1000] + " ...[truncated]"
                    )
                    pf.write("Raw:\n")
                    pf.write(raw_short + "\n")
                pf.write("-" * 40 + "\n\n")
    except Exception as e:
        # náº¿u lá»—i file há»‡ thá»‘ng, in ra log server Ä‘á»ƒ debug
        print("Lá»—i ghi pretrain file:", e)

    return {
        "done": True,
        "tried": tried,
        "saved": saved,
        "log_file": log_path,
        "pretrain_file": pretrain_path,
        "preview": preview_items,
    }


# ====== Current bundle info ======
def current_bundle_base() -> str | None:
    if not SCHEMA_FILES:
        return None
    base = os.path.basename(SCHEMA_FILES[0])
    return os.path.splitext(base)[0]


# ====== Current pretrain log path ======
def current_pretrain_log_path() -> str | None:
    base = current_bundle_base()
    if not base:
        return None
    return os.path.join(SAMPLE_UPLOADED_DIR, f"{base}.pretrain.jsonl")


# ====== Normalize SQL ======
def norm_sql(sql: str) -> str:
    if not sql:
        return ""
    s = sql.strip()
    # bá» ; á»Ÿ cuá»‘i vÃ  chuáº©n hÃ³a khoáº£ng tráº¯ng
    s = re.sub(r";\s*$", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


# ====== Load bundle tables ======
def load_bundle_tables(bundle_path: str) -> set[str]:
    """Äá»c bundle_* trong sample/uploaded/ Ä‘á»ƒ lá»c theo tÃªn báº£ng hiá»‡n dÃ¹ng (optional)."""
    if not bundle_path or not os.path.exists(bundle_path):
        return set()
    with open(bundle_path, "r", encoding="utf-8") as f:
        text = f.read()
    names = set()
    # TÃ¬m tÃªn báº£ng tá»« CREATE TABLE ...
    for m in re.finditer(r"CREATE\s+TABLE\s+([`\"\w\.]+)\s*\(", text, flags=re.I):
        raw = m.group(1).strip('`"')
        if "." in raw:
            raw = raw.split(".")[-1]
        names.add(re.sub(r"[^\w]+", "_", raw))
    return names


# ====== Collect seen questions ======
def collect_seen_questions_for_active() -> set[str]:
    """
    Gom táº¥t cáº£ 'question' Ä‘Ã£ lÆ°u trong memory hiá»‡n hÃ nh (single hoáº·c memories_*).
    DÃ¹ng Ä‘á»ƒ trÃ¡nh sinh trÃ¹ng.
    """
    seen = set()
    # single
    if ACTIVE_AGG_FILE is None and ACTIVE_PRIMARY_TABLE:
        p = os.path.join(MEMORY_DIR, f"memory_{ACTIVE_PRIMARY_TABLE}.txt")
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            seen.add(json.loads(line).get("question", ""))
                        except:
                            pass
    # multi
    if ACTIVE_AGG_FILE and os.path.exists(ACTIVE_AGG_FILE):
        with open(ACTIVE_AGG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        seen.add(json.loads(line).get("question", ""))
                    except:
                        pass
    return {q for q in seen if q}


# ====== Pretrain after upload (improved) ======
def pretrain_after_upload(
    schema_text: str, rounds: int | None = None, strategy: str | None = None
) -> dict:
    rounds = int(rounds or PRETRAIN_ROUNDS)
    strategy = (strategy or PRETRAIN_STRATEGY).lower()

    base_pairs = synthesize_questions(schema_text, limit=rounds * 4)  # sinh dÆ° rá»“i lá»c
    seen = collect_seen_questions_for_active()
    # lá»c trÃ¹ng + trá»™n
    pool = [(q, t) for (q, t) in base_pairs if q not in seen]
    random.shuffle(pool)
    pairs = pool[:rounds] if pool else []

    log_path = current_pretrain_log_path()
    tried = saved = 0
    preview_items = []

    for question, _tbl in pairs:
        tried += 1
        # chá»n model sinh SQL
        if strategy == "grok":
            raw = generate_sql_with_grok(schema_text, question)
            src = "grok"
        elif strategy == "cascade":
            raw, _ = hybrid_generate_sql(schema_text, question)
            src = "cascade"
        else:
            raw = generate_sql_with_sqlcoder(schema_text, question)
            src = "sqlcoder"
        sql_txt = extract_sql(raw or "")

        if not sql_txt:
            item = {
                "question": question,
                "raw": raw,
                "status": "NO_SQL",
                "saved": False,
                "source": src,
            }
        else:
            data, st = try_execute_sql(sql_txt)
            ok, msg = save_to_memory_per_table(question, sql_txt)
            item = {
                "question": question,
                "raw": raw,
                "sql": sql_txt,
                "exec_status": st,
                "saved": ok,
                "message": msg,
                "source": src,
            }
            if ok:
                saved += 1

        if log_path:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

        if len(preview_items) < 5:
            preview_items.append(item)
        if saved >= rounds:  # Ä‘á»§ sá»‘ save yÃªu cáº§u thÃ¬ dá»«ng
            break

    return {
        "done": True,
        "tried": tried,
        "saved": saved,
        "log_file": log_path,
        "preview": preview_items,
    }


# ====== Get pretrain file ======
@app.route("/pretrain-file", methods=["GET"])
def pretrain_file():
    bundle_base = current_bundle_base() or "pretrain_latest"
    display_base = re.sub(r"^bundle_", "", bundle_base)
    pretrain_path = os.path.join(PRETRAIN_DIR, f"{display_base}.txt")
    if not os.path.exists(pretrain_path):
        return jsonify({"exists": False, "path": pretrain_path}), 200
    try:
        with open(pretrain_path, "r", encoding="utf-8") as f:
            content = f.read()
        return jsonify({"exists": True, "path": pretrain_path, "content": content}), 200
    except Exception as e:
        return jsonify({"exists": False, "error": str(e)}), 200


# =======================================================================
# ============================== Routes ================================
# =======================================================================


# ====== Home ======
@app.route("/")
def index():
    return render_template("index_modern.html")


# ====== Upload schema ======
@app.route("/upload-schema", methods=["POST"])
def upload_schema():
    """
    Upload 1..n schema, ghi táº¡m tá»«ng file + meta vÃ o ./sample/uploading/,
    gá»™p láº¡i thÃ nh 1 bundle trong ./sample/uploaded/, xoÃ¡ táº¡m,
    vÃ  set SCHEMA_FILES trá» tá»›i bundle Ä‘á»ƒ chat dÃ¹ng Ä‘Ãºng bá»™ má»›i nháº¥t.
    """
    global SCHEMA_FILES, KNOWN_TABLES, LAST_TABLE_UPLOADED
    global ACTIVE_TABLES, ACTIVE_PRIMARY_TABLE, ACTIVE_IDMAP, ACTIVE_UPLOAD_ORDER, ACTIVE_AGG_FILE

    if "file" not in request.files:
        return jsonify({"error": "KhÃ´ng cÃ³ file Ä‘Æ°á»£c gá»­i"}), 400

    # RESET state
    SCHEMA_FILES = []
    KNOWN_TABLES = set()
    LAST_TABLE_UPLOADED = None
    ACTIVE_TABLES = set()
    ACTIVE_PRIMARY_TABLE = None
    ACTIVE_IDMAP = {}
    ACTIVE_UPLOAD_ORDER = []
    ACTIVE_AGG_FILE = None

    # Dá»n thÆ° má»¥c táº¡m
    _empty_dir(SAMPLE_UPLOADING_DIR)

    files = request.files.getlist("file")
    saved, detected, per_file_blocks = [], [], []

    for file in files:
        if not file or file.filename == "":
            continue
        if not allowed_file(file.filename):
            continue

        filename = secure_filename(file.filename)
        path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(path)
        saved.append(filename)

        # Äá»c ná»™i dung Ä‘á»ƒ phÃ¢n tÃ­ch + táº¡o báº£n sao trong uploading/
        try:
            with open(path, "r", encoding="utf-8") as fp:
                text = fp.read()
        except Exception:
            text = ""

        # Ghi báº£n sao & meta
        base = os.path.splitext(filename)[0]
        uploading_copy = os.path.join(SAMPLE_UPLOADING_DIR, filename)
        with open(uploading_copy, "w", encoding="utf-8") as w:
            w.write(text or "")
        meta = {
            "filename": filename,
            "base": _normalize_table_name(base),
            "tables": parse_tables_from_text(text) or [_normalize_table_name(base)],
        }
        with open(
            os.path.join(SAMPLE_UPLOADING_DIR, f"{base}.meta.json"),
            "w",
            encoding="utf-8",
        ) as w:
            json.dump(meta, w, ensure_ascii=False, indent=2)

        # Thu tháº­p tÃªn báº£ng + block Ä‘á»ƒ gá»™p
        names = meta["tables"]
        for t in names:
            if t:
                KNOWN_TABLES.add(t)
                detected.append(t)
                LAST_TABLE_UPLOADED = t
        per_file_blocks.append(f"-- FILE: {filename}\n{text}\n")

    # Set active theo thá»© tá»± upload
    ACTIVE_TABLES = set(detected)
    ACTIVE_UPLOAD_ORDER = detected[:]  # giá»¯ Ä‘Ãºng thá»© tá»±
    ACTIVE_PRIMARY_TABLE = detected[0] if detected else None

    # Cáº¥p ID 2 chá»¯ sá»‘
    for i, t in enumerate(ACTIVE_UPLOAD_ORDER[:99], start=1):
        ACTIVE_IDMAP[t] = str(i).zfill(2)

    # Táº¡o bundle file trong ./sample/uploaded/
    if len(ACTIVE_UPLOAD_ORDER) > 1 and ACTIVE_IDMAP:
        mem_name = (
            "memories_"
            + "+".join(ACTIVE_IDMAP[t] for t in ACTIVE_UPLOAD_ORDER)
            + ".txt"
        )
        ACTIVE_AGG_FILE = os.path.join(MEMORY_DIR, mem_name)
        bundle_name = (
            "bundle_" + "+".join(ACTIVE_IDMAP[t] for t in ACTIVE_UPLOAD_ORDER) + ".txt"
        )
    else:
        ACTIVE_AGG_FILE = None
        bundle_name = (
            f"bundle_{ACTIVE_PRIMARY_TABLE or (saved[0] if saved else 'single')}.txt"
        )

    bundle_path = os.path.join(SAMPLE_UPLOADED_DIR, bundle_name)
    with open(bundle_path, "w", encoding="utf-8") as w:
        w.write("\n\n".join(per_file_blocks))

    # LÆ°u bundle meta
    bundle_meta = {
        "files": saved,
        "tables": ACTIVE_UPLOAD_ORDER,
        "id_map": ACTIVE_IDMAP,
        "bundle_file": os.path.basename(bundle_path),
        "memories_file": os.path.basename(ACTIVE_AGG_FILE) if ACTIVE_AGG_FILE else None,
    }
    with open(
        os.path.join(
            SAMPLE_UPLOADED_DIR, f"{os.path.splitext(bundle_name)[0]}.meta.json"
        ),
        "w",
        encoding="utf-8",
    ) as w:
        json.dump(bundle_meta, w, ensure_ascii=False, indent=2)

    # XÃ“A sáº¡ch uploading/*
    _empty_dir(SAMPLE_UPLOADING_DIR)

    # Chá»‰ dÃ¹ng bundle Ä‘á»ƒ Ä‘á»c schema
    SCHEMA_FILES = [bundle_path]

    preview = read_all_schemas()

    # ðŸ”¥ cháº¡y pretrain sau upload
    pretrain_info = pretrain_after_upload(preview)

    return jsonify(
        {
            "message": f"ÄÃ£ upload: {', '.join(saved)}",
            "schema_text": preview,
            "files_uploaded": saved,
            "tables": ACTIVE_UPLOAD_ORDER,
            "id_map": ACTIVE_IDMAP,
            "bundle_file": os.path.basename(bundle_path),
            "bundle_path": bundle_path,
            "memories_filename": (
                os.path.basename(ACTIVE_AGG_FILE) if ACTIVE_AGG_FILE else None
            ),
            "active_primary_table": ACTIVE_PRIMARY_TABLE,
            "pretrain": pretrain_info,  # <â€” xem nhanh Ä‘Ã£ sinh Ä‘Æ°á»£c bao nhiÃªu Q&A
        }
    )


@app.route("/pretrain-report", methods=["GET"])
def pretrain_report():
    """
    Tráº£ file pretrain log (jsonl) cá»§a bundle hiá»‡n táº¡i.
    - Tráº£ tá»‘i Ä‘a `max_lines` cuá»‘i (máº·c Ä‘á»‹nh 50).
    - Báº£o vá»‡ lá»—i JSON, bá» qua dÃ²ng khÃ´ng parse Ä‘Æ°á»£c.
    - Tráº£ order: newest first (items[0] lÃ  má»¥c má»›i nháº¥t).
    """
    log_path = current_pretrain_log_path()
    if not log_path:
        return (
            jsonify(
                {
                    "count": 0,
                    "items": [],
                    "message": "ChÆ°a cÃ³ bundle hiá»‡n hÃ nh hoáº·c chÆ°a pretrain.",
                }
            ),
            200,
        )
    if not os.path.exists(log_path):
        return (
            jsonify(
                {
                    "count": 0,
                    "items": [],
                    "message": f"ChÆ°a cÃ³ log pretrain: {log_path} (file khÃ´ng tá»“n táº¡i).",
                    "log_path": log_path,
                }
            ),
            200,
        )

    # get query param max_lines (safe)
    try:
        max_lines = int(request.args.get("max_lines", "50"))
    except:
        max_lines = 50
    max_lines = max(1, min(1000, max_lines))

    # efficient tail: Ä‘á»c tá»« cuá»‘i file, láº¥y max_lines dÃ²ng
    items = []
    try:
        with open(log_path, "rb") as f:
            f.seek(0, os.SEEK_END)
            file_size = f.tell()
            block_size = 4096
            data = b""
            lines_found = []
            # read blocks from end until we have enough lines or file start
            while file_size > 0 and len(lines_found) <= max_lines:
                read_size = min(block_size, file_size)
                f.seek(file_size - read_size)
                chunk = f.read(read_size)
                data = chunk + data
                lines_found = data.splitlines()
                file_size -= read_size
                if file_size == 0:
                    break
            # take last max_lines lines (decode safely)
            raw_lines = [
                ln.decode("utf-8", errors="ignore").strip()
                for ln in lines_found[-max_lines:]
            ]
    except Exception:
        # fallback: read entire file (small files)
        raw_lines = []
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                raw_lines = [ln.strip() for ln in f.readlines() if ln.strip()]
                raw_lines = raw_lines[-max_lines:]
        except Exception as e2:
            return (
                jsonify(
                    {
                        "count": 0,
                        "items": [],
                        "message": f"Lá»—i Ä‘á»c file log: {str(e2)}",
                        "log_path": log_path,
                    }
                ),
                200,
            )

    parsed = []
    for ln in reversed(raw_lines):  # reversed => newest first
        try:
            obj = json.loads(ln)
        except Exception:
            # náº¿u khÃ´ng pháº£i JSON, bá»c vÃ o raw
            obj = {"raw": ln}
        # normalize shape: pick common keys for UI
        entry = {
            "question": obj.get("question") or obj.get("q") or None,
            "sql": obj.get("sql") or obj.get("sql_text") or None,
            "raw": obj.get("raw")
            or obj.get("generated")
            or obj.get("response")
            or None,
            "exec_status": obj.get("exec_status") or obj.get("status") or None,
            "saved": bool(obj.get("saved")) if "saved" in obj else None,
            "message": obj.get("message") or None,
            "source": obj.get("source") or None,
        }
        parsed.append(entry)

    return jsonify({"count": len(parsed), "items": parsed, "log_path": log_path}), 200


# ====== Get current schema ======
@app.route("/schema", methods=["GET"])
def get_schema():
    preview = read_all_schemas()
    # Láº¥y bundle hiá»‡n táº¡i náº¿u cÃ³
    bundle_file = None
    if SCHEMA_FILES:
        bp = SCHEMA_FILES[0]
        if bp.startswith(SAMPLE_UPLOADED_DIR):
            bundle_file = os.path.basename(bp)

    return jsonify(
        {
            "schema_text": (
                preview if preview else "(ChÆ°a cÃ³ schema â€” vui lÃ²ng upload trÆ°á»›c)"
            ),
            "files": [os.path.basename(p) for p in SCHEMA_FILES],
            "tables": ACTIVE_UPLOAD_ORDER,
            "id_map": ACTIVE_IDMAP,
            "bundle_file": bundle_file,
            "memories_filename": (
                os.path.basename(ACTIVE_AGG_FILE) if ACTIVE_AGG_FILE else None
            ),
            "active_primary_table": ACTIVE_PRIMARY_TABLE,
        }
    )


# ====== Chat ======
@app.route("/chat", methods=["POST"])
def chat():
    global pending_question
    data = request.get_json(force=True)
    msg = (data.get("message") or "").strip()
    model = (data.get("model") or DEFAULT_MODEL).strip()  # Get model from request
    
    if not msg:
        return jsonify({"response": "âš ï¸ Tin nháº¯n rá»—ng"}), 200

    # Äang chá» xÃ¡c nháº­n
    if pending_question:
        low = msg.lower()
        if any(w in low for w in YES_WORDS):
            schema_text = read_all_schemas()
            if not schema_text:
                pending_question = None
                return jsonify({"response": "âš ï¸ Vui lÃ²ng upload schema trÆ°á»›c"}), 200
            try:
                sql, src = hybrid_generate_sql(schema_text, pending_question, model)
                sql = extract_sql(sql)
                q = pending_question
                pending_question = None
                data_res, st = try_execute_sql(sql)
                combined = f"SQL ÄÆ°á»£c Táº¡o:\n{sql}\n\nStatus: {st}\nResult:\n{preview_result_text(data_res)}"
                return (
                    jsonify(
                        {
                            "response": combined,
                            "source": src,
                            "needs_check": True,
                            "question": q,
                            "sql": sql,
                            "result": data_res,
                            "result_status": st,
                            "response": combined,
                        }
                    ),
                    200,
                )
            except Exception as e:
                pending_question = None
                return jsonify({"response": f"âš ï¸ Error: {str(e)}"}), 200

        if any(w in low for w in NO_WORDS):
            pending_question = None
            return jsonify({"response": "Ok, tÃ´i sáº½ khÃ´ng táº¡o cÃ¢u truy váº¥n."}), 200

        return (
            jsonify(
                {"response": "âš ï¸ Vui lÃ²ng tráº£ lá»i 'cÃ³/Ä‘á»“ng Ã½' hoáº·c 'khÃ´ng/khÃ´ng cáº§n'."}
            ),
            200,
        )

    # KhÃ´ng chá» xÃ¡c nháº­n â†’ tra dataset
    sql = find_in_dataset(msg)
    if sql:
        data_res, st = try_execute_sql(sql)
        combined = f"SQL ÄÆ°á»£c Táº¡o:\n{sql}\n\nResult:\n{preview_result_text(data_res)}"
        return (
            jsonify(
                {
                    "response": combined,
                    "source": "dataset",
                    "sql": sql,
                    "result": data_res,
                    "result_status": st,
                }
            ),
            200,
        )

    # KhÃ´ng cÃ³ trong dataset -> há»i confirm
    pending_question = msg
    return (
        jsonify(
            {
                "response": "â“ CÃ¢u há»i nÃ y chÆ°a cÃ³ trong dataset. Báº¡n cÃ³ muá»‘n tÃ´i táº¡o cÃ¢u truy váº¥n SQL dá»±a trÃªn schema Ä‘Ã£ upload khÃ´ng?",
                "needs_confirmation": True,
                "question": msg,
            }
        ),
        200,
    )


# ====== Check & Approve ======
@app.route("/check", methods=["POST"])
def check():
    """LÆ°u vÃ o memory_[table].txt náº¿u xÃ¡c Ä‘á»‹nh Ä‘Æ°á»£c tÃªn báº£ng."""
    data = request.get_json(force=True)
    question = (data.get("question") or "").strip()
    sql = (data.get("sql") or "").strip()
    approve = bool(data.get("approve", False))

    if not question or not sql:
        return jsonify({"message": "Thiáº¿u question hoáº·c sql"}), 400

    if not approve:
        return jsonify({"message": "ÄÃ£ bá» qua, khÃ´ng lÆ°u."}), 200

    ok, msg = save_to_memory_per_table(question, sql)
    return jsonify({"message": msg}), 200


# ====== Evaluate ======
@app.route("/evaluate", methods=["GET"])
def evaluate():
    schema_text = read_all_schemas()
    if not schema_text:
        return jsonify({"accuracy": 0.0, "error": "ChÆ°a cÃ³ schema Ä‘á»ƒ evaluate."}), 200
    if not os.path.exists(EVAL_FILE):
        return jsonify({"accuracy": 0.0, "error": "Thiáº¿u file data/eval.jsonl."}), 200

    golds, preds, rows = [], [], 0
    with open(EVAL_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            q = (obj.get("question") or "").strip()
            g = (obj.get("gold") or "").strip()
            if not q or not g:
                continue
            try:
                sql_pred = generate_sql_with_grok(schema_text, q).strip()
            except Exception as e:
                sql_pred = f"ERROR: {e}"
            golds.append(g)
            preds.append(sql_pred)
            rows += 1

    acc = accuracy_score(golds, preds) if rows else 0.0
    return jsonify({"accuracy": float(acc), "samples": rows}), 200


# ====== Refine ======
@app.route("/refine", methods=["POST"])
def refine():
    data = request.get_json(force=True)
    question = (data.get("question") or "").strip()
    prev_sql = (data.get("sql") or "").strip()
    feedback = (data.get("feedback") or "").strip()
    extra_context = (data.get("extra_context") or "").strip()
    model = (data.get("model") or DEFAULT_MODEL).strip()  # Get model from request

    if not question or not prev_sql:
        return jsonify({"error": "Thiáº¿u question hoáº·c sql"}), 400

    schema_text = read_all_schemas()
    if not schema_text:
        return jsonify({"error": "âš ï¸ Vui lÃ²ng upload schema trÆ°á»›c"}), 200

    try:
        new_sql, src = hybrid_refine_sql(
            schema_text, question, prev_sql, feedback, extra_context, model
        )
        new_sql = extract_sql(new_sql)
        exec_data, exec_status = try_execute_sql(new_sql)
        combined = f"SQL ÄÆ°á»£c Táº¡o:\n{new_sql}\n\nStatus: {exec_status}\nResult:\n{preview_result_text(exec_data)}"
        return (
            jsonify(
                {
                    "response": combined,
                    "source": src,
                    "needs_check": True,
                    "question": question,
                    "sql": new_sql,
                    "result": exec_data,
                    "result_status": exec_status,
                }
            ),
            200,
        )
    except Exception as e:
        return jsonify({"error": f"âš ï¸ Error: {str(e)}"}), 200


# ====== Health Check ======
@app.route("/health/db")
def health_db():
    cli = get_ch_client()
    if not cli:
        return jsonify({"ok": False, "reason": "NO_DB_CLIENT"}), 200
    try:
        r = cli.query("SELECT 1 AS x").result_rows
        return jsonify({"ok": True, "rows": r}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 200


# ====== Debug Table Exists ======
@app.route("/debug/table/<name>")
def debug_table(name):
    cli = get_ch_client()
    if not cli:
        return jsonify({"ok": False, "reason": "NO_DB_CLIENT"}), 200
    try:
        exists = cli.query(f"EXISTS TABLE {name}").result_rows
        desc = cli.query(f"DESCRIBE TABLE {name}").column_names if exists else []
        return jsonify({"ok": True, "exists": exists, "desc": desc}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 200


# ====== Pretrain on current schema ======
@app.route("/pretrain", methods=["POST"])
def pretrain_endpoint():
    """
    Tiáº¿p tá»¥c pretrain vá»›i cÃ¢u há»i má»›i (trÃ¡nh trÃ¹ng). Body JSON:
    {"rounds": 10, "strategy": "cascade" | "sqlcoder" | "gemini"}
    """
    schema_text = read_all_schemas()
    if not schema_text:
        return jsonify({"error": "ChÆ°a cÃ³ schema/bundle Ä‘á»ƒ pretrain"}), 200

    payload = request.get_json(silent=True) or {}
    rounds = payload.get("rounds")
    strategy = payload.get("strategy")

    info = pretrain_after_upload(schema_text, rounds=rounds, strategy=strategy)
    return jsonify(info), 200


# ====== Get pretrain config ======
@app.route("/pretrain-config", methods=["GET"])
def pretrain_config():
    return (
        jsonify(
            {
                "PRETRAIN_ON_UPLOAD": PRETRAIN_ON_UPLOAD,
                "PRETRAIN_ROUNDS": PRETRAIN_ROUNDS,
                "PRETRAIN_STRATEGY": PRETRAIN_STRATEGY,
                "ACTIVE_TABLES": list(ACTIVE_TABLES),
                "ACTIVE_PRIMARY_TABLE": ACTIVE_PRIMARY_TABLE,
            }
        ),
        200,
    )


# =======================================================================
# ============================== Run App ================================
# =======================================================================

if __name__ == "__main__":
    # Gá»£i Ã½ cháº¡y:
    #   set GEMINI_API_KEY=... (Windows) / export GEMINI_API_KEY=... (Linux/Mac)
    #   python gpt41.py
    app.run(host="0.0.0.0", port=5002)


