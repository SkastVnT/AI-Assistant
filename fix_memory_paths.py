#!/usr/bin/env python3
"""Fix path traversal vulnerabilities via memory_id and source_filename."""
import re

path = "services/chatbot/chatbot_main.py"
content = open(path, encoding="utf-8-sig").read()

# ── Fix 1: get_memory - add UUID validation ──────────────────────────────────
old1 = '''@app.route("/api/memory/get/<memory_id>", methods=["GET"])
def get_memory(memory_id):
    """Get a specific memory by ID"""
    try:
        memory_file = MEMORY_DIR / f"{memory_id}.json"'''

new1 = '''@app.route("/api/memory/get/<memory_id>", methods=["GET"])
def get_memory(memory_id):
    """Get a specific memory by ID"""
    import re as _re
    if not _re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", memory_id):
        return jsonify({"error": "Invalid memory ID"}), 400
    try:
        memory_file = MEMORY_DIR / f"{memory_id}.json"'''

# ── Fix 2: delete_memory - add UUID validation ────────────────────────────────
old2 = '''@app.route("/api/memory/delete/<memory_id>", methods=["DELETE"])
def delete_memory(memory_id):
    """Delete a memory (supports both old and new format)"""
    try:'''

new2 = '''@app.route("/api/memory/delete/<memory_id>", methods=["DELETE"])
def delete_memory(memory_id):
    """Delete a memory (supports both old and new format)"""
    import re as _re
    if not _re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", memory_id):
        return jsonify({"error": "Invalid memory ID"}), 400
    try:'''

# ── Fix 3: update_memory - add UUID validation ────────────────────────────────
old3 = '''@app.route("/api/memory/update/<memory_id>", methods=["PUT"])
def update_memory(memory_id):
    """Update a memory"""
    try:
        memory_file = MEMORY_DIR / f"{memory_id}.json"'''

new3 = '''@app.route("/api/memory/update/<memory_id>", methods=["PUT"])
def update_memory(memory_id):
    """Update a memory"""
    import re as _re
    if not _re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", memory_id):
        return jsonify({"error": "Invalid memory ID"}), 400
    try:
        memory_file = MEMORY_DIR / f"{memory_id}.json"'''

# ── Fix 4: memory_ids in chat loop - validate each mem_id ────────────────────
old4 = '''        # Load selected memories
        memories = []
        if memory_ids:
            for mem_id in memory_ids:
                memory_file = MEMORY_DIR / f"{mem_id}.json"'''

new4 = '''        # Load selected memories
        memories = []
        if memory_ids:
            import re as _re
            _uuid_re = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
            for mem_id in memory_ids:
                if not _uuid_re.match(str(mem_id)):
                    continue
                memory_file = MEMORY_DIR / f"{mem_id}.json"'''

for old, new, label in [(old1, new1, "get_memory"), (old2, new2, "delete_memory"),
                         (old3, new3, "update_memory"), (old4, new4, "memory_ids_loop")]:
    if old in content:
        content = content.replace(old, new)
        print(f"Fixed: {label}")
    else:
        print(f"NOT FOUND: {label}")

open(path, 'w', encoding='utf-8-sig').write(content)
print("Saved.")
