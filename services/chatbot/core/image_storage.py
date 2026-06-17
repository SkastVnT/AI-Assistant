"""
Image Storage Service
Upload images to ImgBB and save metadata to MongoDB/Firebase
"""

import base64
import hashlib
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

# ImgBB API
IMGBB_API_KEY = os.getenv("IMGBB_API_KEY", "")
IMGBB_UPLOAD_URL = "https://api.imgbb.com/1/upload"

# Google Drive (now using Service Account instead of webhook)
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
GOOGLE_DRIVE_FOLDER_URL = (
    "https://drive.google.com/drive/folders/" + GOOGLE_DRIVE_FOLDER_ID
    if GOOGLE_DRIVE_FOLDER_ID
    else None
)
GOOGLE_DRIVE_ENABLED = os.getenv(
    "GOOGLE_DRIVE_ENABLED", "true"
).strip().lower() not in ("0", "false", "no", "off", "")

# Initialize Google Drive Service (only when explicitly enabled)
if GOOGLE_DRIVE_ENABLED:
    try:
        from .google_drive_service import GoogleDriveService

        drive_service = GoogleDriveService()
        if GOOGLE_DRIVE_FOLDER_ID:
            drive_service.set_folder_id(GOOGLE_DRIVE_FOLDER_ID)
        logger.info("[ImageStorage] Google Drive service initialized")
    except Exception as e:
        drive_service = None
        logger.warning(f"[ImageStorage] Google Drive service init failed: {e}")
else:
    drive_service = None
    logger.info("[ImageStorage] Google Drive disabled (GOOGLE_DRIVE_ENABLED=false)")

# MongoDB (optional)
try:
    import gridfs
    from pymongo import MongoClient

    MONGO_URI = os.getenv("MONGODB_URI", "")
    MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "chatbot_db").strip() or "chatbot_db"
    MONGODB_X509_ENABLED = os.getenv("MONGODB_X509_ENABLED", "false").lower() == "true"
    MONGODB_X509_URI = os.getenv("MONGODB_X509_URI", "").strip()
    MONGODB_X509_CERT_PATH = os.getenv("MONGODB_X509_CERT_PATH", "").strip()
    MONGODB_TLS_ALLOW_INVALID_CERTIFICATES = (
        os.getenv("MONGODB_TLS_ALLOW_INVALID_CERTIFICATES", "false").lower() == "true"
    )
    mongo_uri = (
        MONGODB_X509_URI if (MONGODB_X509_ENABLED and MONGODB_X509_URI) else MONGO_URI
    )

    if mongo_uri:
        connect_kwargs = {
            "serverSelectionTimeoutMS": 5000,
            "tls": True,
            "tlsAllowInvalidCertificates": MONGODB_TLS_ALLOW_INVALID_CERTIFICATES,
        }

        if MONGODB_X509_ENABLED and MONGODB_X509_CERT_PATH:
            cert_path = Path(MONGODB_X509_CERT_PATH)
            if cert_path.exists():
                connect_kwargs["tlsCertificateKeyFile"] = str(cert_path)
                connect_kwargs["authMechanism"] = "MONGODB-X509"
                connect_kwargs["authSource"] = "$external"
            else:
                logger.warning(f"[ImageStorage] X.509 cert file not found: {cert_path}")

        mongo_client = MongoClient(mongo_uri, **connect_kwargs)
        mongo_client.admin.command("ping")
        mongo_db = mongo_client[MONGODB_DB_NAME]
        images_collection = mongo_db["generated_images"]
        legacy_assets_collection = mongo_db["raw_legacy_assets"]
        legacy_gridfs = gridfs.GridFS(mongo_db, collection="raw_assets_fs")
        logger.info(f"[ImageStorage] MongoDB connected -> database: {mongo_db.name}")
    else:
        mongo_client = None
        images_collection = None
        legacy_assets_collection = None
        legacy_gridfs = None
except Exception as e:
    logger.warning(f"[ImageStorage] MongoDB not available: {e}")
    mongo_client = None
    images_collection = None
    legacy_assets_collection = None
    legacy_gridfs = None

# Reconnect support — called lazily by save_to_mongodb when images_collection is None
_last_connect_attempt: float = 0.0
_RECONNECT_COOLDOWN = 60.0  # seconds between retry attempts


def _try_connect_mongodb() -> bool:
    """Attempt to (re)connect to MongoDB. No-op if already connected or called too recently."""
    global mongo_client, images_collection, legacy_assets_collection, legacy_gridfs, _last_connect_attempt
    import time

    if images_collection is not None:
        return True

    now = time.monotonic()
    if now - _last_connect_attempt < _RECONNECT_COOLDOWN:
        return False
    _last_connect_attempt = now

    _uri = os.getenv("MONGODB_URI", "").strip()
    _x509 = os.getenv("MONGODB_X509_ENABLED", "false").lower() == "true"
    _x509_uri = os.getenv("MONGODB_X509_URI", "").strip()
    _db_name = os.getenv("MONGODB_DB_NAME", "chatbot_db").strip() or "chatbot_db"
    _tls_invalid = os.getenv("MONGODB_TLS_ALLOW_INVALID_CERTIFICATES", "false").lower() == "true"
    _cert = os.getenv("MONGODB_X509_CERT_PATH", "").strip()
    _mongo_uri = _x509_uri if (_x509 and _x509_uri) else _uri

    if not _mongo_uri:
        return False

    try:
        import gridfs as _gfs
        from pymongo import MongoClient as _MC

        _kw: dict = {"serverSelectionTimeoutMS": 5000, "tls": True, "tlsAllowInvalidCertificates": _tls_invalid}
        if _x509 and _cert:
            _cp = Path(_cert)
            if _cp.exists():
                _kw["tlsCertificateKeyFile"] = str(_cp)
                _kw["authMechanism"] = "MONGODB-X509"
                _kw["authSource"] = "$external"

        _client = _MC(_mongo_uri, **_kw)
        _client.admin.command("ping")
        _db = _client[_db_name]

        mongo_client = _client
        images_collection = _db["generated_images"]
        legacy_assets_collection = _db["raw_legacy_assets"]
        legacy_gridfs = _gfs.GridFS(_db, collection="raw_assets_fs")
        logger.info(f"[ImageStorage] MongoDB reconnected -> database: {_db.name}")
        return True
    except Exception as exc:
        logger.warning(f"[ImageStorage] MongoDB reconnect failed: {exc}")
        return False


# Firebase Admin (optional)
try:
    import firebase_admin
    from firebase_admin import credentials, firestore

    FIREBASE_CREDS_PATH = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "")
    if FIREBASE_CREDS_PATH and os.path.exists(FIREBASE_CREDS_PATH):
        if not firebase_admin._apps:
            cred = credentials.Certificate(FIREBASE_CREDS_PATH)
            firebase_admin.initialize_app(cred)
        firebase_db = firestore.client()
        logger.info("[ImageStorage] Firebase connected")
    else:
        firebase_db = None
except Exception as e:
    logger.warning(f"[ImageStorage] Firebase not available: {e}")
    firebase_db = None

# Firebase Realtime Database (REST API — no Admin SDK required)
FIREBASE_RTDB_URL = os.getenv("FIREBASE_RTDB_URL", "").rstrip("/")
FIREBASE_DB_SECRET = os.getenv("FIREBASE_DB_SECRET", "")
# Disabled at runtime once we hit a 401/403 — saves writing the same noisy
# warning on every image generation when the DB rules reject anonymous writes.
_RTDB_DISABLED = False


def _rtdb_mark_disabled(reason: str) -> None:
    global _RTDB_DISABLED
    if not _RTDB_DISABLED:
        _RTDB_DISABLED = True
        logger.warning(
            "[RTDB] Disabling Firebase RTDB writes for this session: %s. "
            "Set FIREBASE_DB_SECRET or relax security rules to re-enable.",
            reason,
        )


def _utc_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _rtdb_safe_key(value: str) -> str:
    # RTDB keys cannot contain . $ # [ ] /
    return re.sub(r"[.$#\[\]/]", "_", (value or "").strip())


def _normalize_image_metadata(image_data: dict[str, Any]) -> dict[str, Any]:
    payload = dict(image_data or {})

    drive_url = payload.get("drive_url")
    cloud_url = payload.get("cloud_url") or payload.get("url")
    local_url = payload.get("local_path")
    primary_url = drive_url or cloud_url or local_url

    payload["url"] = cloud_url
    payload["cloud_url"] = cloud_url
    payload["imageURL"] = primary_url
    payload["image_url"] = primary_url
    payload["imageURLs"] = {
        "primary": primary_url,
        "drive": drive_url,
        "imgbb": cloud_url,
        "local": local_url,
    }
    payload["schema_version"] = 2
    payload["updated_at"] = _utc_iso()
    payload["created_at"] = payload.get("created_at") or payload["updated_at"]
    return payload


def archive_legacy_asset(
    *,
    asset_type: str,
    asset_id: str,
    metadata: dict[str, Any] | None = None,
    raw_payload: dict[str, Any] | None = None,
    file_bytes: bytes | None = None,
    filename: str | None = None,
    mime_type: str | None = None,
) -> str | None:
    """Archive full legacy payload + binary file in MongoDB.

    - Metadata + raw payload stored in `raw_legacy_assets`
    - Binary data stored in GridFS (`raw_assets_fs`) when available
    """
    if legacy_assets_collection is None:
        return None

    try:
        doc = {
            "asset_type": asset_type,
            "asset_id": asset_id,
            "filename": filename,
            "mime_type": mime_type,
            "metadata": metadata or {},
            "raw_payload": raw_payload or {},
            "schema_version": 1,
            "created_at": datetime.utcnow(),
        }

        if file_bytes:
            sha256 = hashlib.sha256(file_bytes).hexdigest()
            doc["binary_sha256"] = sha256
            doc["binary_size"] = len(file_bytes)
            if legacy_gridfs is not None:
                fs_id = legacy_gridfs.put(
                    file_bytes,
                    filename=filename or asset_id,
                    contentType=mime_type or "application/octet-stream",
                    asset_type=asset_type,
                    asset_id=asset_id,
                )
                doc["gridfs_id"] = str(fs_id)

        result = legacy_assets_collection.insert_one(doc)
        return str(result.inserted_id)
    except Exception as e:
        logger.warning(f"[MongoDB] Legacy archive failed: {e}")
        return None


def rtdb_push(path: str, data: dict) -> str | None:
    """Push data to Firebase RTDB under the given path (POST → auto key).

    Returns the auto-generated key string, or None on failure.
    Works without a service account — uses DB Secret if set, otherwise
    relies on the RTDB security rules allowing writes.
    """
    if not FIREBASE_RTDB_URL or _RTDB_DISABLED:
        return None
    try:
        url = f"{FIREBASE_RTDB_URL}/{path.strip('/')}.json"
        params = {"auth": FIREBASE_DB_SECRET} if FIREBASE_DB_SECRET else {}
        resp = requests.post(url, json=data, params=params, timeout=10)
        if resp.status_code == 200:
            key = (resp.json() or {}).get("name")
            logger.info(f"[RTDB] Push /{path} → key={key}")
            return key
        if resp.status_code in (401, 403):
            _rtdb_mark_disabled(f"HTTP {resp.status_code} on push")
        else:
            logger.warning(f"[RTDB] Push failed {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"[RTDB] Push error: {e}")
    return None


def rtdb_set(path: str, data: dict) -> bool:
    """Set data at a specific RTDB path (PUT).  Returns True on success."""
    if not FIREBASE_RTDB_URL or _RTDB_DISABLED:
        return False
    try:
        url = f"{FIREBASE_RTDB_URL}/{path.strip('/')}.json"
        params = {"auth": FIREBASE_DB_SECRET} if FIREBASE_DB_SECRET else {}
        resp = requests.put(url, json=data, params=params, timeout=10)
        if resp.status_code == 200:
            logger.info(f"[RTDB] Set /{path}: OK")
            return True
        if resp.status_code in (401, 403):
            _rtdb_mark_disabled(f"HTTP {resp.status_code} on set")
        else:
            logger.warning(f"[RTDB] Set failed {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"[RTDB] Set error: {e}")
    return False


def rtdb_get(path: str) -> dict | None:
    """Read JSON object at a specific RTDB path (GET)."""
    if not FIREBASE_RTDB_URL or _RTDB_DISABLED:
        return None
    try:
        url = f"{FIREBASE_RTDB_URL}/{path.strip('/')}.json"
        params = {"auth": FIREBASE_DB_SECRET} if FIREBASE_DB_SECRET else {}
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code in (401, 403):
            _rtdb_mark_disabled(f"HTTP {resp.status_code} on get")
        else:
            logger.warning(f"[RTDB] Get failed {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"[RTDB] Get error: {e}")
    return None


def rtdb_health() -> dict:
    """Ping Firebase RTDB. Returns {ok: bool, url: str, error: str|None}."""
    if not FIREBASE_RTDB_URL:
        return {"ok": False, "url": "", "error": "FIREBASE_RTDB_URL not configured"}
    try:
        params = (
            {"auth": FIREBASE_DB_SECRET, "shallow": "true"}
            if FIREBASE_DB_SECRET
            else {"shallow": "true"}
        )
        resp = requests.get(f"{FIREBASE_RTDB_URL}/.json", params=params, timeout=8)
        return {
            "ok": resp.status_code == 200,
            "url": FIREBASE_RTDB_URL,
            "error": None if resp.status_code == 200 else f"HTTP {resp.status_code}",
        }
    except Exception as e:
        logger.warning(f"[RTDB] Health check failed: {e}")
        return {"ok": False, "url": FIREBASE_RTDB_URL, "error": "connection failed"}


def upload_to_imgbb(image_base64: str, name: str = None) -> str | None:
    """
    Upload image to ImgBB and return the URL

    Args:
        image_base64: Base64 encoded image data
        name: Optional name for the image

    Returns:
        URL of uploaded image or None if failed
    """
    if not IMGBB_API_KEY:
        logger.warning("[ImgBB] No API key configured")
        return None

    try:
        # Remove data URL prefix if present
        if "base64," in image_base64:
            image_base64 = image_base64.split("base64,")[1]

        payload = {
            "key": IMGBB_API_KEY,
            "image": image_base64,
            "name": name or f"generated_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        }

        response = requests.post(IMGBB_UPLOAD_URL, data=payload, timeout=30)

        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                url = result["data"]["url"]
                logger.info(f"[ImgBB] Image uploaded: {url}")
                return url
            else:
                logger.error(f"[ImgBB] Upload failed: {result}")
        else:
            logger.error(f"[ImgBB] HTTP error: {response.status_code}")

    except Exception as e:
        logger.error(f"[ImgBB] Exception: {e}")

    return None


def upload_to_drive(
    image_base64: str, name: str = None, metadata: dict[str, Any] = None
) -> dict[str, Any]:
    """
    Upload image to Google Drive using Service Account.

    Args:
        image_base64: Base64 encoded image (with or without data URL prefix)
        name: Optional filename
        metadata: Optional metadata dict (for logging only)

    Returns:
        {
            'success': bool,
            'url': webViewLink or None,
            'file_id': Google Drive file ID or None,
            'folder_url': Google Drive folder URL or None,
            'message': error message if failed
        }
    """
    result = {
        "success": False,
        "url": None,
        "file_id": None,
        "folder_url": GOOGLE_DRIVE_FOLDER_URL,
        "message": "",
    }

    # Check if service is available
    if drive_service is None:
        result["message"] = "Google Drive service not initialized"
        return result

    if not GOOGLE_DRIVE_FOLDER_ID:
        result["message"] = "GOOGLE_DRIVE_FOLDER_ID not configured"
        logger.warning("[Drive] GOOGLE_DRIVE_FOLDER_ID not set in .env")
        return result

    try:
        # Clean base64 if needed
        if "base64," in image_base64:
            image_base64 = image_base64.split("base64,")[1]

        # Generate filename
        filename = name or f"generated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

        # Upload to Drive
        drive_result = drive_service.upload_image(image_base64, filename, metadata)

        if drive_result["success"]:
            result.update(
                {
                    "success": True,
                    "url": drive_result["web_view_link"],
                    "file_id": drive_result["file_id"],
                    "message": "Upload successful",
                }
            )
            logger.info(f"[Drive] Image uploaded: {result['file_id']}")
        else:
            result["message"] = drive_result.get("error", "Upload failed")
            logger.warning(f"[Drive] {result['message']}")

    except Exception as e:
        result["message"] = str(e)
        logger.error(f"[Drive] Exception: {e}")

    return result


def save_to_mongodb(image_data: dict[str, Any]) -> str | None:
    """
    Save image metadata to MongoDB

    Args:
        image_data: Dictionary with image metadata

    Returns:
        Document ID or None if failed
    """
    if not images_collection:
        if not _try_connect_mongodb():
            logger.warning("[MongoDB] Not connected and reconnect failed")
            return None

    try:
        image_data["created_at"] = datetime.utcnow()
        result = images_collection.insert_one(image_data)
        logger.info(f"[MongoDB] Image saved: {result.inserted_id}")
        return str(result.inserted_id)
    except Exception as e:
        logger.error(f"[MongoDB] Save error: {e}")
        return None


def save_to_firebase(image_data: dict[str, Any]) -> str | None:
    """
    Save image metadata to Firebase Firestore

    Args:
        image_data: Dictionary with image metadata

    Returns:
        Document ID or None if failed
    """
    if not firebase_db and not FIREBASE_RTDB_URL:
        logger.warning("[Firebase] Not connected (Firestore + RTDB unavailable)")
        return None

    try:
        payload = _normalize_image_metadata(image_data)

        base_id = (
            payload.get("image_id")
            or payload.get("filename")
            or f"img_{int(datetime.utcnow().timestamp())}"
        )
        doc_id = _rtdb_safe_key(str(base_id))

        firestore_ok = False
        if firebase_db is not None:
            firebase_db.collection("generated_images_v2").document(doc_id).set(
                payload, merge=True
            )
            firestore_ok = True

        rtdb_ok = False
        if FIREBASE_RTDB_URL:
            rtdb_ok = rtdb_set(f"generated_images_v2/{doc_id}", payload)
            filename_key = _rtdb_safe_key(payload.get("filename", ""))
            if filename_key:
                rtdb_set(
                    f"generated_images_index/by_filename/{filename_key}",
                    {
                        "doc_id": doc_id,
                        "filename": payload.get("filename"),
                        "updated_at": _utc_iso(),
                    },
                )

        if firestore_ok or rtdb_ok:
            logger.info(
                f"[Firebase] Image saved: {doc_id} (firestore={firestore_ok}, rtdb={rtdb_ok})"
            )
            return doc_id
        logger.warning("[Firebase] Save failed on both Firestore and RTDB")
    except Exception as e:
        logger.error(f"[Firebase] Save error: {e}")
    return None


def store_generated_image(
    image_base64: str,
    prompt: str,
    negative_prompt: str = "",
    metadata: dict[str, Any] = None,
    raw_legacy_payload: dict[str, Any] = None,
) -> dict[str, Any]:
    """
    Store generated image to ImgBB and save metadata to databases

    Args:
        image_base64: Base64 encoded image
        prompt: Generation prompt
        negative_prompt: Negative prompt
        metadata: Additional metadata

    Returns:
        Dictionary with storage results
    """
    result = {
        "success": False,
        "imgbb_url": None,
        "drive_url": None,
        "drive_file_id": None,
        "drive_folder_url": GOOGLE_DRIVE_FOLDER_URL,
        "mongodb_id": None,
        "firebase_id": None,
        "saved_to_mongodb": False,
        "saved_to_firebase": False,
        "legacy_archive_id": None,
    }

    # Upload to ImgBB
    imgbb_url = upload_to_imgbb(image_base64)
    if imgbb_url:
        result["imgbb_url"] = imgbb_url
        result["success"] = True

    drive_result = upload_to_drive(
        image_base64=image_base64,
        name=(metadata or {}).get("filename"),
        metadata=metadata or {},
    )
    if drive_result.get("success"):
        result["drive_url"] = drive_result.get("url")
        result["drive_file_id"] = drive_result.get("file_id")
        result["drive_folder_url"] = (
            drive_result.get("folder_url") or GOOGLE_DRIVE_FOLDER_URL
        )
        result["success"] = True

    # Prepare metadata
    base_metadata = {
        "url": imgbb_url,
        "cloud_url": imgbb_url,
        "drive_url": result["drive_url"],
        "drive_file_id": result["drive_file_id"],
        "drive_folder_url": result["drive_folder_url"],
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "source": "comfyui",
        **(metadata or {}),
    }
    image_metadata = _normalize_image_metadata(base_metadata)

    # Archive raw legacy payload + binary for long-term compatibility
    try:
        raw_b64 = (
            image_base64.split("base64,")[1]
            if "base64," in image_base64
            else image_base64
        )
        image_bytes = base64.b64decode(raw_b64)
        legacy_id = archive_legacy_asset(
            asset_type="image",
            asset_id=str(
                (metadata or {}).get("image_id")
                or (metadata or {}).get("filename")
                or datetime.utcnow().timestamp()
            ),
            metadata=image_metadata,
            raw_payload=raw_legacy_payload
            or {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                **(metadata or {}),
            },
            file_bytes=image_bytes,
            filename=(metadata or {}).get("filename"),
            mime_type="image/png",
        )
        if legacy_id:
            image_metadata["legacy_archive_id"] = legacy_id
            result["legacy_archive_id"] = legacy_id
    except Exception as e:
        logger.warning(f"[ImageStorage] Legacy archive image failed: {e}")

    # Save to MongoDB
    mongo_id = save_to_mongodb(image_metadata.copy())
    if mongo_id:
        result["mongodb_id"] = mongo_id
        result["saved_to_mongodb"] = True

    # Save to Firebase
    firebase_id = save_to_firebase(image_metadata.copy())
    if firebase_id:
        result["firebase_id"] = firebase_id
        result["saved_to_firebase"] = True

    logger.info(f"[ImageStorage] Storage result: {result}")
    return result


def get_images_from_cloud(limit: int = 50) -> list:
    """
    Get images from cloud storage (MongoDB or Firebase)

    Args:
        limit: Maximum number of images to return

    Returns:
        List of image metadata
    """
    images = []

    # Try MongoDB first
    if images_collection:
        try:
            cursor = images_collection.find().sort("created_at", -1).limit(limit)
            for doc in cursor:
                doc["_id"] = str(doc["_id"])
                images.append(doc)
            if images:
                return images
        except Exception as e:
            logger.error(f"[MongoDB] Query error: {e}")

    # Fallback to Firebase Firestore
    if firebase_db:
        try:
            docs = (
                firebase_db.collection("generated_images_v2")
                .order_by("created_at", direction="DESCENDING")
                .limit(limit)
                .stream()
            )
            for doc in docs:
                data = doc.to_dict()
                data["id"] = doc.id
                images.append(data)
            if images:
                return images
        except Exception as e:
            logger.error(f"[Firebase] Query error: {e}")

    # Last fallback: RTDB generated_images_v2
    if FIREBASE_RTDB_URL:
        try:
            raw = rtdb_get("generated_images_v2") or {}
            if isinstance(raw, dict):
                items = list(raw.items())
                items.sort(
                    key=lambda kv: (kv[1] or {}).get("created_at", ""), reverse=True
                )
                for doc_id, data in items[:limit]:
                    row = data or {}
                    row["id"] = doc_id
                    images.append(row)
        except Exception as e:
            logger.error(f"[RTDB] Query error: {e}")

    return images
