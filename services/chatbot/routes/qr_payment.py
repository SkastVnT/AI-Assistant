"""
QR Payment Routes
Generates VietQR payment QR codes for video unlock / image quota purchase.
Sensitive config loaded from private/payment_config.py
"""
import sys
import logging
from pathlib import Path
from flask import Blueprint, request, jsonify, session, redirect

CHATBOT_DIR = Path(__file__).parent.parent.resolve()
if str(CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(CHATBOT_DIR))

logger = logging.getLogger(__name__)
qr_bp = Blueprint("qr_payment", __name__)


def _load_payment_cfg():
    try:
        sys.path.insert(0, str(CHATBOT_DIR / "private"))
        from payment_config import (
            VIDEO_UNLOCK_PRICE, IMAGE_EXTRA_PRICE, IMAGE_EXTRA_QUOTA,
            ACCOUNT_NAME_DISPLAY, ACCOUNT_NO, BANK_ID, build_qr_url,
        )
        return {
            "video_price": VIDEO_UNLOCK_PRICE,
            "image_extra_price": IMAGE_EXTRA_PRICE,
            "image_extra_quota": IMAGE_EXTRA_QUOTA,
            "account_name": ACCOUNT_NAME_DISPLAY,
            "account_no": ACCOUNT_NO,
            "bank_id": BANK_ID,
            "build_qr_url": build_qr_url,
        }
    except Exception as e:
        logger.warning(f"[QR] Cannot load payment_config: {e}")
        return None


def _get_db():
    try:
        from core.extensions import get_db
        return get_db()
    except Exception:
        return None


def _require_auth():
    if not session.get("authenticated"):
        return jsonify({"success": False, "message": "Chưa đăng nhập"}), 401
    return None


@qr_bp.route("/api/payment/info", methods=["GET"])
def payment_info():
    """Return payment info (prices, bank account) for the frontend."""
    err = _require_auth()
    if err:
        return err

    from core.feature_flags import features
    if not features.payment_enabled:
        return jsonify({"success": False, "message": "Tính năng thanh toán đã bị tắt"}), 403

    cfg = _load_payment_cfg()
    if not cfg:
        return jsonify({"success": False, "message": "Cấu hình thanh toán chưa được thiết lập"}), 500

    username = session.get("username", "")
    db = _get_db()

    # Get user's current quota/video status
    video_unlocked = False
    if db:
        try:
            from core.user_auth import check_video_access, get_user_quota
            video_unlocked, _ = check_video_access(db, username)
            quota = get_user_quota(db, username)
        except Exception:
            quota = {}
    else:
        quota = {}

    return jsonify({
        "success": True,
        "account_no": cfg["account_no"],
        "account_name": cfg["account_name"],
        "bank_id": cfg["bank_id"],
        "bank_name": "Vietcombank",
        "prices": {
            "video_unlock": cfg["video_price"],
            "image_extra": cfg["image_extra_price"],
            "image_extra_quota": cfg["image_extra_quota"],
        },
        "user_status": {
            "video_unlocked": video_unlocked,
            "image_quota_used": quota.get("image_quota_used", 0),
            "image_quota_limit": quota.get("image_quota_limit", 5),
        },
    })


@qr_bp.route("/api/payment/qr", methods=["POST"])
def generate_qr():
    """
    Generate a VietQR URL for a payment.
    Body: { "type": "video_unlock" | "image_extra", "amount": int (optional override) }
    Returns: { "qr_url": "https://img.vietqr.io/...", "amount": int, "description": str }
    """
    err = _require_auth()
    if err:
        return err

    from core.feature_flags import features
    if not features.qr_enabled:
        return jsonify({"success": False, "message": "QR generation bị tắt"}), 403

    cfg = _load_payment_cfg()
    if not cfg:
        return jsonify({"success": False, "message": "Cấu hình thanh toán chưa thiết lập"}), 500

    data = request.json or {}
    pay_type = data.get("type", "video_unlock")
    username = session.get("username", "unknown")

    if pay_type == "video_unlock":
        amount = int(data.get("amount") or cfg["video_price"])
        description = f"Mo khoa video {username}"
        label = "Mở khóa Video"
    elif pay_type == "image_extra":
        amount = int(data.get("amount") or cfg["image_extra_price"])
        description = f"Nap them anh {username}"
        label = f"+{cfg['image_extra_quota']} lượt tạo ảnh"
    elif pay_type == "custom":
        amount = max(1000, int(data.get("amount", 10000)))
        description = data.get("description", f"Thanh toan {username}")[:50]
        label = "Thanh toán tùy chỉnh"
    else:
        return jsonify({"success": False, "message": "Invalid type"}), 400

    qr_url = cfg["build_qr_url"](amount, description)

    # Optionally create a pending payment request in DB
    if pay_type == "video_unlock":
        db = _get_db()
        if db:
            try:
                from core.user_auth import create_payment_request
                create_payment_request(db, username, note=f"amount={amount}")
            except Exception as e:
                logger.warning(f"[QR] Could not create payment request: {e}")

    logger.info(f"[QR] Generated QR for {username}: type={pay_type}, amount={amount}")
    return jsonify({
        "success": True,
        "qr_url": qr_url,
        "amount": amount,
        "description": description,
        "label": label,
        "account_no": cfg["account_no"],
        "account_name": cfg["account_name"],
        "bank_name": "Vietcombank",
    })
