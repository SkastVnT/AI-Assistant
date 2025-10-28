#!/usr/bin/env python3
"""
Convert Spider-format JSON files into a JSONL dataset file.

Usage:
    python tools/spider_to_dataset.py --spider-dir "D:\path\to\spider" --out data/dataset_base.jsonl --keep-all
"""

import argparse
import json
import sys
from pathlib import Path


def load_json_file(p: Path):
    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Không thể đọc {p}: {e}", file=sys.stderr)
        return None


def main():
    p = argparse.ArgumentParser(description="Convert Spider JSON -> JSONL")
    p.add_argument(
        "--spider-dir",
        required=True,
        help="Folder chứa các file spider .json (train.json, dev.json, ...)",
    )
    p.add_argument(
        "--out",
        required=True,
        help="Đường dẫn file output .jsonl (tạo thư mục nếu chưa có)",
    )
    p.add_argument(
        "--keep-all",
        action="store_true",
        help="Nếu bật: giữ lại mọi trường từ input; nếu tắt: chỉ giữ db_id, question, query",
    )
    args = p.parse_args()

    spider_dir = Path(args.spider_dir)
    out_path = Path(args.out)
    if not spider_dir.exists() or not spider_dir.is_dir():
        print(f"❌ Thư mục spider-dir không tồn tại: {spider_dir}", file=sys.stderr)
        sys.exit(2)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    # tìm json files (không đi sâu vào subfolders có thể cũng hợp lý)
    json_files = sorted(spider_dir.glob("*.json"))
    if not json_files:
        # thử tìm đệ quy
        json_files = sorted(spider_dir.rglob("*.json"))

    if not json_files:
        print(f"❌ Không tìm thấy .json trong {spider_dir}", file=sys.stderr)
        sys.exit(3)

    total_written = 0
    with out_path.open("w", encoding="utf-8") as out_f:
        for jf in json_files:
            data = load_json_file(jf)
            if data is None:
                continue
            if isinstance(data, dict):
                # cố gắng lấy list bên trong common keys
                for k in ("data", "examples", "instances", "questions", "queries"):
                    if k in data and isinstance(data[k], list):
                        data = data[k]
                        break
                else:
                    print(
                        f"⚠️ {jf} là dict nhưng không thấy list con, skip.",
                        file=sys.stderr,
                    )
                    continue

            if not isinstance(data, list):
                print(f"⚠️ Định dạng không đúng trong {jf}, skip.", file=sys.stderr)
                continue

            for item in data:
                if not isinstance(item, dict):
                    continue
                if args.keep_all:
                    out_obj = item
                else:
                    out_obj = {
                        "db_id": item.get("db_id"),
                        "question": item.get("question")
                        or item.get("question_toks")
                        or item.get("question_toks_clean"),
                        "query": item.get("query")
                        or item.get("sql")
                        or item.get("query_toks"),
                    }
                out_f.write(json.dumps(out_obj, ensure_ascii=False) + "\n")
                total_written += 1

    print(f"✅ Hoàn tất. Ghi {total_written} dòng vào {out_path}")


if __name__ == "__main__":
    main()


##mệt
