# -*- coding: utf-8 -*-
"""
Flask backend cho Text-to-SQL + Memory + Pretrain
- Upload nhiều schema (txt/json/jsonl/csv/sql) -> bundle trong ./sample/uploaded/
- Auto-pretrain (cấu hình qua .env) + Pretrain thêm
- Lưu memory theo 1 bảng (memory_<table>.txt) hoặc nhiều schema (memories_XX+YY+.txt)
- Chat flow: dataset lookup -> confirm generate -> save/skip -> refine
- Xem log pretrain JSONL và file pretrain text đẹp trong ./pretrain/<bundle>.txt
"""

import os
import re
import json
import random
from pathlib import Path
from typing import Tuple

from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

# Optional: Gemini + ClickHouse + HTTP clients (chỉ dùng nếu có env/driver)
import requests

try:
    import google.generativeai as genai
except Exception:
    genai = None

try:
    from clickhouse_connect import get_client
except Exception:
    get_client = None

# ------------------- Load ENV -------------------
load_dotenv()

# Model & strategy
SQLCODER_BACKEND = os.getenv("SQLCODER_BACKEND", "hf").lower()  # hf | ollama | vllm
SQLCODER_MODEL = os.getenv("SQLCODER_MODEL", "defog/sqlcoder-7b-2")
HYBRID_STRATEGY = os.getenv(
    "HYBRID_STRATEGY", "cascade"
).lower()  # sqlcoder_only|gemini_only|cascade
REFINE_STRATEGY = os.getenv(
    "REFINE_STRATEGY", "gemini"
).lower()  # sqlcoder|gemini|cascade
REQUIRE_KNOWN_TABLE = os.getenv("SQLCODER_REQUIRE_KNOWN_TABLE", "1") == "1"

# Pretrain
PRETRAIN_ON_UPLOAD = os.getenv("PRETRAIN_ON_UPLOAD", "1") == "1"
PRETRAIN_ROUNDS = int(os.getenv("PRETRAIN_ROUNDS", "15"))
PRETRAIN_STRATEGY = os.getenv("PRETRAIN_STRATEGY", "cascade").lower()

# Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if genai and GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception:
        pass

# ------------------- Paths -------------------
BASE_DIR = Path(__file__).parent.resolve()
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

SAMPLE_UPLOADING_DIR = BASE_DIR / "sample" / "uploading"
SAMPLE_UPLOADED_DIR = BASE_DIR / "sample" / "uploaded"
SAMPLE_UPLOADING_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_UPLOADED_DIR.mkdir(parents=True, exist_ok=True)

MEMORY_DIR = BASE_DIR / "knowledge_base" / "memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

PRETRAIN_DIR = BASE_DIR / "pretrain"
PRETRAIN_DIR.mkdir(parents=True, exist_ok=True)

DATA_DIR = BASE_DIR / "data"
DATASET_FILE = DATA_DIR / "dataset_base.jsonl"
EVAL_FILE = DATA_DIR / "eval.jsonl"

ALLOWED_EXT = {"txt", "json", "jsonl", "csv", "sql"}

# ------------------- Flask -------------------
app = Flask(__name__)

# ------------------- Runtime State -------------------
SCHEMA_FILES: list[str] = []  # [bundle_path]
KNOWN_TABLES: set[str] = set()
ACTIVE_TABLES: list[str] = []  # theo thứ tự upload
ACTIVE_PRIMARY_TABLE: str | None = None
ACTIVE_IDMAP: dict[str, str] = {}  # table -> "01","02",...
ACTIVE_UPLOAD_ORDER: list[str] = []  # theo thứ tự upload
ACTIVE_AGG_FILE: str | None = None  # path memories_XX+YY.txt (khi multi)
pending_question: str | None = None

YES_WORDS = ["có", "đồng ý", "yes", "ok", "oke", "okay"]
NO_WORDS = ["không", "không cần", "no", "ko", "khong"]


# ------------------- Utils -------------------
def allowed_file(fn: str) -> bool:
    return "." in fn and fn.rsplit(".", 1)[1].lower() in ALLOWED_EXT


def _normalize_table_name(raw: str) -> str:
    raw = raw.strip().strip('`"')
    if "." in raw:
        raw = raw.split(".")[-1]
    return re.sub(r"[^\w]+", "_", raw).lower()


def parse_tables_from_text(text: str) -> list[str]:
    tables = []
    for m in re.finditer(r"CREATE\s+TABLE\s+([`\"\w\.]+)\s*\(", text, flags=re.I):
        t = _normalize_table_name(m.group(1))
        if t:
            tables.append(t)
    return tables


def read_all_schemas() -> str:
    parts = []
    for f in SCHEMA_FILES:
        try:
            with open(f, "r", encoding="utf-8") as fp:
                parts.append(fp.read())
        except Exception:
            pass
    return "\n\n---\n\n".join(parts)


def _empty_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)
    for name in os.listdir(p):
        try:
            full = p / name
            if full.is_file():
                full.unlink(missing_ok=True)
            else:
                import shutil

                shutil.rmtree(full, ignore_errors=True)
        except Exception:
            pass


def current_bundle_base() -> str | None:
    if not SCHEMA_FILES:
        return None
    base = os.path.basename(SCHEMA_FILES[0])
    return os.path.splitext(base)[0]


def current_pretrain_log_path() -> str | None:
    base = current_bundle_base()
    if not base:
        return None
    return str(SAMPLE_UPLOADED_DIR / f"{base}.pretrain.jsonl")


# ------------------- SQL helpers -------------------
SQL_FENCE_RE = re.compile(r"```+[a-zA-Z]*\s*([\s\S]*?)```", re.I)


def extract_sql(text: str) -> str:
    if not text:
        return ""
    m = SQL_FENCE_RE.search(text)
    if m:
        text = m.group(1)
    text = re.sub(r"(?im)^status\s*:\s*.*$", "", text)
    text = re.sub(r"(?im)^result\s*:\s*.*$", "", text)
    text = re.sub(r"(?i)^\s*(sql\s*được\s*tạo|sql|query)\s*[:\-]*", "", text).strip()
    m2 = re.search(r"(?is)\b(select|insert|update|delete)\b[\s\S]*$", text)
    if m2:
        text = text[m2.start() :].strip()
    text = re.sub(r"`{3,}", "", text).strip()
    return text


def looks_valid_sql(sql: str) -> bool:
    if not sql or len(sql) < 10:
        return False
    if not re.search(r"\bselect\b|\binsert\b|\bupdate\b|\bdelete\b", sql, flags=re.I):
        return False
    if REQUIRE_KNOWN_TABLE and KNOWN_TABLES:
        if not any(
            re.search(rf"\b{re.escape(t)}\b", sql, flags=re.I) for t in KNOWN_TABLES
        ):
            return False
    return True


# ------------------- SQLCoder callers (optional) -------------------
def _sqlcoder_prompt(schema_text: str, question: str) -> str:
    return f"""You are SQLCoder specialized in ClickHouse.
Schema:
{schema_text}

Question: {question}

Return ONLY one SQL statement.
If it's a SELECT and no pagination is specified, add LIMIT 20.
No explanation, no markdown fences."""


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
        if isinstance(data, list) and data and "generated_text" in data[0]:
            return data[0]["generated_text"]
        if isinstance(data, dict) and "generated_text" in data:
            return data["generated_text"]
        if isinstance(data, str):
            return data
    except Exception:
        return None
    return None


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
        return (r.json().get("response") or "").strip()
    except Exception:
        return None


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
        return r.json()["choices"][0]["message"]["content"]
    except Exception:
        return None


def generate_sql_with_sqlcoder(schema_text: str, question: str) -> str | None:
    if SQLCODER_BACKEND == "ollama":
        raw = call_sqlcoder_ollama(schema_text, question)
    elif SQLCODER_BACKEND == "vllm":
        raw = call_sqlcoder_vllm(schema_text, question)
    else:
        raw = call_sqlcoder_hf(schema_text, question)
    return extract_sql(raw or "") or None


# ------------------- Gemini callers (optional) -------------------
def generate_sql_with_gemini(schema_text: str, question: str) -> str:
    if not genai or not GEMINI_API_KEY:
        # fallback đơn giản nếu không có Gemini
        t = (KNOWN_TABLES and list(KNOWN_TABLES)[0]) or (
            ACTIVE_PRIMARY_TABLE or "table"
        )
        return f"SELECT * FROM {t} LIMIT 20"
    prompt = f"""You are an SQL expert (ClickHouse).
Schema(s):
{schema_text}

User question: {question}

Return ONLY the SQL query (no explanations)."""
    model = genai.GenerativeModel("gemini-2.0-flash")
    try:
        resp = model.generate_content(prompt)
        return extract_sql(resp.text or "") or ""
    except Exception:
        t = (KNOWN_TABLES and list(KNOWN_TABLES)[0]) or (
            ACTIVE_PRIMARY_TABLE or "table"
        )
        return f"SELECT * FROM {t} LIMIT 20"


def generate_refined_sql_with_sqlcoder(
    schema_text: str, question: str, prev_sql: str, feedback: str, extra: str
) -> str | None:
    # dùng lại SQLCoder với prompt refine đơn giản
    full = f"""You are SQLCoder for ClickHouse.

Schema:
{schema_text}

Question:
{question}

Previous SQL (needs fix):
{prev_sql}

What's wrong:
{feedback or "The previous SQL did not fully answer the question."}

Additional constraints:
{extra or "(none)"}

Revise and return ONLY the final SQL, no fences."""
    return extract_sql(generate_sql_with_sqlcoder(schema_text, full) or "") or None


def generate_refined_sql_with_gemini(
    schema_text: str, question: str, prev_sql: str, feedback: str, extra: str
) -> str:
    if not genai or not GEMINI_API_KEY:
        return prev_sql  # fallback
    prompt = f"""You are an advanced SQL engineer (ClickHouse).

Schema(s):
{schema_text}

Question:
{question}

Previous SQL (needs fix):
{prev_sql}

Critique:
{feedback or "The previous SQL did not fully answer the question."}

Additional notes:
{extra or "(none)"}

Return ONLY the revised SQL (no explanations)."""
    model = genai.GenerativeModel("gemini-2.0-flash")
    try:
        resp = model.generate_content(prompt)
        return extract_sql(resp.text or "") or prev_sql
    except Exception:
        return prev_sql


def hybrid_generate_sql(schema_text: str, question: str) -> Tuple[str, str]:
    if HYBRID_STRATEGY == "sqlcoder_only":
        return (generate_sql_with_sqlcoder(schema_text, question) or ""), "sqlcoder"
    if HYBRID_STRATEGY == "gemini_only":
        return (generate_sql_with_gemini(schema_text, question) or ""), "gemini"
    # cascade
    s1 = generate_sql_with_sqlcoder(schema_text, question) or ""
    if s1 and looks_valid_sql(s1):
        return s1, "sqlcoder"
    s2 = generate_sql_with_gemini(schema_text, question) or ""
    return s2, ("sqlcoder+gemini" if s1 else "gemini")


def hybrid_refine_sql(
    schema_text: str, question: str, prev_sql: str, feedback: str, extra: str
) -> Tuple[str, str]:
    if REFINE_STRATEGY == "sqlcoder":
        s1 = (
            generate_refined_sql_with_sqlcoder(
                schema_text, question, prev_sql, feedback, extra
            )
            or ""
        )
        return s1, "refined_sqlcoder"
    if REFINE_STRATEGY == "gemini":
        s2 = (
            generate_refined_sql_with_gemini(
                schema_text, question, prev_sql, feedback, extra
            )
            or ""
        )
        return s2, "refined_gemini"
    # cascade
    s1 = (
        generate_refined_sql_with_sqlcoder(
            schema_text, question, prev_sql, feedback, extra
        )
        or ""
    )
    if s1 and s1.strip().lower() != prev_sql.strip().lower():
        return s1, "refined_sqlcoder"
    s2 = (
        generate_refined_sql_with_gemini(
            schema_text, question, prev_sql, feedback, extra
        )
        or ""
    )
    return s2, "refined_sqlcoder+gemini"


# ------------------- ClickHouse -------------------
def get_ch_client_safe():
    if get_client is None:
        return None
    try:
        return get_client(
            host=os.getenv("CLICKHOUSE_HOST", "localhost"),
            port=int(os.getenv("CLICKHOUSE_PORT", "8123")),
            username=os.getenv("CLICKHOUSE_USER", "default"),
            password=os.getenv("CLICKHOUSE_PASSWORD", ""),
            database=os.getenv("CLICKHOUSE_DB", "default"),
        )
    except Exception:
        return None


def try_execute_sql(sql: str):
    sql = (sql or "").strip()
    if not sql:
        return None, "NO_SQL"
    cli = get_ch_client_safe()
    if not cli:
        return None, "NO_DB"
    try:
        q = cli.query(sql)
        rows = q.result_rows or []
        cols = q.column_names or []
        if not rows:
            return None, "OK_EMPTY"
        return [dict(zip(cols, r)) for r in rows], "OK"
    except Exception as e:
        return None, f"ERR:{e}"


def preview_result_text(data):
    if data is None:
        return "null"
    try:
        return json.dumps(
            data[:5] if isinstance(data, list) else data, ensure_ascii=False
        )
    except Exception:
        return "null"


# ------------------- Memory & Dataset -------------------
def infer_table_from_sql(sql: str) -> str | None:
    if not sql:
        return None
    for t in sorted(KNOWN_TABLES, key=len, reverse=True):
        if re.search(rf"(?<!\w)`?{re.escape(t)}`?(?!\w)", sql, flags=re.I):
            return t
    return None


def save_to_memory_per_table(question: str, sql: str) -> tuple[bool, str]:
    # multi: memories_...
    if ACTIVE_AGG_FILE and ACTIVE_UPLOAD_ORDER and ACTIVE_IDMAP:
        with open(ACTIVE_AGG_FILE, "a", encoding="utf-8") as f:
            f.write(
                json.dumps({"question": question, "sql": sql}, ensure_ascii=False)
                + "\n"
            )
        mapping = ", ".join(f"{ACTIVE_IDMAP[t]}={t}" for t in ACTIVE_UPLOAD_ORDER)
        return True, f"Đã lưu vào {ACTIVE_AGG_FILE} (mapping: {mapping})"
    # single
    table = ACTIVE_PRIMARY_TABLE or infer_table_from_sql(sql)
    if not table and len(SCHEMA_FILES) == 1:
        base = os.path.splitext(os.path.basename(SCHEMA_FILES[0]))[0]
        table = _normalize_table_name(base)
    if not table:
        return False, "❗ Không xác định được bảng đang hoạt động, nên không lưu."
    path = MEMORY_DIR / f"memory_{table}.txt"
    with open(path, "a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {"question": question, "sql": sql, "table": table}, ensure_ascii=False
            )
            + "\n"
        )
    return True, f"Đã lưu vào {path}"


def collect_seen_questions_for_active() -> set:
    seen = set()
    # single
    if ACTIVE_AGG_FILE is None and ACTIVE_PRIMARY_TABLE:
        p = MEMORY_DIR / f"memory_{ACTIVE_PRIMARY_TABLE}.txt"
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                for ln in f:
                    try:
                        seen.add(json.loads(ln).get("question", ""))
                    except:
                        pass
    # multi
    if ACTIVE_AGG_FILE and os.path.exists(ACTIVE_AGG_FILE):
        with open(ACTIVE_AGG_FILE, "r", encoding="utf-8") as f:
            for ln in f:
                try:
                    seen.add(json.loads(ln).get("question", ""))
                except:
                    pass
    return {q for q in seen if q}


def load_dataset() -> list[dict]:
    ds = []
    if DATASET_FILE.exists():
        with open(DATASET_FILE, "r", encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if ln:
                    obj = json.loads(ln)
                    obj["_src"] = "base"
                    ds.append(obj)
    # single memory
    if ACTIVE_AGG_FILE is None and ACTIVE_PRIMARY_TABLE:
        p = MEMORY_DIR / f"memory_{ACTIVE_PRIMARY_TABLE}.txt"
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                for ln in f:
                    ln = ln.strip()
                    if not ln:
                        continue
                    try:
                        obj = json.loads(ln)
                        obj["_src"] = f"memory:{ACTIVE_PRIMARY_TABLE}"
                        ds.append(obj)
                    except:
                        pass
    # multi memory
    if ACTIVE_AGG_FILE and os.path.exists(ACTIVE_AGG_FILE):
        with open(ACTIVE_AGG_FILE, "r", encoding="utf-8") as f:
            for ln in f:
                ln = ln.strip()
                if not ln:
                    continue
                try:
                    obj = json.loads(ln)
                    obj["_src"] = "memories"
                    ds.append(obj)
                except:
                    pass
    return ds


def find_in_dataset(question: str) -> str | None:
    q = (question or "").strip().lower()
    for it in load_dataset():
        if (it.get("question") or "").strip().lower() == q:
            s = (it.get("sql") or "").strip()
            if s:
                return s
    return None


# ------------------- Pretrain synthesize -------------------
def parse_table_columns_map(schema_text: str) -> dict[str, list[str]]:
    m = {}
    for mm in re.finditer(
        r"CREATE\s+TABLE\s+([`\"\w\.]+)\s*\((.*?)\)", schema_text, flags=re.I | re.S
    ):
        t = _normalize_table_name(mm.group(1))
        block = mm.group(2)
        cols = [
            c.group(1) for c in re.finditer(r"^\s*`?(\w+)`?\s+\w+", block, flags=re.M)
        ]
        if t:
            m[t] = cols
    return m


def synthesize_questions(schema_text: str, limit: int = 15) -> list[tuple[str, str]]:
    table_cols = parse_table_columns_map(schema_text)
    tables = (
        list(table_cols.keys())
        or ACTIVE_TABLES
        or ([ACTIVE_PRIMARY_TABLE] if ACTIVE_PRIMARY_TABLE else [])
    )
    tables = [t for t in tables if t] or []
    if not tables:
        return []

    def pick(cols, *names):
        for n in names:
            for c in cols:
                if c.lower() == n.lower():
                    return c
        return None

    qs = []
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
                (f"Hiển thị 20 dòng đầu tiên của bảng {t}", t),
                (f"Đếm tổng số bản ghi trong bảng {t}", t),
            ]
        )
        if id_col:
            qs.append((f"Đếm số bản ghi theo {id_col} trong bảng {t}", t))
        if time_col:
            qs.append(
                (
                    f"Đếm số bản ghi theo ngày dựa trên {time_col} trong 7 ngày gần nhất của bảng {t}",
                    t,
                )
            )
        if shop_col:
            qs.append((f"Đếm số lượng shop_id khác nhau trong bảng {t}", t))
            qs.append((f"Top 10 shop_id có nhiều bản ghi nhất trong bảng {t}", t))
        if user_col:
            qs.append((f"Top 10 {user_col} có nhiều bản ghi nhất trong bảng {t}", t))
        if conv_col:
            qs.append((f"Đếm số {conv_col} khác nhau trong bảng {t}", t))

    out = []
    seen = set()
    for q, t in qs:
        if q not in seen:
            out.append((q, t))
            seen.add(q)
        if len(out) >= limit:
            break
    return out


def write_pretrain_text(items: list[dict], rounds: int, strategy: str) -> str:
    base = current_bundle_base() or "pretrain_latest"
    display = re.sub(r"^bundle_", "", base)
    path = PRETRAIN_DIR / f"{display}.txt"
    with open(path, "w", encoding="utf-8") as pf:
        pf.write(f"Pretrain for bundle: {base}\n")
        pf.write(f"Rounds requested: {rounds}\n")
        pf.write(f"Strategy: {strategy}\n")
        pf.write(
            f"Generated: {len(items)}, saved={sum(1 for i in items if i.get('saved'))}\n"
        )
        pf.write("=" * 60 + "\n\n")
        for i, it in enumerate(items, start=1):
            src = it.get("source") or ""
            model = (
                "SQLCoder-7B-2"
                if src == "sqlcoder"
                else (
                    "Gemini"
                    if src == "gemini"
                    else (
                        "SQLCoder-7B-2 → Gemini (cascade)"
                        if src in ("cascade", "sqlcoder+gemini")
                        else src
                    )
                )
            )
            pf.write(f"#{i}\n")
            pf.write(f"Q: {it.get('question')}\n")
            pf.write(f"SQL: {it.get('sql') or '(NO_SQL)'}\n")
            pf.write(f"Model: {model}\n")
            pf.write(f"Status: {it.get('exec_status') or it.get('status') or ''}\n")
            pf.write(f"Saved: {'✓' if it.get('saved') else '×'}\n")
            raw = it.get("raw")
            if raw:
                short = (
                    raw
                    if len(str(raw)) <= 1000
                    else str(raw)[:1000] + " ...[truncated]"
                )
                pf.write("Raw:\n")
                pf.write(short + "\n")
            pf.write("-" * 40 + "\n\n")
    return str(path)


def pretrain_on_schema(
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
    preview = []
    all_items = []
    for question, _ in pairs:
        tried += 1
        if strategy == "gemini":
            raw = generate_sql_with_gemini(schema_text, question)
            src = "gemini"
        elif strategy == "cascade":
            raw, src = hybrid_generate_sql(schema_text, question)
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
        if len(preview) < 5:
            preview.append(item)
        if log_path:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        if saved >= rounds:
            break

    pretrain_txt = write_pretrain_text(all_items, rounds, strategy)
    return {
        "done": True,
        "tried": tried,
        "saved": saved,
        "log_file": log_path,
        "pretrain_file": pretrain_txt,
        "preview": preview,
    }


# ------------------- Routes -------------------
@app.route("/")
def index():
    return render_template("dexit.html")


@app.route("/upload-schema", methods=["POST"])
def upload_schema():
    global SCHEMA_FILES, KNOWN_TABLES, ACTIVE_TABLES, ACTIVE_PRIMARY_TABLE, ACTIVE_IDMAP, ACTIVE_UPLOAD_ORDER, ACTIVE_AGG_FILE
    if "file" not in request.files:
        return jsonify({"error": "Không có file"}), 400

    # reset state
    SCHEMA_FILES = []
    KNOWN_TABLES = set()
    ACTIVE_TABLES = []
    ACTIVE_PRIMARY_TABLE = None
    ACTIVE_IDMAP = {}
    ACTIVE_UPLOAD_ORDER = []
    ACTIVE_AGG_FILE = None
    _empty_dir(SAMPLE_UPLOADING_DIR)

    files = request.files.getlist("file")
    saved = []
    per_blocks = []
    detected = []
    for f in files:
        if not f or not f.filename:
            continue
        if not allowed_file(f.filename):
            continue
        fn = secure_filename(f.filename)
        dst = UPLOAD_DIR / fn
        f.save(dst)
        saved.append(fn)
        try:
            txt = dst.read_text(encoding="utf-8")
        except Exception:
            txt = ""
        # copy to uploading & write meta
        (SAMPLE_UPLOADING_DIR / fn).write_text(txt, encoding="utf-8")
        base = os.path.splitext(fn)[0]
        meta = {
            "filename": fn,
            "base": _normalize_table_name(base),
            "tables": parse_tables_from_text(txt) or [_normalize_table_name(base)],
        }
        (SAMPLE_UPLOADING_DIR / f"{base}.meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        for t in meta["tables"]:
            if t:
                KNOWN_TABLES.add(t)
                detected.append(t)
        per_blocks.append(f"-- FILE: {fn}\n{txt}\n")

    ACTIVE_UPLOAD_ORDER = detected[:]
    ACTIVE_TABLES = detected[:]
    ACTIVE_PRIMARY_TABLE = detected[0] if detected else None

    # assign 2-digit ids
    for i, t in enumerate(ACTIVE_UPLOAD_ORDER[:99], start=1):
        ACTIVE_IDMAP[t] = str(i).zfill(2)

    # bundle + memories file
    if len(ACTIVE_UPLOAD_ORDER) > 1 and ACTIVE_IDMAP:
        mem_name = (
            "memories_"
            + "+".join(ACTIVE_IDMAP[t] for t in ACTIVE_UPLOAD_ORDER)
            + ".txt"
        )
        ACTIVE_AGG_FILE = str(MEMORY_DIR / mem_name)
        bundle_name = (
            "bundle_" + "+".join(ACTIVE_IDMAP[t] for t in ACTIVE_UPLOAD_ORDER) + ".txt"
        )
    else:
        ACTIVE_AGG_FILE = None
        bundle_name = (
            f"bundle_{ACTIVE_PRIMARY_TABLE or (saved[0] if saved else 'single')}.txt"
        )

    bundle_path = SAMPLE_UPLOADED_DIR / bundle_name
    bundle_path.write_text("\n\n".join(per_blocks), encoding="utf-8")
    SCHEMA_FILES = [str(bundle_path)]
    _empty_dir(SAMPLE_UPLOADING_DIR)

    preview = read_all_schemas()
    pretrain_info = pretrain_on_schema(preview) if PRETRAIN_ON_UPLOAD else {}

    return (
        jsonify(
            {
                "message": f"Đã upload: {', '.join(saved)}",
                "schema_text": preview,
                "files_uploaded": saved,
                "tables": ACTIVE_UPLOAD_ORDER,
                "id_map": ACTIVE_IDMAP,
                "bundle_file": os.path.basename(bundle_path),
                "bundle_path": str(bundle_path),
                "memories_filename": (
                    os.path.basename(ACTIVE_AGG_FILE) if ACTIVE_AGG_FILE else None
                ),
                "active_primary_table": ACTIVE_PRIMARY_TABLE,
                "pretrain": pretrain_info,
            }
        ),
        200,
    )


@app.route("/schema", methods=["GET"])
def schema_info():
    preview = read_all_schemas()
    bundle_file = os.path.basename(SCHEMA_FILES[0]) if SCHEMA_FILES else None
    return (
        jsonify(
            {
                "schema_text": preview or "(Chưa có schema — vui lòng upload trước)",
                "files": [os.path.basename(p) for p in SCHEMA_FILES],
                "tables": ACTIVE_UPLOAD_ORDER,
                "id_map": ACTIVE_IDMAP,
                "bundle_file": bundle_file,
                "memories_filename": (
                    os.path.basename(ACTIVE_AGG_FILE) if ACTIVE_AGG_FILE else None
                ),
                "active_primary_table": ACTIVE_PRIMARY_TABLE,
            }
        ),
        200,
    )


@app.route("/pretrain", methods=["POST"])
def pretrain_api():
    schema_text = read_all_schemas()
    if not schema_text:
        return jsonify({"error": "Chưa có schema/bundle để pretrain"}), 200
    payload = request.get_json(silent=True) or {}
    rounds = payload.get("rounds") or PRETRAIN_ROUNDS
    strategy = payload.get("strategy") or PRETRAIN_STRATEGY
    info = pretrain_on_schema(schema_text, rounds=int(rounds), strategy=strategy)
    return jsonify(info), 200


@app.route("/pretrain-report", methods=["GET"])
def pretrain_report():
    log_path = current_pretrain_log_path()
    if not log_path or not os.path.exists(log_path):
        return (
            jsonify(
                {
                    "count": 0,
                    "items": [],
                    "message": "Chưa có log pretrain cho bundle hiện tại.",
                }
            ),
            200,
        )
    try:
        max_lines = int(request.args.get("max_lines", "50"))
    except:
        max_lines = 50
    max_lines = max(1, min(1000, max_lines))
    # efficient tail
    try:
        with open(log_path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            block = 4096
            data = b""
            lines = []
            while size > 0 and len(lines) <= max_lines:
                read = min(block, size)
                f.seek(size - read)
                data = f.read(read) + data
                lines = data.splitlines()
                size -= read
            raw = [ln.decode("utf-8", "ignore").strip() for ln in lines[-max_lines:]]
    except Exception:
        with open(log_path, "r", encoding="utf-8") as f:
            raw = [ln.strip() for ln in f if ln.strip()][-max_lines:]

    items = []
    for ln in reversed(raw):
        try:
            obj = json.loads(ln)
        except:
            obj = {"raw": ln}
        items.append(
            {
                "question": obj.get("question"),
                "sql": obj.get("sql"),
                "raw": obj.get("raw") or obj.get("response"),
                "exec_status": obj.get("exec_status") or obj.get("status"),
                "saved": obj.get("saved"),
                "message": obj.get("message"),
                "source": obj.get("source"),
            }
        )
    return jsonify({"count": len(items), "items": items, "log_path": log_path}), 200


@app.route("/pretrain-file", methods=["GET"])
def pretrain_file():
    base = current_bundle_base() or "pretrain_latest"
    display = re.sub(r"^bundle_", "", base)
    p = PRETRAIN_DIR / f"{display}.txt"
    if not p.exists():
        return jsonify({"exists": False, "path": str(p)}), 200
    return (
        jsonify(
            {"exists": True, "path": str(p), "content": p.read_text(encoding="utf-8")}
        ),
        200,
    )


@app.route("/chat", methods=["POST"])
def chat():
    global pending_question
    payload = request.get_json(force=True)
    msg = (payload.get("message") or "").strip()
    if not msg:
        return jsonify({"response": "⚠️ Tin nhắn rỗng"}), 200

    # pending confirm
    if pending_question:
        low = msg.lower()
        if any(w in low for w in YES_WORDS):
            schema_text = read_all_schemas()
            if not schema_text:
                pending_question = None
                return jsonify({"response": "⚠️ Vui lòng upload schema trước"}), 200
            sql, src = hybrid_generate_sql(schema_text, pending_question)
            sql = extract_sql(sql)
            q = pending_question
            pending_question = None
            data, st = try_execute_sql(sql)
            combined = f"SQL Được Tạo:\n{sql}\n\nStatus: {st}\nResult:\n{preview_result_text(data)}"
            return (
                jsonify(
                    {
                        "response": combined,
                        "source": src,
                        "needs_check": True,
                        "question": q,
                        "sql": sql,
                        "result": data,
                        "result_status": st,
                    }
                ),
                200,
            )
        if any(w in low for w in NO_WORDS):
            pending_question = None
            return jsonify({"response": "Ok, tôi sẽ không tạo câu truy vấn."}), 200
        return (
            jsonify(
                {"response": "⚠️ Vui lòng trả lời 'có/đồng ý' hoặc 'không/không cần'."}
            ),
            200,
        )

    # dataset lookup
    sql = find_in_dataset(msg)
    if sql:
        data, st = try_execute_sql(sql)
        combined = f"SQL Được Tạo:\n{sql}\n\nResult:\n{preview_result_text(data)}"
        return (
            jsonify(
                {
                    "response": combined,
                    "source": "dataset",
                    "sql": sql,
                    "result": data,
                    "result_status": st,
                }
            ),
            200,
        )

    # ask confirm
    pending_question = msg
    return (
        jsonify(
            {
                "response": "❓ Câu hỏi này chưa có trong dataset. Bạn có muốn tôi tạo câu truy vấn SQL dựa trên schema đã upload không?",
                "needs_confirmation": True,
                "question": msg,
            }
        ),
        200,
    )


@app.route("/check", methods=["POST"])
def check():
    data = request.get_json(force=True)
    question = (data.get("question") or "").strip()
    sql = (data.get("sql") or "").strip()
    approve = bool(data.get("approve", False))
    if not question or not sql:
        return jsonify({"message": "Thiếu question hoặc sql"}), 400
    if not approve:
        return jsonify({"message": "Đã bỏ qua, không lưu."}), 200
    ok, msg = save_to_memory_per_table(question, sql)
    return jsonify({"message": msg}), 200


@app.route("/refine", methods=["POST"])
def refine():
    data = request.get_json(force=True)
    question = (data.get("question") or "").strip()
    prev_sql = (data.get("sql") or "").strip()
    feedback = (data.get("feedback") or "").strip()
    extra = (data.get("extra_context") or "").strip()
    if not question or not prev_sql:
        return jsonify({"error": "Thiếu question hoặc sql"}), 400
    schema_text = read_all_schemas()
    if not schema_text:
        return jsonify({"error": "⚠️ Vui lòng upload schema trước"}), 200
    new_sql, src = hybrid_refine_sql(schema_text, question, prev_sql, feedback, extra)
    new_sql = extract_sql(new_sql)
    data_res, st = try_execute_sql(new_sql)
    combined = f"SQL Được Tạo:\n{new_sql}\n\nStatus: {st}\nResult:\n{preview_result_text(data_res)}"
    return (
        jsonify(
            {
                "response": combined,
                "source": src,
                "needs_check": True,
                "question": question,
                "sql": new_sql,
                "result": data_res,
                "result_status": st,
            }
        ),
        200,
    )


# ------------------- Run -------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)
