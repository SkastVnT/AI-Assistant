"""
MongoDB Seed Script for ChatBot Service

Inserts demo data (conversations, messages, learning_data) using string UUIDs.
Skips insertion if demo data already exists (idempotent by default).

Usage:
    python scripts/seed_mongodb.py                 # seed 1 conversation
    python scripts/seed_mongodb.py --count 5        # seed 5 conversations
    python scripts/seed_mongodb.py --reset           # delete demo data, then reseed
    python scripts/seed_mongodb.py --reset --count 3 # delete + seed 3
"""

import argparse
import random
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.mongodb_config import get_db, test_connection, DATABASE_NAME

# All seeded docs carry this tag so they can be identified and cleaned up.
SEED_MARKER = "seed_demo"

# ============================================================================
# Data templates
# ============================================================================

MODELS = ["grok-3", "gpt-4o", "gemini-2.0-flash", "claude-sonnet-4"]

EXCHANGE_TEMPLATES = [
    [
        ("user", "What is machine learning?"),
        ("assistant", (
            "Machine learning is a subset of artificial intelligence that enables "
            "systems to learn patterns from data and make predictions without being "
            "explicitly programmed. Common approaches include supervised learning, "
            "unsupervised learning, and reinforcement learning."
        )),
        ("user", "Can you give me a simple example?"),
        ("assistant", (
            "Sure! A spam filter is a classic example. You feed it thousands of "
            "emails labeled 'spam' or 'not spam'. The model learns patterns — like "
            "certain keywords or sender addresses — and can then classify new emails "
            "automatically."
        )),
    ],
    [
        ("user", "How do I create a Python virtual environment?"),
        ("assistant", (
            "Run:\n```bash\npython -m venv myenv\n```\n"
            "Then activate it:\n"
            "- Windows: `myenv\\Scripts\\activate`\n"
            "- Linux/Mac: `source myenv/bin/activate`\n\n"
            "Install packages inside the venv and they stay isolated from your "
            "system Python."
        )),
    ],
    [
        ("user", "Explain the difference between SQL and NoSQL databases."),
        ("assistant", (
            "SQL databases (PostgreSQL, MySQL) store data in structured tables with "
            "fixed schemas and use SQL for queries. They excel at complex joins and "
            "transactions.\n\n"
            "NoSQL databases (MongoDB, Redis, Cassandra) use flexible schemas — "
            "documents, key-value pairs, or graphs. They scale horizontally and are "
            "great for unstructured or rapidly evolving data."
        )),
        ("user", "When should I pick NoSQL over SQL?"),
        ("assistant", (
            "Consider NoSQL when you need:\n"
            "- Flexible or evolving schemas\n"
            "- Horizontal scaling across many servers\n"
            "- High write throughput\n"
            "- Document-oriented data (e.g. JSON)\n\n"
            "Stick with SQL when you need strong consistency, complex joins, or "
            "ACID transactions across multiple tables."
        )),
    ],
    [
        ("user", "What are the SOLID principles?"),
        ("assistant", (
            "SOLID is five object-oriented design principles:\n\n"
            "1. **Single Responsibility** — a class should have one reason to change\n"
            "2. **Open/Closed** — open for extension, closed for modification\n"
            "3. **Liskov Substitution** — subtypes must be substitutable for base types\n"
            "4. **Interface Segregation** — prefer small, specific interfaces\n"
            "5. **Dependency Inversion** — depend on abstractions, not concretions"
        )),
    ],
    [
        ("user", "Help me write a MongoDB aggregation pipeline to count messages per conversation."),
        ("assistant", (
            "```python\npipeline = [\n"
            "    {\"$group\": {\n"
            "        \"_id\": \"$conversation_id\",\n"
            "        \"count\": {\"$sum\": 1}\n"
            "    }},\n"
            "    {\"$sort\": {\"count\": -1}},\n"
            "    {\"$limit\": 10}\n"
            "]\nresults = db.messages.aggregate(pipeline)\n```\n\n"
            "This groups messages by `conversation_id`, counts them, sorts "
            "descending, and returns the top 10."
        )),
    ],
]

LEARNING_DATA_TEMPLATES = [
    {
        "source": "user_feedback",
        "category": "prompt_engineering",
        "data": {
            "topic": "System prompt effectiveness",
            "finding": "Adding explicit role definitions improves response accuracy by ~15%.",
            "sample_size": 200,
        },
        "quality_score": 0.87,
        "is_approved": True,
    },
    {
        "source": "conversation_analysis",
        "category": "error_patterns",
        "data": {
            "topic": "Common user frustrations",
            "finding": "Users retry within 10s when the model misunderstands intent.",
            "sample_size": 500,
        },
        "quality_score": 0.72,
        "is_approved": False,
        "rejection_reason": "Needs larger sample before approval.",
    },
    {
        "source": "model_evaluation",
        "category": "performance",
        "data": {
            "topic": "Response latency by model",
            "finding": "grok-3 avg 1.2s, gpt-4o avg 2.1s, gemini-2.0-flash avg 0.8s",
            "models_tested": ["grok-3", "gpt-4o", "gemini-2.0-flash"],
        },
        "quality_score": 0.93,
        "is_approved": True,
    },
]


# ============================================================================
# Helpers
# ============================================================================

def _uid():
    return str(uuid.uuid4())


def _realistic_time(base, offset_minutes):
    """Return base + offset as a datetime."""
    return base + timedelta(minutes=offset_minutes)


# ============================================================================
# Seed functions
# ============================================================================

def seed_conversation(db, index, base_time):
    """Create one conversation with messages. Returns summary dict."""
    template = EXCHANGE_TEMPLATES[index % len(EXCHANGE_TEMPLATES)]
    model = MODELS[index % len(MODELS)]
    conv_id = _uid()
    session_id = _uid()
    conv_start = _realistic_time(base_time, index * 30)

    # Build messages
    messages = []
    for i, (role, content) in enumerate(template):
        msg_time = _realistic_time(conv_start, i * 2 + 1)
        tokens = len(content.split()) * 2 if role == "assistant" else None
        messages.append({
            "_id": _uid(),
            "conversation_id": conv_id,
            "role": role,
            "content": content,
            "metadata": {"model": model, "seed": SEED_MARKER} if role == "assistant" else {"seed": SEED_MARKER},
            "images": [],
            "tokens": tokens,
            "is_edited": False,
            "edit_history": [],
            "created_at": msg_time,
            "updated_at": msg_time,
        })

    # Conversation document
    titles = [
        "Machine learning basics",
        "Python virtual environments",
        "SQL vs NoSQL databases",
        "SOLID design principles",
        "MongoDB aggregation pipelines",
    ]
    conversation = {
        "_id": conv_id,
        "user_id": "demo_user",
        "title": titles[index % len(titles)],
        "model": model,
        "session_id": session_id,
        "is_archived": False,
        "is_deleted": False,
        "message_count": len(messages),
        "metadata": {"seed": SEED_MARKER, "temperature": 0.7},
        "created_at": conv_start,
        "updated_at": messages[-1]["created_at"],
    }

    db.conversations.insert_one(conversation)
    db.messages.insert_many(messages)
    return {"conv_id": conv_id, "messages": len(messages)}


def seed_learning_data(db, base_time):
    """Insert learning_data records. Returns count inserted."""
    docs = []
    for i, tmpl in enumerate(LEARNING_DATA_TEMPLATES):
        doc = {
            "_id": _uid(),
            "source": tmpl["source"],
            "category": tmpl["category"],
            "data": tmpl["data"],
            "quality_score": tmpl["quality_score"],
            "is_approved": tmpl["is_approved"],
            "created_at": _realistic_time(base_time, i * 60),
            "reviewed_at": _realistic_time(base_time, i * 60 + 30) if tmpl["is_approved"] else None,
            "rejection_reason": tmpl.get("rejection_reason"),
        }
        docs.append(doc)
    db.learning_data.insert_many(docs)
    return len(docs)


def remove_seed_data(db):
    """Delete all documents tagged with the seed marker."""
    conv_r = db.conversations.delete_many({"metadata.seed": SEED_MARKER})
    msg_r = db.messages.delete_many({"metadata.seed": SEED_MARKER})
    ld_r = db.learning_data.delete_many({"data.finding": {"$exists": True}, "_id": {"$type": "string"}})
    # Learning data doesn't have metadata.seed, use a targeted delete
    # Re-delete learning data seeded by this script (they have our specific sources)
    ld_sources = [t["source"] for t in LEARNING_DATA_TEMPLATES]
    ld_r = db.learning_data.delete_many({"source": {"$in": ld_sources}})
    print(f"  conversations: {conv_r.deleted_count} removed")
    print(f"  messages:      {msg_r.deleted_count} removed")
    print(f"  learning_data: {ld_r.deleted_count} removed")


def already_seeded(db):
    """Check if demo data already exists."""
    return db.conversations.count_documents({"metadata.seed": SEED_MARKER}) > 0


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Seed demo data into MongoDB")
    parser.add_argument("--reset", action="store_true", help="Remove existing demo data before seeding")
    parser.add_argument("--count", type=int, default=1, help="Number of demo conversations to create (default: 1)")
    args = parser.parse_args()

    if args.count < 1:
        print("--count must be >= 1")
        sys.exit(1)

    print(f"=== MongoDB Seed | database: {DATABASE_NAME} ===\n")

    # Connect
    print("[connect]")
    if not test_connection():
        print("  FAIL -- check MONGODB_URI")
        sys.exit(2)
    db = get_db()
    print(f"  OK -- {DATABASE_NAME}\n")

    # Reset
    if args.reset:
        print("[reset]")
        remove_seed_data(db)
        print()

    # Check existing
    if not args.reset and already_seeded(db):
        print("[skip] Demo data already exists. Use --reset to replace it.")
        sys.exit(0)

    # Seed
    print(f"[seed] Creating {args.count} conversation(s)...")
    base_time = datetime(2026, 3, 15, 9, 0, 0)
    total_msgs = 0
    for i in range(args.count):
        result = seed_conversation(db, i, base_time)
        total_msgs += result["messages"]
        print(f"  + conversation {i + 1}: {result['conv_id'][:8]}... ({result['messages']} messages)")

    print(f"\n[seed] Creating learning_data...")
    ld_count = seed_learning_data(db, base_time)
    print(f"  + {ld_count} records\n")

    # Summary
    print("[summary]")
    print(f"  conversations: {db.conversations.count_documents({})}")
    print(f"  messages:      {db.messages.count_documents({})}")
    print(f"  learning_data: {db.learning_data.count_documents({})}")

    print("\nDone.")


if __name__ == "__main__":
    main()
