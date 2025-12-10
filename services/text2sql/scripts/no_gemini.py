# -*- coding: utf-8 -*-
"""
Flask backend cho Text-to-SQL + Memory + Pretrain (SQLCoder-only)
- Upload nhiều schema (txt/json/jsonl/csv/sql) -> bundle trong ./sample/uploaded/
- Auto-pretrain (cấu hình qua .env) + Pretrain thêm
- Lưu memory theo 1 bảng (memory_<table>.txt) hoặc nhiều schema (memories_XX+YY+.txt)
- Chat flow: dataset lookup -> confirm generate -> save/skip -> refine
- Xem log pretrain JSONL và file pretrain text trong ./pretrain/<bundle>.txt
- CHỈ DÙNG SQLCoder-7B-2, KHÔNG DÙNG GEMINI
"""

import os
import re
import json
import random
import io
from pathlib import Path
from typing import Tuple

from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

# HTTP client (HF/ollama/vLLM)
import requests

# ClickHouse client (tùy chọn)
try:
    from clickhouse_connect import get_client
except Exception:
    get_client = None

# ------------------- Load ENV -------------------
load_dotenv()

# Model & strategy (không còn tuỳ chọn gemini)
SQLCODER_BACKEND = os.getenv("SQLCODER_BACKEND", "hf").lower()  # hf | ollama | vllm
SQLCODER_MODEL = os.getenv("SQLCODER_MODEL", "defog/sqlcoder-7b-2")
HYBRID_STRATEGY = os.getenv(
    "HYBRID_STRATEGY", "cascade"
).lower()  # sqlcoder_only | cascade
REFINE_STRATEGY = os.getenv("REFINE_STRATEGY", "sqlcoder").lower()  # sqlcoder | cascade
REQUIRE_KNOWN_TABLE = os.getenv("SQLCODER_REQUIRE_KNOWN_TABLE", "1") == "1"

# Pretrain
PRETRAIN_ON_UPLOAD = os.getenv("PRETRAIN_ON_UPLOAD", "1") == "1"
PRETRAIN_ROUNDS = int(os.getenv("PRETRAIN_ROUNDS", "15"))
PRETRAIN_STRATEGY = os.getenv(
    "PRETRAIN_STRATEGY", "cascade"
).lower()  # sqlcoder | cascade

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

_TIME_PAT = re.compile(
    r"^\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+\-]\d{2}:\d{2})?)?$"
)
_ID_NAME = {
    "id",
    "_id",
    "user_id",
    "shop_id",
    "staff_id",
    "ticket_id",
    "conversation_id",
    "order_id",
    "account_id",
}

YES_WORDS = ["có", "đồng ý", "yes", "ok", "oke", "okay"]
NO_WORDS = ["không", "không cần", "no", "ko", "khong"]


# ------------------- Utils -------------------
def parse_schema_any(
    schema_text: str, file_hint: str | None = None, sample_cap: int = 500
):
    """
    Trả về dict {table: [(col, generic_type), ...]}
    Hỗ trợ: CREATE TABLE, JSON/JSONL, CSV header, và text tự do.
    """
    txt = schema_text or ""
    # 1) DDL
    ddl_found = False
    typed = {}
    for m in re.finditer(
        r"CREATE\s+TABLE\s+([`\"\w\.]+)\s*\((.*?)\)", txt, flags=re.I | re.S
    ):
        ddl_found = True
        tname = _norm_table(m.group(1))
        cols_block = m.group(2)
        cols = []
        for c in re.finditer(
            r"^\s*`?(\w+)`?\s+([A-Za-z][\w\(\)\s,'\.]+)", cols_block, flags=re.M
        ):
            col, typ = c.group(1), c.group(2).strip()
            lo = typ.lower()
            if any(k in lo for k in ["datetime", "date"]):
                g = "time"
            elif "int" in lo or "uint" in lo or "float" in lo or "decimal" in lo:
                g = "num"
            elif "string" in lo or "fixedstring" in lo:
                g = "text"
            elif "array" in lo:
                g = "array"
            elif "bool" in lo:
                g = "bool"
            else:
                g = _ctype_from_name_and_val(col, None)
            if col.lower() in _ID_NAME or col.lower().endswith("_id"):
                g = "id"
            cols.append((col, g))
        if cols:
            typed[tname] = cols
    if typed:
        return typed

    # 2) JSON / JSONL
    def _try_json_lines(s: str):
        rows = []
        for i, line in enumerate(io.StringIO(s)):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    rows.append(obj)
                    if len(rows) >= sample_cap:
                        break
            except:
                # nếu gặp một dòng không parse được → coi như không phải JSONL
                return []
        return rows

    json_rows = []
    try:
        # dạng JSON array/object
        jobj = json.loads(txt)
        if isinstance(jobj, list):
            json_rows = [x for x in jobj if isinstance(x, dict)][:sample_cap]
        elif isinstance(jobj, dict):
            json_rows = [jobj]
    except:
        # JSONL (1 object mỗi dòng)
        json_rows = _try_json_lines(txt)

    if json_rows:
        # đoán table name
        tname = _norm_table((file_hint or "uploaded").split("/")[-1].split(".")[0])
        field_types = {}
        for r in json_rows:
            flat = _flatten(r)
            for k, v in flat.items():
                g = _ctype_from_name_and_val(k, v)
                # giữ loại "mạnh" hơn (time/id/num ưu tiên)
                old = field_types.get(k)
                rank = {
                    "id": 5,
                    "time": 4,
                    "num": 3,
                    "cat": 2,
                    "text": 1,
                    "bool": 3,
                    "array": 2,
                    "object": 1,
                }
                if not old or rank.get(g, 1) > rank.get(old, 1):
                    field_types[k] = g
        cols = sorted(field_types.items(), key=lambda x: (x[1] != "id", x[0]))
        return {tname: cols}

    # 3) CSV
    try:
        sniff = csv.Sniffer().sniff(txt.splitlines()[0])
        reader = csv.reader(io.StringIO(txt), dialect=sniff)
        rows = list(reader)
        if rows and len(rows[0]) > 1:
            header = rows[0]
            # lấy 50 dòng mẫu để đoán kiểu
            sample = rows[1:sample_cap]
            col_types = []
            for ix, h in enumerate(header):
                vals = [r[ix] for r in sample if len(r) > ix]
                g = "text"
                for v in vals:
                    if _TIME_PAT.match(v or ""):
                        g = "time"
                        break
                    try:
                        float(v)
                        g = "num"
                    except:
                        pass
                if h.lower() in _ID_NAME or h.lower().endswith("_id"):
                    g = "id"
                col_types.append((h, g))
            tname = _norm_table((file_hint or "uploaded").split("/")[-1].split(".")[0])
            return {tname: col_types}
    except Exception:
        pass

    # 4) Text tự do: móc ra các "từ" dạng *_id, created_at, status,...
    tokens = set()
    for m in re.finditer(r"\b[a-zA-Z_][a-zA-Z0-9_]{2,}\b", txt):
        tokens.add(m.group(0))
    id_candidates = [
        t for t in tokens if t.lower().endswith("_id") or t.lower() in _ID_NAME
    ]
    time_candidates = [
        t
        for t in tokens
        if any(
            k in t.lower() for k in ["created", "updated", "date", "time", "resolved"]
        )
    ]
    cat_candidates = [
        t
        for t in tokens
        if any(
            k in t.lower()
            for k in ["status", "channel", "category", "type", "priority"]
        )
    ]
    common = (
        list({*id_candidates, *time_candidates, *cat_candidates})[:20]
        or list(tokens)[:10]
    )
    cols = []
    for c in common:
        cols.append((c, _ctype_from_name_and_val(c, None)))
    if cols:
        tname = _norm_table((file_hint or "uploaded").split("/")[-1].split(".")[0])
        return {tname: cols}

    return {}


def _flatten(d, parent="", sep="."):
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            out.update(_flatten(v, parent + k + sep, sep))
    elif isinstance(d, list):
        # đại diện mảng bằng join text; đồng thời ghi thêm size
        out[parent[:-1]] = d
        out[parent[:-1] + "_len"] = len(d)
    else:
        out[parent[:-1]] = d
    return out


def _ctype_from_name_and_val(name: str, val):
    n = (name or "").lower()
    # Ưu tiên theo tên
    if n in _ID_NAME or n.endswith("_id"):
        return "id"
    if any(k in n for k in ["created", "updated", "resolved", "date", "time"]):
        return "time"
    if any(
        k in n for k in ["status", "channel", "category", "type", "state", "priority"]
    ):
        return "cat"
    # Theo giá trị
    if isinstance(val, bool):
        return "bool"
    if isinstance(val, (int, float)):
        return "num"
    if isinstance(val, list):
        return "array"
    if isinstance(val, dict):
        return "object"
    if isinstance(val, str):
        if _TIME_PAT.match(val):
            return "time"
        try:
            float(val)
            # đừng nhầm id string thành số: nếu tên gợi ý id thì vẫn là id
            return "num" if "id" not in n else "id"
        except:
            pass
        return "text"
    return "text"


def _norm_table(s: str) -> str:
    s = (s or "").strip().strip('`"')
    return s.split(".")[-1]


def _sqlfp(s: str) -> str:
    # fingerprint cho SQL: bỏ comment, lower, gọn khoảng trắng
    s = re.sub(r"--.*?$", "", s or "", flags=re.M)
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    return re.sub(r"\s+", " ", s.strip().lower())


def _qfp(s: str) -> str:
    # fingerprint cho câu hỏi: lower + gọn khoảng trắng
    return re.sub(r"\s+", " ", (s or "").strip().lower())


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


def parse_table_columns_typed(schema_text: str) -> dict[str, list[tuple[str, str]]]:
    """
    Trả về {table: [(col, type), ...]} dựa trên CREATE TABLE.
    Bắt cả kiểu để bóc tách time/number/string tốt hơn.
    """
    out = {}
    for mm in re.finditer(
        r"CREATE\s+TABLE\s+([`\"\w\.]+)\s*\((.*?)\)", schema_text, flags=re.I | re.S
    ):
        t = _normalize_table_name(mm.group(1))
        block = mm.group(2)
        cols = []
        for c in re.finditer(
            r"^\s*`?(\w+)`?\s+([A-Za-z][\w\(\)\s,'\.]+)", block, flags=re.M
        ):
            col = c.group(1)
            typ = c.group(2).strip()
            cols.append((col, typ))
        if t and cols:
            out[t] = cols
    return out


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


# ------------------- SQLCoder callers -------------------
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


# ------------------- Heuristic fallback (không dùng Gemini) -------------------
def _pick_table(schema_text: str) -> str:
    if ACTIVE_PRIMARY_TABLE:
        return ACTIVE_PRIMARY_TABLE
    if ACTIVE_TABLES:
        return ACTIVE_TABLES[0]
    ms = re.findall(r"CREATE\s+TABLE\s+([`\"\w\.]+)\s*\(", schema_text, flags=re.I)
    if ms:
        return _normalize_table_name(ms[0])
    return "table"


def generate_sql_heuristic(schema_text: str, question: str) -> str:
    q = (question or "").lower()
    t = _pick_table(schema_text)
    # vài mẫu phổ biến
    if (
        "hiển thị" in q
        and ("20" in q or "hai mươi" in q)
        or "20 dòng" in q
        or "show" in q
    ):
        return f"SELECT * FROM {t} LIMIT 20;"
    if "đếm tổng" in q or "tổng số bản ghi" in q or "đếm số bản ghi" in q:
        return f"SELECT count(*) FROM {t};"
    m = re.search(r"đếm số\s+(\w+)\s+khác nhau", q)
    if m:
        col = m.group(1)
        return f"SELECT count(DISTINCT {col}) FROM {t};"
    # fallback chung
    return f"SELECT * FROM {t} LIMIT 20;"


def generate_refined_sql_heuristic(
    schema_text: str, question: str, prev_sql: str, feedback: str, extra: str
) -> str:
    # đơn giản: tạo lại từ câu hỏi (ưu tiên cột nhắc trong feedback/extra)
    base = generate_sql_heuristic(schema_text, question)
    # nếu feedback gợi ý "distinct <col>"
    m = re.search(r"distinct\s+(\w+)", feedback.lower())
    if not m:
        m = re.search(r"distinct\s+(\w+)", (extra or "").lower())
    if m:
        col = m.group(1)
        t = _pick_table(schema_text)
        return f"SELECT count(DISTINCT {col}) FROM {t};"
    return base


# ------------------- Hybrid routers (SQLCoder + heuristic) -------------------
def hybrid_generate_sql(schema_text: str, question: str) -> Tuple[str, str]:
    if HYBRID_STRATEGY == "sqlcoder_only":
        s = generate_sql_with_sqlcoder(schema_text, question) or ""
        return (s or generate_sql_heuristic(schema_text, question)), "sqlcoder"
    # cascade: thử sqlcoder -> heuristic
    s1 = generate_sql_with_sqlcoder(schema_text, question) or ""
    if s1 and looks_valid_sql(s1):
        return s1, "sqlcoder"
    s2 = generate_sql_heuristic(schema_text, question)
    return s2, ("sqlcoder+heuristic" if s1 else "heuristic")


def hybrid_refine_sql(
    schema_text: str, question: str, prev_sql: str, feedback: str, extra: str
) -> Tuple[str, str]:
    if REFINE_STRATEGY == "sqlcoder":
        s1 = (
            generate_sql_with_sqlcoder(
                schema_text,
                f"{question}\nPrevious SQL: {prev_sql}\nFix: {feedback}\nExtra: {extra}",
            )
            or ""
        )
        if s1 and s1.strip().lower() != prev_sql.strip().lower():
            return s1, "refined_sqlcoder"
        s2 = generate_refined_sql_heuristic(
            schema_text, question, prev_sql, feedback, extra
        )
        return s2, "refined_heuristic"
    # cascade refine
    s1 = (
        generate_sql_with_sqlcoder(
            schema_text,
            f"{question}\nPrevious SQL: {prev_sql}\nFix: {feedback}\nExtra: {extra}",
        )
        or ""
    )
    if s1 and s1.strip().lower() != prev_sql.strip().lower():
        return s1, "refined_sqlcoder"
    s2 = generate_refined_sql_heuristic(
        schema_text, question, prev_sql, feedback, extra
    )
    return s2, "refined_sqlcoder+heuristic"


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
        # chống trùng SQL ở file memories_...
        existing = set()
        if os.path.exists(ACTIVE_AGG_FILE):
            with open(ACTIVE_AGG_FILE, "r", encoding="utf-8") as f:
                for ln in f:
                    try:
                        obj = json.loads(ln)
                        existing.add(_sqlfp(obj.get("sql", "")))
                    except:
                        pass
        if _sqlfp(sql) in existing:
            return False, f"❎ Bỏ qua: SQL đã tồn tại trong {ACTIVE_AGG_FILE}"
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

    # chống trùng SQL ở file memory_<table>.txt
    existing = set()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for ln in f:
                try:
                    obj = json.loads(ln)
                    existing.add(_sqlfp(obj.get("sql", "")))
                except:
                    pass
    if _sqlfp(sql) in existing:
        return False, f"❎ Bỏ qua: SQL đã tồn tại trong {path}"

    with open(path, "a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {"question": question, "sql": sql, "table": table}, ensure_ascii=False
            )
            + "\n"
        )
    return True, f"✅ Đã lưu vào {path}"


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
    """
    Sinh nhiều biến thể Q&A theo schema:
    - Cơ bản: preview, count, distinct
    - Theo thời gian: 7/30 ngày, theo giờ
    - Theo định danh: top-N theo *_id / user_id / shop_id / conversation_id
    - Theo số: sum/avg/min/max theo ngày
    """
    tbl_cols = parse_table_columns_typed(schema_text)
    tables = (
        list(tbl_cols.keys())
        or ACTIVE_TABLES
        or ([ACTIVE_PRIMARY_TABLE] if ACTIVE_PRIMARY_TABLE else [])
    )
    tables = [t for t in tables if t]
    if not tables:
        return []

    qs = []
    for t in tables:
        cols_t = tbl_cols.get(t, [])
        names = [c for c, _ in cols_t]

        # Phân loại cột
        def is_time(col, typ):
            n = col.lower()
            return (
                "date" in n
                or "time" in n
                or "created" in n
                or "updated" in n
                or "Date" in typ
                or "DateTime" in typ
            )

        def is_num(typ):
            return any(k in typ for k in ["Int", "UInt", "Float", "Decimal"])

        def is_str(typ):
            return "String" in typ or "FixedString" in typ

        time_cols = [c for c, tp in cols_t if is_time(c, tp)]
        id_cols = [
            c
            for c in names
            if c.lower().endswith("_id")
            or c.lower()
            in (
                "id",
                "_id",
                "user_id",
                "account_id",
                "shop_id",
                "conversation_id",
                "order_id",
                "ticket_id",
            )
        ]
        num_cols = [c for c, tp in cols_t if is_num(tp)]
        str_cols = [c for c, tp in cols_t if is_str(tp)]

        # Câu hỏi cơ bản
        qs.extend(
            [
                (f"Hiển thị 20 dòng đầu tiên của bảng {t}", t),
                (f"Đếm tổng số bản ghi trong bảng {t}", t),
            ]
        )

        # Distinct theo các ID/chuỗi
        for c in (id_cols or str_cols)[:6]:
            qs.append((f"Đếm số giá trị khác nhau của {c} trong bảng {t}", t))
            qs.append((f"Top 10 {c} xuất hiện nhiều nhất trong bảng {t}", t))

        # Theo thời gian (nếu có)
        for tc in time_cols[:3]:
            qs.append(
                (
                    f"Đếm số bản ghi theo ngày trong 7 ngày gần nhất dựa trên {tc} của bảng {t}",
                    t,
                )
            )
            qs.append(
                (
                    f"Đếm số bản ghi theo ngày trong 30 ngày gần nhất dựa trên {tc} của bảng {t}",
                    t,
                )
            )
            qs.append(
                (
                    f"Phân bố số bản ghi theo giờ trong 24 giờ gần nhất dựa trên {tc} của bảng {t}",
                    t,
                )
            )

        # Số liệu tổng hợp theo ngày cho cột số
        for nc in num_cols[:3]:
            if time_cols:
                tc = time_cols[0]
                qs.append(
                    (
                        f"Tính tổng {nc} theo ngày trong 30 ngày gần nhất dựa trên {tc} của bảng {t}",
                        t,
                    )
                )
                qs.append(
                    (
                        f"Tính giá trị trung bình {nc} theo ngày trong 30 ngày gần nhất dựa trên {tc} của bảng {t}",
                        t,
                    )
                )
                qs.append(
                    (
                        f"Tính min và max của {nc} theo ngày trong 30 ngày gần nhất dựa trên {tc} của bảng {t}",
                        t,
                    )
                )
            else:
                qs.append((f"Tính tổng {nc} của bảng {t}", t))
                qs.append((f"Tính giá trị trung bình {nc} của bảng {t}", t))

        # Một ít biến thể theo điều kiện rỗng/không rỗng
        for c in (str_cols or id_cols)[:4]:
            qs.append((f"Đếm số bản ghi có {c} khác rỗng trong bảng {t}", t))

    # Khử trùng lặp theo fingerprint câu hỏi, đảo thứ tự, cắt theo limit
    uniq, seen = [], set()
    random.shuffle(qs)
    for q, t in qs:
        fp = _qfp(q)
        if fp not in seen:
            uniq.append((q, t))
            seen.add(fp)
            if len(uniq) >= limit:
                break
    return uniq

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
            if src == "sqlcoder":
                model = "SQLCoder-7B-2"
            elif src in ("cascade", "sqlcoder+heuristic"):
                model = "SQLCoder-7B-2 → Heuristic"
            elif src.startswith("refined"):
                model = src
            else:
                model = "Heuristic"
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
    if strategy not in ("sqlcoder", "cascade"):
        strategy = "cascade"

    base_pairs = synthesize_questions(schema_text, limit=rounds * 4)
    seen = collect_seen_questions_for_active()
    pool = base_pairs  # cho phép sinh lại cả câu đã có
    random.shuffle(pool)
    pairs = pool[:rounds] if pool else []

    log_path = current_pretrain_log_path()
    tried = saved = 0
    preview = []
    all_items = []
    for question, _ in pairs:
        tried += 1
        if strategy == "sqlcoder":
            raw = generate_sql_with_sqlcoder(schema_text, question)
            src = "sqlcoder"
            if not raw:
                raw = generate_sql_heuristic(schema_text, question)
                src = "heuristic"
        else:  # cascade
            raw, src = hybrid_generate_sql(schema_text, question)
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
    # refine: sqlcoder -> heuristic
    s1 = (
        generate_sql_with_sqlcoder(
            schema_text,
            f"{question}\nPrevious SQL: {prev_sql}\nFix: {feedback}\nExtra: {extra}",
        )
        or ""
    )
    if s1 and s1.strip().lower() != prev_sql.strip().lower():
        new_sql, src = s1, "refined_sqlcoder"
    else:
        new_sql, src = (
            generate_refined_sql_heuristic(
                schema_text, question, prev_sql, feedback, extra
            ),
            "refined_heuristic",
        )

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
