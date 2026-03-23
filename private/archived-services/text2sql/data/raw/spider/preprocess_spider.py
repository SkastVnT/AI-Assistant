# -*- coding: utf-8 -*-
"""
Chuyá»ƒn Spider (train_spider.json / tables.json) thÃ nh instruction JSONL cho SFT:
- input  = schema + question (tiáº¿ng Anh gá»‘c; náº¿u cÃ³ song ngá»¯, ghÃ©p thÃªm vi)
- output = cÃ¢u lá»‡nh SQL ground-truth
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # thÆ° má»¥c TEST/
DATA = ROOT / "data" / "spider"
OUT = ROOT / "models" / "spider_pretrain"
OUT.mkdir(parents=True, exist_ok=True)


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_schema_text(tables_json):
    # táº¡o map {db_id: ' "table" , "col" type , ... [SEP] ... '}
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
            question = ex["question"]  # Spider: tiáº¿ng Anh
            sql = normalize_sql(ex["query"])
            prompt = (
                "### Instruction:\n"
                "Báº¡n lÃ  trá»£ lÃ½ Text-to-SQL. Viáº¿t CHá»ˆ 1 cÃ¢u lá»‡nh SQL phÃ¹ há»£p yÃªu cáº§u.\n"
                "- KhÃ´ng giáº£i thÃ­ch.\n"
                "- KhÃ´ng bá»c backticks.\n"
                "- Dá»±a vÃ o schema vÃ  cÃ¢u há»i.\n\n"
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

    print(f"Done. train={len(trn)} val={len(val)} â†’ {OUT}")


if __name__ == "__main__":
    main()
