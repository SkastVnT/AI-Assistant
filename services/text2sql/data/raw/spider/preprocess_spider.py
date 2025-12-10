# -*- coding: utf-8 -*-
"""
Chuyển Spider (train_spider.json / tables.json) thành instruction JSONL cho SFT:
- input  = schema + question (tiếng Anh gốc; nếu có song ngữ, ghép thêm vi)
- output = câu lệnh SQL ground-truth
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # thư mục TEST/
DATA = ROOT / "data" / "spider"
OUT = ROOT / "models" / "spider_pretrain"
OUT.mkdir(parents=True, exist_ok=True)


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_schema_text(tables_json):
    # tạo map {db_id: ' "table" , "col" type , ... [SEP] ... '}
    db2schema = {}
    for db in tables_json:
        db_id = db["db_id"]
        segs = []
        for t_idx, tname in enumerate(db["table_names_original"]):
            cols = []
            for (tbl_idx, col_name), col_type in zip(
                db["column_names_original"], db["column_types"]
            ):
                if tbl_idx == t_idx and col_name != "*":
                    ctype = col_type
                    if ctype.startswith("int"):
                        ctype = "int"
                    elif ctype in ("text", "varchar", "char"):
                        ctype = "text"
                    elif ctype in ("real", "float", "double", "numeric", "decimal"):
                        ctype = "real"
                    elif ctype in ("bool", "boolean"):
                        ctype = "bool"
                    else:
                        ctype = "text"
                    cols.append(f'"{col_name}" {ctype}')
            seg = " , ".join([f'"{tname}"'] + cols)
            segs.append(seg)
        db2schema[db_id] = " [SEP] ".join(segs)
    return db2schema


def normalize_sql(s: str) -> str:
    s = s.strip()
    if not s.endswith(";"):
        s += ";"
    return s


def main():
    train = load(DATA / "train_spider.json")
    dev = load(DATA / "dev.json")
    tables = load(DATA / "tables.json")

    db2schema = build_schema_text(tables)

    def to_records(split):
        out = []
        for ex in split:
            db_id = ex["db_id"]
            schema = db2schema.get(db_id, "")
            question = ex["question"]  # Spider: tiếng Anh
            sql = normalize_sql(ex["query"])
            prompt = (
                "### Instruction:\n"
                "Bạn là trợ lý Text-to-SQL. Viết CHỈ 1 câu lệnh SQL phù hợp yêu cầu.\n"
                "- Không giải thích.\n"
                "- Không bọc backticks.\n"
                "- Dựa vào schema và câu hỏi.\n\n"
                f"### Schema:\n{schema}\n\n"
                f"### Input:\n{question}\n\n"
                "### SQL:"
            )
            out.append({"input": prompt, "output": sql})
        return out

    trn = to_records(train)
    val = to_records(dev)

    with open(OUT / "train.jsonl", "w", encoding="utf-8") as f:
        for r in trn:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(OUT / "val.jsonl", "w", encoding="utf-8") as f:
        for r in val:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"Done. train={len(trn)} val={len(val)} → {OUT}")


if __name__ == "__main__":
    main()
