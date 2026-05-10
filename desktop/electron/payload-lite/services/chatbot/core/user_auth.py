"""
User Authentication Module
Handles user creation, authentication, admin management, and quota enforcement.
"""
import logging
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

logger = logging.getLogger(__name__)

# Admins with no limits and full access
ADMIN_USERS = [
    {"username": "admin",    "email": "admin@assistant.local",    "role": "admin"},
    {"username": "skastvnt", "email": "skastvnt@assistant.local", "role": "admin"},
]
ADMIN_DEFAULT_PASSWORD = "04122003"
ADMIN_USERNAMES = {a["username"] for a in ADMIN_USERS}

# Quota defaults for regular users
IMAGE_GEN_LIMIT = 5   # images per user total (lifetime for now)
VIDEO_GEN_ENABLED = False  # video is premium — requires payment approval


def init_admin_users(db):
    """Seed admin users into MongoDB if they don't exist."""
    if db is None:
        logger.warning("[Auth] No DB — skipping admin seed")
        return
    users_col = db["users"]
    try:
        users_col.create_index("username", unique=True)
    except Exception:
        pass
    for admin in ADMIN_USERS:
        try:
            users_col.update_one(
                {"username": admin["username"]},
                {"$setOnInsert": {
                    "username": admin["username"],
                    "email": admin["email"],
                    "password_hash": generate_password_hash(ADMIN_DEFAULT_PASSWORD),
                    "role": admin["role"],
                    "display_name": admin["username"].title(),
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "is_active": True,
                    "image_quota_used": 0,
                    "video_unlocked": True,   # admins always unlocked
                }},
                upsert=True,
            )
            # Always ensure role=admin + video_unlocked for existing admin records
            users_col.update_one(
                {"username": admin["username"]},
                {"$set": {"role": "admin", "video_unlocked": True, "updated_at": datetime.utcnow()}},
            )
            logger.info(f"[Auth] Ensured admin user: {admin['username']}")
        except Exception as e:
            logger.warning(f"[Auth] Could not seed {admin['username']}: {e}")


def is_admin(username: str) -> bool:
    return username in ADMIN_USERNAMES


def authenticate_user(db, username, password):
    """Authenticate a user. Returns user dict or None."""
    if db is None:
        return None
    users_col = db["users"]
    user = users_col.find_one({"username": username, "is_active": True})
    if user and check_password_hash(user["password_hash"], password):
        users_col.update_one(
            {"_id": user["_id"]},
            {"$set": {"last_login": datetime.utcnow()}},
        )
        return {
            "user_id": user["username"],
            "username": user["username"],
            "role": user.get("role", "user"),
            "display_name": user.get("display_name", user["username"]),
            "image_quota_used": user.get("image_quota_used", 0),
            "video_unlocked": user.get("video_unlocked", is_admin(username)),
        }
    return None


def create_user(db, username, password, role="user", display_name=None, email=None):
    """Create a new user. Returns user dict or None if exists."""
    if db is None:
        return None
    users_col = db["users"]
    if users_col.find_one({"username": username}):
        return None
    doc = {
        "username": username,
        "password_hash": generate_password_hash(password),
        "role": role,
        "display_name": display_name or username,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "is_active": True,
        "image_quota_used": 0,
        "video_unlocked": is_admin(username),
    }
    if email:
        doc["email"] = email
    users_col.insert_one(doc)
    return {"username": username, "role": role, "display_name": display_name or username}


def change_password(db, username, new_password):
    """Change a user's password."""
    if db is None:
        return False
    users_col = db["users"]
    result = users_col.update_one(
        {"username": username},
        {"$set": {"password_hash": generate_password_hash(new_password), "updated_at": datetime.utcnow()}},
    )
    return result.modified_count > 0


def list_users(db):
    """List all users (excluding password hash)."""
    if db is None:
        return []
    users_col = db["users"]
    users = list(users_col.find({}, {"password_hash": 0}).sort("created_at", -1))
    for u in users:
        u["_id"] = str(u["_id"])
    return users


def toggle_user_active(db, username, active):
    """Enable or disable a user."""
    if db is None:
        return False
    if username in ADMIN_USERNAMES:
        return False
    users_col = db["users"]
    result = users_col.update_one(
        {"username": username},
        {"$set": {"is_active": active, "updated_at": datetime.utcnow()}},
    )
    return result.modified_count > 0


# ─── Quota helpers ────────────────────────────────────────────────────────────

def get_user_quota(db, username: str) -> dict:
    """Return quota info for a user."""
    if db is None:
        return {"image_quota_used": 0, "image_quota_limit": IMAGE_GEN_LIMIT, "video_unlocked": False}
    if is_admin(username):
        return {"image_quota_used": 0, "image_quota_limit": None, "video_unlocked": True}
    user = db["users"].find_one({"username": username}, {"image_quota_used": 1, "video_unlocked": 1})
    if not user:
        return {"image_quota_used": 0, "image_quota_limit": IMAGE_GEN_LIMIT, "video_unlocked": False}
    return {
        "image_quota_used": user.get("image_quota_used", 0),
        "image_quota_limit": IMAGE_GEN_LIMIT,
        "video_unlocked": user.get("video_unlocked", False),
    }


def check_image_quota(db, username: str) -> tuple[bool, str]:
    """Returns (allowed, reason). Admins always allowed."""
    if is_admin(username):
        return True, ""
    quota = get_user_quota(db, username)
    used = quota["image_quota_used"]
    limit = quota["image_quota_limit"]
    if used >= limit:
        return False, f"Bạn đã dùng hết {limit} lượt tạo ảnh. Liên hệ admin để được nâng cấp."
    return True, ""


def increment_image_quota(db, username: str, count: int = 1):
    """Increment image usage counter."""
    if is_admin(username):
        return
    db["users"].update_one(
        {"username": username},
        {"$inc": {"image_quota_used": count}},
    )


def check_video_access(db, username: str) -> tuple[bool, str]:
    """Returns (allowed, reason). Admins always allowed."""
    if is_admin(username):
        return True, ""
    user = db["users"].find_one({"username": username}, {"video_unlocked": 1})
    if user and user.get("video_unlocked"):
        return True, ""
    # Check if there's a pending payment request
    pending = db.get_collection("payment_requests").find_one(
        {"username": username, "status": "pending"}
    )
    if pending:
        return False, "Yêu cầu mở khóa đang chờ admin xét duyệt."
    return False, "Tính năng tạo video yêu cầu thanh toán. Vui lòng quét mã QR để mở khóa."


# ─── Payment requests ─────────────────────────────────────────────────────────

def create_payment_request(db, username: str, note: str = "") -> dict:
    """Create a video unlock payment request."""
    if db is None:
        return {}
    col = db["payment_requests"]
    # Only one pending per user
    existing = col.find_one({"username": username, "status": "pending"})
    if existing:
        existing["_id"] = str(existing["_id"])
        return existing
    doc = {
        "username": username,
        "type": "video_unlock",
        "status": "pending",
        "note": note,
        "created_at": datetime.utcnow(),
        "reviewed_at": None,
        "reviewed_by": None,
    }
    result = col.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc


def approve_payment_request(db, request_id: str, admin_username: str) -> bool:
    """Approve a payment request — unlock video for that user."""
    from bson import ObjectId
    col = db["payment_requests"]
    req = col.find_one({"_id": ObjectId(request_id), "status": "pending"})
    if not req:
        return False
    username = req["username"]
    db["users"].update_one(
        {"username": username},
        {"$set": {"video_unlocked": True, "updated_at": datetime.utcnow()}},
    )
    col.update_one(
        {"_id": ObjectId(request_id)},
        {"$set": {"status": "approved", "reviewed_at": datetime.utcnow(), "reviewed_by": admin_username}},
    )
    logger.info(f"[Auth] Video unlocked for {username} by {admin_username}")
    return True


def reject_payment_request(db, request_id: str, admin_username: str) -> bool:
    """Reject a payment request."""
    from bson import ObjectId
    col = db["payment_requests"]
    result = col.update_one(
        {"_id": ObjectId(request_id), "status": "pending"},
        {"$set": {"status": "rejected", "reviewed_at": datetime.utcnow(), "reviewed_by": admin_username}},
    )
    return result.modified_count > 0


def list_payment_requests(db, status: str = None) -> list:
    """List payment requests, optionally filtered by status."""
    if db is None:
        return []
    query = {}
    if status:
        query["status"] = status
    items = list(db["payment_requests"].find(query).sort("created_at", -1))
    for item in items:
        item["_id"] = str(item["_id"])
    return items


def reset_image_quota(db, username: str) -> bool:
    """Reset a user's image quota (admin action)."""
    result = db["users"].update_one(
        {"username": username},
        {"$set": {"image_quota_used": 0, "updated_at": datetime.utcnow()}},
    )
    return result.modified_count > 0


def set_image_quota_limit(db, username: str, limit: int) -> bool:
    """Set custom image quota limit for a user (stored as override)."""
    result = db["users"].update_one(
        {"username": username},
        {"$set": {"image_quota_limit_override": limit, "updated_at": datetime.utcnow()}},
    )
    return result.modified_count > 0



def init_admin_users(db):
    """Seed admin users into MongoDB if they don't exist."""
    if db is None:
        logger.warning("[Auth] No DB — skipping admin seed")
        return
    users_col = db["users"]
    # Ensure unique index on username
    try:
        users_col.create_index("username", unique=True)
    except Exception:
        pass
    for admin in ADMIN_USERS:
        try:
            users_col.update_one(
                {"username": admin["username"]},
                {"$setOnInsert": {
                    "username": admin["username"],
                    "email": admin["email"],
                    "password_hash": generate_password_hash(ADMIN_DEFAULT_PASSWORD),
                    "role": admin["role"],
                    "display_name": admin["username"].title(),
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "is_active": True,
                }},
                upsert=True,
            )
            # Always ensure role = admin for existing records
            users_col.update_one(
                {"username": admin["username"], "role": {"$ne": "admin"}},
                {"$set": {"role": "admin", "updated_at": datetime.utcnow()}},
            )
            logger.info(f"[Auth] Ensured admin user: {admin['username']}")
        except Exception as e:
            logger.warning(f"[Auth] Could not seed {admin['username']}: {e}")


def authenticate_user(db, username, password):
    """Authenticate a user. Returns user dict or None."""
    if db is None:
        return None
    users_col = db["users"]
    user = users_col.find_one({"username": username, "is_active": True})
    if user and check_password_hash(user["password_hash"], password):
        users_col.update_one(
            {"_id": user["_id"]},
            {"$set": {"last_login": datetime.utcnow()}},
        )
        return {
            "user_id": user["username"],
            "username": user["username"],
            "role": user.get("role", "user"),
            "display_name": user.get("display_name", user["username"]),
        }
    return None


def create_user(db, username, password, role="user", display_name=None, email=None):
    """Create a new user. Returns user dict or None if exists."""
    if db is None:
        return None
    users_col = db["users"]
    if users_col.find_one({"username": username}):
        return None  # already exists
    doc = {
        "username": username,
        "password_hash": generate_password_hash(password),
        "role": role,
        "display_name": display_name or username,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "is_active": True,
    }
    if email:
        doc["email"] = email
    users_col.insert_one(doc)
    return {"username": username, "role": role, "display_name": display_name or username}


def change_password(db, username, new_password):
    """Change a user's password."""
    if db is None:
        return False
    users_col = db["users"]
    result = users_col.update_one(
        {"username": username},
        {"$set": {"password_hash": generate_password_hash(new_password), "updated_at": datetime.utcnow()}},
    )
    return result.modified_count > 0


def list_users(db):
    """List all users (excluding password hash)."""
    if db is None:
        return []
    users_col = db["users"]
    users = list(users_col.find({}, {"password_hash": 0}).sort("created_at", -1))
    for u in users:
        u["_id"] = str(u["_id"])
    return users


def toggle_user_active(db, username, active):
    """Enable or disable a user."""
    if db is None:
        return False
    # Protect admin accounts from being disabled
    if username in [a["username"] for a in ADMIN_USERS]:
        return False
    users_col = db["users"]
    result = users_col.update_one(
        {"username": username},
        {"$set": {"is_active": active, "updated_at": datetime.utcnow()}},
    )
    return result.modified_count > 0


def update_user_profile(db, username, display_name=None, avatar_data=None, bio=None):
    """Update user profile fields (display_name, avatar_data, bio). Returns updated dict or None."""
    if db is None:
        return None
    users_col = db["users"]
    update_fields = {"updated_at": datetime.utcnow()}
    if display_name is not None:
        update_fields["display_name"] = display_name.strip() or username
    if avatar_data is not None:
        update_fields["avatar_data"] = avatar_data
    if bio is not None:
        update_fields["bio"] = bio.strip()[:200]
    result = users_col.update_one({"username": username}, {"$set": update_fields})
    if result.matched_count:
        user = users_col.find_one(
            {"username": username},
            {"_id": 0, "display_name": 1, "avatar_data": 1, "bio": 1},
        )
        return {
            "display_name": user.get("display_name", username),
            "avatar_data": user.get("avatar_data", ""),
            "bio": user.get("bio", ""),
        }
    return None

